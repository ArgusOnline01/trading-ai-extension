"""
Phase 4 Vision Extraction Scaffold
---------------------------------
Reads chart images, OCRs the y-axis to build a pixel→price map,
and extracts POI/IFVG/BOS spans. Detection is stubbed; plug in
your detector/OCR when ready.
"""

import base64
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Iterable

# Load environment variables (OPENAI_API_KEY, etc.) early
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def ocr_y_axis(image_path: Path) -> Optional[Dict[str, float]]:
    """
    Stub: OCR y-axis labels and return a dict of {pixel_y: price}.
    Replace with real OCR (e.g., tesseract, easyocr).
    """
    # TODO: implement OCR for y-axis labels
    return None


def fit_pixel_to_price(ocr_points: Dict[str, float]) -> Optional[Dict[str, float]]:
    """
    Fit a linear map pixel_y -> price.
    Return a dict with slope/intercept or None if insufficient data.
    """
    if not ocr_points or len(ocr_points) < 2:
        return None
    # Simple least squares on (y, price)
    pts = [(float(y), float(p)) for y, p in ocr_points.items()]
    n = len(pts)
    sum_x = sum(y for y, _ in pts)
    sum_y = sum(p for _, p in pts)
    sum_xx = sum(y * y for y, _ in pts)
    sum_xy = sum(y * p for y, p in pts)
    denom = (n * sum_xx - sum_x * sum_x)
    if denom == 0:
        return None
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return {"slope": slope, "intercept": intercept}


def detect_shapes(image_path: Path) -> Dict[str, Any]:
    """
    Stub: detect POI/IFVG rectangles and BOS lines/labels.
    Return pixel coordinates; caller will map to prices.
    """
    # TODO: plug in detection model or color/shape heuristics
    return {
        "poi": [],
        "ifvg": [],
        "bos": [],
    }


def pixel_to_price(mapping: Dict[str, float], y_px: float) -> Optional[float]:
    """Apply linear map pixel_y->price. mapping expected keys: slope, intercept."""
    if not mapping or "slope" not in mapping or "intercept" not in mapping:
        return None
    return mapping["slope"] * y_px + mapping["intercept"]


