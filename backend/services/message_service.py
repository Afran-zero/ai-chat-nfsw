"""
Message service for chat message operations.
Handles message creation, retrieval, reactions, and media.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Tuple
import base64

from config import settings
from core.encryption import get_encryption_service
from core.security import security_service, ContentCategory
from core.supabase_client import supabase
from models.message import (
    Message, MessageCreate, MessagePublic, MessageType,
    ReactionType, Reaction, ChatHistory
)


class MessageService:
    """Service for message operations."""
    
    TABLE_MESSAGES = "messages"
    TABLE_REACTIONS = "reactions"
    
    async def create_message(self, data: MessageCreate) -> Message:
        """
        Create a new message.
        
        Args:
            data: Message creation data
            
        Returns:
            Created message
        """
        message_data = {
            "id": str(uuid.uuid4()),
            "room_id": data.room_id,
            "sender_id": data.sender_id,
            "content": data.content,
            "message_type": data.message_type.value,
            "media_url": data.media_url,
            "media_encrypted": data.media_encrypted,
            "view_once": data.view_once,
            "view_once_viewed": False,
            "reply_to_id": data.reply_to_id,
            "reactions": {},
            "is_remembered": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        result = await supabase.insert(self.TABLE_MESSAGES, message_data)
        return Message(**result)
    
    async def create_bot_message(
        self,
        room_id: int,
        content: str,
        reply_to_id: Optional[str] = None
    ) -> Message:
        """
        Create a bot response message.
        
        Args:
            room_id: Room identifier
            content: Bot response content
            reply_to_id: Optional message being replied to
            
        Returns:
            Created bot message
        """
        message_data = {
            "id": str(uuid.uuid4()),
            "room_id": room_id,
            "sender_id": "bot",
            "content": content,
            "message_type": MessageType.BOT.value,
            "view_once": False,
            "view_once_viewed": False,
            "reply_to_id": reply_to_id,
            "reactions": {},
            "is_remembered": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        result = await supabase.insert(self.TABLE_MESSAGES, message_data)
        return Message(**result)
    
    async def get_message(self, message_id: str) -> Optional[Message]:
        """
        Get a message by ID.
        
        Args:
            message_id: Message identifier
            
        Returns:
            Message or None
        """
        result = await supabase.select(
            self.TABLE_MESSAGES,
            filters={"id": message_id}
        )
        
        if result:
            return Message(**result[0])
        return None
    
    async def get_room_messages(
        self,
        room_id: int,
        limit: int = 50,
        before_timestamp: Optional[datetime] = None
    ) -> ChatHistory:
        """
        Get messages for a room with pagination.
        
        Args:
            room_id: Room identifier
            limit: Maximum messages to return
            before_timestamp: Get messages before this time
            
        Returns:
            ChatHistory with messages and pagination info
        """
        query = supabase.table(self.TABLE_MESSAGES).select("*").eq("room_id", room_id)
        
        if before_timestamp:
            query = query.lt("created_at", before_timestamp.isoformat())
        
        query = query.order("created_at", desc=True).limit(limit + 1)
        result = query.execute()
        
        messages_data = result.data or []
        has_more = len(messages_data) > limit
        
        if has_more:
            messages_data = messages_data[:limit]
        
        messages = [Message(**m) for m in messages_data]
        messages.reverse()  # Oldest first
        
        public_messages = [MessagePublic.from_message(m) for m in messages]
        
        return ChatHistory(
            messages=public_messages,
            has_more=has_more,
            oldest_timestamp=messages[0].created_at if messages else None
        )
    
    async def get_recent_messages(
        self,
        room_id: int,
        limit: int = 20
    ) -> List[Message]:
        """
        Get recent messages for AI context.
        
        Args:
            room_id: Room identifier
            limit: Number of messages
            
        Returns:
            List of recent messages
        """
        result = await supabase.select(
            self.TABLE_MESSAGES,
            filters={"room_id": room_id},
            order_by="created_at",
            descending=True,
            limit=limit
        )
        
        messages = [Message(**m) for m in result]
        messages.reverse()
        return messages
    
    async def add_reaction(
        self,
        message_id: str,
        user_id: str,
        reaction_type: ReactionType
    ) -> Message:
        """
        Add a reaction to a message.
        
        Args:
            message_id: Message identifier
            user_id: User adding reaction
            reaction_type: Type of reaction
            
        Returns:
            Updated message
        """
        message = await self.get_message(message_id)
        if not message:
            raise ValueError("Message not found")
        
        reactions = message.reactions.copy()
        reaction_key = reaction_type.value
        
        if reaction_key not in reactions:
            reactions[reaction_key] = []
        
        if user_id not in reactions[reaction_key]:
            reactions[reaction_key].append(user_id)
        
        await supabase.update(
            self.TABLE_MESSAGES,
            {"reactions": reactions, "updated_at": datetime.utcnow().isoformat()},
            {"id": message_id}
        )
        
        message.reactions = reactions
        return message
    
    async def remove_reaction(
        self,
        message_id: str,
        user_id: str,
        reaction_type: ReactionType
    ) -> Message:
        """
        Remove a reaction from a message.
        
        Args:
            message_id: Message identifier
            user_id: User removing reaction
            reaction_type: Type of reaction
            
        Returns:
            Updated message
        """
        message = await self.get_message(message_id)
        if not message:
            raise ValueError("Message not found")
        
        reactions = message.reactions.copy()
        reaction_key = reaction_type.value
        
        if reaction_key in reactions and user_id in reactions[reaction_key]:
            reactions[reaction_key].remove(user_id)
            if not reactions[reaction_key]:
                del reactions[reaction_key]
        
        await supabase.update(
            self.TABLE_MESSAGES,
            {"reactions": reactions, "updated_at": datetime.utcnow().isoformat()},
            {"id": message_id}
        )
        
        message.reactions = reactions
        return message
    
    async def view_once_message(
        self,
        message_id: str,
        viewer_id: str
    ) -> Tuple[Optional[bytes], str]:
        """
        View a view-once message and mark it as viewed.
        
        Args:
            message_id: Message identifier
            viewer_id: User viewing the message
            
        Returns:
            Tuple of (decrypted_content, content_type) or (None, error)
        """
        message = await self.get_message(message_id)
        
        if not message:
            return None, "Message not found"
        
        if not message.view_once:
            return None, "Not a view-once message"
        
        if message.view_once_viewed:
            return None, "Message already viewed"
        
        if message.sender_id == viewer_id:
            return None, "Cannot view your own view-once message"
        
        # Download and decrypt media
        try:
            encrypted_data = await supabase.download_file(message.media_url)
            
            if message.media_encrypted:
                encryption = get_encryption_service()
                decrypted = encryption.decrypt_from_base64(
                    encrypted_data.decode('utf-8')
                )
            else:
                decrypted = encrypted_data
            
            # Mark as viewed
            await supabase.update(
                self.TABLE_MESSAGES,
                {
                    "view_once_viewed": True,
                    "view_once_viewed_at": datetime.utcnow().isoformat()
                },
                {"id": message_id}
            )
            
            # Delete from storage after viewing
            await supabase.delete_file([message.media_url])
            
            return decrypted, "success"
            
        except Exception as e:
            return None, str(e)
    
    async def upload_media(
        self,
        room_id: int,
        sender_id: str,
        content: bytes,
        content_type: str,
        filename: str,
        view_once: bool = False
    ) -> Tuple[str, bool]:
        """
        Upload and encrypt media for a message.
        
        Args:
            room_id: Room identifier
            sender_id: Sender identifier
            content: File content
            content_type: MIME type
            filename: Original filename
            view_once: Whether this is a view-once image
            
        Returns:
            Tuple of (storage_path, is_encrypted)
        """
        # Validate file
        is_valid, error = security_service.validate_file(content, content_type, filename)
        if not is_valid:
            raise ValueError(error)
        
        # Sanitize filename
        safe_filename = security_service.sanitize_filename(filename)
        
        # Generate storage path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        storage_path = f"rooms/{room_id}/{sender_id}/{timestamp}_{safe_filename}"
        
        # Encrypt media
        encryption = get_encryption_service()
        encrypted_data = encryption.encrypt_to_base64(content)
        
        # Upload to storage
        await supabase.upload_file(
            storage_path,
            encrypted_data.encode('utf-8'),
            "application/octet-stream"
        )
        
        return storage_path, True
    
    async def mark_message_remembered(
        self,
        message_id: str,
        category: str
    ) -> Message:
        """
        Mark a message as remembered.
        
        Args:
            message_id: Message identifier
            category: Memory category
            
        Returns:
            Updated message
        """
        await supabase.update(
            self.TABLE_MESSAGES,
            {
                "is_remembered": True,
                "memory_category": category,
                "updated_at": datetime.utcnow().isoformat()
            },
            {"id": message_id}
        )
        
        return await self.get_message(message_id)
    
    async def delete_room_messages(self, room_id: int) -> int:
        """
        Delete all messages in a room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Number of deleted messages
        """
        # Get message count first
        messages = await supabase.select(
            self.TABLE_MESSAGES,
            columns="id",
            filters={"room_id": room_id}
        )
        
        count = len(messages)
        
        # Delete messages
        await supabase.delete(self.TABLE_MESSAGES, {"room_id": room_id})
        
        return count
    
    async def check_content_safety(self, content: str) -> ContentCategory:
        """
        Check message content for safety.
        
        Args:
            content: Message content
            
        Returns:
            Content safety category
        """
        return security_service.check_content_safety(content)


# Singleton instance
message_service = MessageService()
