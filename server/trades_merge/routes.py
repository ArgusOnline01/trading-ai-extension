from fastapi import APIRouter
from .merge_utils import merge_trade_by_id, auto_merge_all, get_merge_preview

router = APIRouter(prefix="/merge", tags=["Trades Merge"])

@router.post("/batch")
def auto_merge():
    """Merge all pending (unmerged) imported trades"""
    return auto_merge_all()

@router.post("/one/{trade_id}")
def merge_trade(trade_id: int, label: str = None):
    """Merge a single trade by ID with optional label override"""
    return merge_trade_by_id(trade_id, label)

@router.get("/preview/{trade_id}")
def preview_merge(trade_id: int):
    """Preview what will happen when merging a specific trade"""
    return get_merge_preview(trade_id)
