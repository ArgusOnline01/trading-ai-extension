from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TradeRecord(BaseModel):
    """
    Trade record model for performance tracking
    """
    session_id: str  # Unique trade ID (format: trade-{timestamp}-{random})
    timestamp: str  # ISO format datetime string
    symbol: str
    timeframe: str
    bias: str
    setup_type: str
    ai_verdict: str
    user_action: str
    outcome: Optional[str] = None  # "win", "loss", "breakeven", or None (pending)
    r_multiple: Optional[float] = None  # R:R ratio (e.g., 2.5 for 2.5R win)
    comments: Optional[str] = ""
    # Phase 4A.1: Price levels extracted from chart analysis
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    expected_r: Optional[float] = None  # Expected R:R at entry
    # === 5F.2 FIX ===
    # [5F.2 FIX F5] Text-only logging support
    needs_chart: bool = False  # True if trade logged without chart image


class TradeUpdate(BaseModel):
    """
    Model for updating trade outcome
    """
    session_id: str
    outcome: str
    r_multiple: float
    comments: Optional[str] = ""


class PerformanceStats(BaseModel):
    """
    Aggregated performance statistics
    """
    total_trades: int
    win_rate: Optional[float] = None
    avg_r: Optional[float] = None
    profit_factor: Optional[float] = None
    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None
    total_r: Optional[float] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    breakevens: Optional[int] = None

