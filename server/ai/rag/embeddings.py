"""Embedding generation service using OpenAI embeddings API."""

import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenAI embeddings model (text-embedding-3-small is cheaper, text-embedding-3-large is more accurate)
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


class EmbeddingService:
    """Service for generating embeddings using OpenAI API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize embedding service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = EMBEDDING_MODEL
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[EmbeddingService] Error generating embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch processing).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            print(f"[EmbeddingService] Error generating batch embeddings: {e}")
            raise
    
    def create_trade_text(
        self,
        symbol: str,
        direction: str,
        entry_method: Optional[str] = None,
        outcome: Optional[str] = None,
        annotations: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> str:
        """
        Create a text representation of a trade for embedding.
        
        This text will be used to generate embeddings that capture the trade's characteristics.
        
        Args:
            symbol: Trading symbol (e.g., "6E", "CL")
            direction: Trade direction ("long" or "short")
            entry_method: Entry method name (e.g., "IFVG", "50% of zone")
            outcome: Trade outcome ("win", "loss", "breakeven")
            annotations: Dictionary with POI, BOS, circles data
            notes: Additional notes about the trade
            
        Returns:
            Formatted text string for embedding
        """
        parts = []
        
        # Basic trade info
        parts.append(f"Symbol: {symbol}")
        parts.append(f"Direction: {direction}")
        
        if entry_method:
            parts.append(f"Entry Method: {entry_method}")
        
        if outcome:
            parts.append(f"Outcome: {outcome}")
        
        # Annotations
        if annotations:
            if annotations.get("poi"):
                poi = annotations["poi"]
                if isinstance(poi, dict):
                    parts.append(f"POI: Price level with coordinates")
                elif isinstance(poi, list):
                    parts.append(f"POI: {len(poi)} price levels")
            
            if annotations.get("bos"):
                bos = annotations["bos"]
                if isinstance(bos, dict):
                    parts.append(f"BOS: Break of structure line")
                elif isinstance(bos, list):
                    parts.append(f"BOS: {len(bos)} break of structure lines")
            
            if annotations.get("circles"):
                circles = annotations["circles"]
                if isinstance(circles, list):
                    parts.append(f"Circles: {len(circles)} marked areas")
        
        # Notes
        if notes:
            parts.append(f"Notes: {notes}")
        
        return "\n".join(parts)


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service

