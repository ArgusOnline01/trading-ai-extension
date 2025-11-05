"""
Phase 5B: Conversational Teaching Engine Router
Handles lesson recording, BOS/POI extraction, and teaching session management
"""

from fastapi import APIRouter, HTTPException, Form, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import uuid
import os
import json

from utils.file_ops import load_json, save_json, append_json
from utils.gpt_client import extract_bos_poi
from utils.teach_parser import update_partial_lesson, build_clarifying_question, get_missing_fields
from utils.overlay_drawer import draw_overlay_from_labels

router = APIRouter(prefix="/teach", tags=["Teach Copilot"])

# Unified data directory path
DATA_DIR = Path(__file__).parent.parent / "data"
EXAMPLES_DIR = DATA_DIR / "amn_training_examples"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)


class LessonRecord(BaseModel):
    """Model for recording a lesson"""
    trade_id: int
    lesson_text: str


@router.post("/start")
def start_teaching():
    """
    Start a teaching session.
    Activates teaching mode and resets trade index.
    """
    ctx_path = DATA_DIR / "session_contexts.json"
    ctx = load_json(str(ctx_path))
    
    if not isinstance(ctx, dict):
        ctx = {}
    
    ctx["teaching_active"] = True
    ctx["current_trade_index"] = 0
    ctx["session_start"] = datetime.utcnow().isoformat()
    
    save_json(str(ctx_path), ctx)
    
    return {
        "status": "started",
        "message": "Teaching session activated.",
        "trade_index": 0
    }


@router.post("/next")
def next_trade():
    """
    Move to next trade in teaching session.
    Increments the current trade index.
    """
    ctx_path = DATA_DIR / "session_contexts.json"
    ctx = load_json(str(ctx_path))
    
    if not isinstance(ctx, dict):
        ctx = {"current_trade_index": 0}
    
    current_idx = ctx.get("current_trade_index", 0)
    ctx["current_trade_index"] = current_idx + 1
    
    save_json(str(ctx_path), ctx)
    
    return {
        "status": "ready",
        "trade_index": ctx["current_trade_index"]
    }


@router.post("/record")
def record_lesson(trade_id: int = Form(...), lesson_text: str = Form(...)):
    """
    Record a lesson for a specific trade.
    
    Parses lesson text → extracts BOS/POI → stores in teaching examples folder.
    Updates teaching progress in user profile.
    
    Args:
        trade_id: ID of the trade being taught
        lesson_text: User's explanation of the trade setup
    
    Returns:
        Status with example_id and confidence score
    """
    if not lesson_text or not lesson_text.strip():
        raise HTTPException(400, "Lesson text cannot be empty")
    
    # Load performance logs to find trade
    # DB is source of truth now; load from performance.utils (DB-backed)
    from performance.utils import read_logs
    perf = read_logs()
    
    if not isinstance(perf, list):
        perf = []
    
    trade = next((t for t in perf if t.get("id") == trade_id or t.get("trade_id") == trade_id), None)
    
    if not trade:
        raise HTTPException(404, f"Trade {trade_id} not found in performance logs")
    
    # Check if trade is valid for training
    if trade.get("valid_for_training") is False:
        return {
            "status": "skipped",
            "message": f"Trade {trade_id} excluded from training: {trade.get('invalid_reason', 'manually flagged')}",
            "trade_id": trade_id
        }
    
    # Extract BOS/POI using GPT
    parsed = extract_bos_poi(lesson_text)
    
    # Generate unique example ID
    example_id = str(uuid.uuid4())[:8]
    
    # Create teaching example
    example = {
        "id": example_id,
        "trade_id": trade_id,
        "timestamp": datetime.utcnow().isoformat(),
        "source_trade": trade_id,
        "symbol": trade.get("symbol", "Unknown"),
        "direction": trade.get("direction", "unknown"),
        "outcome": trade.get("outcome") or trade.get("label", "unknown"),
        "pnl": trade.get("pnl", 0),
        "lesson_text": lesson_text,
        "bos": parsed.get("bos"),
        "poi": parsed.get("poi", []),
        "feedback_confidence": parsed.get("confidence"),
        "self_recall_score": None,
        "understood": False,
        "chart_path": trade.get("chart_path")
    }
    
    # Save example to amn_training_examples folder
    example_path = EXAMPLES_DIR / f"{example_id}.json"
    save_json(str(example_path), example)
    
    # Update teaching progress in user profile
    profile_path = DATA_DIR / "user_profile.json"
    profile = load_json(str(profile_path))
    
    if not isinstance(profile, dict):
        profile = {}
    
    tp = profile.setdefault("teaching_progress", {
        "examples_total": 0,
        "understood": 0,
        "avg_confidence": 0.0
    })
    
    tp["examples_total"] = tp.get("examples_total", 0) + 1
    
    # Update average confidence
    current_avg = tp.get("avg_confidence", 0.0)
    current_count = tp.get("examples_total", 1)
    new_confidence = parsed.get("confidence", 0.5)
    
    # Weighted average: (old_avg * (count-1) + new_value) / count
    tp["avg_confidence"] = round((current_avg * (current_count - 1) + new_confidence) / current_count, 2)
    
    save_json(str(profile_path), profile)
    
    # Recompile master training dataset (Phase 4D.2)
    try:
        from amn_teaching.dataset_compiler import compile_master_dataset
        compile_master_dataset()
    except Exception as e:
        print(f"[TEACH] Warning: Could not recompile dataset: {e}")
    
    return {
        "status": "saved",
        "example_id": example_id,
        "trade_id": trade_id,
        "feedback_confidence": parsed.get("confidence"),
        "bos_extracted": parsed.get("bos") is not None,
        "poi_count": len(parsed.get("poi", []))
    }


