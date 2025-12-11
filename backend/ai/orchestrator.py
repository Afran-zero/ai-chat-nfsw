"""
AI Orchestrator using LangGraph for automatic persona routing.
NO REGEX - uses embedding similarity for intent classification.
"""

from typing import Dict, Any, Optional, List, Literal, TypedDict
from enum import Enum
import asyncio

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from config import settings
from ai.embeddings import embedding_service
from ai.rag_index import get_rag_index
from ai.personas.base import PersonaRouter
from ai.personas.care import CarePersona
from ai.personas.intimate import IntimatePersona


class IntentType(str, Enum):
    """Intent types for routing."""
    CARE = "care"
    INTIMATE = "intimate"
    NEUTRAL = "neutral"


class OrchestratorState(TypedDict):
    """State for the orchestrator graph."""
    message: str
    room_id: int
    user_id: str
    context: Dict[str, Any]
    intent: Optional[IntentType]
    intent_scores: Dict[str, float]
    nsfw_enabled: bool
    nsfw_consent_needed: bool
    response: Optional[str]
    persona_used: Optional[str]


class Orchestrator:
    """
    Main orchestrator for AI bot using LangGraph.
    Routes messages to appropriate personas based on embedding similarity.
    NO REGEX MATCHING - purely semantic classification.
    """
    
    def __init__(self):
        """Initialize orchestrator with personas and graph."""
        # Initialize personas
        self._care_persona = CarePersona()
        self._intimate_persona = IntimatePersona()
        self._persona_router = PersonaRouter()
        
        # Initialize RAG
        self._rag_index = get_rag_index()
        
        # Build LangGraph
        self._graph = self._build_graph()
        
        # Memory for conversation state
        self._memory = MemorySaver()
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph orchestration graph.
        
        Flow:
        1. Classify Intent (embedding-based, NO regex)
        2. Check NSFW consent if needed
        3. Route to appropriate persona
        4. Generate response
        """
        # Create graph with state schema
        graph = StateGraph(OrchestratorState)
        
        # Add nodes
        graph.add_node("classify_intent", self._classify_intent_node)
        graph.add_node("check_consent", self._check_consent_node)
        graph.add_node("route_persona", self._route_persona_node)
        graph.add_node("care_response", self._care_response_node)
        graph.add_node("intimate_response", self._intimate_response_node)
        graph.add_node("neutral_response", self._neutral_response_node)
        graph.add_node("consent_response", self._consent_response_node)
        
        # Set entry point
        graph.set_entry_point("classify_intent")
        
        # Add edges
        graph.add_edge("classify_intent", "check_consent")
        
        # Conditional edge from consent check
        graph.add_conditional_edges(
            "check_consent",
            self._consent_routing,
            {
                "needs_consent": "consent_response",
                "route": "route_persona"
            }
        )
        
        # Conditional edge from router
        graph.add_conditional_edges(
            "route_persona",
            self._persona_routing,
            {
                "care": "care_response",
                "intimate": "intimate_response",
                "neutral": "neutral_response"
            }
        )
        
        # End edges
        graph.add_edge("care_response", END)
        graph.add_edge("intimate_response", END)
        graph.add_edge("neutral_response", END)
        graph.add_edge("consent_response", END)
        
        return graph.compile(checkpointer=self._memory)
    
    async def _classify_intent_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """
        Classify message intent using embedding similarity.
        NO REGEX - purely semantic classification.
        """
        message = state["message"]
        
        # Use embedding service for classification
        intent_result = embedding_service.classify_intent(message)
        
        # Map to our intent types
        intent_map = {
            "care": IntentType.CARE,
            "nsfw": IntentType.INTIMATE,
            "neutral": IntentType.NEUTRAL
        }
        
        primary = intent_result["primary_intent"]
        intent = intent_map.get(primary, IntentType.NEUTRAL)
        
        return {
            "intent": intent,
            "intent_scores": intent_result["scores"]
        }
    
    async def _check_consent_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """
        Check if NSFW consent is needed.
        """
        intent = state["intent"]
        nsfw_enabled = state["nsfw_enabled"]
        
        # NSFW intent detected but not enabled
        needs_consent = (
            intent == IntentType.INTIMATE and 
            not nsfw_enabled
        )
        
        return {"nsfw_consent_needed": needs_consent}
    
    def _consent_routing(self, state: OrchestratorState) -> str:
        """Route based on consent status."""
        if state["nsfw_consent_needed"]:
            return "needs_consent"
        return "route"
    
    def _persona_routing(self, state: OrchestratorState) -> str:
        """Route to appropriate persona based on intent."""
        intent = state["intent"]
        
        if intent == IntentType.CARE:
            return "care"
        elif intent == IntentType.INTIMATE and state["nsfw_enabled"]:
            return "intimate"
        else:
            return "neutral"
    
    async def _route_persona_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """Prepare for persona routing."""
        return {}  # Just a passthrough node for routing
    
    async def _care_response_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """Generate care/coaching response."""
        context_str = self._build_context_string(state["context"])
        
        response = await self._care_persona.generate_response(
            message=state["message"],
            context=context_str,
            room_id=state["room_id"]
        )
        
        return {
            "response": response,
            "persona_used": "care"
        }
    
    async def _intimate_response_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """Generate intimate persona response."""
        context_str = self._build_context_string(state["context"])
        
        response = await self._intimate_persona.generate_response(
            message=state["message"],
            context=context_str,
            room_id=state["room_id"]
        )
        
        return {
            "response": response,
            "persona_used": "intimate"
        }
    
    async def _neutral_response_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """Generate neutral/helpful response."""
        context_str = self._build_context_string(state["context"])
        
        # Use care persona for neutral responses with adjusted prompt
        response = await self._care_persona.generate_neutral_response(
            message=state["message"],
            context=context_str,
            room_id=state["room_id"]
        )
        
        return {
            "response": response,
            "persona_used": "neutral"
        }
    
    async def _consent_response_node(self, state: OrchestratorState) -> Dict[str, Any]:
        """Generate consent request response."""
        response = (
            "I sense you might want to explore something more intimate. "
            "For that kind of conversation, I need consent from both partners. "
            "Would you like to request NSFW mode? Both of you will need to agree "
            "before I can engage in that way. 💕"
        )
        
        return {
            "response": response,
            "persona_used": "consent_handler"
        }
    
    def _build_context_string(self, context: Dict[str, Any]) -> str:
        """Build context string from context dict."""
        message = context.get("current_message", "")
        history = context.get("message_history", [])
        memories = context.get("memories", [])
        onboarding = context.get("onboarding", {})
        
        return self._rag_index.build_context(
            query=message,
            room_id=context.get("room_id", 0),
            message_history=history,
            memories=memories,
            onboarding=onboarding
        )
    
    async def process_message(
        self,
        message: str,
        context: Dict[str, Any],
        room_id: int,
        user_id: str,
        nsfw_enabled: bool = False
    ) -> str:
        """
        Process a message through the orchestrator.
        
        Args:
            message: User message
            context: Conversation context
            room_id: Room identifier
            user_id: User identifier
            nsfw_enabled: Whether NSFW mode is enabled
            
        Returns:
            Bot response
        """
        # Initialize state
        initial_state: OrchestratorState = {
            "message": message,
            "room_id": room_id,
            "user_id": user_id,
            "context": context,
            "intent": None,
            "intent_scores": {},
            "nsfw_enabled": nsfw_enabled,
            "nsfw_consent_needed": False,
            "response": None,
            "persona_used": None
        }
        
        # Run graph
        config = {"configurable": {"thread_id": f"room_{room_id}"}}
        
        # Execute graph
        final_state = await self._graph.ainvoke(initial_state, config)
        
        return final_state.get("response", "I'm not sure how to respond to that.")
    
    async def detect_nsfw_intent(self, message: str) -> bool:
        """
        Detect if a message has NSFW intent.
        
        Args:
            message: Message to check
            
        Returns:
            True if NSFW intent detected
        """
        return embedding_service.is_nsfw_intent(message)
    
    def get_intent_classification(self, message: str) -> Dict[str, Any]:
        """
        Get detailed intent classification for a message.
        
        Args:
            message: Message to classify
            
        Returns:
            Intent classification with scores
        """
        return embedding_service.classify_intent(message)


# Singleton instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
