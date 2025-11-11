"""
Import trades from screenshot data (manual extraction)
Process: Extract data from screenshots → Create CSV-like data → Import to database

This script helps import trades from screenshots by:
1. You provide trade data extracted from screenshots (manually or via OCR)
2. Script creates trades in database
3. Script calculates exit price from profit if missing
4. Script renders charts for all trades
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import json

from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import Trade


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    """Parse datetime from string"""
    if not val:
        return None
    # Try multiple formats
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S CT",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
    ):
        try:
            # Remove timezone suffix if present
            val_clean = val.replace(" CT", "").replace(" ET", "").strip()
            return datetime.strptime(val_clean, fmt)
        except Exception:
            continue
    return None


def _safe_float(v: Optional[str]) -> Optional[float]:
    """Safely convert to float"""
    if not v:
        return None
    try:
        # Remove $ and commas
        v_clean = str(v).replace("$", "").replace(",", "").strip()
        return float(v_clean) if v_clean else None
    except Exception:
        return None


def _calculate_exit_price(
    entry_price: float,
    direction: str,
    size: float,
    profit: float
) -> Optional[float]:
    """
    Calculate exit price from profit.
    
    For Buy: Exit Price = Entry Price + (Profit / Size)
    For Sell: Exit Price = Entry Price - (Profit / Size)
    """
    if not all([entry_price, direction, size, profit is not None]):
        return None
    
    try:
        if direction.lower() in ["buy", "long"]:
            return entry_price + (profit / size)
        elif direction.lower() in ["sell", "short"]:
            return entry_price - (profit / size)
    except Exception:
        pass
    
    return None


def _normalize_symbol(product: str) -> str:
    """Normalize product symbol (e.g., MNQZ5 -> MNQ)"""
    if not product:
        return ""
    # Remove contract month/year suffix (Z5, H6, etc.)
    # Keep base symbol (MNQ, CL, SIL, etc.)
    symbol = product.upper()
    # Remove trailing digits/letters that look like contract codes
    if len(symbol) > 3:
        # Check if last 2 chars are contract code (e.g., Z5, H6)
        if symbol[-2:].isdigit() or (symbol[-1].isdigit() and symbol[-2].isalpha()):
            symbol = symbol[:-2]
    return symbol


def import_trades_from_data(
    db: Session,
    trades_data: List[Dict],
    combine_name: Optional[str] = None
) -> Dict:
    """
    Import trades from extracted data (from screenshots).
    
    Args:
        db: Database session
        trades_data: List of trade dicts with keys:
            - trade_id (required)
            - entry_time (required)
            - entry_price (required)
            - direction (required: "buy"/"sell" or "long"/"short")
            - size (required)
            - product (required)
            - profit (optional, for calculating exit price)
            - fees (optional)
            - exit_time (optional)
            - exit_price (optional, will calculate from profit if missing)
        combine_name: Optional name for this combine (for notes)
    
    Returns:
        Dict with import statistics
    """
    imported = 0
    updated = 0
    skipped = 0
    errors = []
    
    for trade_data in trades_data:
        try:
            trade_id = str(trade_data.get("trade_id") or trade_data.get("id") or "").strip()
            if not trade_id:
                skipped += 1
                errors.append("Missing trade_id")
                continue
            
            # Check if trade already exists
            existing = db.query(Trade).filter(Trade.trade_id == trade_id).first()
            
            # Parse required fields
            entry_time = _parse_dt(trade_data.get("entry_time") or trade_data.get("time"))
            entry_price = _safe_float(trade_data.get("entry_price") or trade_data.get("entryprice"))
            direction_raw = (trade_data.get("direction") or trade_data.get("side") or "").lower()
            size = _safe_float(trade_data.get("size"))
            product = trade_data.get("product") or trade_data.get("symbol") or ""
            
            # Normalize direction
            if direction_raw in ["buy", "long"]:
                direction = "long"
            elif direction_raw in ["sell", "short"]:
                direction = "short"
            else:
                direction = None
            
            # Validate required fields
            if not all([entry_time, entry_price, direction, size, product]):
                skipped += 1
                errors.append(f"Trade {trade_id}: Missing required fields")
                continue
            
            # Parse optional fields
            exit_time = _parse_dt(trade_data.get("exit_time") or trade_data.get("exitedat"))
            exit_price = _safe_float(trade_data.get("exit_price") or trade_data.get("exitprice"))
            profit = _safe_float(trade_data.get("profit") or trade_data.get("pnl"))
            fees = _safe_float(trade_data.get("fees") or trade_data.get("total_fees"))
            
            # Calculate exit price from profit if missing
            if not exit_price and profit is not None:
                calculated_exit = _calculate_exit_price(entry_price, direction, size, profit)
                if calculated_exit:
                    exit_price = calculated_exit
            
            # Calculate outcome from PnL
            outcome = None
            if profit is not None:
                if profit > 0:
                    outcome = "win"
                elif profit < 0:
                    outcome = "loss"
                else:
                    outcome = "breakeven"
            
            # Normalize symbol
            symbol = _normalize_symbol(product)
            
            # Create or update trade
            # Note: Trade model doesn't have 'notes' or 'size' fields
            # We'll store combine info in session_id or just skip it for now
            if existing:
                # Update existing trade
                existing.entry_time = entry_time
                existing.entry_price = entry_price
                existing.direction = direction
                existing.symbol = symbol
                if exit_time:
                    existing.exit_time = exit_time
                if exit_price:
                    existing.exit_price = exit_price
                if profit is not None:
                    existing.pnl = profit
                if outcome:
                    existing.outcome = outcome
                # Store combine name in session_id if not already set
                if combine_name and not existing.session_id:
                    existing.session_id = f"combine_{combine_name.lower().replace(' ', '_')}"
                updated += 1
            else:
                # Create new trade
                trade = Trade(
                    trade_id=trade_id,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    direction=direction,
                    symbol=symbol,
                    exit_time=exit_time,
                    exit_price=exit_price,
                    pnl=profit,
                    outcome=outcome,
                    session_id=f"combine_{combine_name.lower().replace(' ', '_')}" if combine_name else None
                )
                db.add(trade)
                imported += 1
            
        except Exception as e:
            skipped += 1
            errors.append(f"Trade {trade_data.get('trade_id', 'unknown')}: {str(e)}")
            continue
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": f"Database commit failed: {str(e)}",
            "imported": 0,
            "updated": 0,
            "skipped": skipped,
            "errors": errors
        }
    
    return {
        "success": True,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:10]  # Limit errors shown
    }


def import_from_json_file(json_path: Path, combine_name: Optional[str] = None) -> Dict:
    """
    Import trades from JSON file (extracted from screenshots).
    
    JSON format:
    [
        {
            "trade_id": "1433753170",
            "entry_time": "2025-10-07 01:24:37",
            "entry_price": 25148.00,
            "direction": "buy",
            "size": 5.00,
            "product": "MNQZ5",
            "profit": 20.00,
            "fees": -1.85
        },
        ...
    ]
    """
    if not json_path.exists():
        return {
            "success": False,
            "error": f"File not found: {json_path}",
            "imported": 0,
            "updated": 0,
            "skipped": 0
        }
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            trades_data = json.load(f)
        
        if not isinstance(trades_data, list):
            return {
                "success": False,
                "error": "JSON file must contain a list of trades",
                "imported": 0,
                "updated": 0,
                "skipped": 0
            }
        
        with SessionLocal() as db:
            result = import_trades_from_data(db, trades_data, combine_name)
            return result
    
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"Invalid JSON: {str(e)}",
            "imported": 0,
            "updated": 0,
            "skipped": 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error reading file: {str(e)}",
            "imported": 0,
            "updated": 0,
            "skipped": 0
        }


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python import_from_screenshots.py <json_file> [combine_name]")
        print("\nExample:")
        print("  python import_from_screenshots.py combine1_trades.json 'Combine 1'")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    combine_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"Importing trades from {json_file.name}...")
    if combine_name:
        print(f"Combine: {combine_name}")
    
    result = import_from_json_file(json_file, combine_name)
    
    if result["success"]:
        print(f"\n[SUCCESS] Import successful!")
        print(f"  Imported: {result['imported']} trades")
        print(f"  Updated: {result['updated']} trades")
        print(f"  Skipped: {result['skipped']} trades")
        if result.get("errors"):
            print(f"\n[WARNING] Errors ({len(result['errors'])}):")
            for error in result["errors"]:
                print(f"    - {error}")
    else:
        print(f"\n[ERROR] Import failed: {result.get('error', 'Unknown error')}")

