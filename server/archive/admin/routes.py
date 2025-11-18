from __future__ import annotations

from fastapi import APIRouter
from pathlib import Path

from db.session import SessionLocal
from db.import_from_csv import import_from_csv
from db.models import Trade


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reimport-csv")
def reimport_csv():
    csv_path = Path(__file__).resolve().parent.parent / "data" / "Trading-Images" / "trades_export.csv"
    with SessionLocal() as db:
        result = import_from_csv(db, csv_path)
    return {"csv": str(csv_path), **result}


@router.get("/debug-csv")
def debug_csv(trade_id: str):
    csv_path = Path(__file__).resolve().parent.parent / "data" / "Trading-Images" / "trades_export.csv"
    parsed = {}
    if csv_path.exists():
        import csv
        with csv_path.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_norm = { (k or '').strip().lstrip('\ufeff'): v for k, v in row.items() }
                if str(row_norm.get("Id") or row_norm.get("id")).strip() == str(trade_id):
                    parsed = row_norm
                    break
    with SessionLocal() as db:
        t = db.query(Trade).filter(Trade.trade_id == str(trade_id)).first()
        db_row = None
        if t:
            db_row = {
                "trade_id": t.trade_id,
                "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "pnl": t.pnl,
                "direction": t.direction,
            }
    return {"csv_path": str(csv_path), "csv_row": parsed, "db_row": db_row}


