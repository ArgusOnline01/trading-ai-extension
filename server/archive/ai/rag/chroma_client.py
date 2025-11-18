"""Chroma vector database client for storing and retrieving trade embeddings."""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import chromadb
from chromadb.config import Settings

# Chroma database will be stored locally
CHROMA_DB_PATH = Path(__file__).parent.parent.parent / "data" / "chroma_db"
CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)

COLLECTION_NAME = "annotated_trades"


class ChromaClient:
    """Client for interacting with Chroma vector database."""
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize Chroma client.
        
        Args:
            persist_directory: Directory to persist Chroma database (defaults to server/data/chroma_db)
        """
        if persist_directory is None:
            persist_directory = str(CHROMA_DB_PATH)
        
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self._get_or_create_collection()
    
    def _get_or_create_collection(self):
        """Get or create the annotated_trades collection."""
        try:
            collection = self.client.get_collection(name=COLLECTION_NAME)
            print(f"[Chroma] Found existing collection: {COLLECTION_NAME}")
            return collection
        except Exception:
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=COLLECTION_NAME,
                metadata={"description": "Annotated trades for AI learning"}
            )
            print(f"[Chroma] Created new collection: {COLLECTION_NAME}")
            return collection
    
    def add_trade(
        self,
        trade_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        document: Optional[str] = None
    ):
        """
        Add a trade to the vector database.
        
        Args:
            trade_id: Unique trade identifier
            embedding: Vector embedding (list of floats)
            metadata: Metadata dictionary (symbol, entry_method, outcome, etc.)
            document: Optional text document (description of the trade)
        """
        try:
            self.collection.add(
                ids=[trade_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[document] if document else None
            )
            print(f"[Chroma] Added trade {trade_id} to collection")
        except Exception as e:
            print(f"[Chroma] Error adding trade {trade_id}: {e}")
            raise
    
    def update_trade(
        self,
        trade_id: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[str] = None
    ):
        """
        Update an existing trade in the vector database.
        
        Args:
            trade_id: Unique trade identifier
            embedding: Updated vector embedding (optional)
            metadata: Updated metadata (optional)
            document: Updated document (optional)
        """
        try:
            update_data = {}
            if embedding is not None:
                update_data["embeddings"] = [embedding]
            if metadata is not None:
                update_data["metadatas"] = [metadata]
            if document is not None:
                update_data["documents"] = [document]
            
            if update_data:
                self.collection.update(
                    ids=[trade_id],
                    **update_data
                )
                print(f"[Chroma] Updated trade {trade_id}")
        except Exception as e:
            print(f"[Chroma] Error updating trade {trade_id}: {e}")
            raise
    
    def find_similar_trades(
        self,
        query_embedding: List[float],
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar trades using similarity search.
        
        Args:
            query_embedding: Query vector embedding
            n_results: Number of results to return (default: 5)
            where: Optional metadata filter (e.g., {"outcome": "win"})
            
        Returns:
            List of dictionaries with trade_id, distance, metadata, and document
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            
            # Format results
            similar_trades = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    similar_trades.append({
                        "trade_id": results["ids"][0][i],
                        "distance": results["distances"][0][i] if results.get("distances") else None,
                        "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                        "document": results["documents"][0][i] if results.get("documents") else None
                    })
            
            return similar_trades
        except Exception as e:
            print(f"[Chroma] Error finding similar trades: {e}")
            return []
    
    def delete_trade(self, trade_id: str):
        """Delete a trade from the vector database."""
        try:
            self.collection.delete(ids=[trade_id])
            print(f"[Chroma] Deleted trade {trade_id}")
        except Exception as e:
            print(f"[Chroma] Error deleting trade {trade_id}: {e}")
            raise
    
    def get_collection_count(self) -> int:
        """Get the number of trades in the collection."""
        try:
            return self.collection.count()
        except Exception as e:
            print(f"[Chroma] Error getting collection count: {e}")
            return 0


# Singleton instance
_chroma_client: Optional[ChromaClient] = None


def get_chroma_client() -> ChromaClient:
    """Get or create the singleton Chroma client instance."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = ChromaClient()
    return _chroma_client

