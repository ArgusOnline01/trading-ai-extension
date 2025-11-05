from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Trade


router = APIRouter(prefix="/charts", tags=["charts"])


def _charts_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "charts"


@router.get("/by-trade/{trade_id}")
def get_chart_by_trade(trade_id: str, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    charts_dir = _charts_dir()
    if not charts_dir.exists():
        raise HTTPException(status_code=404, detail="Charts directory not found")

    # Try exact file by common naming pattern: SYMBOL_5m_TRADEID.png
    candidate = charts_dir / f"{trade.symbol}_5m_{trade.trade_id}.png"
    if candidate.exists():
        return FileResponse(candidate, media_type="image/png")

    # Fallback: search by trade_id anywhere in filename
    matches = list(charts_dir.glob(f"*{trade.trade_id}*.png"))
    if matches:
        return FileResponse(matches[0], media_type="image/png")

    raise HTTPException(status_code=404, detail="Chart not found for trade")