@router.post("/flag-invalid")
def flag_invalid(trade_id: int = Form(...), reason: str = Form("undisciplined")):
    """
    Flag a trade as invalid for training.
    
    Marks the trade with valid_for_training=false so it won't be included
    in future teaching sessions.
    
    Args:
        trade_id: ID of trade to flag
        reason: Reason for flagging (default: "undisciplined")
    
    Returns:
        Status confirmation
    """
    from performance.utils import read_logs
    trades = read_logs()
    
    if not isinstance(trades, list):
        trades = []
    
    found = False
    for t in trades:
        if t.get("id") == trade_id or t.get("trade_id") == trade_id:
            t["valid_for_training"] = False
            t["invalid_reason"] = reason
            t["flagged_at"] = datetime.utcnow().isoformat()
            found = True
            break
    
    if not found:
        raise HTTPException(404, f"Trade {trade_id} not found")
    
    save_json(str(perf_path), trades)
    
    return {
        "status": "flagged",
        "trade_id": trade_id,
        "reason": reason,
        "message": f"Trade {trade_id} marked as invalid for training: {reason}"
    }


@router.post("/end")
def end_teaching():
    """
    End the current teaching session.
    Deactivates teaching mode.
    """
    ctx_path = DATA_DIR / "session_contexts.json"
    ctx = load_json(str(ctx_path))
    
    if not isinstance(ctx, dict):
        ctx = {}
    
    ctx["teaching_active"] = False
    ctx["session_end"] = datetime.utcnow().isoformat()
    
    if "session_start" in ctx:
        # Calculate session duration (optional)
        try:
            start = datetime.fromisoformat(ctx["session_start"])
            end = datetime.utcnow()
            duration = (end - start).total_seconds()
            ctx["last_session_duration_seconds"] = int(duration)
        except:
            pass
    
    save_json(str(ctx_path), ctx)
    
    return {
        "status": "ended",
        "message": "Teaching session closed.",
        "session_duration": ctx.get("last_session_duration_seconds")
    }


@router.get("/status")
def get_teaching_status():
    """
    Get current teaching session status.
    Returns active status, current trade index, and progress.
    """
    ctx_path = DATA_DIR / "session_contexts.json"
    ctx = load_json(str(ctx_path))
    
    if not isinstance(ctx, dict):
        ctx = {}
    
    profile_path = DATA_DIR / "user_profile.json"
    profile = load_json(str(profile_path))
    
    teaching_progress = profile.get("teaching_progress", {}) if isinstance(profile, dict) else {}
    
    return {
        "teaching_active": ctx.get("teaching_active", False),
        "current_trade_index": ctx.get("current_trade_index", 0),
        "session_start": ctx.get("session_start"),
        "examples_total": teaching_progress.get("examples_total", 0),
        "examples_understood": teaching_progress.get("understood", 0),
        "avg_confidence": teaching_progress.get("avg_confidence", 0.0),
        "partial_lesson": ctx.get("partial_lesson", {})  # Phase 5C: Include partial lesson
    }


