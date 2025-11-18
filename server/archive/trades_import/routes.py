"""
FastAPI Routes for Trade Import
Handles CSV uploads and trade management
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import tempfile
from .parser import import_csv, load_imported_trades, get_import_stats
from .merge_utils import merge_trade_by_id, batch_merge_trades, auto_merge_all


router = APIRouter(prefix="/trades", tags=["Trades Import"])


@router.post("/import")
async def import_trades(file: UploadFile = File(...)):
    """
    Import Topstep CSV file
    
    Uploads and parses a Topstep Trader CSV export, normalizes the data,
    and saves it to imported_trades.json
    
    Args:
        file: CSV file upload
        
    Returns:
        Success status and import statistics
    """
    try:
        # Validate file type
        suffix = os.path.splitext(file.filename)[1]
        if suffix.lower() != ".csv":
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are allowed. Please upload a Topstep Trader export."
            )
        
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='wb') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Parse and import
        trades = import_csv(tmp_path)
        
        # Clean up temp file
        os.remove(tmp_path)
        
        return {
            "success": True,
            "count": len(trades),
            "message": f"Successfully imported {len(trades)} trades from {file.filename}"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error importing CSV: {str(e)}"
        )


@router.get("/imported")
def list_imported_trades(limit: int = 50):
    """
    List imported trades
    
    Returns a preview of imported trades (default: first 50)
    
    Args:
        limit: Maximum number of trades to return (default: 50)
        
    Returns:
        Trade count and list of trades
    """
    try:
        trades = load_imported_trades()
        
        return {
            "total": len(trades),
            "showing": min(len(trades), limit),
            "trades": trades[:limit]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading trades: {str(e)}"
        )


@router.get("/stats")
def get_stats():
    """
    Get import statistics
    
    Returns summary statistics about imported trades
    
    Returns:
        Statistics including total, merged, pending counts
    """
    try:
        stats = get_import_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting stats: {str(e)}"
        )


@router.post("/merge/one/{trade_id}")
def merge_trade(trade_id: int):
    """
    Merge a specific trade (Phase 4D.2 stub)
    
    Args:
        trade_id: ID of trade to merge
        
    Returns:
        Merge result (currently returns stub message)
    """
    return merge_trade_by_id(trade_id)


@router.post("/merge/batch_import")
def merge_batch(trade_ids: list[int]):
    """
    Merge multiple trades at once (Phase 4D.2 stub)
    
    Args:
        trade_ids: List of trade IDs to merge
        
    Returns:
        Batch merge results (currently returns stub message)
    """
    return batch_merge_trades(trade_ids)


@router.post("/merge/auto")
def merge_all():
    """
    Auto-merge all unmerged trades (Phase 4D.2 stub)
    
    Returns:
        Auto-merge results (currently returns stub message)
    """
    return auto_merge_all()


@router.delete("/imported")
def clear_imported_trades():
    """
    Clear all imported trades
    
    Deletes the imported_trades.json file
    
    Returns:
        Success status
    """
    try:
        import_path = os.path.join(
            os.path.dirname(__file__),
            "..", "data", "imported_trades.json"
        )
        
        if os.path.exists(import_path):
            os.remove(import_path)
            return {
                "success": True,
                "message": "All imported trades cleared"
            }
        else:
            return {
                "success": True,
                "message": "No imported trades to clear"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing trades: {str(e)}"
        )

