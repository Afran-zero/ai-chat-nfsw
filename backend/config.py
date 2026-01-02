"""
Configuration module for the Couple Chat AI application.
Loads environment variables and provides typed configuration.
"""

from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Couple Chat AI"
    debug: bool = False
    environment: Literal["development", "production"] = "development"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anon/service key")
    supabase_storage_bucket: str = "media"
    
    # Encryption
    encryption_key: str = Field(..., description="32-byte AES encryption key (base64 encoded)")
    
    # Room Demo Config
    demo_room_id: int = 1
    demo_room_secret: str = "12589"
    
    # File Upload Limits
    max_file_size_mb: int = 5
    allowed_image_types: str = "image/jpeg,image/png,image/gif,image/webp"
    allowed_audio_types: str = "audio/mpeg,audio/wav,audio/ogg,audio/webm"
    
    @property
    def allowed_image_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_image_types.split(",")]
    
    @property
    def allowed_audio_types_list(self) -> list[str]:
        return [t.strip() for t in self.allowed_audio_types.split(",")]
    
    # ChromaDB
    chroma_cloud_enabled: bool = False
    chroma_api_key: str = ""
    chroma_tenant: str = ""
    chroma_database: str = ""
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "couple_memories"
    
    # Embedding Model
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384
    
    # LLM Configuration - OpenRouter (cloud) or Local
    openrouter_api_key: str = ""  # Get from https://openrouter.ai/keys
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"  # Free model!
    llm_provider: str = "openrouter"  # "openrouter", "groq", or "local"
    
    # Groq API Configuration
    groq_api_key: str = ""  # Get from https://console.groq.com/
    groq_model: str = "llama-3.1-8b-instant"  # Fast inference model
    
    # Local LLM (if using local)
    llm_model_path: str = "./models/llama-3.1-8b-instruct.gguf"
    llm_context_length: int = 4096
    llm_max_tokens: int = 512
    llm_temperature: float = 0.7
    
    # Memory Configuration
    memory_retrieval_limit: int = 10
    message_history_limit: int = 20
    cosine_similarity_threshold: float = 0.85
    
    # NSFW Configuration
    nsfw_consent_timeout_hours: int = 24
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()
