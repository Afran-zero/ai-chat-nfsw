"""
RAG Index using LlamaIndex for memory retrieval and context fusion.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from llama_index.core import (
    VectorStoreIndex,
    Document,
    StorageContext,
    Settings as LlamaSettings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from config import settings


class RAGIndex:
    """
    RAG (Retrieval Augmented Generation) index using LlamaIndex.
    Handles document storage and retrieval for AI context.
    """
    
    def __init__(self):
        """Initialize RAG index with ChromaDB backend."""
        # Initialize embedding model
        self._embed_model = HuggingFaceEmbedding(
            model_name=settings.embedding_model
        )
        
        # Set up LlamaIndex settings
        LlamaSettings.embed_model = self._embed_model
        LlamaSettings.chunk_size = 512
        LlamaSettings.chunk_overlap = 50
        
        # Initialize ChromaDB
        self._chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory
        )
        
        # Collection for RAG documents
        self._collection = self._chroma_client.get_or_create_collection(
            name="rag_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Set up vector store
        self._vector_store = ChromaVectorStore(
            chroma_collection=self._collection
        )
        
        # Storage context
        self._storage_context = StorageContext.from_defaults(
            vector_store=self._vector_store
        )
        
        # Initialize index
        self._index = VectorStoreIndex.from_vector_store(
            vector_store=self._vector_store,
            storage_context=self._storage_context,
        )
        
        # Node parser for chunking
        self._node_parser = SentenceSplitter(
            chunk_size=512,
            chunk_overlap=50
        )
    
    def add_document(
        self,
        text: str,
        room_id: int,
        doc_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a document to the RAG index.
        
        Args:
            text: Document text
            room_id: Associated room
            doc_type: Type of document (message, memory, onboarding)
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        doc_metadata = {
            "room_id": str(room_id),
            "doc_type": doc_type,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        document = Document(
            text=text,
            metadata=doc_metadata
        )
        
        # Parse into nodes and add to index
        nodes = self._node_parser.get_nodes_from_documents([document])
        self._index.insert_nodes(nodes)
        
        return document.doc_id
    
    def add_messages(
        self,
        messages: List[Dict[str, Any]],
        room_id: int
    ) -> List[str]:
        """
        Add multiple messages to the index.
        
        Args:
            messages: List of message dicts with content, sender_id, timestamp
            room_id: Room identifier
            
        Returns:
            List of document IDs
        """
        documents = []
        
        for msg in messages:
            doc = Document(
                text=msg.get("content", ""),
                metadata={
                    "room_id": str(room_id),
                    "doc_type": "message",
                    "sender_id": msg.get("sender_id", ""),
                    "timestamp": msg.get("timestamp", datetime.utcnow().isoformat()),
                }
            )
            documents.append(doc)
        
        if documents:
            nodes = self._node_parser.get_nodes_from_documents(documents)
            self._index.insert_nodes(nodes)
        
        return [doc.doc_id for doc in documents]
    
    def add_memories(
        self,
        memories: List[Dict[str, Any]],
        room_id: int
    ) -> List[str]:
        """
        Add memories to the index.
        
        Args:
            memories: List of memory dicts
            room_id: Room identifier
            
        Returns:
            List of document IDs
        """
        documents = []
        
        for mem in memories:
            doc = Document(
                text=mem.get("text", ""),
                metadata={
                    "room_id": str(room_id),
                    "doc_type": "memory",
                    "category": mem.get("category", "general"),
                    "sender_id": mem.get("sender_id", ""),
                    "relevance": str(mem.get("relevance", 0.0)),
                }
            )
            documents.append(doc)
        
        if documents:
            nodes = self._node_parser.get_nodes_from_documents(documents)
            self._index.insert_nodes(nodes)
        
        return [doc.doc_id for doc in documents]
    
    def retrieve(
        self,
        query: str,
        room_id: int,
        top_k: int = 10,
        doc_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            room_id: Room to search in
            top_k: Number of results
            doc_type: Optional filter by document type
            
        Returns:
            List of relevant documents with scores
        """
        # Create retriever with filters
        filters = {"room_id": str(room_id)}
        if doc_type:
            filters["doc_type"] = doc_type
        
        retriever = VectorIndexRetriever(
            index=self._index,
            similarity_top_k=top_k,
        )
        
        # Retrieve nodes
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            # Filter by room_id manually since ChromaDB filter might not work
            node_room = node.metadata.get("room_id", "")
            if node_room == str(room_id):
                results.append({
                    "text": node.text,
                    "score": node.score,
                    "metadata": node.metadata,
                })
        
        return results
    
    def build_context(
        self,
        query: str,
        room_id: int,
        message_history: List[Dict[str, Any]],
        memories: List[Dict[str, Any]],
        onboarding: Dict[str, Any]
    ) -> str:
        """
        Build a fused context string for the LLM.
        
        Args:
            query: Current user query
            room_id: Room identifier
            message_history: Recent messages
            memories: Retrieved memories
            onboarding: Room onboarding data
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Add onboarding context
        if onboarding:
            onboarding_text = self._format_onboarding(onboarding)
            if onboarding_text:
                context_parts.append(f"## Relationship Context\n{onboarding_text}")
        
        # Add memories
        if memories:
            memories_text = self._format_memories(memories)
            context_parts.append(f"## Remembered Information\n{memories_text}")
        
        # Add message history
        if message_history:
            history_text = self._format_history(message_history[-10:])  # Last 10
            context_parts.append(f"## Recent Conversation\n{history_text}")
        
        # Retrieve additional relevant context
        retrieved = self.retrieve(query, room_id, top_k=5)
        if retrieved:
            retrieved_text = self._format_retrieved(retrieved)
            context_parts.append(f"## Relevant Context\n{retrieved_text}")
        
        return "\n\n".join(context_parts)
    
    def _format_onboarding(self, onboarding: Dict[str, Any]) -> str:
        """Format onboarding data for context."""
        parts = []
        
        if onboarding.get("relationship_type"):
            parts.append(f"- Relationship: {onboarding['relationship_type']}")
        
        if onboarding.get("anniversary_date"):
            parts.append(f"- Anniversary: {onboarding['anniversary_date']}")
        
        return "\n".join(parts)
    
    def _format_memories(self, memories: List[Dict[str, Any]]) -> str:
        """Format memories for context."""
        lines = []
        for mem in memories:
            category = mem.get("category", "general")
            text = mem.get("text", "")
            relevance = mem.get("relevance", 0)
            lines.append(f"- [{category}] {text} (relevance: {relevance:.2f})")
        return "\n".join(lines)
    
    def _format_history(self, messages: List[Dict[str, Any]]) -> str:
        """Format message history for context."""
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role.capitalize()}: {content}")
        return "\n".join(lines)
    
    def _format_retrieved(self, docs: List[Dict[str, Any]]) -> str:
        """Format retrieved documents for context."""
        lines = []
        for doc in docs:
            text = doc.get("text", "")
            score = doc.get("score", 0)
            doc_type = doc.get("metadata", {}).get("doc_type", "unknown")
            lines.append(f"- [{doc_type}] {text[:200]}... (score: {score:.2f})")
        return "\n".join(lines)
    
    def clear_room_documents(self, room_id: int) -> int:
        """
        Clear all documents for a room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Number of documents cleared
        """
        # Get all documents for room
        results = self._collection.get(
            where={"room_id": str(room_id)}
        )
        
        if results['ids']:
            count = len(results['ids'])
            self._collection.delete(ids=results['ids'])
            return count
        
        return 0


# Singleton instance
_rag_index: Optional[RAGIndex] = None


def get_rag_index() -> RAGIndex:
    """Get singleton RAG index instance."""
    global _rag_index
    if _rag_index is None:
        _rag_index = RAGIndex()
    return _rag_index
