"""
Intimate persona for consensual adult conversations.
ONLY activated after explicit mutual consent from both partners.
"""

from ai.personas.base import BasePersona, PersonaType


class IntimatePersona(BasePersona):
    """
    Intimate/romantic persona for consensual adult conversations.
    
    CRITICAL: This persona is ONLY activated when:
    1. NSFW intent is detected
    2. BOTH partners have explicitly consented
    3. The room's nsfw_mode is ENABLED
    
    Without all three conditions, the orchestrator will NOT route to this persona.
    """
    
    SYSTEM_PROMPT = """You are a playful, romantic companion for a consenting adult couple who have both agreed to engage in intimate conversation.

Your role is to:
1. Be FLIRTY and PLAYFUL in a tasteful way
2. CELEBRATE their intimacy and connection
3. SUGGEST romantic ideas and scenarios
4. RESPOND to their romantic energy appropriately
5. MAINTAIN boundaries around illegal or harmful content

Your tone should be:
- Warm, sensual, and inviting
- Playfully teasing but respectful
- Responsive to their comfort level
- Celebratory of their connection

Guidelines:
- Match their energy level - don't escalate beyond their comfort
- Use romantic and sensual language, not crude or vulgar
- Focus on connection and pleasure, not objectification
- Be creative with suggestions and scenarios
- Include affectionate emojis (💋, 🔥, 💕, ✨)
- Reference their relationship context for personalization

ABSOLUTE BOUNDARIES - Never engage with:
- Anything involving minors
- Non-consensual scenarios
- Violent or harmful content
- Illegal activities
- Content either partner has explicitly said is off-limits

If a boundary is approached, gently redirect to something acceptable."""

    CONSENT_CHECK_PROMPT = """Before we continue in this direction, I want to make sure you're both comfortable.

This type of conversation requires consent from both partners. If you'd like to enable intimate mode, both of you need to agree.

Would you like me to request consent from your partner? 💕"""

    def __init__(self):
        """Initialize intimate persona."""
        super().__init__(PersonaType.INTIMATE)
    
    @property
    def system_prompt(self) -> str:
        """Return the intimate persona system prompt."""
        return self.SYSTEM_PROMPT
    
    async def generate_response(
        self,
        message: str,
        context: str,
        room_id: int
    ) -> str:
        """
        Generate a romantic/intimate response.
        
        This method assumes consent has been verified by the orchestrator.
        
        Args:
            message: User's message
            context: Formatted context with history and memories
            room_id: Room identifier
            
        Returns:
            Playful, romantic response
        """
        additional_instructions = """
Remember:
- Both partners have consented to this type of conversation
- Match their energy - don't go further than they have
- Keep things sensual and romantic, not crude
- Reference their relationship for personalization
- Celebrate their connection and intimacy
- Be creative but stay within their comfort zone
"""
        
        prompt = self._format_prompt(message, context, additional_instructions)
        response = await self._generate_completion(
            prompt,
            temperature=0.8  # More creative
        )
        
        return response
    
    async def generate_flirty_response(
        self,
        message: str,
        context: str,
        room_id: int
    ) -> str:
        """
        Generate a lighter flirty response.
        
        Args:
            message: User's message
            context: Formatted context
            room_id: Room identifier
            
        Returns:
            Light, flirty response
        """
        flirty_instructions = """
Keep this response light and flirty:
- Playful teasing
- Sweet compliments
- Romantic suggestions
- Affectionate banter
- Nothing too explicit
"""
        
        prompt = self._format_prompt(message, context, flirty_instructions)
        response = await self._generate_completion(
            prompt,
            temperature=0.85
        )
        
        return response
    
    async def suggest_romantic_activity(
        self,
        context: str,
        room_id: int,
        activity_type: str = "date"
    ) -> str:
        """
        Suggest a romantic activity based on their relationship.
        
        Args:
            context: Formatted context
            room_id: Room identifier
            activity_type: Type of activity (date, surprise, intimate)
            
        Returns:
            Creative romantic suggestion
        """
        activity_prompts = {
            "date": "Suggest a creative, romantic date idea based on what you know about them.",
            "surprise": "Suggest a sweet surprise one partner could do for the other.",
            "intimate": "Suggest a romantic way they could connect more deeply tonight."
        }
        
        instruction = activity_prompts.get(activity_type, activity_prompts["date"])
        
        prompt = f"""<|system|>
{self.system_prompt}

{instruction}
Be specific and personalized based on their relationship context.
</|system|>

<|context|>
{context}
</|context|>

<|user|>
Suggest something romantic for us!
</|user|>

<|assistant|>
"""
        
        response = await self._generate_completion(
            prompt,
            temperature=0.9  # Very creative
        )
        
        return response
    
    def get_consent_check_message(self) -> str:
        """
        Get the consent check message to send when NSFW is detected without consent.
        
        Returns:
            Consent request message
        """
        return self.CONSENT_CHECK_PROMPT
    
    async def handle_boundary(
        self,
        message: str,
        context: str,
        room_id: int,
        boundary_type: str
    ) -> str:
        """
        Handle when a boundary is approached.
        
        Args:
            message: User's message
            context: Formatted context
            room_id: Room identifier
            boundary_type: Type of boundary approached
            
        Returns:
            Gentle redirection response
        """
        boundary_instruction = f"""
The user's message approaches a boundary ({boundary_type}).
Gently redirect the conversation while:
- Not shaming or making them feel bad
- Suggesting an alternative that's within bounds
- Keeping the romantic energy flowing
- Being understanding and kind
"""
        
        prompt = self._format_prompt(message, context, boundary_instruction)
        response = await self._generate_completion(
            prompt,
            temperature=0.6  # More careful
        )
        
        return response
