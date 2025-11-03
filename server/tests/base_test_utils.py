"""
LAT v2 Telemetry Layer - Base Test Utilities

Shared helper utilities for all LAT v2 tests.
Captures request/response timings, stdout logs, and writes structured JSON.
"""
import json
import os
import io
import time
from contextlib import redirect_stdout
from datetime import datetime
from datetime import datetime, UTC

try:
    import requests
except ImportError:
    print("[LATv2] Warning: requests not installed. Run: pip install requests")
    requests = None


RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def run_and_capture(endpoint, payload=None, method="POST", label=""):
    """
    Run a FastAPI endpoint, measure duration, capture stdout.

    Args:
        endpoint: FastAPI endpoint path (e.g., "/ask")
        payload: Request payload (dict for JSON POST, dict for GET params)
        method: HTTP method ("POST" or "GET")
        label: Test label for output filename

    Returns:
        Dictionary with test results including timing, status, stdout, etc.
    """
    if requests is None:
        raise ImportError("requests library is required for LAT v2 tests")

    start = time.perf_counter()
    f = io.StringIO()

    try:
        with redirect_stdout(f):
            url = f"http://127.0.0.1:8765{endpoint}"
            if method == "POST":
                if payload:
                    if endpoint == "/ask":
                        # Use multipart/form-data for /ask endpoint
                        r = requests.post(url, data=payload, timeout=60)
                    else:
                        r = requests.post(url, json=payload, timeout=60)
                else:
                    r = requests.post(url, timeout=60)
            else:
                r = requests.get(url, params=payload or {}, timeout=60)
    except requests.exceptions.RequestException as e:
        duration = round((time.perf_counter() - start) * 1000, 2)
        log = {
            "label": label,
            "timestamp": datetime.now(datetime.UTC).isoformat(),
            "endpoint": endpoint,
            "method": method,
            "status": None,
            "duration_ms": duration,
            "error": str(e),
            "response_text": "",
            "stdout": f.getvalue(),
        }
        outpath = os.path.join(
            RESULTS_DIR,
            f"{label or endpoint.strip('/').replace('/', '_')}.json"
        )
        with open(outpath, "w", encoding="utf-8") as fp:
            json.dump(log, fp, indent=2)
        print(f"[LATv2] Saved log → {outpath}")
        return log

    duration = round((time.perf_counter() - start) * 1000, 2)

    # Try to parse JSON response if possible
    response_text = r.text[:2000]  # Limit to 2000 chars
    try:
        response_json = r.json()
    except (ValueError, json.JSONDecodeError):
        response_json = None

    log = {
        "label": label,
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "method": method,
        "status": r.status_code,
        "duration_ms": duration,
        "response_text": response_text,
        "response_json": response_json,
        "stdout": f.getvalue(),
    }

    # Generate output filename
    safe_label = label or endpoint.strip('/').replace('/', '_').replace(' ', '_')
    outpath = os.path.join(RESULTS_DIR, f"{safe_label}.json")

    with open(outpath, "w", encoding="utf-8") as fp:
        json.dump(log, fp, indent=2)

    print(f"[LATv2] Saved log → {outpath}")
    return log

