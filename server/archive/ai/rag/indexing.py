"""
Auto-indexing service for creating/updating Chroma embeddings when annotations are saved.
"""

from typing import Dict, Any, Optional
from db.session import SessionLocal
from db.models import Trade, Annotation
from ai.rag.chroma_client import get_chroma_client
from ai.rag.embeddings import get_embedding_service


def create_trade_embedding_text(
    trade: Trade,
    annotation: Optional[Annotation] = None
) -> str:
    """
    Create a text representation of a trade for embedding.
    Includes trade info + annotations + notes.
    
    Args:
        trade: Trade object
        annotation: Optional Annotation object
        
    Returns:
        Formatted text string for embedding
    """
    parts = []
    
    # Basic trade info
    parts.append(f"Symbol: {trade.symbol or 'Unknown'}")
    parts.append(f"Direction: {trade.direction or 'Unknown'}")
    
    if trade.outcome:
        parts.append(f"Outcome: {trade.outcome}")
    
    # Include annotation details
    if annotation:
        # POI price levels
        if annotation.poi_locations:
            poi_prices = []
            for poi in annotation.poi_locations:
                if isinstance(poi, dict) and poi.get("price"):
                    poi_prices.append(str(poi["price"]))
            if poi_prices:
                parts.append(f"POI price levels: {', '.join(poi_prices)}")
        
        # BOS price levels
        if annotation.bos_locations:
            bos_prices = []
            for bos in annotation.bos_locations:
                if isinstance(bos, dict) and bos.get("price"):
                    bos_prices.append(str(bos["price"]))
            if bos_prices:
                parts.append(f"BOS price levels: {', '.join(bos_prices)}")
        
        # Notes (most important for learning!)
        if annotation.notes:
            parts.append(f"Trading notes: {annotation.notes}")
    
    return ". ".join(parts)


def index_trade_annotation(trade_id: str, annotation_id: Optional[int] = None):
    """
    Create or update Chroma embedding for a trade's annotation.
    This is called automatically when annotations are saved.
    
    Args:
        trade_id: Trade ID
        annotation_id: Optional annotation ID (if None, gets latest annotation)
    """
    try:
        db = SessionLocal()
        
        # Get trade
        trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
        if not trade:
            print(f"[Indexing] Trade {trade_id} not found, skipping embedding")
            return
        
        # Get annotation
        if annotation_id:
            annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
        else:
            # Get latest annotation for this trade
            annotation = db.query(Annotation).filter(
                Annotation.trade_id == trade_id
            ).order_by(Annotation.created_at.desc()).first()
        
        if not annotation:
            print(f"[Indexing] No annotation found for trade {trade_id}, skipping embedding")
            return
        
        # Create embedding text
        embedding_text = create_trade_embedding_text(trade, annotation)
        
        # Generate embedding
        embedding_service = get_embedding_service()
        embedding = embedding_service.generate_embedding(embedding_text)
        
        # Prepare metadata
        metadata = {
            "trade_id": trade_id,
            "symbol": trade.symbol or "",
            "direction": trade.direction or "",
            "outcome": trade.outcome or "",
            "has_annotations": True,
            "has_notes": bool(annotation.notes),
            "poi_count": len(annotation.poi_locations) if annotation.poi_locations else 0,
            "bos_count": len(annotation.bos_locations) if annotation.bos_locations else 0
        }
        
        # Store in Chroma
        chroma_client = get_chroma_client()
        chroma_client.add_trade(
            trade_id=trade_id,
            embedding=embedding,
            metadata=metadata,
            document=embedding_text
        )
        
        print(f"[Indexing] Successfully indexed trade {trade_id} with annotations")
        
    except Exception as e:
        print(f"[Indexing] Error indexing trade {trade_id}: {e}")
    finally:
        db.close()


def index_corrected_annotation(trade_id: str, corrected_annotations: Dict[str, Any]):
    """
    Create or update Chroma embedding for corrected annotations (from AI lessons).
    This is called when user saves corrections to AI's annotations.
    
    Args:
        trade_id: Trade ID
        corrected_annotations: Dictionary with corrected POI, BOS, circles, notes
    """
    try:
        db = SessionLocal()
        
        # Get trade
        trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
        if not trade:
            print(f"[Indexing] Trade {trade_id} not found, skipping embedding")
            return
        
        # Create a temporary annotation-like object for embedding
        class TempAnnotation:
            def __init__(self, data):
                self.poi_locations = data.get("poi", [])
                self.bos_locations = data.get("bos", [])
                self.circle_locations = data.get("circles", [])
                self.notes = data.get("notes", "")
        
        temp_annotation = TempAnnotation(corrected_annotations)
        
        # Create embedding text
        embedding_text = create_trade_embedding_text(trade, temp_annotation)
        
        # Generate embedding
        embedding_service = get_embedding_service()
        embedding = embedding_service.generate_embedding(embedding_text)
        
        # Prepare metadata
        metadata = {
            "trade_id": trade_id,
            "symbol": trade.symbol or "",
            "direction": trade.direction or "",
            "outcome": trade.outcome or "",
            "has_annotations": True,
            "has_notes": bool(temp_annotation.notes),
            "poi_count": len(temp_annotation.poi_locations),
            "bos_count": len(temp_annotation.bos_locations),
            "is_corrected": True  # Mark as corrected annotation
        }
        
        # Update in Chroma (will overwrite existing if trade_id exists)
        chroma_client = get_chroma_client()
        chroma_client.add_trade(
            trade_id=trade_id,
            embedding=embedding,
            metadata=metadata,
            document=embedding_text
        )
        
        print(f"[Indexing] Successfully indexed corrected annotations for trade {trade_id}")
        
    except Exception as e:
        print(f"[Indexing] Error indexing corrected annotations for trade {trade_id}: {e}")
    finally:
        db.close()

