"""Search Service

Implements hybrid search engine combining FTS5 full-text search
and VSS vector search for comprehensive code understanding.
"""

import asyncio
import json
import logging
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from functools import partial


class SearchResult:
    """Represents a search result with metadata."""
    
    def __init__(self, content: str, file_path: str, content_type: str,
                 score: float, search_type: str, metadata: Optional[Dict] = None):
        self.content = content
        self.file_path = file_path
        self.content_type = content_type
        self.score = score
        self.search_type = search_type
        self.metadata = metadata or {}
        self.rank = 0  # Will be set during result merging
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "content": self.content,
            "file_path": self.file_path,
            "content_type": self.content_type,
            "score": self.score,
            "search_type": self.search_type,
            "rank": self.rank,
            "metadata": self.metadata
        }
    
    def __repr__(self):
        return f"SearchResult(file={self.file_path}, type={self.search_type}, score={self.score:.3f})"


class FTSSearchEngine:
    """Full-text search engine using SQLite FTS5."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query for FTS5 search."""
        # Remove special characters that might break FTS5
        cleaned_query = ''.join(c for c in query if c.isalnum() or c.isspace() or c in '.-_')
        
        # Split into terms and handle phrases
        terms = cleaned_query.strip().split()
        if not terms:
            return '""'
        
        # For single term, use as-is
        if len(terms) == 1:
            return f'"{terms[0]}"'
        
        # For multiple terms, try exact phrase first, then OR terms
        phrase_query = f'"{" ".join(terms)}"'
        or_query = " OR ".join(f'"{term}"' for term in terms)
        
        return f'({phrase_query}) OR ({or_query})'
    
    async def search(self, query: str, content_types: Optional[List[str]] = None,
                    limit: int = 50) -> List[SearchResult]:
        """Perform full-text search.
        
        Args:
            query: Search query
            content_types: Filter by content types
            limit: Maximum results to return
        
        Returns:
            List of SearchResult objects
        """
        if not query.strip():
            return []
        
        try:
            # Prepare FTS query
            fts_query = self._prepare_fts_query(query)
            
            # Build SQL query
            sql = """
                SELECT 
                    ce.content,
                    ce.file_path,
                    ce.content_type,
                    ce.line_start,
                    ce.line_end,
                    ce.function_name,
                    ce.class_name,
                    bm25(code_embeddings_fts) as score
                FROM code_embeddings_fts 
                JOIN code_embeddings ce ON code_embeddings_fts.rowid = ce.id
                WHERE code_embeddings_fts MATCH ?
            """
            
            params = [fts_query]
            
            # Add content type filter
            if content_types:
                placeholders = ','.join('?' * len(content_types))
                sql += f" AND ce.content_type IN ({placeholders})"
                params.extend(content_types)
            
            sql += " ORDER BY score DESC LIMIT ?"
            params.append(limit)
            
            # Execute search
            from functools import partial
            loop = asyncio.get_event_loop()
            
            execute_func = partial(self._execute_search, sql, params, content_types)
            results = await loop.run_in_executor(None, execute_func)
            
            return results
            
        except Exception as e:
            self.logger.error(f"FTS search failed: {e}")
            return []
    
    def _execute_search(self, sql: str, params: List[Any]) -> List[SearchResult]:
        """Execute search query in thread pool."""
        results = []
        
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            
            for row in cursor.fetchall():
                metadata = {
                    "line_start": row["line_start"],
                    "line_end": row["line_end"],
                    "function_name": row["function_name"],
                    "class_name": row["class_name"]
                }
                
                result = SearchResult(
                    content=row["content"],
                    file_path=row["file_path"],
                    content_type=row["content_type"],
                    score=float(row["score"]),
                    search_type="fulltext",
                    metadata=metadata
                )
                
                results.append(result)
        
        return results


