"""
Room management API routes.
Handles room creation, joining, settings, and lifecycle.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from models.room import (
    RoomCreate, RoomJoin, RoomPublic, RoomSettings, 
    RoomOnboarding, ConsentRequest, ConsentStatus
)
from models.user import UserInRoom
from services.room_service import room_service
from services.memory_service import memory_service
from ws.connection_manager import connection_manager


router = APIRouter(prefix="/rooms", tags=["rooms"])


class RoomCreateResponse(BaseModel):
    """Response for room creation."""
    room: RoomPublic
    secret: str
    user: UserInRoom
    message: str


class RoomJoinResponse(BaseModel):
    """Response for joining a room."""
    user: UserInRoom
    room: RoomPublic
    message: str


@router.post("/create", response_model=RoomCreateResponse)
async def create_room(data: RoomCreate):
    """
    Create a new chat room and join as first user.
    
    Returns the room info, secret (only shown once), and user.
    """
    try:
        room, secret, user = await room_service.create_room(data)
        room_public = await room_service.get_room_public(room.id)
        
        return RoomCreateResponse(
            room=room_public,
            secret=secret,
            user=user,
            message="Room created successfully. Save the secret - it won't be shown again!"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/join", response_model=RoomJoinResponse)
async def join_room(data: RoomJoin):
    """
    Join an existing room.
    
    Requires valid room_id and room_secret.
    Room is limited to 2 users maximum.
    """
    try:
        user, room = await room_service.join_room(data)
        room_public = await room_service.get_room_public(room.id)
        
        return RoomJoinResponse(
            user=user,
            room=room_public,
            message="Successfully joined the room"
        )
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


@router.get("/{room_id}", response_model=RoomPublic)
async def get_room(room_id: int):
    """
    Get room information.
    """
    room_public = await room_service.get_room_public(room_id)
    
    if not room_public:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    return room_public


@router.put("/{room_id}/settings")
async def update_room_settings(room_id: int, settings_data: RoomSettings):
    """
    Update room settings.
    """
    try:
        room = await room_service.update_room_settings(room_id, settings_data)
        room_public = await room_service.get_room_public(room.id)
        
        return {"room": room_public, "message": "Settings updated"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put("/{room_id}/onboarding")
async def update_room_onboarding(room_id: int, onboarding: RoomOnboarding):
    """
    Update room onboarding/relationship data.
    
    This information helps personalize bot responses.
    """
    try:
        room = await room_service.update_room_onboarding(room_id, onboarding)
        
        return {"message": "Onboarding data saved", "room_id": room.id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{room_id}/consent", response_model=ConsentStatus)
async def update_nsfw_consent(room_id: int, consent: ConsentRequest):
    """
    Update NSFW consent for a user.
    
    Both partners must consent for NSFW mode to be enabled.
    """
    try:
        status_result = await room_service.update_nsfw_consent(
            room_id,
            consent.user_id,
            consent.consent
        )
        
        # Notify room about consent update via WebSocket
        from models.message import WebSocketMessage
        await connection_manager.broadcast_to_room(
            room_id,
            WebSocketMessage(
                event="consent_updated",
                data={
                    "user_id": consent.user_id,
                    "nsfw_mode": status_result.nsfw_mode.value,
                    "both_consented": status_result.both_consented
                },
                room_id=room_id
            )
        )
        
        return status_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{room_id}/consent", response_model=ConsentStatus)
async def get_consent_status(room_id: int):
    """
    Get current NSFW consent status for the room.
    """
    room = await room_service.get_room(room_id)
    
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    return ConsentStatus(
        room_id=room_id,
        nsfw_mode=room.nsfw_mode,
        partner_a_consent=room.partner_a_nsfw_consent,
        partner_b_consent=room.partner_b_nsfw_consent,
        both_consented=room.partner_a_nsfw_consent and room.partner_b_nsfw_consent
    )


@router.delete("/{room_id}")
async def delete_room(room_id: int, hard_delete: bool = False):
    """
    Delete a room.
    
    Args:
        room_id: Room to delete
        hard_delete: If True, permanently delete all data
    """
    try:
        # Close all WebSocket connections
        await connection_manager.close_room_connections(room_id, "Room deleted")
        
        # Clear memories
        await memory_service.clear_room_memories(room_id)
        
        # Delete room
        if hard_delete:
            await room_service.hard_delete_room(room_id)
            message = "Room permanently deleted"
        else:
            await room_service.delete_room(room_id)
            message = "Room deleted"
        
        return {"message": message, "room_id": room_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{room_id}/reset-memory")
async def reset_room_memory(room_id: int):
    """
    Reset all AI memories for a room.
    
    This clears all remembered information from the vector store.
    """
    try:
        count = await memory_service.clear_room_memories(room_id)
        
        return {
            "message": "Memory reset successfully",
            "room_id": room_id,
            "memories_cleared": count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{room_id}/users")
async def get_room_users(room_id: int):
    """
    Get all users in a room.
    """
    users = await room_service.get_room_users(room_id)
    
    return {
        "room_id": room_id,
        "users": users,
        "count": len(users)
    }


@router.get("/{room_id}/online")
async def get_online_users(room_id: int):
    """
    Get currently online users in a room.
    """
    online_users = connection_manager.get_room_users(room_id)
    
    return {
        "room_id": room_id,
        "online_users": list(online_users),
        "count": len(online_users)
    }
