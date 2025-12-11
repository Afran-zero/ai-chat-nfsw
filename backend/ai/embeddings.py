"""
Embedding service for text embeddings using free models.
Supports BGE-small and E5-small embedding models.
"""

from typing import List, Optional, Union
import numpy as np
from functools import lru_cache

from config import settings


class EmbeddingService:
    """
    Service for generating text embeddings using free models.
    Supports:
    - BAAI/bge-small-en-v1.5
    - intfloat/e5-small-v2
    """
    
    # Reference embeddings for intent classification
    CARE_REFERENCE_TEXTS = [
        "I need relationship advice",
        "How can I communicate better with my partner",
        "I'm feeling sad and need support",
        "Help me understand my emotions",
        "What should I do about this conflict",
        "I need help with trust issues",
        "How do I express my feelings",
        "We're having communication problems",
        "I want to improve our relationship",
        "How do I deal with jealousy",
    ]
    
    NSFW_REFERENCE_TEXTS = [
        "I want something romantic and intimate",
        "Let's talk about our desires",
        "I'm in the mood for something playful",
        "Tell me something seductive",
        "I want to explore our intimacy",
        "Let's have some adult fun",
        "I'm feeling flirty tonight",
        "Talk dirty to me",
        "Let's spice things up",
        "I want something sensual",
    ]
    
    NEUTRAL_REFERENCE_TEXTS = [
        "What's the weather like",
        "Tell me a joke",
        "What should we have for dinner",
        "Plan our weekend",
        "Remind me about the appointment",
        "What movie should we watch",
        "Help me with this recipe",
        "What time is it",
        "Tell me about something interesting",
        "Let's play a game",
    ]
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize embedding service.
        
        Args:
            model_name: HuggingFace model name (default from settings)
        """
        self._model_name = model_name or settings.embedding_model
        self._model = None
        self._reference_embeddings = None
    
    def _load_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model
    
    def _compute_reference_embeddings(self):
        """Precompute reference embeddings for intent classification."""
        if self._reference_embeddings is None:
            model = self._load_model()
            
            self._reference_embeddings = {
                "care": model.encode(self.CARE_REFERENCE_TEXTS, convert_to_numpy=True),
                "nsfw": model.encode(self.NSFW_REFERENCE_TEXTS, convert_to_numpy=True),
                "neutral": model.encode(self.NEUTRAL_REFERENCE_TEXTS, convert_to_numpy=True),
            }
        return self._reference_embeddings
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        model = self._load_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def compute_similarity(
        self,
        embedding1: Union[List[float], np.ndarray],
        embedding2: Union[List[float], np.ndarray]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score (0-1)
        """
        v1 = np.array(embedding1)
        v2 = np.array(embedding2)
        
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def classify_intent(self, text: str) -> dict:
        """
        Classify text intent using embedding similarity.
        NO REGEX - purely embedding-based classification.
        
        Args:
            text: Text to classify
            
        Returns:
            Dict with scores for each intent category
        """
        model = self._load_model()
        references = self._compute_reference_embeddings()
        
        # Get query embedding
        query_embedding = model.encode(text, convert_to_numpy=True)
        
        scores = {}
        
        for category, ref_embeddings in references.items():
            # Compute similarity to all references in category
            similarities = []
            for ref_emb in ref_embeddings:
                sim = self.compute_similarity(query_embedding, ref_emb)
                similarities.append(sim)
            
            # Use max similarity as category score
            scores[category] = max(similarities)
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        
        # Determine primary intent
        primary_intent = max(scores, key=scores.get)
        
        return {
            "primary_intent": primary_intent,
            "scores": scores,
            "confidence": scores[primary_intent]
        }
    
    def is_nsfw_intent(self, text: str, threshold: float = 0.4) -> bool:
        """
        Check if text has NSFW intent.
        
        Args:
            text: Text to check
            threshold: Minimum score to consider NSFW
            
        Returns:
            True if NSFW intent detected
        """
        intent = self.classify_intent(text)
        return (
            intent["primary_intent"] == "nsfw" and 
            intent["confidence"] >= threshold
        )
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings from this model."""
        model = self._load_model()
        return model.get_sentence_embedding_dimension()


@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance."""
    return EmbeddingService()


# Convenience access
embedding_service = get_embedding_service()
