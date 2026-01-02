"""
Message models for chat messages, reactions, and memories.
Handles text, media, bot responses, and vector memory storage.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Message content type."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    BOT = "bot"
    SYSTEM = "system"


class ReactionType(str, Enum):
    """Message reaction types."""
    HEART = "heart"
    LAUGH = "laugh"
    CRY = "cry"
    SHOCKED = "shocked"
    ANGRY = "angry"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class MemoryCategory(str, Enum):
    """Categories for remembered information."""
    PREFERENCE = "preference"
    FACT = "fact"
    EMOTION = "emotion"
    RELATIONSHIP = "relationship"
    EXPERIENCE = "experience"
    BOUNDARY = "boundary"
    GENERAL = "general"


class Message(BaseModel):
    """
    Complete message data model.
    Used for database operations.
    """
    id: str
    room_id: int
    sender_id: str  # User ID or "bot" for bot messages
    content: str
    message_type: MessageType = MessageType.TEXT
    media_url: Optional[str] = None
    media_encrypted: bool = False
    view_once: bool = False
    view_once_viewed: bool = False
    reply_to_id: Optional[str] = None
    reactions: Dict[str, List[str]] = Field(default_factory=dict)  # reaction_type -> [user_ids]
    is_remembered: bool = False
    memory_category: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """
    Request to create a new message.
    """
    room_id: int
    sender_id: str
    content: str
    message_type: MessageType = MessageType.TEXT
    media_url: Optional[str] = None
    media_encrypted: bool = False
    view_once: bool = False
    reply_to_id: Optional[str] = None


class MessagePublic(BaseModel):
    """
    Public message information.
    Exposed in API responses and WebSocket events.
    """
    id: str
    room_id: int
    sender_id: str
    content: str
    message_type: MessageType
    media_url: Optional[str] = None
    view_once: bool = False
    view_once_viewed: bool = False
    reply_to_id: Optional[str] = None
    reactions: Dict[str, List[str]] = Field(default_factory=dict)
    is_remembered: bool = False
    memory_category: Optional[str] = None
    created_at: datetime
    
    @classmethod
    def from_message(cls, message: Message) -> "MessagePublic":
        """Create MessagePublic from Message model."""
        return cls(
            id=message.id,
            room_id=message.room_id,
            sender_id=message.sender_id,
            content=message.content,
            message_type=message.message_type,
            media_url=message.media_url,
            view_once=message.view_once,
            view_once_viewed=message.view_once_viewed,
            reply_to_id=message.reply_to_id,
            reactions=message.reactions,
            is_remembered=message.is_remembered,
            memory_category=message.memory_category,
            created_at=message.created_at
        )


class WebSocketMessage(BaseModel):
    """
    WebSocket event message format.
    Used for real-time communication.
    """
    event: str  # Event type: new_message, reaction_added, user_joined, typing, etc.
    data: Dict[str, Any]  # Event payload
    room_id: int
    sender_id: Optional[str] = None  # User who triggered the event
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MemoryEntry(BaseModel):
    """
    Vector memory entry for ChromaDB.
    Stores remembered information with embeddings.
    """
    id: str
    text: str
    room_id: int
    sender_id: str
    category: MemoryCategory
    message_id: Optional[str] = None
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_chroma_metadata(self) -> Dict[str, Any]:
        """Convert to ChromaDB metadata format."""
        return {
            "room_id": self.room_id,
            "sender_id": self.sender_id,
            "category": self.category.value,
            "message_id": self.message_id or "",
            "timestamp": self.timestamp.isoformat(),
            **self.metadata
        }


class MemorySearchResult(BaseModel):
    """
    Result from memory vector search.
    """
    memory_id: str
    text: str
    category: MemoryCategory
    sender_id: str
    similarity: float  # Cosine similarity score
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Reaction(BaseModel):
    """
    Single reaction on a message.
    """
    user_id: str
    reaction_type: ReactionType
    created_at: datetime


class ReactionCreate(BaseModel):
    """
    Request to add a reaction.
    """
    message_id: str
    reaction_type: ReactionType


class ReactionRemove(BaseModel):
    """
    Request to remove a reaction.
    """
    message_id: str
    reaction_type: ReactionType


class RememberRequest(BaseModel):
    """
    Request to remember a message.
    """
    message_id: str
    category: MemoryCategory
    custom_note: Optional[str] = None  # Optional custom text instead of message content


class ChatHistory(BaseModel):
    """
    Paginated chat history response.
    """
    messages: List[MessagePublic]
    has_more: bool
    oldest_timestamp: Optional[datetime] = None
