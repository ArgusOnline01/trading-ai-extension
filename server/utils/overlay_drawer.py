"""
Phase 5C: Overlay Drawer
Draws BOS lines and POI zones over existing chart images for preview
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# Try to import matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from PIL import Image
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
    PIL_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    PIL_AVAILABLE = False
    print("[WARN] matplotlib or PIL not installed. Overlay rendering disabled.")


def find_chart_image(trade_id: int, symbol: str = None) -> Optional[Path]:
    """
    Find the chart image file for a given trade.
    
    Args:
        trade_id: Trade ID
        symbol: Optional symbol for pattern matching
        
    Returns:
        Path to chart image, or None if not found
    """
    charts_dir = Path(__file__).parent.parent / "data" / "charts"
    
    if not charts_dir.exists():
        return None
    
    # Try exact match first: SYMBOL_5m_TRADE_ID.png
    if symbol:
        exact_path = charts_dir / f"{symbol}_5m_{trade_id}.png"
        if exact_path.exists():
            return exact_path
        
        # Try glob pattern
        pattern = f"{symbol}_5m_{trade_id}*.png"
        matches = list(charts_dir.glob(pattern))
        if matches:
            return matches[0]
    
    # Try generic patterns
    patterns = [
        f"*_5m_{trade_id}.png",
        f"chart_{trade_id}.png",
        f"{trade_id}.png"
    ]
    
    for pattern in patterns:
        matches = list(charts_dir.glob(pattern))
        if matches:
            return matches[0]
    
    return None


def draw_overlay_from_labels(
    trade_id: int,
    bos: Optional[Dict[str, float]] = None,
    poi_list: List[Dict[str, Any]] = None,
    bias: Optional[str] = None,
    mode: str = "draft",
    symbol: Optional[str] = None
) -> Optional[str]:
    """
    Draw BOS line and POI zones over the cached chart image for preview.
    
    Args:
        trade_id: Trade ID to find the chart
        bos: BOS dict with "start" and "end" keys (price levels)
        poi_list: List of POI dicts with "low", "high", "reason" keys
        bias: "bullish" or "bearish" for POI coloring
        mode: "draft" or "final" (affects filename)
        symbol: Optional symbol for finding chart file
        
    Returns:
        Path to overlay image, or None if chart not found or rendering failed
    """
    if not MATPLOTLIB_AVAILABLE or not PIL_AVAILABLE:
        print("[ERROR] matplotlib or PIL not available for overlay rendering")
        return None
    
    # Find the chart image
    chart_path = find_chart_image(trade_id, symbol)
    if not chart_path or not chart_path.exists():
        print(f"[OVERLAY] Chart not found for trade {trade_id}")
        return None
    
    # Setup output directory
    overlays_dir = Path(__file__).parent.parent / "data" / "amn_training_examples" / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate overlay filename
    overlay_filename = f"{trade_id}_{mode}.png"
    overlay_path = overlays_dir / overlay_filename
    
    try:
        # Load the base chart image
        img = Image.open(chart_path)
        img_array = np.array(img)
        
        # Create figure with same size as image
        dpi = 100
        fig_width = img.width / dpi
        fig_height = img.height / dpi
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
        ax.imshow(img_array)
        ax.axis('off')
        
        # Get image dimensions
        img_height = img.height
        img_width = img.width
        
        # Phase 5C: Simplified overlay drawing
        # Note: For accurate price-to-pixel mapping, we'd need to:
        # 1. Load the original price data used to render the chart
        # 2. Map prices to pixel coordinates based on chart axes
        # For now, we'll draw annotations in visible areas as placeholders
        # Full implementation would integrate with chart_reconstruction/renderer.py
        
        # Draw BOS line (horizontal dashed line)
        if bos and bos.get("start") and bos.get("end"):
            # Draw at approximate middle area (will be refined in future)
            bos_y = img_height * 0.5
            ax.axhline(y=bos_y, color="#00B0FF", linestyle="--", linewidth=2.5, alpha=0.9, zorder=10)
            ax.text(img_width * 0.02, bos_y + 5, f"BOS {bos['start']}→{bos['end']}", 
                   color="#00B0FF", fontsize=11, weight='bold',
                   bbox=dict(boxstyle='round,pad=0.4', facecolor='#131722', edgecolor='#00B0FF', alpha=0.9))
        
        # Draw POI zones (horizontal spans)
        if poi_list:
            poi_color_bullish = "#4FC3F7"  # Light blue
            poi_color_bearish = "#EF5350"   # Red
            
            poi_color = poi_color_bullish if bias == "bullish" else poi_color_bearish
            
            # Spread POIs vertically (will need price mapping for accuracy)
            for i, poi in enumerate(poi_list):
                if poi.get("low") and poi.get("high"):
                    # Calculate Y positions (simplified - spread from center)
                    base_y = img_height * 0.5
                    spacing = img_height * 0.15
                    poi_y_low = base_y - spacing + (i * spacing * 0.5)
                    poi_y_high = poi_y_low + (img_height * 0.08)
                    
                    # Draw horizontal span for POI zone
                    ax.axhspan(poi_y_low, poi_y_high, color=poi_color, alpha=0.35, zorder=5)
                    
                    # Add label
                    reason = poi.get("reason", "POI")
                    reason_short = reason[:20] if reason else "POI"
                    ax.text(img_width * 0.02, (poi_y_low + poi_y_high) / 2, 
                           f"POI {poi['low']}–{poi['high']}: {reason_short}", 
                           color=poi_color, fontsize=9, weight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='#131722', edgecolor=poi_color, alpha=0.8))
        
        # Save overlay
        plt.tight_layout(pad=0)
        plt.savefig(overlay_path, bbox_inches='tight', pad_inches=0, 
                   facecolor='#131722', dpi=dpi)
        plt.close(fig)
        
        print(f"[OVERLAY] Rendered overlay: {overlay_path}")
        return str(overlay_path)
        
    except Exception as e:
        print(f"[ERROR] Failed to create overlay: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_overlay_url(overlay_path: str) -> str:
    """
    Convert overlay file path to URL path for frontend access.
    
    Args:
        overlay_path: Full file path to overlay
        
    Returns:
        URL path relative to server root
    """
    if not overlay_path:
        return ""
    
    # Extract relative path from data directory
    path = Path(overlay_path)
    data_dir = Path(__file__).parent.parent / "data"
    
    try:
        relative = path.relative_to(data_dir)
        # Convert to URL path (forward slashes)
        url_path = str(relative).replace("\\", "/")
        return f"/charts/overlays/{url_path}" if "overlays" not in url_path else f"/data/{url_path}"
    except ValueError:
        # Path not relative to data dir, return as-is
        return overlay_path

