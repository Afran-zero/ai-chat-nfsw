"""
Bot service for AI assistant interactions.
Uses OpenRouter or Groq API for cloud LLM access.
"""

import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime

from config import settings
from models.room import NSFWMode
from services.room_service import room_service


# Simple in-memory storage (persists during server runtime)
_name_memory: Dict[int, Dict[str, str]] = {}  # room_id -> {user_id: name}
_conversation_history: Dict[int, List[Dict]] = {}  # room_id -> messages


class BotService:
    """
    Service for AI bot interactions.
    Uses OpenRouter or Groq API for LLM responses.
    """
    
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(self):
        """Initialize bot service."""
        self._http_client = None
        self._groq_client = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for API calls."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    def _get_groq_client(self):
        """Get Groq client for API calls."""
        if self._groq_client is None:
            try:
                from groq import Groq
                self._groq_client = Groq(api_key=settings.groq_api_key)
            except ImportError:
                print("❌ Groq package not installed. Install with: pip install groq")
                return None
        return self._groq_client
    
    def _remember_name(self, room_id: int, user_id: str, name: str):
        """Store a user's name in memory."""
        if room_id not in _name_memory:
            _name_memory[room_id] = {}
        _name_memory[room_id][user_id] = name
        print(f"💾 Remembered name: {name} for user {user_id} in room {room_id}")
    
    def _get_remembered_name(self, room_id: int, user_id: str) -> Optional[str]:
        """Get a user's remembered name."""
        return _name_memory.get(room_id, {}).get(user_id)
    
    def _get_all_names(self, room_id: int) -> Dict[str, str]:
        """Get all remembered names in a room."""
        return _name_memory.get(room_id, {})
    
    def _add_to_history(self, room_id: int, role: str, content: str):
        """Add message to conversation history."""
        if room_id not in _conversation_history:
            _conversation_history[room_id] = []
        _conversation_history[room_id].append({"role": role, "content": content})
        # Keep last 20 messages
        if len(_conversation_history[room_id]) > 20:
            _conversation_history[room_id] = _conversation_history[room_id][-20:]
    
    def _get_history(self, room_id: int) -> List[Dict]:
        """Get conversation history for a room."""
        return _conversation_history.get(room_id, [])
    
    def _extract_and_remember_name(self, message: str, room_id: int, user_id: str) -> Optional[str]:
        """Extract name from message if mentioned."""
        msg_lower = message.lower()
        name_phrases = ["my name is", "i'm ", "i am ", "call me ", "name's "]
        
        for phrase in name_phrases:
            if phrase in msg_lower:
                idx = msg_lower.find(phrase) + len(phrase)
                remaining = message[idx:].strip()
                if remaining:
                    # Get first word as name
                    name = remaining.split()[0].strip(".,!?'\"")
                    if name and len(name) > 1:
                        self._remember_name(room_id, user_id, name.capitalize())
                        return name.capitalize()
        return None
    
    def _build_system_prompt(self, room_id: int, user_id: str, nsfw_enabled: bool = False) -> str:
        """Build system prompt with context."""
        names = self._get_all_names(room_id)
        current_name = self._get_remembered_name(room_id, user_id)
        
        base_prompt = """You are a warm, caring AI companion for a private couple's chat app called Nushur. 
You're friendly, supportive, and have a gentle romantic personality.
Keep responses concise (1-3 sentences) unless asked for more detail.
Use emojis sparingly but warmly.
Remember details users share with you and reference them naturally."""
        
        if current_name:
            base_prompt += f"\n\nThe user you're talking to is named {current_name}."
        
        if names:
            names_str = ", ".join([f"{v}" for v in names.values()])
            base_prompt += f"\nPeople in this room: {names_str}"
        
        if nsfw_enabled:
            base_prompt += "\n\nNSFW mode is enabled. You can be more flirty and romantic if appropriate."
        
        return base_prompt
    
    async def _call_openrouter(self, messages: List[Dict], room_id: int, user_id: str, nsfw_enabled: bool = False) -> str:
        """Call OpenRouter API."""
        print(f"🤖 OpenRouter API key present: {bool(settings.openrouter_api_key)}")
        print(f"🤖 Model: {settings.openrouter_model}")
        
        if not settings.openrouter_api_key:
            print("⚠️ No API key, using simple response")
            return await self._simple_response(messages[-1]["content"] if messages else "", room_id, user_id)
        
        system_prompt = self._build_system_prompt(room_id, user_id, nsfw_enabled)
        
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            client = self._get_client()
            print(f"🤖 Calling OpenRouter with {len(full_messages)} messages...")
            response = await client.post(
                self.OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://nushur.app",
                    "X-Title": "Nushur Chat"
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": full_messages,
                    "max_tokens": settings.llm_max_tokens,
                    "temperature": settings.llm_temperature,
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data["choices"][0]["message"]["content"]
                print(f"✅ OpenRouter response: {result[:100]}...")
                return result
            else:
                print(f"❌ OpenRouter error: {response.status_code} - {response.text}")
                return await self._simple_response(messages[-1]["content"] if messages else "", room_id, user_id)
                
        except Exception as e:
            print(f"OpenRouter exception: {e}")
            return await self._simple_response(messages[-1]["content"] if messages else "", room_id, user_id)
    
    async def _call_groq(self, messages: List[Dict], room_id: int, user_id: str, nsfw_enabled: bool = False) -> str:
        """Call Groq API using official Python client."""
        print(f"🤖 Groq API key present: {bool(settings.groq_api_key)}")
        print(f"🤖 Model: {settings.groq_model}")
        
        if not settings.groq_api_key:
            print("⚠️ No Groq API key, using simple response")
            return await self._simple_response(messages[-1]["content"] if messages else "", room_id, user_id)
        
        groq_client = self._get_groq_client()
        if not groq_client:
            print("⚠️ Groq client not available, using simple response")
            return await self._simple_response(messages[-1]["content"] if messages else "", room_id, user_id)
        
        system_prompt = self._build_system_prompt(room_id, user_id, nsfw_enabled)
        
        full_messages = [{"role": "system", "content": system_prompt}] + messages
        
        try:
            print(f"🤖 Calling Groq with {len(full_messages)} messages...")
            
            # Run Groq client in thread pool since it's synchronous
            import asyncio
            loop = asyncio.get_event_loop()
            completion = await loop.run_in_executor(
                None,
                lambda: groq_client.chat.completions.create(
                    model=settings.groq_model,
                    messages=full_messages,
                    max_tokens=settings.llm_max_tokens,
                    temperature=settings.llm_temperature,
                )
            )
            
            result = completion.choices[0].message.content
            print(f"✅ Groq response: {result[:100]}...")
            return result
                
        except Exception as e:
            print(f"Groq exception: {e}")
            return await self._simple_response(messages[-1]["content"] if messages else "", room_id, user_id)
    
    async def _simple_response(self, message: str, room_id: int, user_id: str) -> str:
        """Simple fallback response when API is not available."""
        msg_lower = message.lower()
        
        # Check for name introduction
        extracted_name = self._extract_and_remember_name(message, room_id, user_id)
        if extracted_name:
            return f"Nice to meet you, {extracted_name}! I'll remember that."
        
        # Check if asking about name
        remembered = self._get_remembered_name(room_id, user_id)
        if any(x in msg_lower for x in ["what's my name", "do you know my name", "remember my name", "who am i"]):
            if remembered:
                return f"Of course! Your name is {remembered}"
            return "I don't think you've told me your name yet. What should I call you?"
        
        # Simple greetings
        if any(x in msg_lower for x in ["hello", "hi ", "hey", "hi!"]):
            if remembered:
                return f"Hey {remembered}! How are you doing?"
            return "Hey there! How can I help you today?"
        
        if any(x in msg_lower for x in ["how are you", "how're you", "how r u"]):
            return "I'm doing great, thanks for asking! How about you?"
        
        if any(x in msg_lower for x in ["love you", "i love"]):
            return "Aww, that's so sweet!"
        
        if any(x in msg_lower for x in ["thank", "thanks"]):
            return "You're welcome!"
        
        if any(x in msg_lower for x in ["bye", "goodbye", "good night", "goodnight"]):
            if remembered:
                return f"Bye {remembered}! Take care"
            return "Goodbye! Take care"
        
        # Default response
        if settings.openrouter_api_key:
            return "I'm thinking..."
        return "I'm here for you! (Add OPENROUTER_API_KEY to .env for full AI)"
    
    async def generate_response(
        self,
        room_id: int,
        user_message: str,
        user_id: str
    ) -> str:
        """
        Generate a bot response to a user message.
        
        Args:
            room_id: Room identifier
            user_message: The user's message
            user_id: User who sent the message
            
        Returns:
            Bot response text
        """
        # Extract and remember name if mentioned
        self._extract_and_remember_name(user_message, room_id, user_id)
        
        # Add user message to history
        self._add_to_history(room_id, "user", user_message)
        
        # Get room for NSFW mode check
        room = await room_service.get_room(room_id)
        nsfw_enabled = room.nsfw_mode == NSFWMode.ENABLED if room else False
        
        # Get conversation history
        history = self._get_history(room_id)
        
        # Generate response
        if settings.llm_provider == "groq" and settings.groq_api_key:
            response = await self._call_groq(history, room_id, user_id, nsfw_enabled)
        elif settings.llm_provider == "openrouter" and settings.openrouter_api_key:
            response = await self._call_openrouter(history, room_id, user_id, nsfw_enabled)
        else:
            response = await self._simple_response(user_message, room_id, user_id)
        
        # Add bot response to history
        self._add_to_history(room_id, "assistant", response)
        
        return response
    
    async def get_bot_status(self, room_id: int) -> Dict[str, Any]:
        """Get current bot status for a room."""
        room = await room_service.get_room(room_id)
        
        return {
            "active": True,
            "nsfw_mode": room.nsfw_mode.value if room else "disabled",
            "ai_enabled": bool(settings.openrouter_api_key or settings.groq_api_key),
            "provider": settings.llm_provider,
            "model": settings.groq_model if settings.llm_provider == "groq" else settings.openrouter_model,
            "names_remembered": len(self._get_all_names(room_id)),
        }


# Singleton instance
bot_service = BotService()