def extract_prices(image_path: Path, use_vision: bool = True) -> Dict[str, Any]:
    """
    High-level extractor: OCR y-axis, fit mapping, detect shapes,
    convert spans to prices. Returns a dict ready to merge into advisor payload.
    """
    if use_vision:
        # Vision-based OCR and detection
        ocr_data = vision_ocr_y_axis(image_path)
        raw_ocr_text = ocr_data.get("raw_text") if ocr_data else None
        ocr_items = ocr_data.get("items") if ocr_data else None
        ocr_pts = {str(item["y_px"]): float(item["price"]) for item in ocr_items} if ocr_items else {}
        detections = vision_detect_shapes(image_path)
        raw_shapes_text = detections.get("raw_text")
    else:
        ocr_pts = ocr_y_axis(image_path)
        detections = detect_shapes(image_path)
        raw_ocr_text = None
        raw_shapes_text = None
    mapping = fit_pixel_to_price(ocr_pts or {})
    mapping_ok = False
    if mapping and ocr_pts:
        prices = [float(v) for v in ocr_pts.values()]
        if len(prices) >= 3:
            span = max(prices) - min(prices)
            mapping_ok = span > 0
    price_min = None
    price_max = None
    if ocr_pts:
        values = list((float(v) for v in ocr_pts.values()))
        if values:
            price_min = min(values)
            price_max = max(values)
            # small safety padding
            span = price_max - price_min
            price_min -= span * 0.05
            price_max += span * 0.05

    def clamp_price(val: Optional[float]) -> Optional[float]:
        if val is None or price_min is None or price_max is None:
            return val
        return max(price_min, min(price_max, val))

    def normalize_span(span_obj):
        """
        Normalize detector output to a (y_min, y_max) tuple.
        Supports:
          - dict with y_min_px/y_max_px keys
          - dict with y1/y2 keys
          - 2-item list/tuple
        """
        if span_obj is None:
            return None
        if isinstance(span_obj, dict):
            y_min = span_obj.get("y_min_px") or span_obj.get("y_min") or span_obj.get("top") or span_obj.get("y1")
            y_max = span_obj.get("y_max_px") or span_obj.get("y_max") or span_obj.get("bottom") or span_obj.get("y2")
            if y_min is not None and y_max is not None:
                return float(y_min), float(y_max)
        elif isinstance(span_obj, (list, tuple)) and len(span_obj) == 2:
            return float(span_obj[0]), float(span_obj[1])
        return None

    def span_to_price(span_obj):
        # Prefer model prices when provided; otherwise map y_px->price.
        if isinstance(span_obj, dict):
            price_low = span_obj.get("price_low") or span_obj.get("price_min") or span_obj.get("low_price")
            price_high = span_obj.get("price_high") or span_obj.get("price_max") or span_obj.get("high_price")
            try:
                if price_low is not None and price_high is not None:
                    lo = float(price_low)
                    hi = float(price_high)
                    if lo > hi:
                        lo, hi = hi, lo
                    return (lo, hi)
            except Exception:
                pass
        span = normalize_span(span_obj)
        if not span or not mapping:
            return None
        lo = pixel_to_price(mapping, span[0])
        hi = pixel_to_price(mapping, span[1])
        if lo is None or hi is None:
            return None
        if lo > hi:
            lo, hi = hi, lo
        lo = clamp_price(lo)
        hi = clamp_price(hi)
        return (lo, hi)

    poi_prices = [span_to_price(p) for p in detections.get("poi", [])]
    ifvg_prices = [span_to_price(p) for p in detections.get("ifvg", [])]
    def normalize_line(line_obj):
        if line_obj is None:
            return None
        if isinstance(line_obj, dict):
            if "price" in line_obj and line_obj.get("price") is not None:
                return {"price": line_obj.get("price")}
            # fallback to y if price missing
            return line_obj.get("y_px") or line_obj.get("y") or line_obj.get("y1")
        return line_obj

    bos_prices = []
    for b in detections.get("bos", []):
        y_val = normalize_line(b)
        if y_val is None:
            continue
        price_from_map = None
        price_from_label = None
        if mapping is not None:
            try:
                price_from_map = pixel_to_price(mapping, float(y_val))
            except Exception:
                price_from_map = None
        if isinstance(y_val, dict) and "price" in y_val:
            try:
                price_from_label = float(y_val["price"])
            except Exception:
                price_from_label = None

        chosen = None
        if price_from_map is not None:
            price_from_map = clamp_price(price_from_map)
            if price_from_map is not None:
                chosen = price_from_map
        if chosen is None and price_from_label is not None:
            chosen = price_from_label
        if chosen is not None:
            bos_prices.append(chosen)

    # Optional fractal target (often drawn as a circle on chart)
    fractal_price = None
    fractal_obj = detections.get("fractal_candidates") or detections.get("fractal_target")
    fractal_candidates = []
    if isinstance(fractal_obj, list):
        fractal_candidates = fractal_obj
    elif fractal_obj is not None:
        fractal_candidates = [fractal_obj]

    # Select fractal: prefer a price, and bias based on BOS/POI orientation.
    poi_mid = None
    if poi_prices:
        # use first poi span
        span = poi_prices[0]
        if span and span[0] is not None and span[1] is not None:
            poi_mid = (span[0] + span[1]) / 2.0
    bos_ref = bos_prices[0] if bos_prices else None
    best = None
    best_dist = None
    candidates = []
    for f in fractal_candidates:
        price_val = None
        if isinstance(f, dict) and "price" in f and f["price"] is not None:
            try:
                price_val = float(f["price"])
            except Exception:
                price_val = None
        f_type = f.get("type") if isinstance(f, dict) else None
        if price_val is None:
            y_val = normalize_line(f)
            if y_val is not None and not isinstance(y_val, dict) and mapping is not None:
                try:
                    price_val = pixel_to_price(mapping, float(y_val))
                    price_val = clamp_price(price_val)
                except Exception:
                    price_val = None
        if price_val is None:
            continue
        candidates.append({"price": price_val, "type": f_type})

    if candidates:
        if bos_ref is not None:
            if poi_mid is not None and bos_ref > poi_mid:
                # bullish: pick candidate closest to BOS, preferring those >= BOS; fall back to closest overall
                above = [c["price"] for c in candidates if c["price"] >= bos_ref]
                pool = above if above else [c["price"] for c in candidates]
                best = sorted(pool, key=lambda p: abs(p - bos_ref))[0]
            elif poi_mid is not None and bos_ref < poi_mid:
                # bearish: pick candidate closest to BOS, preferring <= BOS
                below = [c["price"] for c in candidates if c["price"] <= bos_ref]
                pool = below if below else [c["price"] for c in candidates]
                best = sorted(pool, key=lambda p: abs(p - bos_ref))[0]
            else:
                best = sorted((c["price"] for c in candidates), key=lambda p: abs(p - bos_ref))[0]
        else:
            # No BOS; pick candidate closest to POI midpoint if available, else first.
            if poi_mid is not None:
                best = sorted((c["price"] for c in candidates), key=lambda p: abs(p - poi_mid))[0]
            else:
                best = candidates[0]["price"]
    fractal_price = best

    return {
        "poi_spans": poi_prices,
        "ifvg_spans": ifvg_prices,
        "bos_levels": bos_prices,
        "fractal_target": fractal_price,
        "fractal_candidates": detections.get("fractal_candidates"),
        "symbol": detections.get("symbol"),
        "timeframe": detections.get("timeframe"),
        "session": detections.get("session"),
        "pixel_map": mapping,
        "raw": detections,
        "raw_ocr_text": raw_ocr_text,
        "raw_shapes_text": raw_shapes_text,
    }


