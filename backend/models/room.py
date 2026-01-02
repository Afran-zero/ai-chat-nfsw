"""
Room models for chat room management.
Handles room creation, settings, consent, and lifecycle.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from models.user import UserPublic


class RoomStatus(str, Enum):
    """Room lifecycle status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class NSFWMode(str, Enum):
    """NSFW content mode."""
    DISABLED = "disabled"
    ENABLED = "enabled"
    INTIMATE = "intimate"


class Room(BaseModel):
    """
    Complete room data model.
    Used for database operations.
    """
    id: int
    name: str
    secret_hash: str
    status: RoomStatus
    nsfw_mode: NSFWMode = NSFWMode.DISABLED
    partner_a_nsfw_consent: bool = False
    partner_b_nsfw_consent: bool = False
    created_at: datetime
    last_activity_at: Optional[datetime] = None
    onboarding_data: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class RoomCreate(BaseModel):
    """
    Request to create a new room.
    """
    name: str = Field(..., min_length=1, max_length=100)
    creator_nickname: str = Field(..., min_length=1, max_length=50)
    device_id: str
    room_secret: Optional[str] = None  # If not provided, will be generated


class RoomJoin(BaseModel):
    """
    Request to join an existing room.
    """
    room_name: str = Field(..., min_length=1, max_length=100)
    room_secret: str
    nickname: str = Field(..., min_length=1, max_length=50)
    device_id: str


class RoomPublic(BaseModel):
    """
    Public room information.
    Exposed in API responses without sensitive data.
    """
    id: int
    name: str
    status: RoomStatus
    nsfw_mode: NSFWMode
    users: List[UserPublic]
    created_at: datetime
    last_activity_at: Optional[datetime] = None


class RoomSettings(BaseModel):
    """
    Room configuration settings.
    """
    bot_personality: Optional[str] = None
    auto_delete_messages: bool = False
    message_retention_days: Optional[int] = None
    allow_media: bool = True
    max_file_size_mb: int = 5
    language: str = "en"


class RoomOnboarding(BaseModel):
    """
    Onboarding/relationship information.
    Helps personalize bot responses.
    """
    relationship_type: Optional[str] = None  # e.g., "romantic", "friendship", "casual"
    relationship_duration: Optional[str] = None  # e.g., "2 years", "new"
    communication_style: Optional[str] = None  # e.g., "casual", "formal", "flirty"
    interests: Optional[List[str]] = None
    boundaries: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None


class ConsentRequest(BaseModel):
    """
    Request to update NSFW consent.
    """
    user_id: str
    consent: bool


class ConsentStatus(BaseModel):
    """
    Current NSFW consent status for a room.
    """
    room_id: int
    nsfw_mode: NSFWMode
    partner_a_consent: bool
    partner_b_consent: bool
    both_consented: bool
