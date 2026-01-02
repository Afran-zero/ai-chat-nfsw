"""
User models for room participants.
Handles user roles, sessions, and public profiles.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles in a room."""
    PARTNER_A = "partner_a"
    PARTNER_B = "partner_b"


class UserInRoom(BaseModel):
    """
    User participant in a room.
    Full data model for database operations.
    """
    id: str
    room_id: int
    nickname: str
    device_id: str
    role: UserRole
    is_online: bool = False
    last_seen: datetime
    avatar_url: Optional[str] = None
    nsfw_consent: bool = False
    nsfw_consent_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserPublic(BaseModel):
    """
    Public user information.
    Exposed in API responses without sensitive data.
    """
    id: str
    nickname: str
    avatar_url: Optional[str] = None
    is_online: bool = False
    last_seen: datetime


class UserSession(BaseModel):
    """
    WebSocket session information.
    Tracks active connections and user presence.
    """
    user_id: str
    room_id: int
    device_id: str
    connected_at: datetime
    
    class Config:
        from_attributes = True
