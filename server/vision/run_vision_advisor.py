#!/usr/bin/env python3
"""
Batch pipeline: image(s) -> vision extraction -> advisor payload.
This is a scaffold; extraction is stubbed and micro uses filename labels.
"""
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Ensure repo root on sys.path for 'server' imports
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.vision.extract import extract_trade_row
from server.vision.micro_classifier import classify_micro


def load_manifest(manifest_path: Path):
    rows = []
    with manifest_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def build_payloads(manifest_rows):
    payloads = []
    # group by trade_id
    by_id: Dict[str, Dict[str, Any]] = {}
    for r in manifest_rows:
        tid = r.get("trade_id")
        tf = r.get("timeframe")
        fn = r.get("filename")
        if not tid or not tf or not fn:
            continue
        entry = by_id.setdefault(tid, {"trade_id": tid})
        entry.setdefault("files", {})[tf] = fn
        if tf == "1m":
            entry["micro_shift"] = (r.get("micro_shift") or "").lower()
    for tid, data in by_id.items():
        payload: Dict[str, Any] = {
            "trade_id": tid,
            "entry_method": "poi50",  # default, adjust if needed
            "micro_shift": None,
        }
        files = data.get("files", {})
        # 5m extraction
        five_m = files.get("5m")
        if five_m:
            path5 = Path("server/data/Vision_image_dataset") / five_m
            payload.update(extract_trade_row(path5))
        # 1m micro
        one_m = files.get("1m")
        if one_m:
            path1 = Path("server/data/Vision_image_dataset") / one_m
            mc = classify_micro(path1)
            if mc is not None:
                payload["micro_shift"] = mc
        payloads.append(payload)
    return payloads


def main():
    manifest = ROOT / "server" / "data" / "Vision_image_dataset" / "manifest.csv"
    if not manifest.exists():
        print("Manifest not found:", manifest)
        return
    manifest_rows = load_manifest(manifest)
    payloads = build_payloads(manifest_rows)
    print(json.dumps(payloads, indent=2))

    # Optional: call advisor endpoint for each payload (requires running API)
    # Uncomment to post to /chat/advisor/evaluate
    # import urllib.request, urllib.error
    # for p in payloads:
    #     data = json.dumps(p).encode('utf-8')
    #     req = urllib.request.Request(
    #         "http://127.0.0.1:8765/chat/advisor/evaluate",
    #         data=data,
    #         headers={'Content-Type': 'application/json'}
    #     )
    #     try:
    #         with urllib.request.urlopen(req, timeout=10) as resp:
    #             res = json.loads(resp.read().decode())
    #             print(p.get('trade_id'), res.get('decision'), res.get('grade'), res.get('rule'), res.get('risk'))
    #     except urllib.error.URLError as e:
    #         print(p.get('trade_id'), 'advisor call failed', e)


if __name__ == "__main__":
    main()
