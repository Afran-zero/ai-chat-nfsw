"""Routes module initialization."""

from routes.rooms import router as rooms_router
from routes.chat import router as chat_router
from routes.bot import router as bot_router
from routes.memory import router as memory_router

__all__ = [
    "rooms_router",
    "chat_router", 
    "bot_router",
    "memory_router",
]