def extract_trade_row(image_path: Path, use_vision: bool = True) -> Dict[str, Any]:
    """
    Produce a minimal advisor-ready row with extracted fields.
    Fields left None when not detected.
    """
    out = extract_prices(image_path, use_vision=use_vision)
    # Pick first spans if available
    poi_span = next((p for p in out.get("poi_spans", []) if p and all(v is not None for v in p)), (None, None))
    ifvg_span = next((p for p in out.get("ifvg_spans", []) if p and all(v is not None for v in p)), (None, None))
    bos_level = next((b for b in out.get("bos_levels", []) if b is not None), None)
    fractal_target = out.get("fractal_target")

    row = {
        "poi_low": poi_span[0],
        "poi_high": poi_span[1],
        "ifvg_low": ifvg_span[0],
        "ifvg_high": ifvg_span[1],
        "bos_level": bos_level,
        "fractal_target": fractal_target,
        "fractal_candidates": out.get("fractal_candidates"),
        "raw_ocr_text": out.get("raw_ocr_text"),
        "raw_shapes_text": out.get("raw_shapes_text"),
        # entry/sl/tp left for user or other detectors
    }
    return row


if __name__ == "__main__":
    # Simple manual test stub
    sample = Path("server/data/Vision_image_dataset/trade-01.png")
    if sample.exists():
        print(extract_trade_row(sample))
    else:
        print("Sample image not found; place an image at", sample)


# --- Optional: OpenAI Vision helpers (uses OPENAI_API_KEY from .env) ---
def _read_b64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode("utf-8")


def vision_complete(prompt: str, image_path: Path, model: str = "gpt-5.1") -> Optional[str]:
    """
    Call OpenAI Vision with an image and prompt. Returns text content or None on failure.
    """
    try:
      from openai import OpenAI
    except ImportError:
        print("[VISION] openai SDK not installed; run `pip install openai`.")
        return None
    try:
        client = OpenAI()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You extract chart details. Respond with concise JSON if asked."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{_read_b64(image_path)}"}},
                    ],
                },
            ],
            max_completion_tokens=500,
            temperature=0.1,
        )
        content = (resp.choices[0].message.content or "").strip()
        if not content:
            print(f"[VISION] Empty response for {image_path.name} (prompt='{prompt[:60]}...').")
        return content
    except Exception as e:
        print(f"[VISION] vision_complete error for {image_path.name}: {e}")
        return None