@router.post("/stream")
async def teach_stream(request: Request):
    """
    Phase 5C: Incremental teaching flow.
    
    Receives each chat message while teaching_active=True,
    updates partial_lesson, and returns updated fields + missing info.
    
    Request body:
        {
            "message": "BOS from 1.1450 to 1.1480 bullish POI 1.1440-1.1452"
        }
    
    Returns:
        {
            "status": "updated",
            "partial_lesson": {...},
            "missing_fields": [...],
            "next_question": "..."
        }
    """
    try:
        data = await request.json()
        message = data.get("message", "")
        
        if not message or not message.strip():
            return JSONResponse({
                "status": "idle",
                "message": "Empty message received."
            })
        
        ctx_path = DATA_DIR / "session_contexts.json"
        ctx = load_json(str(ctx_path))
        
        if not isinstance(ctx, dict):
            ctx = {}
        
        if not ctx.get("teaching_active"):
            return JSONResponse({
                "status": "idle",
                "message": "Teaching mode not active. Start a session first."
            })
        
        # Get current trade from index
        trade_index = ctx.get("current_trade_index", 0)
        from performance.utils import read_logs
        perf = load_json(str(perf_path))
        
        if not isinstance(perf, list) or trade_index >= len(perf):
            return JSONResponse({
                "status": "error",
                "message": "No trade available at current index."
            })
        
        trade = perf[trade_index]
        trade_id = trade.get("id") or trade.get("trade_id")
        
        # Get or initialize partial lesson
        partial = ctx.get("partial_lesson", {})
        
        # Update partial lesson with new message
        updated = update_partial_lesson(message, partial)
        
        # Save updated partial lesson
        ctx["partial_lesson"] = updated
        save_json(str(ctx_path), ctx)
        
        # Determine missing fields
        missing = get_missing_fields(updated)
        
        # Build clarifying question
        question = build_clarifying_question(missing)
        
        return JSONResponse({
            "status": "updated",
            "partial_lesson": updated,
            "missing_fields": missing,
            "next_question": question,
            "confidence_hint": updated.get("confidence_hint", 0.5)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Stream processing failed: {str(e)}")


@router.post("/preview")
async def preview_overlay(request: Request):
    """
    Phase 5C: Render temporary overlay for current lesson using mf tool.
    
    Request body:
        {
            "example_like": {
                "trade_id": 42,
                "bos": {"start": 1.1450, "end": 1.1480},
                "poi": [{"low": 1.1440, "high": 1.1452, "reason": "..."}],
                "bias": "bullish"
            }
        }
        OR (if empty) uses current partial_lesson from session
    
    Returns:
        {
            "status": "ok",
            "overlay_path": "...",
            "overlay_url": "/charts/overlays/..."
        }
    """
    try:
        # Try to get data from request
        try:
            data = await request.json()
        except:
            data = {}
        
        example_like = data.get("example_like")
        
        # If no example provided, try to use partial_lesson from session
        if not example_like:
            ctx_path = DATA_DIR / "session_contexts.json"
            ctx = load_json(str(ctx_path))
            
            if not isinstance(ctx, dict):
                return JSONResponse({
                    "status": "error",
                    "message": "No lesson data provided and no active session."
                })
            
            partial = ctx.get("partial_lesson", {})
            trade_index = ctx.get("current_trade_index", 0)
            
            # Get trade info
            perf_path = DATA_DIR / "performance_logs.json"
            perf = load_json(str(perf_path))
            
            if not isinstance(perf, list) or trade_index >= len(perf):
                return JSONResponse({
                    "status": "error",
                    "message": "No trade available at current index."
                })
            
            trade = perf[trade_index]
            trade_id = trade.get("id") or trade.get("trade_id")
            symbol = trade.get("symbol")
            
            example_like = {
                "trade_id": trade_id,
                "bos": partial.get("bos"),
                "poi": partial.get("poi", []),
                "bias": partial.get("bias"),
                "symbol": symbol
            }
        
        trade_id = example_like.get("trade_id")
        bos = example_like.get("bos")
        poi = example_like.get("poi", [])
        bias = example_like.get("bias")
        symbol = example_like.get("symbol")
        
        if not trade_id:
            return JSONResponse({
                "status": "error",
                "message": "trade_id required."
            })
        
        # Draw overlay
        overlay_path = draw_overlay_from_labels(
            trade_id=trade_id,
            bos=bos,
            poi_list=poi,
            bias=bias,
            mode="draft",
            symbol=symbol
        )
        
        if not overlay_path:
            return JSONResponse({
                "status": "error",
                "message": "Failed to generate overlay. Chart image may not exist."
            })
        
        # Convert to URL path
        from utils.overlay_drawer import get_overlay_url
        overlay_url = get_overlay_url(overlay_path)
        
        return JSONResponse({
            "status": "ok",
            "overlay_path": overlay_path,
            "overlay_url": overlay_url
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")


@router.post("/skip")
def skip_trade():
    """
    Phase 5C: Skip current trade and move to next.
    
    Clears partial_lesson and advances trade index.
    
    Returns:
        {
            "status": "skipped",
            "next_trade_index": 1,
            "message": "Trade skipped."
        }
    """
    ctx_path = DATA_DIR / "session_contexts.json"
    ctx = load_json(str(ctx_path))
    
    if not isinstance(ctx, dict):
        ctx = {"current_trade_index": 0, "teaching_active": False}
    
    current_idx = ctx.get("current_trade_index", 0)
    ctx["current_trade_index"] = current_idx + 1
    ctx["partial_lesson"] = {}  # Clear partial lesson
    
    save_json(str(ctx_path), ctx)
    
    return {
        "status": "skipped",
        "next_trade_index": ctx["current_trade_index"],
        "message": "Trade skipped. Moved to next trade."
    }


@router.get("/lessons")
def list_lessons():
    """
    List all saved teaching lessons with summary information.
    
    Returns:
        List of lessons with key fields (id, symbol, confidence, BOS/POI status)
    """
    try:
        lessons = []
        
        # Load all example files
        for example_file in EXAMPLES_DIR.glob("*.json"):
            if example_file.name.startswith("overlays"):
                continue
                
            try:
                example = load_json(str(example_file))
                if not isinstance(example, dict):
                    continue
                
                lessons.append({
                    "example_id": example.get("id") or example_file.stem,
                    "trade_id": example.get("trade_id") or example.get("source_trade"),
                    "symbol": example.get("symbol", "Unknown"),
                    "direction": example.get("direction", "unknown"),
                    "outcome": example.get("outcome", "unknown"),
                    "pnl": example.get("pnl", 0),
                    "timestamp": example.get("timestamp", ""),
                    "bos": example.get("bos"),
                    "poi": example.get("poi", []),
                    "poi_count": len(example.get("poi", [])),
                    "confidence": example.get("feedback_confidence", 0.0),
                    "understood": example.get("understood", False),
                    "lesson_preview": (example.get("lesson_text", "") or "")[:100] + ("..." if len(example.get("lesson_text", "")) > 100 else ""),
                    "chart_path": example.get("chart_path")
                })
            except Exception as e:
                print(f"[TEACH] Error loading {example_file}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        lessons.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return {
            "status": "ok",
            "total": len(lessons),
            "lessons": lessons
        }
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.get("/lessons/{example_id}")
def get_lesson(example_id: str):
    """
    Get detailed information about a specific teaching lesson.
    
    Args:
        example_id: The example ID (UUID or trade_id)
    
    Returns:
        Complete lesson object with all fields
    """
    try:
        # Try direct file match first
        example_path = EXAMPLES_DIR / f"{example_id}.json"
        
        if not example_path.exists():
            # Try to find by trade_id
            for example_file in EXAMPLES_DIR.glob("*.json"):
                try:
                    example = load_json(str(example_file))
                    if str(example.get("trade_id")) == str(example_id) or str(example.get("id")) == str(example_id):
                        example_path = example_file
                        break
                except:
                    continue
        
        if not example_path.exists():
            raise HTTPException(404, f"Lesson {example_id} not found")
        
        lesson = load_json(str(example_path))
        
        if not isinstance(lesson, dict):
            raise HTTPException(500, "Invalid lesson file format")
        
        return {
            "status": "ok",
            "lesson": lesson
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.get("/progress")
def get_teaching_progress():
    """
    Get overall teaching progress statistics.
    
    Returns:
        Teaching progress summary including total examples, confidence, understood count
    """
    try:
        profile_path = DATA_DIR / "user_profile.json"
        profile = load_json(str(profile_path))
        
        if not isinstance(profile, dict):
            profile = {}
        
        tp = profile.get("teaching_progress", {
            "examples_total": 0,
            "understood": 0,
            "avg_confidence": 0.0
        })
        
        # Count lessons with different outcomes
        all_lessons = []
        for example_file in EXAMPLES_DIR.glob("*.json"):
            if example_file.name.startswith("overlays"):
                continue
            try:
                example = load_json(str(example_file))
                if isinstance(example, dict):
                    all_lessons.append(example)
            except:
                continue
        
        # Calculate statistics
        win_count = sum(1 for l in all_lessons if l.get("outcome") in ["win", "W"])
        loss_count = sum(1 for l in all_lessons if l.get("outcome") in ["loss", "L"])
        understood_count = sum(1 for l in all_lessons if l.get("understood", False))
        
        return {
            "status": "ok",
            "progress": {
                "examples_total": tp.get("examples_total", len(all_lessons)),
                "understood": tp.get("understood", understood_count),
                "avg_confidence": tp.get("avg_confidence", 0.0),
                "win_count": win_count,
                "loss_count": loss_count,
                "total_lessons": len(all_lessons)
            }
        }
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.delete("/lessons/{example_id}")
def delete_lesson(example_id: str):
    """
    Delete a teaching lesson.
    
    Args:
        example_id: The example ID (UUID or trade_id)
    
    Returns:
        Confirmation of deletion
    """
    try:
        # Try direct file match first
        example_path = EXAMPLES_DIR / f"{example_id}.json"
        
        if not example_path.exists():
            # Try to find by trade_id
            for example_file in EXAMPLES_DIR.glob("*.json"):
                try:
                    example = load_json(str(example_file))
                    if str(example.get("trade_id")) == str(example_id) or str(example.get("id")) == str(example_id):
                        example_path = example_file
                        break
                except:
                    continue
        
        if not example_path.exists():
            raise HTTPException(404, f"Lesson {example_id} not found")
        
        # Delete the file
        example_path.unlink()
        
        # Recompile master training dataset
        try:
            from amn_teaching.dataset_compiler import compile_master_dataset
            compile_master_dataset()
        except Exception as e:
            print(f"[TEACH] Warning: Could not recompile dataset: {e}")
        
        return {
            "status": "deleted",
            "example_id": example_id,
            "message": f"Lesson {example_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)


@router.put("/lessons/{example_id}")
async def update_lesson(example_id: str, request: Request = None):
    """
    Update/edit a teaching lesson.
    
    Args:
        example_id: The example ID (UUID or trade_id)
        request: FastAPI Request object with JSON body containing fields to update
    
    Returns:
        Updated lesson object
    """
    try:
        # Try direct file match first
        example_path = EXAMPLES_DIR / f"{example_id}.json"
        
        if not example_path.exists():
            # Try to find by trade_id
            for example_file in EXAMPLES_DIR.glob("*.json"):
                try:
                    example = load_json(str(example_file))
                    if str(example.get("trade_id")) == str(example_id) or str(example.get("id")) == str(example_id):
                        example_path = example_file
                        break
                except:
                    continue
        
        if not example_path.exists():
            raise HTTPException(404, f"Lesson {example_id} not found")
        
        # Load existing lesson
        lesson = load_json(str(example_path))
        
        if not isinstance(lesson, dict):
            raise HTTPException(500, "Invalid lesson file format")
        
        # Get update data from request body
        lesson_update = {}
        if request:
            try:
                lesson_update = await request.json()
            except:
                pass
        
        # Update fields if provided
        if lesson_update:
            # Update lesson_text
            if "lesson_text" in lesson_update:
                lesson["lesson_text"] = lesson_update["lesson_text"]
            
            # Update BOS
            if "bos" in lesson_update:
                lesson["bos"] = lesson_update["bos"]
            
            # Update POI
            if "poi" in lesson_update:
                lesson["poi"] = lesson_update["poi"]
            
            # Update understood flag
            if "understood" in lesson_update:
                lesson["understood"] = lesson_update["understood"]
            
            # Update confidence if lesson_text changed (re-extract)
            if "lesson_text" in lesson_update:
                try:
                    parsed = extract_bos_poi(lesson_update["lesson_text"])
                    lesson["bos"] = parsed.get("bos") or lesson.get("bos")
                    lesson["poi"] = parsed.get("poi", []) or lesson.get("poi", [])
                    lesson["feedback_confidence"] = parsed.get("confidence") or lesson.get("feedback_confidence", 0.0)
                except Exception as e:
                    print(f"[TEACH] Could not re-extract BOS/POI: {e}")
            
            # Update timestamp
            lesson["updated_at"] = datetime.utcnow().isoformat()
            
            # Save updated lesson
            save_json(str(example_path), lesson)
            
            # Recompile master training dataset
            try:
                from amn_teaching.dataset_compiler import compile_master_dataset
                compile_master_dataset()
            except Exception as e:
                print(f"[TEACH] Warning: Could not recompile dataset: {e}")
        
        return {
            "status": "updated",
            "lesson": lesson
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": str(e)
        }, status_code=500)

