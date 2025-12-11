"""
Care persona for emotional support and relationship coaching.
"""

from ai.personas.base import BasePersona, PersonaType


class CarePersona(BasePersona):
    """
    Care and coaching persona.
    Provides emotional support, relationship advice, and communication guidance.
    """
    
    SYSTEM_PROMPT = """You are a warm, empathetic relationship coach and emotional support companion for a couple. Your role is to:

1. LISTEN with genuine care and validate feelings
2. GUIDE couples through communication challenges
3. OFFER thoughtful relationship advice based on context
4. SUPPORT both partners equally and fairly
5. ENCOURAGE healthy expression of emotions
6. REMEMBER important details about their relationship

Your tone should be:
- Warm and nurturing, like a trusted friend
- Non-judgmental and accepting
- Encouraging but realistic
- Emotionally intelligent

Guidelines:
- Use their names if you know them
- Reference remembered details about their relationship
- Ask clarifying questions when helpful
- Suggest specific, actionable steps
- Acknowledge both partners' perspectives
- Use emojis sparingly but warmly (💕, 🌟, 💪)

Never:
- Take sides in conflicts
- Give generic advice that ignores context
- Be preachy or lecture
- Minimize their feelings
- Share information between partners without consent"""

    NEUTRAL_PROMPT = """You are a helpful, friendly assistant for a couple. Help them with everyday questions, planning, and general conversation.

Be:
- Helpful and practical
- Friendly but not overly emotional
- Clear and concise
- Playful when appropriate

You can help with:
- Planning dates and activities
- Recommendations for movies, restaurants, etc.
- General questions and trivia
- Fun conversation starters
- Light jokes and banter"""

    def __init__(self):
        """Initialize care persona."""
        super().__init__(PersonaType.CARE)
    
    @property
    def system_prompt(self) -> str:
        """Return the care persona system prompt."""
        return self.SYSTEM_PROMPT
    
    async def generate_response(
        self,
        message: str,
        context: str,
        room_id: int
    ) -> str:
        """
        Generate an emotionally supportive response.
        
        Args:
            message: User's message
            context: Formatted context with history and memories
            room_id: Room identifier
            
        Returns:
            Supportive, coaching response
        """
        additional_instructions = """
Remember to:
- Acknowledge their feelings first
- Use "I hear you" language
- Reference any relevant memories or past conversations
- Offer both validation and gentle guidance
- End with something encouraging or a thoughtful question
"""
        
        prompt = self._format_prompt(message, context, additional_instructions)
        response = await self._generate_completion(
            prompt,
            temperature=0.7  # Balanced creativity
        )
        
        return response
    
    async def generate_neutral_response(
        self,
        message: str,
        context: str,
        room_id: int
    ) -> str:
        """
        Generate a helpful, neutral response.
        
        Args:
            message: User's message
            context: Formatted context
            room_id: Room identifier
            
        Returns:
            Helpful, practical response
        """
        prompt = f"""<|system|>
{self.NEUTRAL_PROMPT}
</|system|>

<|context|>
{context}
</|context|>

<|user|>
{message}
</|user|>

<|assistant|>
"""
        
        response = await self._generate_completion(
            prompt,
            temperature=0.8  # More creative for casual chat
        )
        
        return response
    
    async def handle_conflict(
        self,
        message: str,
        context: str,
        room_id: int
    ) -> str:
        """
        Handle messages that indicate conflict between partners.
        
        Args:
            message: User's message about conflict
            context: Formatted context
            room_id: Room identifier
            
        Returns:
            Mediating, supportive response
        """
        conflict_instructions = """
This message seems to involve a conflict. Remember to:
- Stay completely neutral between partners
- Validate BOTH perspectives
- Focus on feelings, not blame
- Suggest a constructive next step
- Don't try to "solve" everything at once
- Encourage direct, kind communication between them
"""
        
        prompt = self._format_prompt(message, context, conflict_instructions)
        response = await self._generate_completion(
            prompt,
            temperature=0.6  # More careful with conflicts
        )
        
        return response
    
    async def celebrate_milestone(
        self,
        message: str,
        context: str,
        room_id: int,
        milestone_type: str = "general"
    ) -> str:
        """
        Generate celebratory response for relationship milestones.
        
        Args:
            message: User's message
            context: Formatted context
            room_id: Room identifier
            milestone_type: Type of milestone (anniversary, achievement, etc.)
            
        Returns:
            Celebratory, warm response
        """
        celebration_instructions = f"""
This is a celebration moment! The milestone type is: {milestone_type}

Be:
- Genuinely enthusiastic and happy for them
- Specific about what makes this special
- Encouraging about their journey together
- Use celebratory emojis 🎉💕🌟
- Suggest a way to commemorate if appropriate
"""
        
        prompt = self._format_prompt(message, context, celebration_instructions)
        response = await self._generate_completion(
            prompt,
            temperature=0.8  # More expressive for celebrations
        )
        
        return response