def vision_ocr_y_axis(image_path: Path) -> Optional[Dict[str, Any]]:
    """
    Use OpenAI Vision to read y-axis labels (pixel y + price).
    Expected response: JSON array of {\"y_px\": <number>, \"price\": <number>}.
    """
    prompt = (
        "Read the y-axis price labels on this chart. Return JSON array of objects with keys "
        "'y_px' (pixel row) and 'price' (numeric). Use pixel coordinates relative to the image top-left. "
        "Only include clearly legible labels; ignore faint/partial text. Provide at least 10 labels if visible, "
        "covering top, middle, and bottom of the axis, and include any labels near drawn boxes/lines."
    )
    txt = vision_complete(prompt, image_path)
    if not txt:
        return None
    try:
        print(f"[VISION][DEBUG] OCR raw ({image_path.name}): {txt}")
        data = json.loads(txt)
        if isinstance(data, list):
            return {"items": data, "raw_text": txt}
    except Exception:
        print(f"[VISION] OCR JSON parse failed for {image_path.name}: {txt}")
        return None
    return None


def vision_detect_shapes(image_path: Path) -> Dict[str, Any]:
    """
    Use OpenAI Vision to detect POI/IFVG rectangles, BOS lines, and fractal target circles.
    Expected response: JSON with keys poi, ifvg, bos, fractal_target:
      poi/ifvg: array of {\"y_min_px\":..., \"y_max_px\":...} (optionally price_low/price_high if clearly read)
      bos: array of {\"y_px\":...} (or {\"price\":...} if legible)
      fractal_target: object with {\"y_px\":...} or {\"price\":...} for the target circle.
    """
    prompt = (
        "Detect the drawn features on this trading chart and return JSON with keys poi, ifvg, bos, fractal_candidates, "
        "symbol, timeframe, session. "
        "Always prefer on-chart price labels. You must detect POI boxes if they exist: include price_low and price_high (numeric) "
        "and y_min_px and y_max_px (pixel rows, top-left origin). If price text is missing for a POI, estimate using the y-axis grid. "
        "IFVG boxes are separate from POI; include them only if drawn. "
        "For BOS: include BOTH price and y_px for the BOS line; if price not printed, estimate price from the y-axis and still include y_px. "
        "Fractal_candidates: array of objects for any drawn circles (fractal low/high/next/target). For each, include fields: type "
        "(one of low, high, target), price if visible, and y_px. Provide the projected/next target circle as type=target. "
        "Also extract symbol/ticker, chart timeframe (e.g., 5m/15m/H1), and session label if shown on the chart; use empty string if not visible. "
        "Do not return null values; provide the best estimate instead. Respond with strictly valid JSON."
    )
    txt = vision_complete(prompt, image_path)
    if not txt:
        return {"poi": [], "ifvg": [], "bos": [], "fractal_target": None, "raw_text": None}
    try:
        print(f"[VISION][DEBUG] SHAPES raw ({image_path.name}): {txt}")
        data = json.loads(txt)
        return {
            "poi": data.get("poi", []) if isinstance(data, dict) else [],
            "ifvg": data.get("ifvg", []) if isinstance(data, dict) else [],
            "bos": data.get("bos", []) if isinstance(data, dict) else [],
            "fractal_target": data.get("fractal_target") if isinstance(data, dict) else None,
            "fractal_candidates": data.get("fractal_candidates") if isinstance(data, dict) else None,
            "symbol": data.get("symbol") if isinstance(data, dict) else None,
            "timeframe": data.get("timeframe") if isinstance(data, dict) else None,
            "session": data.get("session") if isinstance(data, dict) else None,
            "raw_text": txt,
        }
    except Exception:
        print(f"[VISION] Shape JSON parse failed for {image_path.name}: {txt}")
        return {
            "poi": [],
            "ifvg": [],
            "bos": [],
            "fractal_target": None,
            "fractal_candidates": None,
            "symbol": None,
            "timeframe": None,
            "session": None,
            "raw_text": txt,
        }
