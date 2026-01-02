"""
Couple Chat AI - Main FastAPI Application

A private two-person chat platform with:
- Encrypted text, image, and voice messages
- "View Once" image mode
- Message reactions
- AI bot with multiple personas
- "Tap to Remember" → embeddings → vector memory
- Consent-aware NSFW activation
"""

import sys
from pathlib import Path

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config import settings
from routes import rooms_router, chat_router, bot_router, memory_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs startup and shutdown tasks.
    """
    # Startup
    print(f"🚀 Starting {settings.app_name}...")
    print(f"📍 Environment: {settings.environment}")
    print(f"🔐 Encryption: AES-256-GCM enabled")
    print(f"🧠 Embedding model: {settings.embedding_model}")
    chroma_info = "Cloud" if settings.chroma_cloud_enabled else f"Local ({settings.chroma_persist_directory})"
    print(f"💾 ChromaDB: {chroma_info}")
    print(f"✅ Server ready!")
    
    yield
    
    # Shutdown
    print(f"👋 Shutting down {settings.app_name}...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    ## Couple Chat AI API
    
    A private chat platform for two people with AI assistance.
    
    ### Features
    - **Real-time chat** via WebSocket
    - **Encrypted media** with AES-256-GCM
    - **View Once** images that delete after viewing
    - **Message reactions** (heart, laugh, cry, shocked, angry)
    - **AI bot** with automatic persona switching
    - **Memory system** using embeddings and ChromaDB
    - **NSFW mode** requiring mutual consent
    
    ### Authentication
    Rooms are protected with a secret key. To join:
    1. Create a room to get the secret
    2. Share the room_id and secret with your partner
    3. Both partners join using the credentials
    
    ### Demo Room
    For testing: `room_id=1`, `room_secret="12589"`
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:8000",  # FastAPI docs
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Register routers
app.include_router(rooms_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(bot_router, prefix="/api")
app.include_router(memory_router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "services": {
            "api": "up",
            "websocket": "up"
        }
    }


# API info
@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "version": "1.0.0",
        "endpoints": {
            "rooms": "/api/rooms",
            "chat": "/api/chat",
            "bot": "/api/bot",
            "memory": "/api/memory"
        },
        "websocket": "/api/chat/ws/{room_id}/{user_id}",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
