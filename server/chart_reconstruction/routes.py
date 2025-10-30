"""
Chart Reconstruction API Routes
Optional endpoints for viewing chart metadata and retry queue
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

router = APIRouter(prefix="/charts", tags=["Chart Reconstruction"])


def get_data_path(filename):
    """Helper to get data file path"""
    return Path(__file__).parent.parent / "data" / filename


@router.get("/metadata")
def get_chart_metadata():
    """
    Get metadata for all rendered charts
    
    Returns:
        List of chart metadata dicts with trade_id, symbol, path, etc.
    """
    meta_path = get_data_path("chart_metadata.json")
    
    if not meta_path.exists():
        return {
            "status": "no_charts",
            "message": "No charts have been rendered yet. Run: python chart_reconstruction/render_charts.py",
            "charts": []
        }
    
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        return {
            "status": "success",
            "count": len(metadata),
            "charts": metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading metadata: {str(e)}")


@router.get("/retry-queue")
def get_retry_queue():
    """
    Get list of trades that failed to render
    
    Returns:
        List of failed trade dicts with trade_id, symbol, reason
    """
    retry_path = get_data_path("retry_queue.json")
    
    if not retry_path.exists():
        return {
            "status": "no_failures",
            "message": "No failed charts in queue",
            "failed": []
        }
    
    try:
        failed = json.loads(retry_path.read_text(encoding="utf-8"))
        return {
            "status": "has_failures",
            "count": len(failed),
            "failed": failed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading retry queue: {str(e)}")


@router.get("/stats")
def get_chart_stats():
    """
    Get statistics about chart reconstruction
    
    Returns:
        Stats including total rendered, failed, etc.
    """
    meta_path = get_data_path("chart_metadata.json")
    retry_path = get_data_path("retry_queue.json")
    trades_path = get_data_path("imported_trades.json")
    charts_dir = get_data_path("charts")
    
    stats = {
        "total_trades": 0,
        "rendered": 0,
        "failed": 0,
        "pending": 0,
        "chart_files": 0
    }
    
    # Count total trades
    if trades_path.exists():
        try:
            trades = json.loads(trades_path.read_text(encoding="utf-8"))
            stats["total_trades"] = len(trades)
        except:
            pass
    
    # Count rendered
    if meta_path.exists():
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            stats["rendered"] = len(metadata)
        except:
            pass
    
    # Count failed
    if retry_path.exists():
        try:
            failed = json.loads(retry_path.read_text(encoding="utf-8"))
            stats["failed"] = len(failed)
        except:
            pass
    
    # Count pending
    stats["pending"] = stats["total_trades"] - stats["rendered"] - stats["failed"]
    
    # Count chart files
    if charts_dir.exists() and charts_dir.is_dir():
        stats["chart_files"] = len(list(charts_dir.glob("*.png")))
    
    return stats


@router.get("/chart/{trade_id}")
def get_chart_for_trade(trade_id: int):
    """
    Get chart metadata for a specific trade
    
    Args:
        trade_id: Trade ID
        
    Returns:
        Chart metadata for the trade
    """
    meta_path = get_data_path("chart_metadata.json")
    
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="No charts rendered yet")
    
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        
        for chart in metadata:
            if chart.get("trade_id") == trade_id:
                return chart
        
        raise HTTPException(status_code=404, detail=f"No chart found for trade {trade_id}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.delete("/metadata")
def clear_metadata():
    """
    Clear chart metadata and retry queue
    Use this to reset and start fresh
    
    Returns:
        Success message
    """
    meta_path = get_data_path("chart_metadata.json")
    retry_path = get_data_path("retry_queue.json")
    
    deleted = []
    
    if meta_path.exists():
        meta_path.unlink()
        deleted.append("metadata")
    
    if retry_path.exists():
        retry_path.unlink()
        deleted.append("retry_queue")
    
    return {
        "status": "cleared",
        "deleted": deleted,
        "message": "Metadata and retry queue cleared. Chart images remain intact."
    }

