"""Retrieval system for finding similar trades using RAG."""

from typing import List, Dict, Any, Optional
from ai.rag.chroma_client import get_chroma_client
from ai.rag.embeddings import get_embedding_service


class RetrievalService:
    """Service for retrieving similar trades using RAG."""
    
    def __init__(self):
        """Initialize retrieval service."""
        self.chroma_client = get_chroma_client()
        self.embedding_service = get_embedding_service()
    
    def find_similar_trades(
        self,
        query_text: str,
        n_results: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar trades based on query text.
        
        Args:
            query_text: Text description of what to search for
            n_results: Number of similar trades to return (default: 5)
            filters: Optional metadata filters (e.g., {"outcome": "win"})
            
        Returns:
            List of dictionaries with trade_id, distance, metadata, and document
        """
        # Generate embedding for query
        query_embedding = self.embedding_service.generate_embedding(query_text)
        
        # Find similar trades
        similar_trades = self.chroma_client.find_similar_trades(
            query_embedding=query_embedding,
            n_results=n_results,
            where=filters
        )
        
        return similar_trades
    
    def find_similar_trades_by_chart(
        self,
        chart_description: str,
        symbol: Optional[str] = None,
        direction: Optional[str] = None,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar trades based on chart description.
        
        Args:
            chart_description: Description of the chart (e.g., "Bullish setup with POI at 1.0850")
            symbol: Optional symbol filter
            direction: Optional direction filter ("long" or "short")
            n_results: Number of results to return
            
        Returns:
            List of similar trades
        """
        # Build query text
        query_parts = [chart_description]
        if symbol:
            query_parts.append(f"Symbol: {symbol}")
        if direction:
            query_parts.append(f"Direction: {direction}")
        
        query_text = "\n".join(query_parts)
        
        # Build filters
        filters = {}
        if symbol:
            filters["symbol"] = symbol
        if direction:
            filters["direction"] = direction
        
        return self.find_similar_trades(
            query_text=query_text,
            n_results=n_results,
            filters=filters if filters else None
        )


# Singleton instance
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Get or create the singleton retrieval service instance."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service

