"""
Unified Chart Service - Phase 5F.1
Single source of truth for all chart lookup and loading operations.
"""
from pathlib import Path
from typing import Any, Dict, Optional
import base64
import io
import json
import os
import requests
import time
import threading

# === 5F.2 FIX ===
# Try to import PIL for image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None

# Constants
CHARTS_DIR = Path(__file__).resolve().parent.parent / "data" / "charts"
PATTERN_CONFIG = Path(__file__).resolve().parent.parent / "config" / "chart_patterns.json"
METADATA_API_BASE = "http://127.0.0.1:8765/charts"
TIMEOUT = float(os.getenv("CHART_METADATA_TIMEOUT_SEC", "10.0"))

# TTL cache for chart resolution results [5F.2 FIX F1]
_chart_url_cache: Dict[str, tuple[Optional[str], float]] = {}  # trade_id -> (chart_url, timestamp)
_chart_cache_lock = threading.Lock()
CHART_CACHE_TTL = 10  # seconds


def _load_patterns() -> list[str]:
    """Load chart filename patterns from config file, with defaults."""
    if PATTERN_CONFIG.exists():
        try:
            patterns = json.loads(PATTERN_CONFIG.read_text(encoding="utf-8"))
            if isinstance(patterns, list) and len(patterns) > 0:
                return patterns
        except Exception as e:
            print(f"[CHART_SERVICE] Failed to load patterns from {PATTERN_CONFIG}: {e}")
    
    # Sane defaults
    return [
        "{symbol}_5m_{trade_id}.png",
        "{symbol}_15m_{trade_id}.png",
        "chart_{trade_id}.png",
    ]


PATTERNS = _load_patterns()
print(f"[CHART_SERVICE] Loaded {len(PATTERNS)} chart patterns")


def _normalize_to_filename(path_or_name: Optional[str]) -> Optional[str]:
    """Extract filename from absolute or relative path."""
    if not path_or_name:
        return None
    # Works for absolute/relative windows/unix paths
    return Path(path_or_name).name


def get_chart_url_fast(trade: Dict[str, Any]) -> Optional[str]:
    """
    Fast version of get_chart_url - only checks direct chart_path field and file existence.
    Does NOT call metadata API or pattern matching to avoid slow operations.
    Phase 5F Fix: Validates file existence before returning URL.
    Use this for bulk operations like listing trades.
    """
    chart_path = trade.get('chart_path')
    if chart_path:
        filename = _normalize_to_filename(chart_path)
        if filename:
            chart_file = CHARTS_DIR / filename
            if chart_file.exists():
                return f"/charts/{filename}"
            else:
                print(f"[CHART_SERVICE] Warning: Chart file not found in fast path: {chart_file}")
                return None
    return None


def resolve_chart_filename(trade: Dict[str, Any]) -> Optional[str]:
    """
    Unified chart filename resolver.
    
    Priority order:
    1. trade['chart_path'] field (normalized to filename)
    2. Metadata API (/charts/chart/{trade_id})
    3. Pattern matching (deterministic)
    4. Glob fallback (allows postfix variations)
    
    Args:
        trade: Trade dictionary with id, trade_id, symbol, chart_path, etc.
        
    Returns:
        Relative filename (e.g., "MNQZ5_5m_1540306142.png") or None if not found
    """
    trade_id = trade.get("id") or trade.get("trade_id") or trade.get("session_id")
    symbol = (trade.get("symbol") or trade.get("asset") or trade.get("ticker") or "").upper()
    
    if not trade_id:
        print(f"[CHART_SERVICE] No trade_id found in trade object")
        return None
    
    if not CHARTS_DIR.exists():
        print(f"[CHART_SERVICE] Charts directory does not exist: {CHARTS_DIR}")
        return None
    
    # Priority 1: Direct chart_path field
    direct = _normalize_to_filename(trade.get("chart_path"))
    if direct:
        candidate = CHARTS_DIR / direct
        if candidate.exists():
            print(f"[CHART_SERVICE] Found via chart_path field: {direct}")
            return direct
        else:
            print(f"[CHART_SERVICE] chart_path field exists but file not found: {direct}")
    
    # Priority 2: Metadata API
    try:
        response = requests.get(f"{METADATA_API_BASE}/chart/{trade_id}", timeout=TIMEOUT)
        if response.ok:
            meta = response.json()
            meta_file = _normalize_to_filename(meta.get("chart_path"))
            if meta_file:
                candidate = CHARTS_DIR / meta_file
                if candidate.exists():
                    print(f"[CHART_SERVICE] Found via metadata API: {meta_file}")
                    return meta_file
    except requests.exceptions.Timeout:
        print(f"[CHART_SERVICE] Metadata API timeout after {TIMEOUT}s for trade_id {trade_id}")
    except Exception as e:
        print(f"[CHART_SERVICE] Metadata API error: {e}")
    
    # Priority 3: Pattern matching (deterministic)
    if symbol:
        for pat in PATTERNS:
            if "{symbol}" in pat and not symbol:
                continue
            try:
                fname = pat.format(symbol=symbol, trade_id=trade_id)
                candidate = CHARTS_DIR / fname
                if candidate.exists():
                    print(f"[CHART_SERVICE] Found via pattern '{pat}': {fname}")
                    return fname
            except KeyError:
                # Pattern has placeholder that doesn't exist
                continue
    
    # Priority 4: Glob fallback (allows postfix variations like "_annotated.png")
    if symbol:
        try:
            glob_pattern = f"{symbol}_*_{trade_id}*.png"
            matches = list(CHARTS_DIR.glob(glob_pattern))
            if matches:
                # Return first match (sorted for consistency)
                result = sorted(matches)[0].name
                print(f"[CHART_SERVICE] Found via glob '{glob_pattern}': {result}")
                return result
        except Exception as e:
            print(f"[CHART_SERVICE] Glob search error: {e}")
    
    print(f"[CHART_SERVICE] Chart not found for trade_id {trade_id}, symbol {symbol}")
    return None


