"""AI module initialization."""

try:
    from ai.embeddings import EmbeddingService, embedding_service, get_embedding_service
    from ai.rag_index import RAGIndex, get_rag_index
    from ai.orchestrator import Orchestrator, get_orchestrator, IntentType
    from ai.personas import BasePersona, PersonaType, PersonaRouter, CarePersona, IntimatePersona
    
    AI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AI modules not available: {e}")
    print("Install with: uv pip install llama-index llama-index-embeddings-huggingface llama-index-vector-stores-chroma")
    AI_AVAILABLE = False
    
    # Provide stubs
    EmbeddingService = None
    embedding_service = None
    get_embedding_service = lambda: None
    RAGIndex = None
    get_rag_index = lambda: None
    Orchestrator = None
    get_orchestrator = lambda: None
    IntentType = None
    BasePersona = None
    PersonaType = None
    PersonaRouter = None
    CarePersona = None
    IntimatePersona = None

__all__ = [
    "AI_AVAILABLE",
    "EmbeddingService",
    "embedding_service",
    "get_embedding_service",
    "RAGIndex",
    "get_rag_index",
    "Orchestrator",
    "get_orchestrator",
    "IntentType",
    "BasePersona",
    "PersonaType",
    "PersonaRouter",
    "CarePersona",
    "IntimatePersona",
]
