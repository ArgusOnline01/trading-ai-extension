"""AI routes for Phase 4D: AI Learning System."""

from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from typing import Optional, List, Dict, Any, Tuple
import base64
import json
from pathlib import Path
from pydantic import BaseModel
from db.session import SessionLocal
from db.models import Trade, Annotation, AILesson, AIProgress
from ai.rag.retrieval import get_retrieval_service
from ai.rag.embeddings import get_embedding_service
from ai.rag.chroma_client import get_chroma_client
from ai.rag.indexing import index_corrected_annotation
from openai_client import get_client
import os
import io

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None
    ImageDraw = None

router = APIRouter(prefix="/ai", tags=["AI Learning"])


def _extract_corrected_shapes(annotation_payload: Optional[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Normalize corrected annotation payload into simple shape dictionaries."""
    shapes = {"bos": [], "poi": [], "circles": []}
    if not annotation_payload:
        return shapes

    for key in ("bos", "poi", "circles"):
        entries = annotation_payload.get(key) or []
        for entry in entries:
            if isinstance(entry, dict):
                corrected = entry.get("corrected") if isinstance(entry.get("corrected"), dict) else None
                original = entry.get("original") if isinstance(entry.get("original"), dict) else {}
                data = corrected or entry
                merged = {
                    **{k: v for k, v in original.items() if k not in ("x", "y", "radius", "left", "top", "width", "height")},
                    **data
                }
                shapes[key].append(merged)
    return shapes


def _render_corrected_overlay(chart_path: Path, corrected_shapes: Dict[str, List[Dict[str, Any]]]) -> Optional[str]:
    """Create a base64 image overlaying corrected annotations on the chart."""
    if Image is None or ImageDraw is None:
        print("[AI Routes] Pillow not installed - skipping corrected overlay image")
        return None

    if not chart_path or not chart_path.exists():
        return None

    try:
        img = Image.open(chart_path).convert("RGB")
    except Exception as exc:
        print(f"[AI Routes] Failed to open chart for overlay: {exc}")
        return None

    draw = ImageDraw.Draw(img, "RGBA")

    # Colors for corrected annotations
    bos_color = (80, 200, 120, 255)  # teal/green
    poi_color = (255, 215, 0, 180)   # gold with transparency
    circle_color = (80, 170, 255, 200)

    # Draw BOS lines
    for bos in corrected_shapes.get("bos", []):
        x1, y1 = bos.get("x1"), bos.get("y1")
        x2, y2 = bos.get("x2"), bos.get("y2")
        if None in (x1, y1, x2, y2):
            continue
        draw.line((x1, y1, x2, y2), fill=bos_color, width=12)
        # End caps
        for (x, y) in ((x1, y1), (x2, y2)):
            r = 18
            draw.ellipse((x - r, y - r, x + r, y + r), fill=bos_color)

    # Draw POI rectangles/boxes
    for poi in corrected_shapes.get("poi", []):
        left = poi.get("left")
        top = poi.get("top")
        width = poi.get("width")
        height = poi.get("height")
        if None in (left, top, width, height):
            continue
        draw.rectangle((left, top, left + width, top + height), outline=poi_color, width=8)

    # Draw circles (fractals)
    for circle in corrected_shapes.get("circles", []):
        x = circle.get("x")
        y = circle.get("y")
        radius = circle.get("radius")
        if None in (x, y, radius):
            continue
        bbox = (x - radius, y - radius, x + radius, y + radius)
        draw.ellipse(bbox, outline=circle_color, width=10)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _normalize_coords(shapes: Dict[str, List[Dict[str, Any]]], image_width: int, image_height: int) -> Dict[str, List[Dict[str, Any]]]:
    """Clamp/filter coordinates to image bounds to avoid legacy outliers."""
    def clamp(v, lo, hi):
        try:
            return max(lo, min(hi, float(v)))
        except Exception:
            return None

    normalized: Dict[str, List[Dict[str, Any]]] = {"bos": [], "poi": [], "circles": []}
    w, h = float(image_width or 0), float(image_height or 0)
    if not w or not h:
        return shapes

    # BOS lines
    for bos in shapes.get("bos", []):
        x1 = clamp(bos.get("x1"), 0, w)
        y1 = clamp(bos.get("y1"), 0, h)
        x2 = clamp(bos.get("x2"), 0, w)
        y2 = clamp(bos.get("y2"), 0, h)
        if None in (x1, y1, x2, y2):
            continue
        normalized["bos"].append({**bos, "x1": x1, "y1": y1, "x2": x2, "y2": y2})

    # POI boxes
    for poi in shapes.get("poi", []):
        left = clamp(poi.get("left"), 0, w)
        top = clamp(poi.get("top"), 0, h)
        width = clamp(poi.get("width"), 0, w)
        height = clamp(poi.get("height"), 0, h)
        if None in (left, top, width, height):
            continue
        normalized["poi"].append({**poi, "left": left, "top": top, "width": width, "height": height})

    # Circles
    for c in shapes.get("circles", []):
        x = clamp(c.get("x"), 0, w)
        y = clamp(c.get("y"), 0, h)
        r = clamp(c.get("radius"), 0, min(w, h))
        if None in (x, y, r):
            continue
        normalized["circles"].append({**c, "x": x, "y": y, "radius": r})

    return normalized


class AnalyzeChartRequest(BaseModel):
    """Request model for chart analysis."""
    chart_image_base64: Optional[str] = None
    trade_id: Optional[str] = None
    query: Optional[str] = None


class AnnotationData(BaseModel):
    """Annotation data model."""
    poi: Optional[List[Dict[str, Any]]] = None
    bos: Optional[List[Dict[str, Any]]] = None
    circles: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class AnalyzeChartResponse(BaseModel):
    """Response model for chart analysis."""
    success: bool
    annotations: AnnotationData
    similar_trades: List[Dict[str, Any]]
    reasoning: Optional[str] = None


class SaveLessonRequest(BaseModel):
    """Request model for saving a lesson."""
    trade_id: str
    ai_annotations: Dict[str, Any]
    corrected_annotations: Dict[str, Any]
    corrected_reasoning: Optional[str] = None  # User's correction to AI's reasoning


@router.post("/analyze-chart", response_model=AnalyzeChartResponse)
async def analyze_chart(
    file: Optional[UploadFile] = File(None),
    trade_id: Optional[str] = Form(None),
    query: Optional[str] = Form(None)
):
    """
    Analyze a chart and suggest annotations (POI, BOS) using AI.
    
    This endpoint:
    1. Takes a chart image (or trade_id to load chart)
    2. Uses RAG to find similar trades
    3. Uses GPT-5 to analyze the chart and suggest annotations
    4. Returns annotation coordinates in JSON format
    
    Args:
        file: Chart image file (optional if trade_id provided)
        trade_id: Trade ID to load chart from database (optional if file provided)
        query: Optional query text for RAG retrieval
        
    Returns:
        AnalyzeChartResponse with suggested annotations and similar trades
    """
    try:
        db = SessionLocal()
        
        # Get chart image
        chart_image_base64 = None
        image_width = None
        image_height = None
        
        if file:
            # Read uploaded file
            image_data = await file.read()
            chart_image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Get image dimensions for coordinate accuracy
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_data))
            image_width = img.width
            image_height = img.height
        elif trade_id:
            # Load chart from database
            trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
            if not trade:
                raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
            
            # Try to load chart file - check both chart_url and common naming pattern
            charts_dir = Path(__file__).parent.parent / "data" / "charts"
            chart_path = None
            
            if trade.chart_url:
                # Try using chart_url (could be relative or absolute)
                chart_url_basename = os.path.basename(trade.chart_url)
                chart_path = charts_dir / chart_url_basename
                if not chart_path.exists():
                    # Try the full path if it's already a path
                    if os.path.exists(trade.chart_url):
                        chart_path = Path(trade.chart_url)
            
            # Fallback: try common naming pattern
            if not chart_path or not chart_path.exists():
                chart_path = charts_dir / f"{trade.symbol}_5m_{trade.trade_id}.png"
            
            # Final fallback: search by trade_id
            if not chart_path or not chart_path.exists():
                matches = list(charts_dir.glob(f"*{trade.trade_id}*.png"))
                if matches:
                    chart_path = matches[0]
            
            if chart_path and chart_path.exists():
                with open(chart_path, "rb") as f:
                    image_data = f.read()
                    chart_image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # Get image dimensions for coordinate accuracy
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(image_data))
                image_width = img.width
                image_height = img.height
            else:
                raise HTTPException(status_code=404, detail=f"Chart file not found for trade {trade_id}. Checked: {charts_dir}")
        else:
            raise HTTPException(status_code=400, detail="Either file or trade_id must be provided")
        
        # Get current trade's annotations and notes (if analyzing a specific trade)
        current_trade_annotation = None
        current_trade_notes = None
        current_trade_annotation_data = None
        if trade_id:
            current_trade_annotation = db.query(Annotation).filter(Annotation.trade_id == trade_id).first()
            if current_trade_annotation:
                if current_trade_annotation.notes:
                    current_trade_notes = current_trade_annotation.notes
                # Extract annotation coordinates as reference points
                current_trade_annotation_data = {
                    "poi": current_trade_annotation.poi_locations or [],
                    "bos": current_trade_annotation.bos_locations or [],
                    "circles": current_trade_annotation.circle_locations or []
                }
        
        # Get past corrections/lessons for THIS specific trade (if any)
        past_lessons_text = ""
        past_lessons = []  # Initialize to avoid undefined variable
        if trade_id:
            past_lessons = db.query(AILesson).filter(AILesson.trade_id == trade_id).order_by(AILesson.created_at.desc()).limit(3).all()
            if past_lessons:
                past_lessons_text = "\n\nCRITICAL - PAST CORRECTIONS FOR THIS SAME TRADE (you MUST learn from these!):\n"
                past_lessons_text += "I have corrected you on this EXACT same chart multiple times. You MUST avoid making the same mistakes again!\n\n"
                
                for i, lesson in enumerate(past_lessons, 1):
                    past_lessons_text += f"=== CORRECTION #{i} (Attempt {len(past_lessons) - i + 1}) ===\n"
                    
                    if lesson.corrected_annotations:
                        # Show ACTUAL corrected annotation coordinates (what the user changed them to)
                        if lesson.corrected_annotations.get("bos"):
                            bos_list = lesson.corrected_annotations["bos"]
                            past_lessons_text += f"I corrected your BOS lines ({len(bos_list)} line(s)):\n"
                            for j, bos in enumerate(bos_list, 1):
                                corrected = bos.get("corrected") if isinstance(bos, dict) else None
                                original = bos.get("original") if isinstance(bos, dict) else None
                                data = corrected or bos
                                price = data.get("price") or (original or {}).get("price", "unknown")
                                x1 = data.get("x1", 0)
                                y1 = data.get("y1", 0)
                                x2 = data.get("x2", 0)
                                y2 = data.get("y2", 0)
                                past_lessons_text += f"  BOS {j} (price {price}): x1={x1:.0f}, y1={y1:.0f}, x2={x2:.0f}, y2={y2:.0f}\n"
                        if lesson.corrected_annotations.get("poi"):
                            poi_list = lesson.corrected_annotations["poi"]
                            past_lessons_text += f"I corrected your POI ({len(poi_list)} box(es)):\n"
                            for j, poi in enumerate(poi_list, 1):
                                corrected = poi.get("corrected") if isinstance(poi, dict) else None
                                original = poi.get("original") if isinstance(poi, dict) else None
                                data = corrected or poi
                                price = data.get("price") or (original or {}).get("price", "unknown")
                                left = data.get("left", 0)
                                top = data.get("top", 0)
                                past_lessons_text += f"  POI {j} (price {price}): left={left:.0f}, top={top:.0f}\n"
                        if lesson.corrected_annotations.get("circles"):
                            circles_list = lesson.corrected_annotations["circles"]
                            past_lessons_text += f"I corrected your circles ({len(circles_list)} circle(s)):\n"
                            for j, circle in enumerate(circles_list, 1):
                                corrected = circle.get("corrected") if isinstance(circle, dict) else None
                                original = circle.get("original") if isinstance(circle, dict) else None
                                data = corrected or circle
                                x = data.get("x", 0)
                                y = data.get("y", 0)
                                radius = data.get("radius", 0)
                                past_lessons_text += f"  Circle {j}: x={x:.0f}, y={y:.0f}, radius={radius:.0f}\n"
                    
                    if lesson.corrected_reasoning:
                        past_lessons_text += f"\nI corrected your reasoning: \"{lesson.corrected_reasoning}\"\n"
                    
                    past_lessons_text += "\n"
                
                past_lessons_text += "CRITICAL INSTRUCTIONS:\n"
                past_lessons_text += "1. These are the EXACT coordinates I corrected your annotations to on this SAME chart\n"
                past_lessons_text += "2. You MUST place your annotations at SIMILAR positions (within 50-100 pixels)\n"
                past_lessons_text += "3. If I corrected circles to mark fractals, place circles at those same fractal points\n"
                past_lessons_text += "4. If I corrected BOS lines, place BOS lines at those same price levels and time ranges\n"
                past_lessons_text += "5. Read my reasoning corrections carefully - they explain WHY I made those corrections\n"
                past_lessons_text += "6. DO NOT make the same mistakes again! Learn from these corrections!\n"
        
        # Get retrieval service
        retrieval_service = get_retrieval_service()
        
        # Find similar trades using RAG
        if query:
            similar_trades = retrieval_service.find_similar_trades(query_text=query, n_results=5)
        else:
            # Use default query
            similar_trades = retrieval_service.find_similar_trades(
                query_text="Trading setup with POI and BOS",
                n_results=5
            )
        
        # Prepare context from similar trades - include actual annotations!
        similar_trades_context = []
        for trade_data in similar_trades:
            trade_id = trade_data.get("trade_id")
            if trade_id:
                trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
                if trade:
                    annotation = db.query(Annotation).filter(Annotation.trade_id == trade_id).first()
                    context = {
                        "trade_id": trade_id,
                        "symbol": trade.symbol,
                        "direction": trade.direction,
                        "outcome": trade.outcome,
                        "distance": trade_data.get("distance")
                    }
                    
                    # Include actual annotation data if available
                    if annotation:
                        # Extract price levels from POI/BOS (more useful than coordinates)
                        poi_prices = []
                        if annotation.poi_locations:
                            for poi in annotation.poi_locations:
                                if isinstance(poi, dict) and poi.get("price"):
                                    poi_prices.append(poi["price"])
                        
                        bos_prices = []
                        if annotation.bos_locations:
                            for bos in annotation.bos_locations:
                                if isinstance(bos, dict) and bos.get("price"):
                                    bos_prices.append(bos["price"])
                        
                        context["annotations"] = {
                            "poi_prices": poi_prices,
                            "bos_prices": bos_prices,
                            "notes": annotation.notes or ""
                        }
                    
                    similar_trades_context.append(context)
        
        # Use GPT-5 to analyze chart and generate annotations
        client = get_client()
        
        # Build prompt for GPT-5 - include actual annotation examples!
        examples_text = ""
        
        # FIRST: Include current trade's notes and existing annotations if available (most important!)
        current_trade_context = ""
        if current_trade_notes:
            current_trade_context = f"\n\nIMPORTANT - This is the CURRENT trade I'm analyzing. Here are MY NOTES about this specific trade:\n\"{current_trade_notes}\"\n\nUse these notes to understand my exact strategy and reasoning for this trade. The annotations you create should match what I described in these notes.\n"
        
        # Include existing annotations as APPROXIMATE reference points (not exact copies)
        # This helps the AI understand the coordinate system, but it should still learn to identify positions visually
        reference_annotations_text = ""
        reference_annotation = current_trade_annotation_data
        if reference_annotation:
            reference_annotations_text = "\n\nREFERENCE (APPROXIMATE GUIDANCE ONLY): I have already annotated this chart. These are my approximate positions - use them as a ROUGH GUIDE to understand the coordinate system, but you must still visually identify the exact positions from the chart image:\n"
            if reference_annotation.get("bos") and len(reference_annotation["bos"]) > 0:
                for i, bos in enumerate(reference_annotation["bos"][:2], 1):  # Show first 2 BOS lines
                    price = bos.get("price", "unknown")
                    x1 = bos.get("x1", 0)
                    y1 = bos.get("y1", 0)
                    x2 = bos.get("x2", 0)
                    y2 = bos.get("y2", 0)
                    reference_annotations_text += f"  My BOS {i} (price {price}): approximately x1≈{x1:.0f}, y1≈{y1:.0f}, x2≈{x2:.0f}, y2≈{y2:.0f}\n"
            if reference_annotation.get("poi") and len(reference_annotation["poi"]) > 0:
                for i, poi in enumerate(reference_annotation["poi"][:2], 1):  # Show first 2 POI
                    price = poi.get("price", "unknown")
                    left = poi.get("left", 0)
                    top = poi.get("top", 0)
                    reference_annotations_text += f"  My POI {i} (price {price}): approximately left≈{left:.0f}, top≈{top:.0f}\n"
            if reference_annotation.get("circles") and len(reference_annotation["circles"]) > 0:
                for i, circle in enumerate(reference_annotation["circles"][:2], 1):  # Show first 2 circles
                    x = circle.get("x", 0)
                    y = circle.get("y", 0)
                    radius = circle.get("radius", 0)
                    reference_annotations_text += f"  My Circle {i}: approximately x≈{x:.0f}, y≈{y:.0f}, radius≈{radius:.0f}\n"
            if reference_annotations_text:
                reference_annotations_text += "\nIMPORTANT: These are APPROXIMATE reference points to help you understand the coordinate system. You must still:\n"
                reference_annotations_text += "1. Look at the chart image and visually identify where annotations should be placed\n"
                reference_annotations_text += "2. Use the reference coordinates as a ROUGH guide (within 100-200 pixels), not exact copies\n"
                reference_annotations_text += "3. For annotations at different price levels or times, you must identify them visually from the chart\n"
                reference_annotations_text += "4. The goal is to learn to identify positions from the chart, not to copy my coordinates exactly\n"
        
        if similar_trades_context:
            examples_text = "\n\nHere are examples of how I annotated SIMILAR trades (for reference):\n\n"
            for i, example in enumerate(similar_trades_context[:3], 1):  # Show top 3 examples
                symbol = example.get("symbol", "Unknown")
                direction = example.get("direction", "")
                outcome = example.get("outcome", "")
                examples_text += f"Example {i} - {symbol} {direction} {outcome}:\n"
                
                if example.get("annotations"):
                    ann = example["annotations"]
                    if ann.get("poi_prices"):
                        poi_str = ", ".join([str(p) for p in ann["poi_prices"]])
                        examples_text += f"- POI price levels: {poi_str}\n"
                    if ann.get("bos_prices"):
                        bos_str = ", ".join([str(p) for p in ann["bos_prices"]])
                        examples_text += f"- BOS price levels: {bos_str}\n"
                    if ann.get("notes"):
                        examples_text += f"- My notes: \"{ann['notes']}\"\n"
                else:
                    examples_text += "- (No annotations for this trade)\n"
                examples_text += "\n"
        
        # Build prompt for GPT-5 (include system instructions in the question)
        # Include image dimensions so AI can give accurate coordinates
        image_dimensions_text = ""
        if image_width and image_height:
            # Estimate chart plotting area (accounting for margins, axes, title)
            # Typical margins: ~10-15% on each side for axes/title
            # Left margin: ~80-120px for Y-axis labels
            # Bottom margin: ~60-80px for X-axis labels  
            # Top margin: ~40-60px for title
            # Right margin: ~20-40px
            estimated_left_margin = int(image_width * 0.08)  # ~8% for Y-axis
            estimated_right_margin = int(image_width * 0.02)  # ~2% right margin
            estimated_top_margin = int(image_height * 0.05)  # ~5% for title
            estimated_bottom_margin = int(image_height * 0.08)  # ~8% for X-axis
            
            chart_area_left = estimated_left_margin
            chart_area_right = image_width - estimated_right_margin
            chart_area_top = estimated_top_margin
            chart_area_bottom = image_height - estimated_bottom_margin
            chart_area_width = chart_area_right - chart_area_left
            chart_area_height = chart_area_bottom - chart_area_top
            
            image_dimensions_text = f"""
IMPORTANT: The chart image dimensions are {image_width} pixels wide by {image_height} pixels tall.

CHART PLOTTING AREA (where candlesticks are actually drawn):
- The actual chart area is NOT the full image - it has margins for axes, labels, and title
- Estimated chart area: X from {chart_area_left} to {chart_area_right} pixels (width: {chart_area_width}px)
- Estimated chart area: Y from {chart_area_top} to {chart_area_bottom} pixels (height: {chart_area_height}px)
- Left margin (~{estimated_left_margin}px): Y-axis price labels
- Bottom margin (~{estimated_bottom_margin}px): X-axis time labels
- Top margin (~{estimated_top_margin}px): Chart title
- Right margin (~{estimated_right_margin}px): Small padding

COORDINATE CALCULATION - STEP BY STEP:

STEP 1: Identify the actual chart plotting area visually:
- Look at the image and find where the candlesticks actually start (left edge) and end (right edge)
- Find where the candlesticks start vertically (top of chart area) and end (bottom of chart area)
- These boundaries define the actual plotting area, NOT the full image dimensions

STEP 2: For Y-coordinates (price) - CRITICAL: Y-axis is INVERTED (0 at top, increases downward):
- Look at the Y-axis price labels on the LEFT side of the chart
- Find the MIN price (e.g., 1.158) - this is at the BOTTOM of the chart area (HIGH Y value)
- Find the MAX price (e.g., 1.170) - this is at the TOP of the chart area (LOW Y value)
- IMPORTANT: Higher prices = LOWER Y pixel values (closer to top of image)
- To find Y for a specific price: Look at where that price label appears on the Y-axis, then trace horizontally to find the pixel Y coordinate
- Example: If price=1.169, find "1.169" on the Y-axis labels, then find the horizontal pixel position at that level
- DO NOT calculate - VISUALLY identify where the price level appears on the chart image
- The Y coordinate should be the pixel row where that price level appears

STEP 3: For X-coordinates (time) - CRITICAL: Find EXACT time positions visually:
- Look at the X-axis time labels at the BOTTOM of the chart
- Find the START time (e.g., "Oct 27, 15:30") - note its pixel X position
- Find the END time (e.g., "Oct 30, 13:40") - note its pixel X position
- If notes mention a specific time like "Oct 28, 9:20" or "around 9:00 October 28th 9:20":
  * Find that EXACT time label on the X-axis (look for "Oct 28" and "09:20" or "9:20")
  * Note the pixel X position where that time label appears
  * This is your reference point
- For BOS lines: 
  * x1 should be where the price level was FIRST touched (look at candlesticks touching that price level)
  * x2 should be where the price level was LAST touched or where it becomes relevant
  * DO NOT span the entire chart - only span the specific time window where that price level was relevant
  * Typical width: 200-400 pixels (a few hours to half a day), NOT 3000+ pixels
- DO NOT calculate from time ratios - VISUALLY identify where specific times appear on the X-axis labels

All coordinates should be relative to the FULL IMAGE (0,0 at top-left), but you must account for the chart margins when calculating positions.
"""
        
        user_prompt = f"""You are an expert trader analyzing charts for Smart Money Concepts (SMC) setups.
Your task is to identify:
1. POI (Point of Interest) - Price levels where price may react
2. BOS (Break of Structure) - Lines showing structure breaks
3. Any other relevant annotations

Return your analysis as JSON with this format:
{{
  "poi": [{{"left": x, "top": y, "width": w, "height": h, "price": price_level}}],
  "bos": [{{"x1": x1, "y1": y1, "x2": x2, "y2": y2, "price": price_level}}],
  "circles": [{{"x": x, "y": y, "radius": r}}],
  "notes": "Brief explanation of the setup",
  "reasoning": "Why you identified these annotations"
}}
{image_dimensions_text}
CRITICAL COORDINATE ACCURACY REQUIREMENTS:
- You MUST look at the actual chart image and calculate EXACT pixel coordinates
- Do NOT use approximate values or "around" - use precise pixel positions
- For POI: left/top should be the exact pixel position of the price level on the chart
- For BOS: x1/y1 and x2/y2 should be the exact pixel positions where the line starts and ends on the chart
- For circles: x/y should be the exact pixel position of the center point on the chart
- To find coordinates: Look at the chart's Y-axis (price scale) and X-axis (time scale) to determine the exact pixel position
- Example: If a price level is 1.169 and the Y-axis shows 1.158-1.170, calculate: y_position = (1.169 - 1.158) / (1.170 - 1.158) * image_height
- The price field should be the actual price level (e.g., 1.169), but coordinates must be exact pixels

Coordinates should be relative to the chart image dimensions (pixels).
{current_trade_context}{past_lessons_text}{reference_annotations_text}{examples_text}"""
        
        # Build additional context strings (outside f-string to avoid backslash issues)
        current_trade_note_instruction = ""
        if current_trade_context:
            current_trade_note_instruction = "CRITICAL: The current trade notes above are the PRIMARY source of truth. Use them to understand my exact strategy and recreate my annotations accurately."
        
        past_lessons_instruction = ""
        if past_lessons_text:
            past_lessons_instruction = """🚨 CRITICAL - YOU HAVE BEEN CORRECTED ON THIS EXACT SAME CHART BEFORE! 🚨
The past corrections above show you the EXACT coordinates I corrected your annotations to. You MUST:
- Place annotations at those SAME positions (within 50-100 pixels)
- Use those coordinates as your PRIMARY reference
- DO NOT guess or estimate - use the corrected coordinates I provided
- If I corrected circles to mark fractals at specific positions, place circles at those EXACT positions
- If I corrected BOS lines to specific coordinates, place BOS lines at those EXACT coordinates
- Read my reasoning corrections - they explain WHY I made those corrections
- This is the SAME chart, so the coordinates should be nearly identical!"""
        
        reference_instruction = ""
        if reference_annotations_text:
            reference_instruction = "NOTE: The reference coordinates above are APPROXIMATE guides to help you understand the coordinate system. You must still visually identify positions from the chart image."
        
        based_on_text = "Based on "
        if current_trade_context:
            based_on_text += "the current trade notes and "
        if past_lessons_text:
            based_on_text += "the past corrections (which are MOST IMPORTANT for this same chart) and "
        based_on_text += "these examples, analyze this chart and identify similar setups."
        
        # Append additional instructions to the prompt
        additional_instructions = """
Pay attention to:
- Where I placed POI in similar situations (price levels)
- How I identified BOS breaks (price levels)
- The reasoning in my notes (especially the current trade notes if provided)
- Specific terminology I use (fractals, internal structure, bullish/bearish structure, liquidity sweeps, etc.)
Try to recreate similar annotation patterns on this chart, matching my strategy as described in the notes.

BOS LINE INTERPRETATION:
- If notes mention "BOS around the high from 1.169 to [time]" or "BOS from X to Y", this usually means ONE horizontal line at that price level spanning from the first touch to the second touch
- If notes mention "internal structure BOS" and "external structure BOS", these might be TWO separate horizontal lines at different price levels
- For horizontal BOS lines: y1 and y2 should be the SAME (same price level), x1 and x2 should span ONLY the specific time range where that price level was touched
- Look at the candlesticks visually to see where the price level was actually touched - the BOS line should span ONLY that specific area, not the entire chart
- Typical BOS line width: 200-600 pixels (representing a few hours to a day), NOT 3000+ pixels (entire chart width)
- If you cannot determine exact times, make the line span the visible area where candlesticks touch that price level, but keep it narrow (200-400 pixels wide)

CRITICAL COORDINATE ACCURACY:
- DO NOT calculate coordinates mathematically - VISUALLY identify exact pixel positions from the chart image
- For Y-coordinates: Find the price label on the Y-axis, then find the horizontal pixel row at that level
- For X-coordinates: Find the time label on the X-axis, then find the vertical pixel column at that position
- If you cannot see exact labels, estimate based on the visual position of candlesticks and grid lines
- The goal is to match where the user actually placed their annotations - look at the chart and find those exact positions
- When in doubt, place annotations closer to where candlesticks actually touch the price level, not at calculated positions"""
        
        # Combine all parts of the prompt
        user_prompt = user_prompt + "\n" + current_trade_note_instruction + "\n" + past_lessons_instruction + "\n" + reference_instruction + "\n" + based_on_text + additional_instructions

        # Disable overlay image sending (reverted Option B)
        corrected_overlay_base64 = None

        # Log what we're sending to AI (for debugging)
        if past_lessons_text:
            print(f"\n[AI Routes] ===== SENDING PAST CORRECTIONS TO AI =====")
            print(f"[AI Routes] Trade ID: {trade_id}")
            print(f"[AI Routes] Number of past corrections: {len(past_lessons)}")
            print(f"[AI Routes] Past corrections text preview (first 500 chars):\n{past_lessons_text[:500]}...")
            print(f"[AI Routes] ===========================================\n")
        
        # Call GPT-5 with vision
        try:
            response = await client.create_response(
                question=user_prompt,
                image_base64=chart_image_base64,
                model="gpt-5-chat-latest",
                conversation_history=None
            )
            
            # Parse response (assuming GPT returns JSON)
            answer = response.get("answer", "")
            
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', answer, re.DOTALL)
            if json_match:
                annotation_data = json.loads(json_match.group())
                # Log the raw coordinates for debugging
                print(f"[AI Routes] AI returned annotations:")
                print(f"  POI count: {len(annotation_data.get('poi', []))}")
                for i, poi in enumerate(annotation_data.get('poi', [])):
                    print(f"    POI {i}: left={poi.get('left')}, top={poi.get('top')}, price={poi.get('price')}")
                print(f"  BOS count: {len(annotation_data.get('bos', []))}")
                for i, bos in enumerate(annotation_data.get('bos', [])):
                    print(f"    BOS {i}: x1={bos.get('x1')}, y1={bos.get('y1')}, x2={bos.get('x2')}, y2={bos.get('y2')}, price={bos.get('price')}")
                print(f"  Circles count: {len(annotation_data.get('circles', []))}")
                for i, circle in enumerate(annotation_data.get('circles', [])):
                    print(f"    Circle {i}: x={circle.get('x')}, y={circle.get('y')}, radius={circle.get('radius')}")
            else:
                # Fallback: return empty annotations
                print(f"[AI Routes] Warning: AI did not return valid JSON. Response: {answer[:500]}...")
                annotation_data = {
                    "poi": [],
                    "bos": [],
                    "circles": [],
                    "notes": answer,
                    "reasoning": answer
                }
        except Exception as e:
            print(f"[AI Routes] Error calling GPT-5: {e}")
            # Fallback: return empty annotations
            annotation_data = {
                "poi": [],
                "bos": [],
                "circles": [],
                "notes": f"Error analyzing chart: {str(e)}",
                "reasoning": None
            }
        
        # Format response
        return AnalyzeChartResponse(
            success=True,
            annotations=AnnotationData(
                poi=annotation_data.get("poi", []),
                bos=annotation_data.get("bos", []),
                circles=annotation_data.get("circles", []),
                notes=annotation_data.get("notes")
            ),
            similar_trades=similar_trades_context,
            reasoning=annotation_data.get("reasoning")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart analysis failed: {str(e)}")
    finally:
        db.close()


@router.post("/lessons")
async def save_lesson(request: SaveLessonRequest):
    """
    Save an AI lesson (corrections to AI annotations).
    
    Args:
        request: SaveLessonRequest with trade_id, ai_annotations, and corrected_annotations
        
    Returns:
        Success message
    """
    try:
        db = SessionLocal()
        
        # Create lesson record
        lesson = AILesson(
            trade_id=request.trade_id,
            ai_annotations=request.ai_annotations,
            corrected_annotations=request.corrected_annotations,
            corrected_reasoning=request.corrected_reasoning
        )
        
        db.add(lesson)
        db.commit()
        db.refresh(lesson)

        # Update overall AI progress metrics (simple counter for now)
        progress = db.query(AIProgress).first()
        if not progress:
            progress = AIProgress(total_lessons=1)
            db.add(progress)
        else:
            progress.total_lessons = (progress.total_lessons or 0) + 1
        db.commit()
        
        # Auto-index corrected annotations in Chroma for RAG (Phase 4D.1)
        try:
            index_corrected_annotation(request.trade_id, request.corrected_annotations)
        except Exception as e:
            print(f"[AI Routes] Warning: Failed to index corrected annotations: {e}")
            # Don't fail the request if indexing fails
        
        # TODO: Calculate accuracy score (Phase 4D.3)
        
        return {
            "success": True,
            "lesson_id": lesson.id,
            "message": "Lesson saved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save lesson: {str(e)}")
    finally:
        db.close()


@router.get("/lessons")
async def get_all_lessons(trade_id: Optional[str] = None, limit: int = 50):
    """
    Get all AI lessons, optionally filtered by trade_id.
    """
    try:
        db = SessionLocal()
        
        query = db.query(AILesson)
        if trade_id:
            query = query.filter(AILesson.trade_id == trade_id)
        
        lessons = query.order_by(AILesson.created_at.desc()).limit(limit).all()
        
        result = []
        for lesson in lessons:
            # Get trade info
            trade = db.query(Trade).filter(Trade.trade_id == lesson.trade_id).first()
            
            result.append({
                "id": lesson.id,
                "trade_id": lesson.trade_id,
                "symbol": trade.symbol if trade else "Unknown",
                "direction": trade.direction if trade else "Unknown",
                "ai_annotations": lesson.ai_annotations,
                "corrected_annotations": lesson.corrected_annotations,
                "corrected_reasoning": lesson.corrected_reasoning,
                "accuracy_score": lesson.accuracy_score,
                "created_at": lesson.created_at.isoformat() if lesson.created_at else None
            })
        
        return {
            "lessons": result,
            "total": len(result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get lessons: {str(e)}")
    finally:
        db.close()


@router.delete("/lessons")
async def delete_lessons(trade_id: Optional[str] = None):
    """
    Delete AI lessons. If trade_id provided, delete only for that trade.
    Also updates AIProgress totals.
    """
    try:
        db = SessionLocal()
        q = db.query(AILesson)
        if trade_id:
            q = q.filter(AILesson.trade_id == trade_id)
        deleted = q.delete(synchronize_session=False)
        db.commit()

        # Sync progress counter
        progress = db.query(AIProgress).first()
        if progress:
            progress.total_lessons = db.query(AILesson).count()
            db.commit()

        return {"success": True, "deleted": int(deleted)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete lessons: {str(e)}")
    finally:
        db.close()


@router.get("/progress")
async def get_ai_progress():
    """
    Get AI learning progress metrics.
    
    Returns:
        Dictionary with progress metrics (total lessons, accuracy scores, etc.)
    """
    try:
        db = SessionLocal()
        from db.models import AIProgress
        
        progress = db.query(AIProgress).first()
        if not progress:
            # Create default progress record
            progress = AIProgress(
                total_lessons=0,
                poi_accuracy=0.0,
                bos_accuracy=0.0,
                setup_type_accuracy=0.0,
                overall_accuracy=0.0
            )
            db.add(progress)
            db.commit()
            db.refresh(progress)

        # Fallback: if total_lessons looks stale, sync with actual lesson count
        lessons_count = db.query(AILesson).count()
        if progress.total_lessons != lessons_count:
            progress.total_lessons = lessons_count
            db.commit()
 
        return {
            "total_lessons": progress.total_lessons,
            "poi_accuracy": progress.poi_accuracy,
            "bos_accuracy": progress.bos_accuracy,
            "setup_type_accuracy": progress.setup_type_accuracy,
            "overall_accuracy": progress.overall_accuracy,
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")
    finally:
        db.close()