def get_chart_url(trade: Dict[str, Any]) -> Optional[str]:
    """
    Return standardized /charts/{filename} URL if chart is resolvable, else None.
    Uses TTL cache for performance [5F.2 FIX F1].
    Phase 5F Fix: Validates file existence before returning URL.
    
    Args:
        trade: Trade dictionary
        
    Returns:
        URL path like "/charts/MNQZ5_5m_1540306142.png" or None
    """
    global _chart_url_cache  # Required for cache assignment inside function
    
    trade_id = str(trade.get("id") or trade.get("trade_id") or trade.get("session_id"))
    if not trade_id:
        # No trade_id - can't cache
        fname = resolve_chart_filename(trade)
        if fname:
            # Validate file exists before returning URL
            chart_file = CHARTS_DIR / fname
            if chart_file.exists():
                return f"/charts/{fname}"
            else:
                print(f"[CHART_SERVICE] Warning: Chart file not found: {chart_file}")
        return None
    
    current_time = time.time()
    
    # Check cache
    with _chart_cache_lock:
        if trade_id in _chart_url_cache:
            cached_url, cache_timestamp = _chart_url_cache[trade_id]
            if (current_time - cache_timestamp) < CHART_CACHE_TTL:
                # Validate cached URL still exists
                if cached_url:
                    filename = cached_url.replace("/charts/", "")
                    chart_file = CHARTS_DIR / filename
                    if chart_file.exists():
                        print(f"[CHART_SERVICE] Using cached URL for trade {trade_id} (age: {current_time - cache_timestamp:.1f}s)")
                        return cached_url
                    else:
                        print(f"[CHART_SERVICE] Cached URL invalid (file missing): {cached_url}")
                        # Remove invalid cache entry
                        del _chart_url_cache[trade_id]
                else:
                    # Cache hit but URL is None - still valid (no chart available)
                    return None
        
        # Cache miss or expired - resolve
        fname = resolve_chart_filename(trade)
        chart_url = None
        
        if fname:
            # Validate file exists before caching
            chart_file = CHARTS_DIR / fname
            if chart_file.exists():
                chart_url = f"/charts/{fname}"
            else:
                print(f"[CHART_SERVICE] Warning: Chart file not found for trade {trade_id}: {chart_file}")
                # Log diagnostic info
                print(f"[CHART_SERVICE] Chart directory exists: {CHARTS_DIR.exists()}")
                print(f"[CHART_SERVICE] Chart directory contents: {list(CHARTS_DIR.glob('*.png'))[:5] if CHARTS_DIR.exists() else 'N/A'}")
        
        # Update cache (even if None to prevent repeated lookups)
        _chart_url_cache[trade_id] = (chart_url, current_time)
        
        # Clean old cache entries (keep last 100)
        if len(_chart_url_cache) > 100:
            sorted_entries = sorted(_chart_url_cache.items(), key=lambda x: x[1][1], reverse=True)
            _chart_url_cache = dict(sorted_entries[:100])
        
        return chart_url


def load_chart_base64(trade: Dict[str, Any]) -> Optional[str]:
    """
    Load the chart image and return base64 data URL for Vision API usage.
    
    Args:
        trade: Trade dictionary
        
    Returns:
        Base64 data URL string like "data:image/jpeg;base64,..." or None
    """
    fname = resolve_chart_filename(trade)
    if not fname:
        return None
    
    img_path = CHARTS_DIR / fname
    if not img_path.exists():
        print(f"[CHART_SERVICE] Chart file not found: {img_path}")
        return None
    
    try:
        if PIL_AVAILABLE:
            with Image.open(img_path) as im:
                # Convert to RGB (handles PNG with transparency)
                if im.mode != "RGB":
                    im = im.convert("RGB")
                
                # Resize if too large (OpenAI Vision API limits)
                max_size = 2048
                if im.width > max_size or im.height > max_size:
                    im.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Convert to JPEG base64
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=88, optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                return f"data:image/jpeg;base64,{b64}"
        else:
            # Fallback: read raw and encode
            with open(img_path, "rb") as f:
                image_data = f.read()
                b64 = base64.b64encode(image_data).decode("utf-8")
                return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[CHART_SERVICE] Failed to load/process chart from {img_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

