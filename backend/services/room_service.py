"""
Room service for managing chat rooms.
Handles room creation, joining, and lifecycle management.
"""

import uuid
from datetime import datetime
from typing import Optional, Tuple

from config import settings
from core.security import SecurityService, security_service
from core.supabase_client import supabase
from models.room import (
    Room, RoomCreate, RoomJoin, RoomPublic, RoomStatus, 
    NSFWMode, ConsentStatus, RoomSettings, RoomOnboarding
)
from models.user import UserInRoom, UserRole, UserPublic


class RoomService:
    """Service for room management operations."""
    
    TABLE_ROOMS = "rooms"
    TABLE_USERS = "room_users"
    
    async def create_room(self, data: RoomCreate) -> Tuple[Room, str, UserInRoom]:
        """
        Create a new chat room and add creator as first user.
        
        Args:
            data: Room creation data
            
        Returns:
            Tuple of (Room, plain_secret, UserInRoom)
        """
        # Generate or use provided secret
        plain_secret = data.room_secret or security_service.generate_room_secret()
        secret_hash = security_service.hash_secret(plain_secret)
        
        room_data = {
            "name": data.name,
            "secret_hash": secret_hash,
            "status": RoomStatus.ACTIVE.value,
            "nsfw_mode": NSFWMode.DISABLED.value,
            "partner_a_nsfw_consent": False,
            "partner_b_nsfw_consent": False,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        result = await supabase.insert(self.TABLE_ROOMS, room_data)
        room = Room(**result)
        
        # Create the first user (room creator)
        user_data = {
            "id": str(uuid.uuid4()),
            "room_id": room.id,
            "nickname": data.creator_nickname,
            "device_id": data.device_id,
            "role": UserRole.PARTNER_A.value,
            "is_online": True,
            "last_seen": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "nsfw_consent": False,
        }
        
        user_result = await supabase.insert(self.TABLE_USERS, user_data)
        user = UserInRoom(**user_result)
        
        return room, plain_secret, user
    
    async def get_room(self, room_id: int) -> Optional[Room]:
        """
        Get a room by ID.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Room or None if not found
        """
        result = await supabase.select(
            self.TABLE_ROOMS,
            filters={"id": room_id}
        )
        
        if result:
            return Room(**result[0])
        return None
    
    async def get_room_by_name(self, name: str) -> Optional[Room]:
        """
        Get a room by name.
        
        Args:
            name: Room name
            
        Returns:
            Room or None if not found
        """
        result = await supabase.select(
            self.TABLE_ROOMS,
            filters={"name": name}
        )
        
        if result:
            return Room(**result[0])
        return None
    
    async def join_room(self, data: RoomJoin) -> Tuple[UserInRoom, Room]:
        """
        Join an existing room by name.
        
        Args:
            data: Room join data with credentials
            
        Returns:
            Tuple of (UserInRoom, Room)
            
        Raises:
            ValueError: If room not found, invalid secret, or room full
        """
        # Get room by name
        room = await self.get_room_by_name(data.room_name)
        if not room:
            raise ValueError("Room not found")
        
        if room.status != RoomStatus.ACTIVE:
            raise ValueError("Room is not active")
        
        # Verify secret
        if not security_service.verify_secret(data.room_secret, room.secret_hash):
            raise ValueError("Invalid room secret")
        
        # Check existing users
        users = await self.get_room_users(room.id)
        
        # Check if device already has a user in this room
        existing_user = next(
            (u for u in users if u.device_id == data.device_id),
            None
        )
        if existing_user:
            # Update last seen and return existing user
            await supabase.update(
                self.TABLE_USERS,
                {"last_seen": datetime.utcnow().isoformat(), "is_online": True},
                {"id": existing_user.id}
            )
            existing_user.is_online = True
            existing_user.last_seen = datetime.utcnow()
            return existing_user, room
        
        # Check room capacity (max 2 users)
        if len(users) >= 2:
            raise ValueError("Room is full (maximum 2 users)")
        
        # Determine role
        role = UserRole.PARTNER_A if len(users) == 0 else UserRole.PARTNER_B
        
        # Create user
        user_data = {
            "id": str(uuid.uuid4()),
            "room_id": room.id,
            "nickname": data.nickname,
            "device_id": data.device_id,
            "role": role.value,
            "is_online": True,
            "last_seen": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "nsfw_consent": False,
        }
        
        result = await supabase.insert(self.TABLE_USERS, user_data)
        user = UserInRoom(**result)
        
        # Update room last activity
        await supabase.update(
            self.TABLE_ROOMS,
            {"last_activity_at": datetime.utcnow().isoformat()},
            {"id": room.id}
        )
        
        return user, room
    
    async def get_room_users(self, room_id: int) -> list[UserInRoom]:
        """
        Get all users in a room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            List of users in the room
        """
        result = await supabase.select(
            self.TABLE_USERS,
            filters={"room_id": room_id}
        )
        
        return [UserInRoom(**u) for u in result]
    
    async def get_room_public(self, room_id: int) -> Optional[RoomPublic]:
        """
        Get public room information.
        
        Args:
            room_id: Room identifier
            
        Returns:
            RoomPublic or None
        """
        room = await self.get_room(room_id)
        if not room:
            return None
        
        users = await self.get_room_users(room_id)
        user_publics = [
            UserPublic(
                id=u.id,
                nickname=u.nickname,
                avatar_url=u.avatar_url,
                is_online=u.is_online,
                last_seen=u.last_seen
            )
            for u in users
        ]
        
        return RoomPublic(
            id=room.id,
            name=room.name,
            status=room.status,
            nsfw_mode=room.nsfw_mode,
            users=user_publics,
            created_at=room.created_at,
            last_activity_at=room.last_activity_at
        )
    
    async def update_user_online_status(
        self, 
        user_id: str, 
        is_online: bool
    ) -> None:
        """
        Update user online status.
        
        Args:
            user_id: User identifier
            is_online: Online status
        """
        await supabase.update(
            self.TABLE_USERS,
            {
                "is_online": is_online,
                "last_seen": datetime.utcnow().isoformat()
            },
            {"id": user_id}
        )
    
    async def update_nsfw_consent(
        self,
        room_id: int,
        user_id: str,
        consent: bool
    ) -> ConsentStatus:
        """
        Update NSFW consent for a user.
        
        Args:
            room_id: Room identifier
            user_id: User identifier
            consent: Consent value
            
        Returns:
            Current consent status for the room
        """
        # Get user to determine role
        users = await self.get_room_users(room_id)
        user = next((u for u in users if u.id == user_id), None)
        
        if not user:
            raise ValueError("User not found in room")
        
        # Update user consent
        await supabase.update(
            self.TABLE_USERS,
            {
                "nsfw_consent": consent,
                "nsfw_consent_at": datetime.utcnow().isoformat() if consent else None
            },
            {"id": user_id}
        )
        
        # Update room consent field based on role
        consent_field = (
            "partner_a_nsfw_consent" if user.role == UserRole.PARTNER_A 
            else "partner_b_nsfw_consent"
        )
        
        await supabase.update(
            self.TABLE_ROOMS,
            {consent_field: consent},
            {"id": room_id}
        )
        
        # Get updated room
        room = await self.get_room(room_id)
        
        # Check if both consented
        both_consented = room.partner_a_nsfw_consent and room.partner_b_nsfw_consent
        
        # Update NSFW mode if both consented
        if both_consented and room.nsfw_mode != NSFWMode.ENABLED:
            await supabase.update(
                self.TABLE_ROOMS,
                {"nsfw_mode": NSFWMode.ENABLED.value},
                {"id": room_id}
            )
            room.nsfw_mode = NSFWMode.ENABLED
        elif not both_consented and room.nsfw_mode == NSFWMode.ENABLED:
            await supabase.update(
                self.TABLE_ROOMS,
                {"nsfw_mode": NSFWMode.DISABLED.value},
                {"id": room_id}
            )
            room.nsfw_mode = NSFWMode.DISABLED
        
        return ConsentStatus(
            room_id=room_id,
            nsfw_mode=room.nsfw_mode,
            partner_a_consent=room.partner_a_nsfw_consent,
            partner_b_consent=room.partner_b_nsfw_consent,
            both_consented=both_consented
        )
    
    async def request_nsfw_consent(self, room_id: int, requester_id: str) -> None:
        """
        Initiate NSFW consent request.
        
        Args:
            room_id: Room identifier
            requester_id: User requesting NSFW mode
        """
        await supabase.update(
            self.TABLE_ROOMS,
            {"nsfw_mode": NSFWMode.PENDING_CONSENT.value},
            {"id": room_id}
        )
    
    async def update_room_settings(
        self,
        room_id: int,
        settings_data: RoomSettings
    ) -> Room:
        """
        Update room settings.
        
        Args:
            room_id: Room identifier
            settings_data: Settings to update
            
        Returns:
            Updated room
        """
        update_data = settings_data.model_dump(exclude_none=True)
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        await supabase.update(self.TABLE_ROOMS, update_data, {"id": room_id})
        
        return await self.get_room(room_id)
    
    async def update_room_onboarding(
        self,
        room_id: int,
        onboarding: RoomOnboarding
    ) -> Room:
        """
        Update room onboarding data.
        
        Args:
            room_id: Room identifier
            onboarding: Onboarding data
            
        Returns:
            Updated room
        """
        update_data = {
            "relationship_type": onboarding.relationship_type,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if onboarding.anniversary_date:
            update_data["anniversary_date"] = onboarding.anniversary_date.isoformat()
        
        await supabase.update(self.TABLE_ROOMS, update_data, {"id": room_id})
        
        return await self.get_room(room_id)
    
    async def delete_room(self, room_id: int) -> bool:
        """
        Delete a room and all associated data.
        
        Args:
            room_id: Room identifier
            
        Returns:
            True if deleted successfully
        """
        # Soft delete by updating status
        await supabase.update(
            self.TABLE_ROOMS,
            {
                "status": RoomStatus.DELETED.value,
                "updated_at": datetime.utcnow().isoformat()
            },
            {"id": room_id}
        )
        
        return True
    
    async def hard_delete_room(self, room_id: int) -> bool:
        """
        Permanently delete a room and all data.
        
        Args:
            room_id: Room identifier
            
        Returns:
            True if deleted successfully
        """
        # Delete users first
        await supabase.delete(self.TABLE_USERS, {"room_id": room_id})
        
        # Delete room
        await supabase.delete(self.TABLE_ROOMS, {"id": room_id})
        
        return True


# Singleton instance
room_service = RoomService()
