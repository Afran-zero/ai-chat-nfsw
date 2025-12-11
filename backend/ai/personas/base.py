"""
Base persona module with routing logic and common functionality.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum

from config import settings


class PersonaType(str, Enum):
    """Available persona types."""
    CARE = "care"
    INTIMATE = "intimate"
    NEUTRAL = "neutral"


class BasePersona(ABC):
    """
    Abstract base class for all persona implementations.
    Defines the interface for response generation.
    """
    
    def __init__(self, persona_type: PersonaType):
        """
        Initialize base persona.
        
        Args:
            persona_type: Type of this persona
        """
        self.persona_type = persona_type
        self._llm = None
    
    def _get_llm(self):
        """Lazy load LLM."""
        if self._llm is None:
            from llama_cpp import Llama
            self._llm = Llama(
                model_path=settings.llm_model_path,
                n_ctx=settings.llm_context_length,
                n_threads=4,
                verbose=False
            )
        return self._llm
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this persona."""
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        message: str,
        context: str,
        room_id: int
    ) -> str:
        """
        Generate a response to the user message.
        
        Args:
            message: User's message
            context: Formatted context string
            room_id: Room identifier
            
        Returns:
            Generated response
        """
        pass
    
    def _format_prompt(
        self,
        message: str,
        context: str,
        additional_instructions: str = ""
    ) -> str:
        """
        Format the complete prompt for the LLM.
        
        Args:
            message: User's message
            context: Formatted context
            additional_instructions: Extra instructions
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""<|system|>
{self.system_prompt}

{additional_instructions}
</|system|>

<|context|>
{context}
</|context|>

<|user|>
{message}
</|user|>

<|assistant|>
"""
        return prompt
    
    async def _generate_completion(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stop_sequences: Optional[list] = None
    ) -> str:
        """
        Generate completion from LLM.
        
        Args:
            prompt: Formatted prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop_sequences: Stop sequences
            
        Returns:
            Generated text
        """
        llm = self._get_llm()
        
        response = llm(
            prompt,
            max_tokens=max_tokens or settings.llm_max_tokens,
            temperature=temperature or settings.llm_temperature,
            stop=stop_sequences or ["</|assistant|>", "<|user|>", "\n\n\n"],
            echo=False
        )
        
        text = response["choices"][0]["text"].strip()
        return text


class PersonaRouter:
    """
    Routes messages to appropriate personas based on intent.
    Uses embedding-based classification (NO REGEX).
    """
    
    def __init__(self):
        """Initialize persona router."""
        self._personas: Dict[PersonaType, BasePersona] = {}
    
    def register_persona(self, persona: BasePersona) -> None:
        """
        Register a persona for routing.
        
        Args:
            persona: Persona instance to register
        """
        self._personas[persona.persona_type] = persona
    
    def get_persona(self, persona_type: PersonaType) -> Optional[BasePersona]:
        """
        Get a registered persona by type.
        
        Args:
            persona_type: Type of persona to get
            
        Returns:
            Persona instance or None
        """
        return self._personas.get(persona_type)
    
    async def route_and_respond(
        self,
        message: str,
        context: str,
        room_id: int,
        intent_scores: Dict[str, float],
        nsfw_enabled: bool
    ) -> tuple[str, PersonaType]:
        """
        Route message to appropriate persona and generate response.
        
        Args:
            message: User message
            context: Formatted context
            room_id: Room identifier
            intent_scores: Scores from intent classification
            nsfw_enabled: Whether NSFW mode is enabled
            
        Returns:
            Tuple of (response, persona_type_used)
        """
        # Determine persona based on scores
        if intent_scores.get("care", 0) > 0.4:
            persona_type = PersonaType.CARE
        elif intent_scores.get("nsfw", 0) > 0.4 and nsfw_enabled:
            persona_type = PersonaType.INTIMATE
        else:
            persona_type = PersonaType.NEUTRAL
        
        # Get persona
        persona = self._personas.get(persona_type)
        
        if persona is None:
            # Fallback to care persona if available
            persona = self._personas.get(PersonaType.CARE)
        
        if persona is None:
            return "I'm sorry, I can't respond right now.", PersonaType.NEUTRAL
        
        # Generate response
        response = await persona.generate_response(message, context, room_id)
        
        return response, persona_type
