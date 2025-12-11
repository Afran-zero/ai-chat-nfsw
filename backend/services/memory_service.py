"""
Memory service for ChromaDB vector storage and retrieval.
Handles embedding storage, deduplication, and memory lifecycle.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from models.message import MemoryEntry, MemoryCategory, MemorySearchResult


class MemoryService:
    """
    Service for managing vector memory using ChromaDB.
    Handles embedding storage, retrieval, and lifecycle.
    """
    
    def __init__(self):
        """Initialize ChromaDB client and collection."""
        # New ChromaDB API (v1.0+)
        self._client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory
        )
        
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        self._embedding_model = None
    
    def _get_embedding_model(self):
        """Lazy load embedding model."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(settings.embedding_model)
        return self._embedding_model
    
    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        model = self._get_embedding_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    async def add_memory(
        self,
        room_id: int,
        sender_id: str,
        text: str,
        category: MemoryCategory,
        message_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """
        Add a memory entry to the vector store.
        
        Args:
            room_id: Room identifier
            sender_id: Who created this memory
            text: Memory content
            category: Memory category
            message_id: Optional source message ID
            metadata: Additional metadata
            
        Returns:
            Created memory entry
        """
        # Check for duplicates using similarity
        is_duplicate = await self._check_duplicate(room_id, text)
        if is_duplicate:
            raise ValueError("Similar memory already exists")
        
        # Generate embedding
        embedding = self._generate_embedding(text)
        
        # Create entry
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            text=text,
            room_id=room_id,
            sender_id=sender_id,
            category=category,
            message_id=message_id,
            timestamp=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Handle category-specific rules
        await self._apply_category_rules(room_id, category, text)
        
        # Add to ChromaDB
        self._collection.add(
            ids=[entry.id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[entry.to_chroma_metadata()]
        )
        
        return entry
    
    async def _check_duplicate(self, room_id: int, text: str) -> bool:
        """
        Check if similar memory already exists.
        
        Args:
            room_id: Room identifier
            text: Text to check
            
        Returns:
            True if duplicate found
        """
        embedding = self._generate_embedding(text)
        
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=1,
            where={"room_id": room_id}
        )
        
        if results['distances'] and results['distances'][0]:
            # Cosine distance, lower is more similar
            similarity = 1 - results['distances'][0][0]
            return similarity >= settings.cosine_similarity_threshold
        
        return False
    
    async def _apply_category_rules(
        self,
        room_id: int,
        category: MemoryCategory,
        text: str
    ) -> None:
        """
        Apply category-specific memory management rules.
        
        - EVENT: Keep forever
        - PREFERENCE: Overwrite previous by similar content
        - BOUNDARY: Keep forever
        - EMOTION: Keep last 10
        """
        if category == MemoryCategory.EMOTION:
            # Keep only last 10 emotional memories
            results = self._collection.get(
                where={
                    "$and": [
                        {"room_id": room_id},
                        {"category": MemoryCategory.EMOTION.value}
                    ]
                }
            )
            
            if results['ids'] and len(results['ids']) >= 10:
                # Sort by timestamp and remove oldest
                entries = list(zip(
                    results['ids'],
                    results['metadatas']
                ))
                entries.sort(key=lambda x: x[1].get('timestamp', ''), reverse=True)
                
                # Delete entries beyond limit
                to_delete = [e[0] for e in entries[9:]]
                if to_delete:
                    self._collection.delete(ids=to_delete)
        
        elif category == MemoryCategory.PREFERENCE:
            # Find and remove similar preferences
            embedding = self._generate_embedding(text)
            
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=5,
                where={
                    "$and": [
                        {"room_id": room_id},
                        {"category": MemoryCategory.PREFERENCE.value}
                    ]
                }
            )
            
            if results['ids'] and results['distances']:
                to_delete = []
                for i, (id_, dist) in enumerate(zip(results['ids'][0], results['distances'][0])):
                    similarity = 1 - dist
                    if similarity >= 0.7:  # Similar preference threshold
                        to_delete.append(id_)
                
                if to_delete:
                    self._collection.delete(ids=to_delete)
    
    async def search_memories(
        self,
        room_id: int,
        query: str,
        limit: int = 10,
        category: Optional[MemoryCategory] = None
    ) -> List[MemorySearchResult]:
        """
        Search memories by semantic similarity.
        
        Args:
            room_id: Room identifier
            query: Search query
            limit: Maximum results
            category: Optional category filter
            
        Returns:
            List of matching memories
        """
        embedding = self._generate_embedding(query)
        
        where_filter: Dict[str, Any] = {"room_id": room_id}
        if category:
            where_filter = {
                "$and": [
                    {"room_id": room_id},
                    {"category": category.value}
                ]
            }
        
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=limit,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )
        
        memories = []
        if results['ids'] and results['ids'][0]:
            for i, id_ in enumerate(results['ids'][0]):
                doc = results['documents'][0][i] if results['documents'] else ""
                meta = results['metadatas'][0][i] if results['metadatas'] else {}
                dist = results['distances'][0][i] if results['distances'] else 1.0
                
                memories.append(MemorySearchResult(
                    id=id_,
                    text=doc,
                    category=MemoryCategory(meta.get('category', 'general')),
                    similarity_score=1 - dist,
                    timestamp=datetime.fromisoformat(meta.get('timestamp', datetime.utcnow().isoformat())),
                    sender_id=meta.get('sender_id', '')
                ))
        
        return memories
    
    async def get_context_memories(
        self,
        room_id: int,
        recent_messages: List[str],
        limit: int = 10
    ) -> List[MemorySearchResult]:
        """
        Get relevant memories based on recent conversation.
        
        Args:
            room_id: Room identifier
            recent_messages: Recent message contents
            limit: Maximum memories to retrieve
            
        Returns:
            Relevant memories for context
        """
        if not recent_messages:
            return []
        
        # Combine recent messages for context query
        context_text = " ".join(recent_messages[-5:])  # Last 5 messages
        
        return await self.search_memories(room_id, context_text, limit)
    
    async def get_room_memories(
        self,
        room_id: int,
        category: Optional[MemoryCategory] = None
    ) -> List[MemoryEntry]:
        """
        Get all memories for a room.
        
        Args:
            room_id: Room identifier
            category: Optional category filter
            
        Returns:
            All memories in the room
        """
        where_filter: Dict[str, Any] = {"room_id": room_id}
        if category:
            where_filter = {
                "$and": [
                    {"room_id": room_id},
                    {"category": category.value}
                ]
            }
        
        results = self._collection.get(
            where=where_filter,
            include=["documents", "metadatas"]
        )
        
        memories = []
        if results['ids']:
            for i, id_ in enumerate(results['ids']):
                doc = results['documents'][i] if results['documents'] else ""
                meta = results['metadatas'][i] if results['metadatas'] else {}
                
                memories.append(MemoryEntry(
                    id=id_,
                    text=doc,
                    room_id=room_id,
                    sender_id=meta.get('sender_id', ''),
                    category=MemoryCategory(meta.get('category', 'general')),
                    message_id=meta.get('message_id'),
                    timestamp=datetime.fromisoformat(meta.get('timestamp', datetime.utcnow().isoformat())),
                    metadata={}
                ))
        
        return memories
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory.
        
        Args:
            memory_id: Memory identifier
            
        Returns:
            True if deleted
        """
        try:
            self._collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False
    
    async def clear_room_memories(self, room_id: int) -> int:
        """
        Clear all memories for a room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Number of deleted memories
        """
        results = self._collection.get(
            where={"room_id": room_id}
        )
        
        if results['ids']:
            count = len(results['ids'])
            self._collection.delete(ids=results['ids'])
            return count
        
        return 0
    
    async def get_memory_stats(self, room_id: int) -> Dict[str, int]:
        """
        Get memory statistics for a room.
        
        Args:
            room_id: Room identifier
            
        Returns:
            Dict with category counts
        """
        results = self._collection.get(
            where={"room_id": room_id},
            include=["metadatas"]
        )
        
        stats = {cat.value: 0 for cat in MemoryCategory}
        
        if results['metadatas']:
            for meta in results['metadatas']:
                cat = meta.get('category', 'general')
                if cat in stats:
                    stats[cat] += 1
        
        stats['total'] = sum(stats.values())
        return stats


# Singleton instance
memory_service = MemoryService()
