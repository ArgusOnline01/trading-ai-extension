from fastapi import APIRouter
from .merge_utils import merge_trade_by_id, auto_merge_all, get_merge_preview
from performance.learning import generate_learning_profile

router = APIRouter(prefix="/merge", tags=["Trades Merge"])

@router.post("/batch")
def auto_merge():
    """Merge all pending (unmerged) imported trades"""
    result = auto_merge_all()
    try:
        generate_learning_profile()
    except Exception:
        pass
    return result

@router.post("/one/{trade_id}")
def merge_trade(trade_id: int, label: str = None):
    """Merge a single trade by ID with optional label override"""
    result = merge_trade_by_id(trade_id, label)
    try:
        generate_learning_profile()
    except Exception:
        pass
    return result

@router.get("/preview/{trade_id}")
def preview_merge(trade_id: int):
    """Preview what will happen when merging a specific trade"""
    return get_merge_preview(trade_id)
