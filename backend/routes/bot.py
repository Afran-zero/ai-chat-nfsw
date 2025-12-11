"""
Bot API routes.
Handles bot interactions, intent classification, and NSFW consent flow.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from models.message import WebSocketMessage
from services.bot_service import bot_service
from services.room_service import room_service
from ws.connection_manager import connection_manager
from ai import AI_AVAILABLE, get_orchestrator


router = APIRouter(prefix="/bot", tags=["bot"])


class BotMessageRequest(BaseModel):
    """Request to send a message to the bot."""
    room_id: int
    user_id: str
    message: str


class BotResponse(BaseModel):
    """Bot response model."""
    response: str
    persona_used: Optional[str] = None
    intent: Optional[str] = None
    nsfw_consent_needed: bool = False


class IntentClassificationRequest(BaseModel):
    """Request to classify message intent."""
    message: str


class IntentClassificationResponse(BaseModel):
    """Intent classification response."""
    primary_intent: str
    scores: Dict[str, float]
    confidence: float
    is_nsfw: bool


class NSFWConsentRequest(BaseModel):
    """Request to initiate NSFW consent."""
    room_id: int
    requester_id: str


@router.post("/message", response_model=BotResponse)
async def send_bot_message(request: BotMessageRequest):
    """
    Send a message to the bot and get a response.
    
    The bot will automatically route to the appropriate persona
    based on message intent (using embedding similarity, NOT regex).
    """
    if not AI_AVAILABLE:
        return BotResponse(
            response="AI features are not available. Please install llama-index and related packages.",
            persona_used="system",
            intent="error",
            nsfw_consent_needed=False
        )
    
    try:
        # Check for NSFW intent
        is_nsfw = await bot_service.check_nsfw_intent(request.message, request.room_id)
        
        if is_nsfw:
            # Check if NSFW is enabled
            room = await room_service.get_room(request.room_id)
            if not room or room.nsfw_mode.value != "enabled":
                # Return consent request instead
                return BotResponse(
                    response=(
                        "I sense you might want to explore something more intimate. 💕\n\n"
                        "For that kind of conversation, I need consent from both partners. "
                        "Would you like to request NSFW mode? Use the consent button in settings."
                    ),
                    persona_used="consent_handler",
                    intent="nsfw",
                    nsfw_consent_needed=True
                )
        
        # Generate response
        response = await bot_service.generate_response(
            request.room_id,
            request.message,
            request.user_id
        )
        
        # Get intent for response
        orchestrator = get_orchestrator()
        intent_result = orchestrator.get_intent_classification(request.message) if orchestrator else {"primary_intent": "general"}
        
        return BotResponse(
            response=response,
            persona_used=intent_result["primary_intent"],
            intent=intent_result["primary_intent"],
            nsfw_consent_needed=False
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/classify", response_model=IntentClassificationResponse)
async def classify_intent(request: IntentClassificationRequest):
    """
    Classify the intent of a message.
    
    Uses embedding similarity (NO regex) to determine:
    - care: Relationship advice, emotional support
    - nsfw: Intimate/romantic content
    - neutral: General conversation
    """
    try:
        orchestrator = get_orchestrator()
        result = orchestrator.get_intent_classification(request.message)
        
        return IntentClassificationResponse(
            primary_intent=result["primary_intent"],
            scores=result["scores"],
            confidence=result["confidence"],
            is_nsfw=result["primary_intent"] == "nsfw" and result["confidence"] > 0.4
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/request-nsfw-consent")
async def request_nsfw_consent(request: NSFWConsentRequest):
    """
    Initiate NSFW consent request.
    
    This will notify both partners and wait for mutual consent.
    """
    try:
        # Request consent
        result = await bot_service.request_nsfw_consent(
            request.room_id,
            request.requester_id
        )
        
        # Notify room about consent request
        await connection_manager.broadcast_to_room(
            request.room_id,
            WebSocketMessage(
                event="nsfw_consent_requested",
                data={
                    "requester_id": request.requester_id,
                    "message": "Your partner has requested to enable intimate mode. Both partners must consent."
                },
                room_id=request.room_id,
                sender_id=request.requester_id
            )
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/status/{room_id}")
async def get_bot_status(room_id: int):
    """
    Get the current bot status for a room.
    
    Returns:
    - Whether bot is active
    - Current NSFW mode status
    - Memory statistics
    """
    try:
        status_data = await bot_service.get_bot_status(room_id)
        return status_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/personas")
async def list_personas():
    """
    List available bot personas.
    """
    return {
        "personas": [
            {
                "id": "care",
                "name": "Care Coach",
                "description": "Emotional support and relationship advice",
                "requires_consent": False
            },
            {
                "id": "intimate",
                "name": "Intimate",
                "description": "Playful romantic persona for consenting partners",
                "requires_consent": True
            },
            {
                "id": "neutral",
                "name": "Helper",
                "description": "General assistance and casual conversation",
                "requires_consent": False
            }
        ]
    }


@router.post("/suggest-activity/{room_id}")
async def suggest_activity(room_id: int, activity_type: str = "date"):
    """
    Get a romantic activity suggestion from the bot.
    
    Args:
        room_id: Room identifier
        activity_type: Type of activity (date, surprise, intimate)
    """
    try:
        # Build context
        from services.message_service import message_service
        from services.memory_service import memory_service
        
        recent = await message_service.get_recent_messages(room_id, limit=5)
        memories = await memory_service.get_room_memories(room_id)
        room = await room_service.get_room(room_id)
        
        # Build context string
        context_parts = []
        
        if room and room.relationship_type:
            context_parts.append(f"Relationship: {room.relationship_type}")
        
        if memories:
            context_parts.append("Remembered preferences:")
            for mem in memories[:5]:
                context_parts.append(f"- {mem.text}")
        
        context = "\n".join(context_parts)
        
        # Generate suggestion based on NSFW mode
        if activity_type == "intimate":
            if not room or room.nsfw_mode.value != "enabled":
                return {
                    "suggestion": "Intimate suggestions require NSFW mode to be enabled by both partners.",
                    "requires_consent": True
                }
            
            from ai.personas.intimate import IntimatePersona
            persona = IntimatePersona()
            suggestion = await persona.suggest_romantic_activity(
                context, room_id, activity_type
            )
        else:
            from ai.personas.care import CarePersona
            persona = CarePersona()
            suggestion = await persona.generate_neutral_response(
                f"Suggest a {activity_type} idea for us",
                context,
                room_id
            )
        
        return {
            "suggestion": suggestion,
            "activity_type": activity_type,
            "requires_consent": False
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
