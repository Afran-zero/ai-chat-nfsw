"""
Models package for FastAPI application.
Contains Pydantic models for request/response validation.
"""

from models.user import UserInRoom, UserRole, UserPublic, UserSession
from models.room import (
    Room, RoomCreate, RoomJoin, RoomPublic, RoomSettings, 
    RoomOnboarding, ConsentRequest, ConsentStatus, NSFWMode, RoomStatus
)
from models.message import (
    Message, MessageCreate, MessagePublic, MessageType,
    WebSocketMessage, MemoryEntry, MemoryCategory, MemorySearchResult,
    ReactionType, Reaction, ChatHistory, RememberRequest,
    ReactionCreate, ReactionRemove
)

__all__ = [
    # User models
    "UserInRoom",
    "UserRole",
    "UserPublic",
    "UserSession",
    # Room models
    "Room",
    "RoomCreate",
    "RoomJoin",
    "RoomPublic",
    "RoomSettings",
    "RoomOnboarding",
    "ConsentRequest",
    "ConsentStatus",
    "NSFWMode",
    "RoomStatus",
    # Message models
    "Message",
    "MessageCreate",
    "MessagePublic",
    "MessageType",
    "WebSocketMessage",
    "MemoryEntry",
    "MemoryCategory",
    "MemorySearchResult",
    "ReactionType",
    "Reaction",
    "ChatHistory",
    "RememberRequest",
    "ReactionCreate",
    "ReactionRemove",
]
