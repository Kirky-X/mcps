"""Embedding Handler for MCP Protocol

Handles embedding generation and management operations.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseHandler


class EmbeddingHandler(BaseHandler):
    """Handler for embedding-related MCP operations."""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.embedding_service = None  # Will be injected
    
    async def _initialize_impl(self):
        """Initialize embedding handler."""
        # Verify database tables exist
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN (
                    'code_embeddings', 'code_embeddings_vss'
                )
                """
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            required_tables = ['code_embeddings']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                raise RuntimeError(f"Required embedding tables not found: {missing_tables}")
            
            # VSS extension not available in current setup
            self.vss_available = False
            self.logger.info("VSS extension not configured - using basic similarity search")
    
    def set_embedding_service(self, embedding_service):
        """Set embedding service."""
        self.embedding_service = embedding_service
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(a * a for a in vec2))
        
        if magnitude1 == 0.0 or magnitude2 == 0.0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def handle_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate embeddings for text content.
        
        Args:
            params: {
                "text": str,
                "content_type": str,    # "code", "documentation", "comment", etc.
                "content_id": str,      # Optional: ID of related content
                "metadata": dict,       # Optional: additional metadata
                "model": str            # Optional: specific embedding model
            }
        
        Returns:
            Generated embedding with metadata
        """
        self._validate_params(params, ["text"])
        
        if not self.embedding_service:
            return self._format_error_response("Embedding service not configured")
        
        text = params["text"]
        content_type = self._get_param(params, "content_type", "text")
        content_id = self._get_param(params, "content_id", None)
        metadata = self._get_param(params, "metadata", {})
        model = self._get_param(params, "model", None)
        
        return await self._execute_with_error_handling(
            "embedding_generation",
            self._generate_embedding,
            text,
            content_type,
            content_id,
            metadata,
            model
        )
    
    async def _generate_embedding(self, text: str, content_type: str,
                                content_id: Optional[str], metadata: Dict[str, Any],
                                model: Optional[str]) -> Dict[str, Any]:
        """Generate embedding using embedding service."""
        # Generate embedding
        embedding_result = await self.embedding_service.generate_embedding(
            text=text,
            model=model
        )
        
        if not embedding_result:
            return self._format_error_response("Failed to generate embedding")
        
        # Store embedding in database
        embedding_id = await self._store_embedding(
            text=text,
            embedding=embedding_result["embedding"],
            content_type=content_type,
            content_id=content_id,
            metadata={
                **metadata,
                "model": embedding_result.get("model", "unknown"),
                "dimensions": len(embedding_result["embedding"])
            }
        )
        
        return self._format_response({
            "embedding_id": embedding_id,
            "embedding": embedding_result["embedding"],
            "dimensions": len(embedding_result["embedding"]),
            "content_type": content_type,
            "content_id": content_id,
            "metadata": {
                "model": embedding_result.get("model", "unknown"),
                "generation_time": embedding_result.get("generation_time", 0),
                "text_length": len(text)
            }
        })
    
    async def handle_batch_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate embeddings for multiple texts in batch.
        
        Args:
            params: {
                "texts": List[str],
                "content_type": str,
                "content_ids": List[str],  # Optional: IDs for each text
                "metadata": List[dict],    # Optional: metadata for each text
                "model": str               # Optional: specific embedding model
            }
        
        Returns:
            List of generated embeddings with metadata
        """
        self._validate_params(params, ["texts"])
        
        if not self.embedding_service:
            return self._format_error_response("Embedding service not configured")
        
        texts = params["texts"]
        content_type = self._get_param(params, "content_type", "text")
        content_ids = self._get_param(params, "content_ids", [None] * len(texts))
        metadata_list = self._get_param(params, "metadata", [{}] * len(texts))
        model = self._get_param(params, "model", None)
        
        # Validate input lengths
        if len(content_ids) != len(texts):
            content_ids = [None] * len(texts)
        if len(metadata_list) != len(texts):
            metadata_list = [{}] * len(texts)
        
        return await self._execute_with_error_handling(
            "batch_embedding_generation",
            self._generate_batch_embeddings,
            texts,
            content_type,
            content_ids,
            metadata_list,
            model
        )
    
    async def _generate_batch_embeddings(self, texts: List[str], content_type: str,
                                       content_ids: List[Optional[str]], 
                                       metadata_list: List[Dict[str, Any]],
                                       model: Optional[str]) -> Dict[str, Any]:
        """Generate embeddings for multiple texts."""
        results = []
        failed_indices = []
        
        # Generate embeddings in batch if service supports it
        if hasattr(self.embedding_service, 'generate_batch_embeddings'):
            batch_result = await self.embedding_service.generate_batch_embeddings(
                texts=texts,
                model=model
            )
            
            if batch_result and batch_result.get("success"):
                embeddings = batch_result["embeddings"]
                
                # Store each embedding
                for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                    try:
                        embedding_id = await self._store_embedding(
                            text=text,
                            embedding=embedding,
                            content_type=content_type,
                            content_id=content_ids[i],
                            metadata={
                                **metadata_list[i],
                                "model": batch_result.get("model", "unknown"),
                                "dimensions": len(embedding),
                                "batch_index": i
                            }
                        )
                        
                        results.append({
                            "embedding_id": embedding_id,
                            "embedding": embedding,
                            "dimensions": len(embedding),
                            "content_type": content_type,
                            "content_id": content_ids[i],
                            "success": True
                        })
                    except Exception as e:
                        failed_indices.append(i)
                        results.append({
                            "success": False,
                            "error": str(e),
                            "text_index": i
                        })
            else:
                # Fallback to individual generation
                return await self._generate_individual_embeddings(
                    texts, content_type, content_ids, metadata_list, model
                )
        else:
            # Generate embeddings individually
            return await self._generate_individual_embeddings(
                texts, content_type, content_ids, metadata_list, model
            )
        
        return self._format_response({
            "results": results,
            "total_count": len(texts),
            "success_count": len(results) - len(failed_indices),
            "failed_count": len(failed_indices),
            "failed_indices": failed_indices
        })
    
    async def _generate_individual_embeddings(self, texts: List[str], content_type: str,
                                            content_ids: List[Optional[str]], 
                                            metadata_list: List[Dict[str, Any]],
                                            model: Optional[str]) -> Dict[str, Any]:
        """Generate embeddings individually for each text."""
        results = []
        failed_indices = []
        
        for i, text in enumerate(texts):
            try:
                embedding_result = await self.embedding_service.generate_embedding(
                    text=text,
                    model=model
                )
                
                if embedding_result:
                    embedding_id = await self._store_embedding(
                        text=text,
                        embedding=embedding_result["embedding"],
                        content_type=content_type,
                        content_id=content_ids[i],
                        metadata={
                            **metadata_list[i],
                            "model": embedding_result.get("model", "unknown"),
                            "dimensions": len(embedding_result["embedding"]),
                            "individual_generation": True
                        }
                    )
                    
                    results.append({
                        "embedding_id": embedding_id,
                        "embedding": embedding_result["embedding"],
                        "dimensions": len(embedding_result["embedding"]),
                        "content_type": content_type,
                        "content_id": content_ids[i],
                        "success": True
                    })
                else:
                    failed_indices.append(i)
                    results.append({
                        "success": False,
                        "error": "Failed to generate embedding",
                        "text_index": i
                    })
            except Exception as e:
                failed_indices.append(i)
                results.append({
                    "success": False,
                    "error": str(e),
                    "text_index": i
                })
        
        return self._format_response({
            "results": results,
            "total_count": len(texts),
            "success_count": len(results) - len(failed_indices),
            "failed_count": len(failed_indices),
            "failed_indices": failed_indices
        })
    
    async def handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for similar embeddings.
        
        Args:
            params: {
                "query_text": str,         # Text to find similar embeddings for
                "query_embedding": List[float],  # Or direct embedding vector
                "max_results": int,
                "similarity_threshold": float,   # Optional: minimum similarity
                "content_type": str,             # Optional: filter by content type
                "metadata_filters": dict         # Optional: filter by metadata
            }
        
        Returns:
            Similar embeddings with similarity scores
        """
        if not self.vss_available:
            return self._format_error_response("Vector search not available")
        
        query_text = self._get_param(params, "query_text", None)
        query_embedding = self._get_param(params, "query_embedding", None)
        
        if not query_text and not query_embedding:
            return self._format_error_response("Either query_text or query_embedding must be provided")
        
        max_results = self._get_param(params, "max_results", 10)
        similarity_threshold = self._get_param(params, "similarity_threshold", 0.0)
        content_type = self._get_param(params, "content_type", None)
        metadata_filters = self._get_param(params, "metadata_filters", {})
        
        return await self._execute_with_error_handling(
            "embedding_search",
            self._search_embeddings,
            query_text,
            query_embedding,
            max_results,
            similarity_threshold,
            content_type,
            metadata_filters
        )
    
    async def _search_embeddings(self, query_text: Optional[str], 
                               query_embedding: Optional[List[float]],
                               max_results: int, similarity_threshold: float,
                               content_type: Optional[str], 
                               metadata_filters: Dict[str, Any]) -> Dict[str, Any]:
        """Search for similar embeddings using VSS."""
        # Get query embedding
        if query_text and not query_embedding:
            if not self.embedding_service:
                return self._format_error_response("Embedding service not configured")
            
            embedding_result = await self.embedding_service.generate_embedding(query_text)
            if not embedding_result:
                return self._format_error_response("Failed to generate query embedding")
            
            query_embedding = embedding_result["embedding"]
        
        if not query_embedding:
            return self._format_error_response("No query embedding available")
        
        # Build search query with filters
        where_conditions = []
        params = [json.dumps(query_embedding)]
        
        if content_type:
            where_conditions.append("ce.content_type = ?")
            params.append(content_type)
        
        # Add metadata filters
        for key, value in metadata_filters.items():
            where_conditions.append("JSON_EXTRACT(ce.metadata, ?) = ?")
            params.extend([f"$.{key}", value])
        
        where_clause = ""
        if where_conditions:
            where_clause = "AND " + " AND ".join(where_conditions)
        
        # Perform basic similarity search (without VSS)
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                f"""
                SELECT 
                    id, content_id, content_type, content_text,
                    embedding, metadata, created_at
                FROM code_embeddings
                WHERE 1=1 {where_clause}
                """,
                params[1:]  # Skip the embedding parameter for basic search
            )
            
            rows = await cursor.fetchall()
            results = []
            
            for row in rows:
                # Calculate cosine similarity manually
                stored_embedding = json.loads(row[4])
                similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                
                if similarity >= similarity_threshold:
                    result = {
                        "embedding_id": row[0],
                        "content_id": row[1],
                        "content_type": row[2],
                        "content_text": row[3],
                        "metadata": json.loads(row[5]) if row[5] else {},
                        "created_at": row[6],
                        "similarity": similarity,
                        "distance": 1.0 - similarity
                    }
                    results.append(result)
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x["similarity"], reverse=True)
            results = results[:max_results]
        
        return self._format_response({
            "query_text": query_text,
            "results": results,
            "total_results": len(results),
            "similarity_threshold": similarity_threshold,
            "metadata": {
                "query_embedding_dimensions": len(query_embedding),
                "content_type_filter": content_type,
                "metadata_filters": metadata_filters
            }
        })
    
    async def handle_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get embedding service status and statistics.
        
        Returns:
            Service status and database statistics
        """
        return await self._execute_with_error_handling(
            "embedding_status",
            self._get_embedding_status
        )
    
    async def _get_embedding_status(self) -> Dict[str, Any]:
        """Get embedding service status."""
        status = {
            "service_available": self.embedding_service is not None,
            "vss_available": self.vss_available,
            "database_stats": {}
        }
        
        # Get database statistics
        async with self.db_manager.get_raw_connection() as conn:
            # Count total embeddings
            cursor = await conn.execute("SELECT COUNT(*) FROM code_embeddings")
            total_embeddings = (await cursor.fetchone())[0]
            
            # Count by content type
            cursor = await conn.execute(
                "SELECT content_type, COUNT(*) FROM code_embeddings GROUP BY content_type"
            )
            content_type_counts = dict(await cursor.fetchall())
            
            # Get recent activity
            cursor = await conn.execute(
                """
                SELECT COUNT(*) FROM code_embeddings 
                WHERE created_at > datetime('now', '-24 hours')
                """
            )
            recent_embeddings = (await cursor.fetchone())[0]
            
            status["database_stats"] = {
                "total_embeddings": total_embeddings,
                "content_type_counts": content_type_counts,
                "recent_embeddings_24h": recent_embeddings
            }
        
        # Get service status if available
        if self.embedding_service:
            service_status = await self.embedding_service.get_status()
            status["service_status"] = service_status
        
        return self._format_response(status)
    
    async def _store_embedding(self, text: str, embedding: List[float],
                             content_type: str, content_id: Optional[str],
                             metadata: Dict[str, Any]) -> str:
        """Store embedding in database."""
        embedding_id = str(uuid.uuid4())
        
        async with self.db_manager.get_raw_connection() as conn:
            # Store in main embeddings table
            await conn.execute(
                """
                INSERT INTO code_embeddings (
                    id, content_id, content_type, content_text, 
                    embedding, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    embedding_id,
                    content_id,
                    content_type,
                    text,
                    json.dumps(embedding),
                    json.dumps(metadata),
                    datetime.utcnow().isoformat()
                )
            )
            
            # VSS not available in current setup
            self.logger.debug(f"Stored embedding {embedding_id} for content_type: {content_type}")
            
            await conn.commit()
        
        return embedding_id