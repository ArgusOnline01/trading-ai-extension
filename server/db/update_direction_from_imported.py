from pathlib import Path
import json
import csv

from db.session import SessionLocal
from db.models import Trade


def _load_csv_directions(csv_path: Path) -> dict:
    directions = {}
    if not csv_path.exists():
        return directions

    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trade_id = row.get("Id")
            direction = row.get("Type")
            if not trade_id or not direction:
                continue
            direction = direction.strip().lower()
            if direction in ("long", "short"):
                directions[trade_id.strip()] = direction
    return directions


def sync_directions():
    session = SessionLocal()
    try:
        base_dir = Path(__file__).resolve().parents[1] / "data"
        json_path = base_dir / "imported_trades.json"
        csv_path = base_dir / "Trading-Images" / "trades_export.csv"

        if not json_path.exists():
            print(f"[ERROR] File not found: {json_path}")
            return

        csv_directions = _load_csv_directions(csv_path)
        if csv_directions:
            print(f"[INFO] Loaded {len(csv_directions)} directions from {csv_path.name}")
        else:
            print("[WARN] CSV directions not found; falling back to JSON only")

        records = json.loads(json_path.read_text(encoding="utf-8"))
        updated = 0
        missing = 0

        for item in records:
            trade_id = str(item.get("id"))
            direction = csv_directions.get(trade_id)
            if not direction:
                direction = item.get("direction", "").strip().lower()

            if not trade_id or direction not in ("long", "short"):
                continue

            trade = session.query(Trade).filter(Trade.trade_id == trade_id).first()
            if not trade:
                missing += 1
                continue

            if trade.direction != direction:
                print(f"[UPDATE] {trade_id}: {trade.direction} -> {direction}")
                trade.direction = direction
                session.add(trade)
                updated += 1

        session.commit()
        print(f"[DONE] Updated directions for {updated} trades. Missing trades: {missing}")
    finally:
        session.close()


if __name__ == "__main__":
    sync_directions()
