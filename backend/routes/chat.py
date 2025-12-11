"""
Chat API routes and WebSocket endpoint.
Handles real-time messaging, file uploads, and reactions.
"""

import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, status
from pydantic import BaseModel

from config import settings
from models.message import (
    MessageCreate, MessagePublic, MessageType, ReactionType,
    ReactionCreate, ReactionRemove, ChatHistory, WebSocketMessage
)
from services.message_service import message_service
from services.room_service import room_service
from services.bot_service import bot_service
from ws.connection_manager import connection_manager


router = APIRouter(prefix="/chat", tags=["chat"])


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    room_id: int
    sender_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    reply_to_id: Optional[str] = None
    mention_bot: bool = False


class SendMessageResponse(BaseModel):
    """Response after sending a message."""
    message: MessagePublic
    bot_response: Optional[MessagePublic] = None


@router.post("/send", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Send a text message to a room.
    
    If mention_bot is True, the bot will respond.
    """
    try:
        # Create message
        message_data = MessageCreate(
            room_id=request.room_id,
            sender_id=request.sender_id,
            content=request.content,
            message_type=request.message_type,
            reply_to_id=request.reply_to_id
        )
        
        message = await message_service.create_message(message_data)
        message_public = MessagePublic.from_message(message)
        
        # Broadcast to room
        await connection_manager.broadcast_to_room(
            request.room_id,
            WebSocketMessage(
                event="new_message",
                data=message_public.model_dump(),
                room_id=request.room_id,
                sender_id=request.sender_id
            )
        )
        
        # Generate bot response if mentioned
        bot_response = None
        if request.mention_bot:
            bot_text = await bot_service.generate_response(
                request.room_id,
                request.content,
                request.sender_id
            )
            
            bot_message = await message_service.create_bot_message(
                room_id=request.room_id,
                content=bot_text,
                reply_to_id=message.id
            )
            
            bot_response = MessagePublic.from_message(bot_message)
            
            # Broadcast bot response
            await connection_manager.broadcast_to_room(
                request.room_id,
                WebSocketMessage(
                    event="new_message",
                    data=bot_response.model_dump(),
                    room_id=request.room_id,
                    sender_id="bot"
                )
            )
        
        return SendMessageResponse(
            message=message_public,
            bot_response=bot_response
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/upload")
async def upload_media(
    room_id: int = Form(...),
    sender_id: str = Form(...),
    file: UploadFile = File(...),
    view_once: bool = Form(False),
    caption: str = Form("")
):
    """
    Upload media (image or audio) to a room.
    
    Files are encrypted server-side before storage.
    Max file size: 5MB
    """
    try:
        # Read file content
        content = await file.read()
        
        # Upload and encrypt
        storage_path, is_encrypted = await message_service.upload_media(
            room_id=room_id,
            sender_id=sender_id,
            content=content,
            content_type=file.content_type,
            filename=file.filename,
            view_once=view_once
        )
        
        # Determine message type
        message_type = MessageType.IMAGE if "image" in file.content_type else MessageType.AUDIO
        
        # Create message
        message_data = MessageCreate(
            room_id=room_id,
            sender_id=sender_id,
            content=caption or f"[{message_type.value}]",
            message_type=message_type,
            media_url=storage_path,
            media_encrypted=is_encrypted,
            view_once=view_once
        )
        
        message = await message_service.create_message(message_data)
        message_public = MessagePublic.from_message(message)
        
        # Broadcast to room
        await connection_manager.broadcast_to_room(
            room_id,
            WebSocketMessage(
                event="new_message",
                data=message_public.model_dump(),
                room_id=room_id,
                sender_id=sender_id
            )
        )
        
        return {
            "message": message_public,
            "uploaded": True,
            "encrypted": is_encrypted,
            "view_once": view_once
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/view-once/{message_id}")
async def view_once_message(message_id: str, viewer_id: str):
    """
    View a view-once message.
    
    The message is decrypted and immediately deleted after viewing.
    Only the recipient (not the sender) can view.
    """
    try:
        content, result = await message_service.view_once_message(message_id, viewer_id)
        
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result
            )
        
        # Return decrypted content
        import base64
        return {
            "content": base64.b64encode(content).decode('utf-8'),
            "viewed": True,
            "message": "This message has been deleted after viewing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/history/{room_id}", response_model=ChatHistory)
async def get_chat_history(
    room_id: int,
    limit: int = 50,
    before: Optional[str] = None
):
    """
    Get chat history for a room with pagination.
    
    Args:
        room_id: Room to get history for
        limit: Maximum messages to return (default 50)
        before: Get messages before this ISO timestamp
    """
    try:
        before_timestamp = None
        if before:
            before_timestamp = datetime.fromisoformat(before)
        
        history = await message_service.get_room_messages(
            room_id,
            limit=limit,
            before_timestamp=before_timestamp
        )
        
        return history
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/reaction")
async def add_reaction(reaction: ReactionCreate, user_id: str):
    """
    Add a reaction to a message.
    
    Supported reactions: heart, laugh, cry, shocked, angry
    """
    try:
        message = await message_service.add_reaction(
            reaction.message_id,
            user_id,
            reaction.reaction_type
        )
        
        # Broadcast reaction update
        await connection_manager.broadcast_to_room(
            message.room_id,
            WebSocketMessage(
                event="reaction_added",
                data={
                    "message_id": reaction.message_id,
                    "user_id": user_id,
                    "reaction_type": reaction.reaction_type.value,
                    "reactions": message.reactions
                },
                room_id=message.room_id,
                sender_id=user_id
            )
        )
        
        return {"success": True, "reactions": message.reactions}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/reaction")
async def remove_reaction(reaction: ReactionRemove, user_id: str):
    """
    Remove a reaction from a message.
    """
    try:
        message = await message_service.remove_reaction(
            reaction.message_id,
            user_id,
            reaction.reaction_type
        )
        
        # Broadcast reaction update
        await connection_manager.broadcast_to_room(
            message.room_id,
            WebSocketMessage(
                event="reaction_removed",
                data={
                    "message_id": reaction.message_id,
                    "user_id": user_id,
                    "reaction_type": reaction.reaction_type.value,
                    "reactions": message.reactions
                },
                room_id=message.room_id,
                sender_id=user_id
            )
        )
        
        return {"success": True, "reactions": message.reactions}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/history/{room_id}")
async def clear_chat_history(room_id: int):
    """
    Clear all messages in a room.
    
    This does not affect memories - use /rooms/{room_id}/reset-memory for that.
    """
    try:
        count = await message_service.delete_room_messages(room_id)
        
        # Notify room
        await connection_manager.broadcast_to_room(
            room_id,
            WebSocketMessage(
                event="history_cleared",
                data={"room_id": room_id, "cleared_count": count},
                room_id=room_id
            )
        )
        
        return {
            "message": "Chat history cleared",
            "room_id": room_id,
            "messages_deleted": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ==================== WebSocket Endpoint ====================

@router.websocket("/ws/{room_id}/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    user_id: str,
    device_id: str = "default"
):
    """
    WebSocket endpoint for real-time chat.
    
    Events sent:
    - new_message: New message in room
    - user_joined: User joined the room
    - user_left: User left the room
    - typing_status: User typing indicator
    - reaction_added: Reaction added to message
    - reaction_removed: Reaction removed from message
    - consent_updated: NSFW consent status changed
    - history_cleared: Chat history was cleared
    - room_closed: Room was deleted/closed
    
    Events received:
    - message: Send a new message
    - typing: Update typing status
    - reaction: Add/remove reaction
    """
    try:
        # Connect
        session = await connection_manager.connect(
            websocket,
            room_id,
            user_id,
            device_id
        )
        
        # Update user online status
        await room_service.update_user_online_status(user_id, True)
        
        # Main message loop
        while True:
            try:
                data = await websocket.receive_text()
                event_data = json.loads(data)
                
                event_type = event_data.get("event")
                payload = event_data.get("data", {})
                
                if event_type == "message":
                    # Handle new message
                    content = payload.get("content", "")
                    message_type = MessageType(payload.get("type", "text"))
                    reply_to = payload.get("reply_to_id")
                    mention_bot = payload.get("mention_bot", False)
                    
                    message_data = MessageCreate(
                        room_id=room_id,
                        sender_id=user_id,
                        content=content,
                        message_type=message_type,
                        reply_to_id=reply_to
                    )
                    
                    message = await message_service.create_message(message_data)
                    message_public = MessagePublic.from_message(message)
                    
                    # Broadcast message
                    await connection_manager.broadcast_to_room(
                        room_id,
                        WebSocketMessage(
                            event="new_message",
                            data=message_public.model_dump(),
                            room_id=room_id,
                            sender_id=user_id
                        )
                    )
                    
                    # Generate bot response if mentioned
                    if mention_bot or content.lower().startswith("@bot"):
                        bot_text = await bot_service.generate_response(
                            room_id,
                            content,
                            user_id
                        )
                        
                        bot_message = await message_service.create_bot_message(
                            room_id=room_id,
                            content=bot_text,
                            reply_to_id=message.id
                        )
                        
                        bot_public = MessagePublic.from_message(bot_message)
                        
                        await connection_manager.broadcast_to_room(
                            room_id,
                            WebSocketMessage(
                                event="new_message",
                                data=bot_public.model_dump(),
                                room_id=room_id,
                                sender_id="bot"
                            )
                        )
                
                elif event_type == "typing":
                    # Handle typing indicator
                    is_typing = payload.get("is_typing", False)
                    await connection_manager.set_typing(room_id, user_id, is_typing)
                
                elif event_type == "reaction":
                    # Handle reaction
                    message_id = payload.get("message_id")
                    reaction_type = ReactionType(payload.get("reaction_type"))
                    action = payload.get("action", "add")
                    
                    if action == "add":
                        message = await message_service.add_reaction(
                            message_id, user_id, reaction_type
                        )
                        event_name = "reaction_added"
                    else:
                        message = await message_service.remove_reaction(
                            message_id, user_id, reaction_type
                        )
                        event_name = "reaction_removed"
                    
                    await connection_manager.broadcast_to_room(
                        room_id,
                        WebSocketMessage(
                            event=event_name,
                            data={
                                "message_id": message_id,
                                "user_id": user_id,
                                "reaction_type": reaction_type.value,
                                "reactions": message.reactions
                            },
                            room_id=room_id,
                            sender_id=user_id
                        )
                    )
                
            except json.JSONDecodeError:
                # Invalid JSON, ignore
                continue
                
    except WebSocketDisconnect:
        # Handle disconnect
        session = await connection_manager.disconnect(websocket)
        if session:
            await room_service.update_user_online_status(session.user_id, False)
    
    except Exception as e:
        # Handle other errors
        await connection_manager.disconnect(websocket)
        raise
