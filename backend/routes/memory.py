"""
Memory API routes.
Handles "Remember This" functionality and memory management.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from models.message import (
    MemoryCategory, MemoryEntry, MemorySearchResult, 
    RememberRequest, WebSocketMessage
)
from services.memory_service import memory_service
from services.message_service import message_service
from ws.connection_manager import connection_manager


router = APIRouter(prefix="/memory", tags=["memory"])


class RememberResponse(BaseModel):
    """Response after remembering something."""
    success: bool
    memory_id: str
    message: str
    category: MemoryCategory


class MemorySearchRequest(BaseModel):
    """Request to search memories."""
    room_id: int
    query: str
    limit: int = 10
    category: Optional[MemoryCategory] = None


class MemoryStatsResponse(BaseModel):
    """Memory statistics response."""
    room_id: int
    total: int
    by_category: dict


class AddMemoryRequest(BaseModel):
    """Request to add a custom memory."""
    room_id: int
    sender_id: str
    text: str
    category: MemoryCategory


@router.post("/remember", response_model=RememberResponse)
async def remember_message(request: RememberRequest, user_id: str):
    """
    Remember a message for future context.
    
    This generates an embedding and stores it in ChromaDB with metadata.
    Duplicates are automatically filtered using cosine similarity.
    """
    try:
        # Get the message
        message = await message_service.get_message(request.message_id)
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )
        
        # Determine text to remember
        text_to_remember = request.custom_note or message.content
        
        # Add to memory
        memory = await memory_service.add_memory(
            room_id=message.room_id,
            sender_id=message.sender_id,
            text=text_to_remember,
            category=request.category,
            message_id=request.message_id,
            metadata={"noted_by": user_id}
        )
        
        # Mark message as remembered
        await message_service.mark_message_remembered(
            request.message_id,
            request.category.value
        )
        
        # Notify room
        await connection_manager.broadcast_to_room(
            message.room_id,
            WebSocketMessage(
                event="message_remembered",
                data={
                    "message_id": request.message_id,
                    "memory_id": memory.id,
                    "category": request.category.value,
                    "remembered_by": user_id
                },
                room_id=message.room_id,
                sender_id=user_id
            )
        )
        
        return RememberResponse(
            success=True,
            memory_id=memory.id,
            message="Memory saved successfully",
            category=request.category
        )
        
    except ValueError as e:
        # Duplicate memory
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/add", response_model=RememberResponse)
async def add_custom_memory(request: AddMemoryRequest):
    """
    Add a custom memory (not from a specific message).
    
    Useful for manually noting important information.
    """
    try:
        memory = await memory_service.add_memory(
            room_id=request.room_id,
            sender_id=request.sender_id,
            text=request.text,
            category=request.category
        )
        
        return RememberResponse(
            success=True,
            memory_id=memory.id,
            message="Memory added successfully",
            category=request.category
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/search", response_model=List[MemorySearchResult])
async def search_memories(request: MemorySearchRequest):
    """
    Search memories using semantic similarity.
    
    Returns memories ranked by relevance to the query.
    """
    try:
        results = await memory_service.search_memories(
            room_id=request.room_id,
            query=request.query,
            limit=request.limit,
            category=request.category
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{room_id}", response_model=List[MemoryEntry])
async def get_room_memories(
    room_id: int,
    category: Optional[MemoryCategory] = None
):
    """
    Get all memories for a room.
    
    Optionally filter by category.
    """
    try:
        memories = await memory_service.get_room_memories(room_id, category)
        return memories
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{room_id}/stats", response_model=MemoryStatsResponse)
async def get_memory_stats(room_id: int):
    """
    Get memory statistics for a room.
    """
    try:
        stats = await memory_service.get_memory_stats(room_id)
        
        return MemoryStatsResponse(
            room_id=room_id,
            total=stats.pop('total', 0),
            by_category=stats
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str):
    """
    Delete a specific memory.
    """
    try:
        success = await memory_service.delete_memory(memory_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Memory not found"
            )
        
        return {"success": True, "message": "Memory deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/room/{room_id}")
async def clear_room_memories(room_id: int):
    """
    Clear all memories for a room.
    
    This is irreversible - all remembered information will be lost.
    """
    try:
        count = await memory_service.clear_room_memories(room_id)
        
        # Notify room
        await connection_manager.broadcast_to_room(
            room_id,
            WebSocketMessage(
                event="memories_cleared",
                data={"room_id": room_id, "count": count},
                room_id=room_id
            )
        )
        
        return {
            "success": True,
            "message": "All memories cleared",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/categories")
async def list_memory_categories():
    """
    List available memory categories with descriptions.
    """
    return {
        "categories": [
            {
                "id": "event",
                "name": "Event",
                "description": "Important dates, anniversaries, milestones",
                "retention": "Forever"
            },
            {
                "id": "preference",
                "name": "Preference",
                "description": "Likes, dislikes, favorites",
                "retention": "Latest per topic (overwrites similar)"
            },
            {
                "id": "boundary",
                "name": "Boundary",
                "description": "Personal boundaries and limits",
                "retention": "Forever"
            },
            {
                "id": "emotion",
                "name": "Emotion",
                "description": "Emotional moments and feelings",
                "retention": "Last 10 entries"
            },
            {
                "id": "general",
                "name": "General",
                "description": "Other important information",
                "retention": "Standard"
            }
        ]
    }