class VSSSearchEngine:
    """Vector similarity search engine using sqlite-vss."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.vss_available = False
        self._check_vss_availability()
    
    def _check_vss_availability(self):
        """Check if VSS extension is available."""
        try:
            import sqlite_vss
            
            with sqlite3.connect(self.db_path) as conn:
                try:
                    # Try to load VSS extension
                    conn.enable_load_extension(True)
                    
                    # Load vector0 extension first, then vss0
                    vss_path = "/root/miniforge3/lib/python3.12/site-packages/sqlite_vss"
                    conn.load_extension(f"{vss_path}/vector0")
                    conn.load_extension(f"{vss_path}/vss0")
                    
                    # Try to query VSS tables
                    cursor = conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_vss'"
                    )
                    vss_tables = cursor.fetchall()
                    
                    if vss_tables:
                        self.vss_available = True
                        self.logger.info(f"VSS extension available with {len(vss_tables)} tables")
                    else:
                        # Try to create a test VSS table to verify extension works
                        try:
                            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS test_vss USING vss0(embedding(3))")
                            conn.execute("DROP TABLE test_vss")
                            self.vss_available = True
                            self.logger.info("VSS extension available but no tables found yet")
                        except Exception:
                            self.logger.warning("VSS extension loaded but not functional")
                            
                except Exception as vss_error:
                    self.logger.warning(f"VSS extension loading failed: {vss_error}")
                    
        except ImportError:
            self.logger.warning("sqlite_vss module not available")
        except Exception as e:
            self.logger.warning(f"VSS availability check failed: {e}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with VSS extension."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Load VSS extension if available
        if self.vss_available:
            try:
                conn.enable_load_extension(True)
                
                # Load vector0 extension first, then vss0
                vss_path = "/root/miniforge3/lib/python3.12/site-packages/sqlite_vss"
                conn.load_extension(f"{vss_path}/vector0")
                conn.load_extension(f"{vss_path}/vss0")
            except Exception as e:
                self.logger.warning(f"Failed to load VSS extension in connection: {e}")
                self.vss_available = False
        
        return conn
    
    async def search(self, query_embedding: List[float], 
                    content_types: Optional[List[str]] = None,
                    limit: int = 50,
                    similarity_threshold: float = 0.7) -> List[SearchResult]:
        """Perform vector similarity search.
        
        Args:
            query_embedding: Query vector
            content_types: Filter by content types
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score
        
        Returns:
            List of SearchResult objects
        """

        if not self.vss_available or not query_embedding:
            return []
        
        try:
            # Determine which VSS table to use based on embedding dimensions
            embedding_dim = len(query_embedding)
            vss_table = f"code_embeddings_vss_{embedding_dim}" if embedding_dim != 384 else "code_embeddings_vss"
            
            # Build SQL query - simple VSS search first
            sql = f"""
                SELECT rowid, distance
                FROM {vss_table}
                WHERE vss_search(embedding, ?)
            """
            
            params = [json.dumps(query_embedding)]
            
            sql += " ORDER BY distance ASC LIMIT ?"
            params.append(limit)
            
            # Execute search
            loop = asyncio.get_event_loop()
            execute_func = partial(self._execute_search, sql, params, content_types)
            results = await loop.run_in_executor(None, execute_func)
            
            return results
            
        except Exception as e:
            self.logger.error(f"VSS search failed: {e}")
            return []
    
    def _execute_search(self, sql: str, params: List[Any], content_types: Optional[List[str]] = None) -> List[SearchResult]:
        """Execute VSS search query."""

        results = []
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params)
            
            # Get VSS results (rowid, distance)
            vss_results = cursor.fetchall()
            
            if not vss_results:
                return results
            
            # Get rowids for content lookup
            rowids = [row[0] for row in vss_results]
            distance_map = {row[0]: row[1] for row in vss_results}
            
            # Query content table for full information
            placeholders = ','.join('?' * len(rowids))
            content_sql = f"""
                SELECT id, content, file_path, content_type, line_start, line_end, 
                       function_name, class_name, language
                FROM code_embeddings 
                WHERE id IN ({placeholders})
            """
            
            # Add content_type filter if specified
            content_params = list(rowids)
            if content_types:
                content_type_placeholders = ','.join('?' * len(content_types))
                content_sql += f" AND content_type IN ({content_type_placeholders})"
                content_params.extend(content_types)
            
            cursor.execute(content_sql, content_params)
            
            for row in cursor.fetchall():
                row_id = row[0]
                distance = distance_map.get(row_id, 1.0)
                similarity = 1.0 - distance
                
                metadata = {
                     "line_start": row[4],
                     "line_end": row[5],
                     "function_name": row[6],
                     "class_name": row[7],
                     "language": row[8]
                 }
                
                result = SearchResult(
                    content=row[1],
                    file_path=row[2],
                    content_type=row[3],
                    score=similarity,
                    search_type="vss",
                    metadata=metadata
                )
                
                results.append(result)
            
            conn.close()
                
        except Exception as e:
            self.logger.error(f"VSS search execution failed: {e}")
        
        return results


class HybridSearchEngine:
    """Hybrid search engine combining FTS and VSS."""
    
    def __init__(self, db_path: str, embedding_service=None):
        self.db_path = db_path
        self.embedding_service = embedding_service
        self.fts_engine = FTSSearchEngine(db_path)
        self.vss_engine = VSSSearchEngine(db_path)
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize the hybrid search engine."""
        # Initialize sub-engines if they have initialize methods
        if hasattr(self.fts_engine, 'initialize'):
            await self.fts_engine.initialize()
        if hasattr(self.vss_engine, 'initialize'):
            await self.vss_engine.initialize()
        self.is_initialized = True
    
    def _normalize_scores(self, results: List[SearchResult], 
                         search_type: str) -> List[SearchResult]:
        """Normalize scores to 0-1 range."""
        if not results:
            return results
        
        if search_type == "fulltext":
            # FTS scores are typically negative (BM25), normalize to 0-1
            max_score = max(result.score for result in results)
            min_score = min(result.score for result in results)
            
            if max_score == min_score:
                for result in results:
                    result.score = 1.0
            else:
                for result in results:
                    result.score = (result.score - min_score) / (max_score - min_score)
        
        elif search_type == "semantic":
            # VSS scores are already 0-1 (similarity), but ensure they're in range
            for result in results:
                result.score = max(0.0, min(1.0, result.score))
        
        return results
    
    def _merge_results(self, fts_results: List[SearchResult], 
                      vss_results: List[SearchResult],
                      fts_weight: float = 0.6,
                      vss_weight: float = 0.4) -> List[SearchResult]:
        """Merge and rank results from different search engines.
        
        Uses Reciprocal Rank Fusion (RRF) algorithm.
        """
        # Create a map to track unique results by content hash
        result_map = {}
        
        # Add FTS results
        for i, result in enumerate(fts_results):
            content_hash = hash(result.content + result.file_path)
            if content_hash not in result_map:
                result_map[content_hash] = result
                result.rank = i + 1
            else:
                # Merge scores if same content found in both searches
                existing = result_map[content_hash]
                existing.score = (existing.score + result.score) / 2
                existing.search_type = "hybrid"
        
        # Add VSS results
        for i, result in enumerate(vss_results):
            content_hash = hash(result.content + result.file_path)
            if content_hash not in result_map:
                result_map[content_hash] = result
                result.rank = i + 1
            else:
                # Merge with existing FTS result
                existing = result_map[content_hash]
                # Use weighted combination
                if existing.search_type == "fulltext":
                    existing.score = (existing.score * fts_weight + 
                                    result.score * vss_weight)
                else:
                    existing.score = (existing.score + result.score) / 2
                existing.search_type = "hybrid"
        
        # Calculate RRF scores
        merged_results = list(result_map.values())
        for result in merged_results:
            # RRF formula: 1 / (k + rank), where k=60 is common
            rrf_score = 1.0 / (60 + result.rank)
            
            # Combine with original score
            if result.search_type == "hybrid":
                result.score = (result.score + rrf_score) / 2
            else:
                result.score = result.score * 0.7 + rrf_score * 0.3
        
        # Sort by final score
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for i, result in enumerate(merged_results):
            result.rank = i + 1
        
        return merged_results
    
    async def search(self, query: str, 
                    content_types: Optional[List[str]] = None,
                    search_type: str = "hybrid",
                    limit: int = 50,
                    fts_weight: float = 0.6,
                    vss_weight: float = 0.4,
                    similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """Perform hybrid search.
        
        Args:
            query: Search query
            content_types: Filter by content types
            search_type: "hybrid", "fulltext", or "semantic"
            limit: Maximum results to return
            fts_weight: Weight for FTS results in hybrid search
            vss_weight: Weight for VSS results in hybrid search
            similarity_threshold: Minimum similarity for VSS
        
        Returns:
            {
                "results": List[SearchResult],
                "total_results": int,
                "search_type": str,
                "query": str,
                "execution_time": float,
                "fts_results": int,
                "vss_results": int
            }
        """
        start_time = time.time()
        
        try:
            fts_results = []
            vss_results = []
            
            # Perform full-text search
            if search_type in ["hybrid", "fulltext"]:
                fts_results = await self.fts_engine.search(
                    query, content_types, limit
                )
                fts_results = self._normalize_scores(fts_results, "fulltext")
            
            # Perform vector search
            if search_type in ["hybrid", "semantic"] and self.embedding_service:
                # Generate query embedding
                embedding_result = await self.embedding_service.generate_embedding(
                    query, content_type="code"
                )
                
                if embedding_result and "embedding" in embedding_result:
                    vss_results = await self.vss_engine.search(
                        embedding_result["embedding"],
                        content_types,
                        limit,
                        similarity_threshold
                    )
                    vss_results = self._normalize_scores(vss_results, "semantic")
            
            # Merge results based on search type
            if search_type == "hybrid":
                final_results = self._merge_results(
                    fts_results, vss_results, fts_weight, vss_weight
                )
            elif search_type == "fulltext":
                final_results = fts_results
            else:  # semantic
                final_results = vss_results
            
            # Limit final results
            final_results = final_results[:limit]
            
            execution_time = time.time() - start_time
            
            return {
                "results": [result.to_dict() for result in final_results],
                "total_results": len(final_results),
                "search_type": search_type,
                "query": query,
                "execution_time": execution_time,
                "fts_results": len(fts_results),
                "vss_results": len(vss_results)
            }
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            return {
                "results": [],
                "total_results": 0,
                "search_type": search_type,
                "query": query,
                "execution_time": time.time() - start_time,
                "error": str(e),
                "fts_results": 0,
                "vss_results": 0
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get search engine status."""
        status = {
            "fts_available": True,
            "vss_available": self.vss_engine.vss_available,
            "embedding_service_available": self.embedding_service is not None,
            "database_path": self.db_path
        }
        
        # Check database tables
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = [row[0] for row in cursor.fetchall()]
                
                status["available_tables"] = tables
                status["fts_tables"] = [t for t in tables if "_fts" in t]
                status["vss_tables"] = [t for t in tables if "_vss" in t]
                
                # Get record counts
                if "code_embeddings" in tables:
                    cursor = conn.execute("SELECT COUNT(*) FROM code_embeddings")
                    status["total_embeddings"] = cursor.fetchone()[0]
                
        except Exception as e:
            status["database_error"] = str(e)
        
        return status


class SearchService:
    """Main search service interface."""
    
    def __init__(self, db_path: str, embedding_service=None):
        self.hybrid_engine = HybridSearchEngine(db_path, embedding_service)
        self.logger = logging.getLogger(__name__)
    
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Perform search using hybrid engine."""
        return await self.hybrid_engine.search(query, **kwargs)
    
    async def fulltext_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Perform full-text search only."""
        kwargs["search_type"] = "fulltext"
        return await self.hybrid_engine.search(query, **kwargs)
    
    async def semantic_search(self, query: str, **kwargs) -> Dict[str, Any]:
        """Perform semantic search only."""
        kwargs["search_type"] = "semantic"
        return await self.hybrid_engine.search(query, **kwargs)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get search service status."""
        return await self.hybrid_engine.get_status()