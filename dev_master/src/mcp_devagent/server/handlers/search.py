"""Search Handler for MCP Protocol

Handles hybrid search operations combining FTS5 and VSS.
"""

import json
import math
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseHandler


class SearchHandler(BaseHandler):
    """Handler for search-related MCP operations."""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.embedding_service = None  # Will be injected
    
    async def _initialize_impl(self):
        """Initialize search handler."""
        # Verify database tables exist
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN (
                    'agent_interactions', 'code_files',
                    'code_embeddings', 'search_sessions'
                )
                """
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            required_tables = ['agent_interactions', 'code_files']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                raise RuntimeError(f"Required search tables not found: {missing_tables}")
            
            # Check if VSS tables exist (optional for vector search)
            self.vss_available = 'code_embeddings' in tables
            if self.vss_available:
                self.logger.info("VSS vector search available")
            else:
                self.logger.warning("VSS vector search not available")
    
    def set_embedding_service(self, embedding_service):
        """Set embedding service for vector search."""
        self.embedding_service = embedding_service
    
    async def handle_hybrid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform hybrid search combining FTS5 and VSS.
        
        Args:
            params: {
                "query": str,
                "search_type": str,  # "cot_records", "code_artifacts", "both"
                "max_results": int,
                "weights": dict,     # Optional: {"fts": 0.6, "vss": 0.4}
                "filters": dict      # Optional filters
            }
        
        Returns:
            Combined search results with relevance scores
        """
        self._validate_params(params, ["query"])
        
        query = params["query"]
        search_type = self._get_param(params, "search_type", "both")
        max_results = self._get_param(params, "max_results", 10)
        weights = self._get_param(params, "weights", {"fts": 0.6, "vss": 0.4})
        filters = self._get_param(params, "filters", {})
        
        return await self._execute_with_error_handling(
            "hybrid_search",
            self._perform_hybrid_search,
            query,
            search_type,
            max_results,
            weights,
            filters
        )
    
    async def _perform_hybrid_search(self, query: str, search_type: str, 
                                   max_results: int, weights: Dict[str, float],
                                   filters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform hybrid search combining FTS5 and VSS."""
        results = {
            "query": query,
            "search_type": search_type,
            "results": [],
            "metadata": {
                "total_results": 0,
                "fts_results": 0,
                "vss_results": 0,
                "weights": weights
            }
        }
        
        # Perform FTS5 search
        fts_results = await self._perform_fts_search(query, search_type, max_results * 2, filters)
        results["metadata"]["fts_results"] = len(fts_results)
        
        # Perform VSS search if available and embedding service is set
        vss_results = []
        if self.vss_available and self.embedding_service:
            vss_results = await self._perform_vss_search(query, search_type, max_results * 2, filters)
            results["metadata"]["vss_results"] = len(vss_results)
        
        # Combine and rank results
        combined_results = await self._combine_search_results(
            fts_results, vss_results, weights, max_results
        )
        
        results["results"] = combined_results
        results["metadata"]["total_results"] = len(combined_results)
        
        return self._format_response(results)
    
    async def handle_fulltext(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform FTS5 full-text search.
        
        Args:
            params: {
                "query": str,
                "search_type": str,
                "max_results": int,
                "filters": dict
            }
        
        Returns:
            FTS5 search results
        """
        self._validate_params(params, ["query"])
        
        query = params["query"]
        search_type = self._get_param(params, "search_type", "both")
        max_results = self._get_param(params, "max_results", 10)
        filters = self._get_param(params, "filters", {})
        
        return await self._execute_with_error_handling(
            "fulltext_search",
            self._perform_fts_search_only,
            query,
            search_type,
            max_results,
            filters
        )
    
    async def _perform_fts_search_only(self, query: str, search_type: str, 
                                     max_results: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform FTS5 search only."""
        fts_results = await self._perform_fts_search(query, search_type, max_results, filters)
        
        return self._format_response({
            "query": query,
            "search_type": search_type,
            "results": fts_results,
            "metadata": {
                "total_results": len(fts_results),
                "search_method": "fts5"
            }
        })
    
    async def handle_semantic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform semantic vector search.
        
        Args:
            params: {
                "query": str,
                "search_type": str,
                "max_results": int,
                "filters": dict
            }
        
        Returns:
            VSS search results
        """
        self._validate_params(params, ["query"])
        
        if not self.vss_available:
            return self._format_error_response("Vector search not available")
        
        if not self.embedding_service:
            return self._format_error_response("Embedding service not configured")
        
        query = params["query"]
        search_type = self._get_param(params, "search_type", "both")
        max_results = self._get_param(params, "max_results", 10)
        filters = self._get_param(params, "filters", {})
        
        return await self._execute_with_error_handling(
            "semantic_search",
            self._perform_vss_search_only,
            query,
            search_type,
            max_results,
            filters
        )
    
    async def _perform_vss_search_only(self, query: str, search_type: str, 
                                     max_results: int, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Perform VSS search only."""
        vss_results = await self._perform_vss_search(query, search_type, max_results, filters)
        
        return self._format_response({
            "query": query,
            "search_type": search_type,
            "results": vss_results,
            "metadata": {
                "total_results": len(vss_results),
                "search_method": "vss"
            }
        })
    
    async def _perform_fts_search(self, query: str, search_type: str, 
                                max_results: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform FTS5 full-text search."""
        results = []
        
        # Prepare FTS5 query (escape special characters)
        fts_query = self._prepare_fts_query(query)
        
        async with self.db_manager.get_raw_connection() as conn:
            # Search CoT records if requested
            if search_type in ["cot_records", "both"]:
                cot_results = await self._search_cot_records_fts(conn, fts_query, max_results, filters)
                results.extend(cot_results)
            
            # Search code artifacts if requested
            if search_type in ["code_artifacts", "both"]:
                code_results = await self._search_code_artifacts_fts(conn, fts_query, max_results, filters)
                results.extend(code_results)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return results[:max_results]
    
    async def _search_cot_records_fts(self, conn, fts_query: str, max_results: int, 
                                    filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search CoT records using FTS5."""
        # Build WHERE clause for filters
        where_conditions = []
        params = [fts_query]
        
        if "run_id" in filters:
            where_conditions.append("cot.run_id = ?")
            params.append(filters["run_id"])
        
        if "agent_type" in filters:
            where_conditions.append("cot.agent_type = ?")
            params.append(filters["agent_type"])
        
        where_clause = ""
        if where_conditions:
            where_clause = "AND " + " AND ".join(where_conditions)
        
        cursor = await conn.execute(
            f"""
            SELECT 
                cot.id, cot.run_id, cot.agent_type, cot.operation_type,
                cot.reasoning, cot.context, cot.created_at,
                fts.rank
            FROM cot_records_fts fts
            JOIN cot_records cot ON cot.id = fts.rowid
            WHERE cot_records_fts MATCH ? {where_clause}
            ORDER BY fts.rank
            LIMIT ?
            """,
            params + [max_results]
        )
        
        rows = await cursor.fetchall()
        results = []
        
        for row in rows:
            result = {
                "id": row[0],
                "type": "cot_record",
                "run_id": row[1],
                "agent_type": row[2],
                "operation_type": row[3],
                "reasoning": row[4],
                "context": json.loads(row[5]) if row[5] else {},
                "created_at": row[6],
                "score": -row[7],  # FTS5 rank is negative, convert to positive
                "search_method": "fts5"
            }
            results.append(result)
        
        return results
    
    async def _search_code_artifacts_fts(self, conn, fts_query: str, max_results: int, 
                                       filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search code artifacts using FTS5."""
        # Build WHERE clause for filters
        where_conditions = []
        params = [fts_query]
        
        if "file_type" in filters:
            where_conditions.append("ca.file_type = ?")
            params.append(filters["file_type"])
        
        if "project_id" in filters:
            where_conditions.append("ca.project_id = ?")
            params.append(filters["project_id"])
        
        where_clause = ""
        if where_conditions:
            where_clause = "AND " + " AND ".join(where_conditions)
        
        cursor = await conn.execute(
            f"""
            SELECT 
                ca.id, ca.file_path, ca.file_type, ca.content,
                ca.metadata, ca.project_id, ca.created_at,
                fts.rank
            FROM code_artifacts_fts fts
            JOIN code_artifacts ca ON ca.id = fts.rowid
            WHERE code_artifacts_fts MATCH ? {where_clause}
            ORDER BY fts.rank
            LIMIT ?
            """,
            params + [max_results]
        )
        
        rows = await cursor.fetchall()
        results = []
        
        for row in rows:
            result = {
                "id": row[0],
                "type": "code_artifact",
                "file_path": row[1],
                "file_type": row[2],
                "content": row[3],
                "metadata": json.loads(row[4]) if row[4] else {},
                "project_id": row[5],
                "created_at": row[6],
                "score": -row[7],  # FTS5 rank is negative, convert to positive
                "search_method": "fts5"
            }
            results.append(result)
        
        return results
    
    async def _perform_vss_search(self, query: str, search_type: str, 
                                max_results: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform VSS vector search."""
        if not self.embedding_service:
            return []
        
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)
        if not query_embedding:
            return []
        
        results = []
        
        async with self.db_manager.get_raw_connection() as conn:
            # Search using VSS
            cursor = await conn.execute(
                """
                SELECT 
                    ce.content_id, ce.content_type, ce.content_text,
                    ce.metadata, ce.created_at,
                    vss.distance
                FROM code_embeddings_vss vss
                JOIN code_embeddings ce ON ce.id = vss.rowid
                WHERE vss_search(vss.embedding, ?)
                ORDER BY vss.distance
                LIMIT ?
                """,
                (json.dumps(query_embedding), max_results)
            )
            
            rows = await cursor.fetchall()
            
            for row in rows:
                # Convert distance to similarity score (0-1)
                distance = row[5]
                similarity = 1.0 / (1.0 + distance)
                
                result = {
                    "id": row[0],
                    "type": row[1],
                    "content": row[2],
                    "metadata": json.loads(row[3]) if row[3] else {},
                    "created_at": row[4],
                    "score": similarity,
                    "distance": distance,
                    "search_method": "vss"
                }
                results.append(result)
        
        return results
    
    async def _combine_search_results(self, fts_results: List[Dict[str, Any]], 
                                    vss_results: List[Dict[str, Any]], 
                                    weights: Dict[str, float], 
                                    max_results: int) -> List[Dict[str, Any]]:
        """Combine and rank FTS and VSS search results."""
        # Normalize scores to 0-1 range
        fts_normalized = self._normalize_scores(fts_results)
        vss_normalized = self._normalize_scores(vss_results)
        
        # Create combined results map
        combined_map = {}
        
        # Add FTS results
        for result in fts_normalized:
            key = self._get_result_key(result)
            combined_map[key] = {
                **result,
                "fts_score": result["score"],
                "vss_score": 0.0,
                "combined_score": result["score"] * weights.get("fts", 0.6)
            }
        
        # Add/merge VSS results
        for result in vss_normalized:
            key = self._get_result_key(result)
            if key in combined_map:
                # Merge with existing FTS result
                combined_map[key]["vss_score"] = result["score"]
                combined_map[key]["combined_score"] = (
                    combined_map[key]["fts_score"] * weights.get("fts", 0.6) +
                    result["score"] * weights.get("vss", 0.4)
                )
                combined_map[key]["search_method"] = "hybrid"
            else:
                # Add as VSS-only result
                combined_map[key] = {
                    **result,
                    "fts_score": 0.0,
                    "vss_score": result["score"],
                    "combined_score": result["score"] * weights.get("vss", 0.4)
                }
        
        # Sort by combined score and return top results
        combined_results = list(combined_map.values())
        combined_results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return combined_results[:max_results]
    
    def _normalize_scores(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize scores to 0-1 range."""
        if not results:
            return results
        
        scores = [r.get("score", 0) for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            # All scores are the same
            for result in results:
                result["score"] = 1.0
        else:
            # Normalize to 0-1 range
            for result in results:
                original_score = result.get("score", 0)
                normalized_score = (original_score - min_score) / (max_score - min_score)
                result["score"] = normalized_score
        
        return results
    
    def _get_result_key(self, result: Dict[str, Any]) -> str:
        """Generate unique key for result deduplication."""
        return f"{result.get('type', 'unknown')}:{result.get('id', 'unknown')}"
    
    def _prepare_fts_query(self, query: str) -> str:
        """Prepare query for FTS5 search (escape special characters)."""
        # Simple escaping for FTS5
        # In production, this should be more sophisticated
        escaped = query.replace('"', '""')
        return f'"{escaped}"'