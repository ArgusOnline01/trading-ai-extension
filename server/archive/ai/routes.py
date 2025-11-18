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
from ai.accuracy import calculate_annotation_accuracy  # Phase 4D.3
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
    questions: Optional[List[Dict[str, str]]] = None  # Phase 4D.2: AI-generated questions


class SaveLessonRequest(BaseModel):
    """Request model for saving a lesson."""
    trade_id: str
    ai_annotations: Dict[str, Any]
    corrected_annotations: Dict[str, Any]
    corrected_reasoning: Optional[str] = None  # User's correction to AI's reasoning
    deleted_annotations: Optional[List[Dict[str, Any]]] = None  # AI annotations that were deleted
    questions: Optional[List[Dict[str, str]]] = None  # Phase 4D.2: AI-generated questions
    answers: Optional[List[Dict[str, str]]] = None  # Phase 4D.2: User's answers to questions


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
                                
                                # Corrected coordinates
                                x1 = data.get("x1", 0)
                                y1 = data.get("y1", 0)
                                x2 = data.get("x2", 0)
                                y2 = data.get("y2", 0)
                                corrected_length = abs(x2 - x1)
                                
                                # Original coordinates (if available)
                                orig_x1 = original.get("x1", 0) if original else 0
                                orig_x2 = original.get("x2", 0) if original else 0
                                original_length = abs(orig_x2 - orig_x1) if original else 0
                                
                                # Calculate percentage for clarity
                                img_w = image_width or 4440
                                img_h = image_height or 2651
                                x1_pct = (x1 / img_w * 100) if img_w > 0 else 0
                                x2_pct = (x2 / img_w * 100) if img_w > 0 else 0
                                y1_pct = (y1 / img_h * 100) if img_h > 0 else 0
                                y2_pct = (y2 / img_h * 100) if img_h > 0 else 0
                                
                                past_lessons_text += f"  BOS {j} (price {price}): I placed it at approximately x1={x1:.0f} ({x1_pct:.1f}% from left), x2={x2:.0f} ({x2_pct:.1f}% from left)\n"
                                past_lessons_text += f"    → Length: {corrected_length:.0f}px ({corrected_length / img_w * 100:.1f}% of chart width)\n"
                                if original and original_length > 0:
                                    length_diff = corrected_length - original_length
                                    length_change_pct = (length_diff / original_length * 100) if original_length > 0 else 0
                                    if abs(length_change_pct) > 10:  # Only show if significant change
                                        past_lessons_text += f"    → I {'extended' if length_diff > 0 else 'shortened'} your line by {abs(length_diff):.0f}px ({abs(length_change_pct):.1f}%) - this shows the BOS should span {'more' if length_diff > 0 else 'less'} of the time period\n"
                                past_lessons_text += f"    → This marks the BOS at price level {price} - look for this price level on the chart and identify where the structure break occurred\n"
                        if lesson.corrected_annotations.get("poi"):
                            poi_list = lesson.corrected_annotations["poi"]
                            past_lessons_text += f"I corrected your POI ({len(poi_list)} box(es)):\n"
                            for j, poi in enumerate(poi_list, 1):
                                corrected = poi.get("corrected") if isinstance(poi, dict) else None
                                original = poi.get("original") if isinstance(poi, dict) else None
                                data = corrected or poi
                                price = data.get("price") or (original or {}).get("price", "unknown")
                                
                                # Corrected dimensions
                                left = data.get("left", 0)
                                top = data.get("top", 0)
                                width = data.get("width", 0)
                                height = data.get("height", 0)
                                
                                # Original dimensions (if available)
                                orig_width = original.get("width", 0) if original else 0
                                orig_height = original.get("height", 0) if original else 0
                                
                                img_w = image_width or 4440
                                img_h = image_height or 2651
                                
                                past_lessons_text += f"  POI {j} (price {price}): left={left:.0f}, top={top:.0f}\n"
                                past_lessons_text += f"    → Size: {width:.0f}px wide × {height:.0f}px tall ({width / img_w * 100:.1f}% × {height / img_h * 100:.1f}% of chart)\n"
                                
                                if original and orig_width > 0 and orig_height > 0:
                                    width_diff = width - orig_width
                                    height_diff = height - orig_height
                                    width_change_pct = (width_diff / orig_width * 100) if orig_width > 0 else 0
                                    height_change_pct = (height_diff / orig_height * 100) if orig_height > 0 else 0
                                    
                                    if abs(width_change_pct) > 10 or abs(height_change_pct) > 10:  # Show if significant change
                                        changes = []
                                        if abs(width_change_pct) > 10:
                                            changes.append(f"{'widened' if width_diff > 0 else 'narrowed'} by {abs(width_diff):.0f}px ({abs(width_change_pct):.1f}%)")
                                        if abs(height_change_pct) > 10:
                                            changes.append(f"{'heightened' if height_diff > 0 else 'shortened'} by {abs(height_diff):.0f}px ({abs(height_change_pct):.1f}%)")
                                        past_lessons_text += f"    → I {' and '.join(changes)} - this shows the POI zone should cover {'more' if width_diff > 0 or height_diff > 0 else 'less'} area\n"
                        if lesson.corrected_annotations.get("circles"):
                            circles_list = lesson.corrected_annotations["circles"]
                            past_lessons_text += f"I corrected your circles ({len(circles_list)} circle(s)):\n"
                            for j, circle in enumerate(circles_list, 1):
                                corrected = circle.get("corrected") if isinstance(circle, dict) else None
                                original = circle.get("original") if isinstance(circle, dict) else None
                                data = corrected or circle
                                
                                # Corrected dimensions
                                x = data.get("x", 0)
                                y = data.get("y", 0)
                                radius = data.get("radius", 0)
                                
                                # Original dimensions (if available)
                                orig_radius = original.get("radius", 0) if original else 0
                                
                                past_lessons_text += f"  Circle {j}: x={x:.0f}, y={y:.0f}, radius={radius:.0f}px\n"
                                
                                if original and orig_radius > 0:
                                    radius_diff = radius - orig_radius
                                    radius_change_pct = (radius_diff / orig_radius * 100) if orig_radius > 0 else 0
                                    if abs(radius_change_pct) > 10:  # Show if significant change
                                        past_lessons_text += f"    → I {'enlarged' if radius_diff > 0 else 'shrunk'} your circle by {abs(radius_diff):.0f}px ({abs(radius_change_pct):.1f}%) - this shows the fractal marker should be {'larger' if radius_diff > 0 else 'smaller'} to emphasize the pattern\n"
                    
                    if lesson.corrected_reasoning:
                        past_lessons_text += f"\nI corrected your reasoning: \"{lesson.corrected_reasoning}\"\n"

                    # Phase 4D.2: Include Q&A from past lessons
                    if lesson.answers and isinstance(lesson.answers, list) and len(lesson.answers) > 0:
                        past_lessons_text += f"\n💬 TEACHING Q&A (I answered your questions to explain my strategy):\n"
                        for qa in lesson.answers:
                            if isinstance(qa, dict) and qa.get('answer'):
                                question = qa.get('question_text', 'Question')
                                answer = qa.get('answer', '')
                                context = qa.get('context', '')
                                past_lessons_text += f"  Q: {question}\n"
                                past_lessons_text += f"  A: {answer}\n"
                                if context:
                                    past_lessons_text += f"     (Context: {context})\n"
                                past_lessons_text += "\n"
                        past_lessons_text += "  → Use my answers above to understand WHY I placed annotations where I did\n"
                        past_lessons_text += "  → My reasoning and strategy are explained in these answers\n"

                    # Show deleted and added annotations
                    deleted_count = 0
                    added_count = 0
                    
                    # Count deletions from deleted_annotations field
                    if lesson.deleted_annotations:
                        deleted_count = len(lesson.deleted_annotations)
                    
                    # Count additions (annotations with no original, marked as added)
                    if lesson.corrected_annotations:
                        for ann_type in ['bos', 'poi', 'circles']:
                            ann_list = lesson.corrected_annotations.get(ann_type, [])
                            for ann in ann_list:
                                if isinstance(ann, dict):
                                    is_added = ann.get('added', False)
                                    has_original = ann.get('original') is not None
                                    if is_added and not has_original:
                                        added_count += 1
                    
                    if deleted_count > 0:
                        past_lessons_text += f"\n🗑️ DELETIONS: I deleted {deleted_count} annotation(s) you created that SHOULD NOT EXIST:\n"
                        past_lessons_text += "  → These annotations were hallucinations or incorrect identifications\n"
                        past_lessons_text += "  → DO NOT create similar annotations - they don't represent valid patterns\n"
                        
                    if added_count > 0:
                        past_lessons_text += f"\n➕ ADDITIONS: I added {added_count} annotation(s) that you MISSED:\n"
                        past_lessons_text += "  → These annotations should have been identified but weren't in your initial analysis\n"
                        past_lessons_text += "  → Learn to identify these patterns/structures that you overlooked\n"
                    
                    past_lessons_text += "\n"
                
                past_lessons_text += "🎯 LEARNING FROM CORRECTIONS - FOCUS ON LOGIC, PATTERNS, AND DIMENSIONS:\n"
                past_lessons_text += f"1. The coordinates above show WHERE I placed annotations on this chart (image size: {image_width}x{image_height} pixels)\n"
                past_lessons_text += "2. The DIMENSIONS (length, width, height, radius) show HOW MUCH of the chart each annotation should cover\n"
                past_lessons_text += "3. MORE IMPORTANTLY: Focus on LEARNING THE LOGIC and PATTERNS from my corrections, not just copying exact coordinates\n"
                past_lessons_text += "4. Understand WHY I placed annotations at those positions AND sizes:\n"
                past_lessons_text += "   - What price levels did I mark? (e.g., BOS at 1.169, circles at fractals)\n"
                past_lessons_text += "   - What time periods did I mark? (e.g., BOS spanning from Oct 28 9:20 to retest)\n"
                past_lessons_text += "   - How much area did I mark? (e.g., POI covering 5% of chart width means it spans a specific time range)\n"
                past_lessons_text += "   - What patterns did I identify? (e.g., swing highs, fractals, structure breaks)\n"
                past_lessons_text += "5. If I extended/shortened a BOS line or resized a POI, understand WHY:\n"
                past_lessons_text += "   - Extended BOS = structure break spans a longer time period (from initial break to confirmation)\n"
                past_lessons_text += "   - Wider POI = zone covers multiple price levels or a longer accumulation period\n"
                past_lessons_text += "   - Larger circle = emphasize a more significant fractal or turning point\n"
                past_lessons_text += "6. Read my reasoning corrections carefully - they explain the LOGIC behind my corrections\n"
                past_lessons_text += "7. Use the corrected coordinates AND dimensions as GUIDANCE to understand the approximate positions and scale\n"
                past_lessons_text += "8. The goal is to learn to identify similar patterns AND their appropriate scale on future charts\n"
                past_lessons_text += "9. Apply the same REASONING I used when making corrections to identify positions AND sizes on this chart\n"
        
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
        
        # Prepare context from similar trades - ENHANCED: Include corrections and reasoning!
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

                    # Phase 4D.3: Include LESSONS (corrections, Q&A, reasoning) from this trade
                    lessons = db.query(AILesson).filter(AILesson.trade_id == trade_id).order_by(AILesson.created_at.desc()).limit(1).all()
                    if lessons and len(lessons) > 0:
                        latest_lesson = lessons[0]
                        context["has_corrections"] = True

                        # Include user's reasoning if available
                        if latest_lesson.corrected_reasoning:
                            context["user_reasoning"] = latest_lesson.corrected_reasoning

                        # Include Q&A answers to capture strategy
                        if latest_lesson.answers and isinstance(latest_lesson.answers, list):
                            qa_summary = []
                            for qa in latest_lesson.answers[:3]:  # Top 3 Q&A
                                if isinstance(qa, dict) and qa.get('answer'):
                                    qa_summary.append(f"Q: {qa.get('question_text')} | A: {qa.get('answer')}")
                            if qa_summary:
                                context["qa_insights"] = qa_summary

                        # Include deletion/addition counts to show patterns
                        deleted_count = len(latest_lesson.deleted_annotations) if latest_lesson.deleted_annotations else 0
                        added_count = 0
                        if latest_lesson.corrected_annotations:
                            for ann_type in ['bos', 'poi', 'circles']:
                                ann_list = latest_lesson.corrected_annotations.get(ann_type, [])
                                for ann in ann_list:
                                    if isinstance(ann, dict) and ann.get('added', False) and not ann.get('original'):
                                        added_count += 1

                        if deleted_count > 0:
                            context["deletions"] = f"User deleted {deleted_count} AI annotation(s) - they were incorrect/hallucinations"
                        if added_count > 0:
                            context["additions"] = f"User added {added_count} annotation(s) AI missed"

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
            examples_text = "\n\n🎓 LEARNING FROM SIMILAR TRADES (RAG - Use these to understand my strategy):\n\n"
            for i, example in enumerate(similar_trades_context[:3], 1):  # Show top 3 examples
                symbol = example.get("symbol", "Unknown")
                direction = example.get("direction", "")
                outcome = example.get("outcome", "")
                examples_text += f"Example {i} - {symbol} {direction} {outcome}:\n"

                # Phase 4D.3: Include corrections and reasoning (NEW - helps AI learn patterns)
                if example.get("has_corrections"):
                    examples_text += "✨ I CORRECTED AI on this trade - learn from my corrections:\n"

                    if example.get("user_reasoning"):
                        examples_text += f"  - My reasoning: \"{example['user_reasoning']}\"\n"

                    if example.get("qa_insights"):
                        examples_text += "  - My Q&A explanations:\n"
                        for qa in example["qa_insights"]:
                            examples_text += f"    • {qa}\n"

                    if example.get("deletions"):
                        examples_text += f"  - ⚠️ {example['deletions']}\n"

                    if example.get("additions"):
                        examples_text += f"  - ✅ {example['additions']}\n"

                # Original annotations
                if example.get("annotations"):
                    ann = example["annotations"]
                    if ann.get("poi_prices"):
                        poi_str = ", ".join([str(p) for p in ann["poi_prices"]])
                        examples_text += f"- POI price levels: {poi_str}\n"
                    if ann.get("bos_prices"):
                        bos_str = ", ".join([str(p) for p in ann["bos_prices"]])
                        examples_text += f"- BOS price levels: {bos_str}\n"
                    if ann.get("notes"):
                        examples_text += f"- My original notes: \"{ann['notes']}\"\n"
                else:
                    examples_text += "- (No annotations for this trade)\n"
                examples_text += "\n"

            examples_text += "🎯 KEY LEARNING: Use the corrections, Q&A, and reasoning above to understand:\n"
            examples_text += "1. What patterns I identify (liquidity sweeps, structure breaks, fractals)\n"
            examples_text += "2. Where I place POI/BOS (not random - specific price levels for specific reasons)\n"
            examples_text += "3. What I delete (avoid hallucinations - don't mark every level)\n"
            examples_text += "4. What I add (patterns I consistently identify that AI misses)\n"
            examples_text += "5. My strategy reasoning (WHY I place annotations, not just WHERE)\n\n"
        
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
            past_lessons_instruction = """🎯 LEARNING OPPORTUNITY - YOU HAVE BEEN CORRECTED ON THIS SAME CHART BEFORE!
The past corrections above show you WHERE and WHY I corrected your annotations. Focus on LEARNING:
- The LOGIC and PATTERNS I identified (price levels, time periods, chart structures)
- The REASONING behind my corrections (read my reasoning corrections carefully!)
- The APPROXIMATE positions I marked (use coordinates as guidance, but identify visually)
- The PATTERNS to look for (swing highs, fractals, structure breaks, etc.)

Your goal is to:
1. Understand WHY I placed annotations at those positions
2. Identify the SAME LOGICAL PATTERNS visually from the chart
3. Apply the SAME REASONING I used when making corrections
4. Learn to recognize similar patterns on future charts

The coordinates are GUIDANCE, but the LOGIC is what matters. Focus on learning the patterns, not memorizing exact pixels!"""
        
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
            import traceback
            error_trace = traceback.format_exc()
            print(f"[AI Routes] ERROR calling GPT-5: {e}")
            print(f"[AI Routes] Full traceback:\n{error_trace}")
            # Fallback: return empty annotations
            annotation_data = {
                "poi": [],
                "bos": [],
                "circles": [],
                "notes": f"Error analyzing chart: {str(e)}",
                "reasoning": None
            }

        # Phase 4D.2: Generate teaching questions based on annotations
        questions = []
        try:
            if annotation_data.get("poi") or annotation_data.get("bos") or annotation_data.get("circles"):
                # Generate contextual questions about the annotations
                question_prompt = f"""Based on the annotations I just created, generate 2-3 conversational questions to help me learn your trading strategy.

Annotations created:
- POI zones: {len(annotation_data.get('poi', []))}
- BOS lines: {len(annotation_data.get('bos', []))}
- Circles/Fractals: {len(annotation_data.get('circles', []))}

Generate questions that are:
1. Conversational and natural (not interrogative)
2. About your reasoning (e.g., "Why did you place POI at this price level?")
3. About patterns you identified (e.g., "What makes this BOS significant?")
4. Optional - you can skip them if you want

Return as JSON array:
[
  {{"id": "q1", "text": "Why did you place POI here instead of at the swing low?", "context": "poi"}},
  {{"id": "q2", "text": "What confirmation did you use for the BOS line?", "context": "bos"}}
]

IMPORTANT: Only return the JSON array, nothing else."""

                question_response = await client.create_response(
                    question=question_prompt,
                    image_base64=None,  # Text-only for question generation
                    model="gpt-5-chat-latest",
                    conversation_history=None
                )

                question_answer = question_response.get("answer", "")
                import re
                question_json_match = re.search(r'\[.*\]', question_answer, re.DOTALL)
                if question_json_match:
                    questions = json.loads(question_json_match.group())
                    print(f"[AI Routes] Generated {len(questions)} teaching questions")
                else:
                    print(f"[AI Routes] No questions generated (AI response: {question_answer[:200]})")
        except Exception as e:
            print(f"[AI Routes] Warning: Failed to generate questions: {e}")
            # Don't fail the request if question generation fails

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
            reasoning=annotation_data.get("reasoning"),
            questions=questions if questions else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[AI Routes] CRITICAL ERROR in analyze_chart: {e}")
        print(f"[AI Routes] Full traceback:\n{error_trace}")
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
        
        # Phase 4D.3: Calculate accuracy score before saving
        accuracy_metrics = calculate_annotation_accuracy(
            ai_annotations=request.ai_annotations,
            corrected_annotations=request.corrected_annotations,
            deleted_annotations=request.deleted_annotations
        )

        accuracy_score = accuracy_metrics.get("overall_accuracy", 0.0)

        print(f"[AI Routes] Calculated accuracy for trade {request.trade_id}:")
        print(f"  Overall: {accuracy_score:.2%}")
        print(f"  POI: {accuracy_metrics.get('poi_accuracy', 0):.2%}")
        print(f"  BOS: {accuracy_metrics.get('bos_accuracy', 0):.2%}")
        print(f"  Circles: {accuracy_metrics.get('circles_accuracy', 0):.2%}")
        print(f"  Detection rate: {accuracy_metrics.get('detection_rate', 0):.2%}")
        print(f"  Precision: {accuracy_metrics.get('precision', 0):.2%}")

        # Create lesson record (Phase 4D.2: Include questions and answers, Phase 4D.3: Include accuracy)
        lesson = AILesson(
            trade_id=request.trade_id,
            ai_annotations=request.ai_annotations,
            corrected_annotations=request.corrected_annotations,
            corrected_reasoning=request.corrected_reasoning,
            deleted_annotations=request.deleted_annotations,
            questions=request.questions,
            answers=request.answers,
            accuracy_score=accuracy_score  # Phase 4D.3
        )

        db.add(lesson)
        db.commit()
        db.refresh(lesson)

        # Phase 4D.3: Update overall AI progress metrics with accuracy calculations
        progress = db.query(AIProgress).first()
        if not progress:
            progress = AIProgress(
                total_lessons=1,
                poi_accuracy=accuracy_metrics.get("poi_accuracy", 0.0),
                bos_accuracy=accuracy_metrics.get("bos_accuracy", 0.0),
                setup_type_accuracy=0.0,  # TODO: Implement setup type accuracy
                overall_accuracy=accuracy_score
            )
            db.add(progress)
        else:
            # Update running averages
            total = (progress.total_lessons or 0) + 1
            progress.total_lessons = total

            # Calculate new running averages
            old_poi = progress.poi_accuracy or 0.0
            old_bos = progress.bos_accuracy or 0.0
            old_overall = progress.overall_accuracy or 0.0

            progress.poi_accuracy = (old_poi * (total - 1) + accuracy_metrics.get("poi_accuracy", 0.0)) / total
            progress.bos_accuracy = (old_bos * (total - 1) + accuracy_metrics.get("bos_accuracy", 0.0)) / total
            progress.overall_accuracy = (old_overall * (total - 1) + accuracy_score) / total

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
    Phase 4D.3: Get AI learning progress metrics with detailed history.

    Returns:
        Dictionary with progress metrics, accuracy trends, and recent performance
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

        # Phase 4D.3: Get recent lessons for accuracy trend
        recent_lessons = db.query(AILesson).order_by(AILesson.created_at.desc()).limit(20).all()

        # Calculate accuracy trend (last 10 vs previous 10)
        last_10_accuracy = 0.0
        prev_10_accuracy = 0.0

        if len(recent_lessons) >= 10:
            last_10 = [l.accuracy_score for l in recent_lessons[:10] if l.accuracy_score is not None]
            last_10_accuracy = sum(last_10) / len(last_10) if last_10 else 0.0

            if len(recent_lessons) >= 20:
                prev_10 = [l.accuracy_score for l in recent_lessons[10:20] if l.accuracy_score is not None]
                prev_10_accuracy = sum(prev_10) / len(prev_10) if prev_10 else 0.0

        improvement_rate = last_10_accuracy - prev_10_accuracy

        # Build accuracy history (for line graph)
        accuracy_history = []
        for i, lesson in enumerate(reversed(recent_lessons)):  # Oldest to newest
            if lesson.accuracy_score is not None:
                accuracy_history.append({
                    "lesson_number": lessons_count - len(recent_lessons) + i + 1,
                    "accuracy": round(lesson.accuracy_score, 4),
                    "trade_id": lesson.trade_id,
                    "date": lesson.created_at.isoformat() if lesson.created_at else None
                })

        # Calculate milestones
        milestones = {
            "foundation": lessons_count >= 20,  # 20-30 trades
            "intermediate": lessons_count >= 50 and progress.overall_accuracy >= 0.80,  # 50+ trades, 80%+ accuracy
            "advanced": lessons_count >= 100 and progress.overall_accuracy >= 0.85,  # 100+ trades, 85%+ accuracy
            "expert": lessons_count >= 200 and progress.overall_accuracy >= 0.90  # 200+ trades, 90%+ accuracy
        }

        # Determine current milestone
        current_milestone = "getting_started"
        if milestones["expert"]:
            current_milestone = "expert"
        elif milestones["advanced"]:
            current_milestone = "advanced"
        elif milestones["intermediate"]:
            current_milestone = "intermediate"
        elif milestones["foundation"]:
            current_milestone = "foundation"

        return {
            "total_lessons": progress.total_lessons,
            "poi_accuracy": round(progress.poi_accuracy or 0.0, 4),
            "bos_accuracy": round(progress.bos_accuracy or 0.0, 4),
            "setup_type_accuracy": round(progress.setup_type_accuracy or 0.0, 4),
            "overall_accuracy": round(progress.overall_accuracy or 0.0, 4),
            "updated_at": progress.updated_at.isoformat() if progress.updated_at else None,

            # Phase 4D.3: New fields
            "last_10_accuracy": round(last_10_accuracy, 4),
            "improvement_rate": round(improvement_rate, 4),
            "accuracy_history": accuracy_history,
            "milestones": milestones,
            "current_milestone": current_milestone
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")
    finally:
        db.close()

