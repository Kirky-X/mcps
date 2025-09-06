"""Vector Cache Service for MCP DevAgent.

Provides caching mechanisms for query embeddings and precomputed knowledge base vectors.
"""

import hashlib
import json
import logging
import os
import pickle
import sqlite3
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CacheEntry:
    """Cache entry for embeddings."""
    key: str
    embedding: List[float]
    content_type: str
    provider: str
    model: str
    created_at: float
    access_count: int = 0
    last_accessed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "embedding": self.embedding,
            "content_type": self.content_type,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        return cls(**data)


class VectorCacheService:
    """Service for caching query embeddings and managing precomputed vectors."""
    
    def __init__(self, cache_dir: str = "data/cache", max_cache_size: int = 10000):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_db_path = self.cache_dir / "vector_cache.db"
        self.max_cache_size = max_cache_size
        self.logger = logging.getLogger(__name__)
        
        # In-memory cache for frequently accessed embeddings
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.memory_cache_size = 1000
        
        self._initialize_cache_db()
    
    def _initialize_cache_db(self):
        """Initialize the cache database."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS vector_cache (
                        cache_key TEXT PRIMARY KEY,
                        embedding BLOB NOT NULL,
                        content_type TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        model TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        access_count INTEGER DEFAULT 0,
                        last_accessed REAL DEFAULT 0.0
                    )
                """)
                
                # Create index for faster lookups
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cache_access 
                    ON vector_cache(last_accessed DESC)
                """)
                
                # Create knowledge base table for precomputed vectors
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_base (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        subcategory TEXT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        embedding BLOB NOT NULL,
                        metadata TEXT,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL
                    )
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_knowledge_category 
                    ON knowledge_base(category, subcategory)
                """)
                
                conn.commit()
                self.logger.info(f"Vector cache database initialized at {self.cache_db_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize cache database: {e}")
            raise
    
    def _generate_cache_key(self, text: str, content_type: str, provider: str, model: str) -> str:
        """Generate a unique cache key for the given parameters."""
        key_data = f"{text}|{content_type}|{provider}|{model}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    async def get_cached_embedding(self, text: str, content_type: str, 
                                 provider: str, model: str) -> Optional[List[float]]:
        """Get cached embedding if available."""
        cache_key = self._generate_cache_key(text, content_type, provider, model)
        
        # Check memory cache first
        if cache_key in self.memory_cache:
            entry = self.memory_cache[cache_key]
            entry.access_count += 1
            entry.last_accessed = time.time()
            self.logger.debug(f"Cache hit (memory): {cache_key[:16]}...")
            return entry.embedding
        
        # Check database cache
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.execute(
                    "SELECT embedding, access_count FROM vector_cache WHERE cache_key = ?",
                    (cache_key,)
                )
                row = cursor.fetchone()
                
                if row:
                    embedding = pickle.loads(row[0])
                    access_count = row[1] + 1
                    
                    # Update access statistics
                    conn.execute(
                        "UPDATE vector_cache SET access_count = ?, last_accessed = ? WHERE cache_key = ?",
                        (access_count, time.time(), cache_key)
                    )
                    conn.commit()
                    
                    # Add to memory cache if frequently accessed
                    if access_count > 3:
                        self._add_to_memory_cache(cache_key, embedding, content_type, provider, model)
                    
                    self.logger.debug(f"Cache hit (database): {cache_key[:16]}...")
                    return embedding
                    
        except Exception as e:
            self.logger.error(f"Error retrieving cached embedding: {e}")
        
        return None
    
    async def cache_embedding(self, text: str, embedding: List[float], 
                            content_type: str, provider: str, model: str):
        """Cache an embedding for future use."""
        cache_key = self._generate_cache_key(text, content_type, provider, model)
        current_time = time.time()
        
        try:
            # Store in database
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO vector_cache 
                    (cache_key, embedding, content_type, provider, model, created_at, last_accessed)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (cache_key, pickle.dumps(embedding), content_type, provider, model, 
                     current_time, current_time)
                )
                conn.commit()
            
            # Add to memory cache
            self._add_to_memory_cache(cache_key, embedding, content_type, provider, model)
            
            # Clean up old entries if cache is too large
            await self._cleanup_cache()
            
            self.logger.debug(f"Cached embedding: {cache_key[:16]}...")
            
        except Exception as e:
            self.logger.error(f"Error caching embedding: {e}")
    
    def _add_to_memory_cache(self, cache_key: str, embedding: List[float], 
                           content_type: str, provider: str, model: str):
        """Add entry to memory cache."""
        if len(self.memory_cache) >= self.memory_cache_size:
            # Remove least recently used entry
            lru_key = min(self.memory_cache.keys(), 
                         key=lambda k: self.memory_cache[k].last_accessed)
            del self.memory_cache[lru_key]
        
        entry = CacheEntry(
            key=cache_key,
            embedding=embedding,
            content_type=content_type,
            provider=provider,
            model=model,
            created_at=time.time(),
            last_accessed=time.time()
        )
        self.memory_cache[cache_key] = entry
    
    async def _cleanup_cache(self):
        """Clean up old cache entries to maintain size limits."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                # Count current entries
                cursor = conn.execute("SELECT COUNT(*) FROM vector_cache")
                count = cursor.fetchone()[0]
                
                if count > self.max_cache_size:
                    # Remove oldest entries
                    entries_to_remove = count - self.max_cache_size + 100  # Remove extra for buffer
                    conn.execute(
                        """
                        DELETE FROM vector_cache 
                        WHERE cache_key IN (
                            SELECT cache_key FROM vector_cache 
                            ORDER BY last_accessed ASC 
                            LIMIT ?
                        )
                        """,
                        (entries_to_remove,)
                    )
                    conn.commit()
                    self.logger.info(f"Cleaned up {entries_to_remove} old cache entries")
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {e}")
    
    async def add_knowledge_base_entry(self, category: str, title: str, content: str, 
                                     embedding: List[float], subcategory: str = None, 
                                     metadata: Dict[str, Any] = None):
        """Add entry to precomputed knowledge base."""
        try:
            current_time = time.time()
            metadata_json = json.dumps(metadata) if metadata else None
            
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO knowledge_base 
                    (category, subcategory, title, content, embedding, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (category, subcategory, title, content, pickle.dumps(embedding), 
                     metadata_json, current_time, current_time)
                )
                conn.commit()
                
            self.logger.info(f"Added knowledge base entry: {category}/{title}")
            
        except Exception as e:
            self.logger.error(f"Error adding knowledge base entry: {e}")
    
    async def search_knowledge_base(self, category: str = None, 
                                  subcategory: str = None, 
                                  limit: int = 100) -> List[Dict[str, Any]]:
        """Search precomputed knowledge base entries."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                if category and subcategory:
                    cursor = conn.execute(
                        """
                        SELECT id, category, subcategory, title, content, embedding, metadata
                        FROM knowledge_base 
                        WHERE category = ? AND subcategory = ?
                        ORDER BY updated_at DESC
                        LIMIT ?
                        """,
                        (category, subcategory, limit)
                    )
                elif category:
                    cursor = conn.execute(
                        """
                        SELECT id, category, subcategory, title, content, embedding, metadata
                        FROM knowledge_base 
                        WHERE category = ?
                        ORDER BY updated_at DESC
                        LIMIT ?
                        """,
                        (category, limit)
                    )
                else:
                    cursor = conn.execute(
                        """
                        SELECT id, category, subcategory, title, content, embedding, metadata
                        FROM knowledge_base 
                        ORDER BY updated_at DESC
                        LIMIT ?
                        """,
                        (limit,)
                    )
                
                results = []
                for row in cursor.fetchall():
                    entry = {
                        "id": row[0],
                        "category": row[1],
                        "subcategory": row[2],
                        "title": row[3],
                        "content": row[4],
                        "embedding": pickle.loads(row[5]),
                        "metadata": json.loads(row[6]) if row[6] else None
                    }
                    results.append(entry)
                
                return results
                
        except Exception as e:
            self.logger.error(f"Error searching knowledge base: {e}")
            return []
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                # Vector cache stats
                cursor = conn.execute("SELECT COUNT(*) FROM vector_cache")
                cache_count = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT SUM(access_count) FROM vector_cache")
                total_hits = cursor.fetchone()[0] or 0
                
                # Knowledge base stats
                cursor = conn.execute("SELECT COUNT(*) FROM knowledge_base")
                kb_count = cursor.fetchone()[0]
                
                cursor = conn.execute(
                    "SELECT category, COUNT(*) FROM knowledge_base GROUP BY category"
                )
                kb_categories = dict(cursor.fetchall())
                
                return {
                    "cache_entries": cache_count,
                    "memory_cache_entries": len(self.memory_cache),
                    "total_cache_hits": total_hits,
                    "knowledge_base_entries": kb_count,
                    "knowledge_base_categories": kb_categories,
                    "cache_hit_rate": total_hits / max(cache_count, 1),
                    "cache_db_path": str(self.cache_db_path)
                }
                
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {}
    
    async def clear_cache(self, category: str = None):
        """Clear cache entries."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                if category == "vector_cache":
                    conn.execute("DELETE FROM vector_cache")
                    self.memory_cache.clear()
                    self.logger.info("Cleared vector cache")
                elif category == "knowledge_base":
                    conn.execute("DELETE FROM knowledge_base")
                    self.logger.info("Cleared knowledge base")
                else:
                    conn.execute("DELETE FROM vector_cache")
                    conn.execute("DELETE FROM knowledge_base")
                    self.memory_cache.clear()
                    self.logger.info("Cleared all cache")
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")