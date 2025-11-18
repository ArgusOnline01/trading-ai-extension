from fastapi import APIRouter, UploadFile, File, HTTPException
from tempfile import NamedTemporaryFile
from pathlib import Path
import shutil

from analytics.advisor import evaluate_setup
from vision.extract import extract_prices, extract_trade_row
from vision.micro_classifier import classify_micro

router = APIRouter(prefix="/vision", tags=["vision"])


@router.post("/extract")
async def vision_extract(
    image: UploadFile = File(...),
):
    """
    Extract POI/IFVG/BOS + micro_shift from an uploaded chart image.
    Does NOT call the advisor. Requires OpenAI Vision access.
    """
    try:
        with NamedTemporaryFile(delete=False, suffix=Path(image.filename).suffix or ".png") as tmp:
            shutil.copyfileobj(image.file, tmp)
            tmp_path = Path(tmp.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    try:
        details = extract_prices(tmp_path, use_vision=True)
        # Build a minimal row from details to avoid double vision calls
        poi_span = next((p for p in details.get("poi_spans", []) if p and all(v is not None for v in p)), (None, None))
        ifvg_span = next((p for p in details.get("ifvg_spans", []) if p and all(v is not None for v in p)), (None, None))
        bos_level = next((b for b in details.get("bos_levels", []) if b is not None), None)
        fractal_target = details.get("fractal_target")

        extracted = {
            "poi_low": poi_span[0],
            "poi_high": poi_span[1],
            "ifvg_low": ifvg_span[0],
            "ifvg_high": ifvg_span[1],
            "bos_level": bos_level,
            "fractal_target": fractal_target,
            "fractal_candidates": details.get("fractal_candidates"),
            "symbol": details.get("symbol"),
            "timeframe": details.get("timeframe"),
            "session": details.get("session"),
            "raw_ocr_text": details.get("raw_ocr_text"),
            "raw_shapes_text": details.get("raw_shapes_text"),
            "pixel_map": details.get("pixel_map"),
            "raw_detections": details.get("raw"),
        }
        micro_flag = classify_micro(tmp_path)
        return {
            "extracted": extracted,
            "micro_shift": micro_flag,
            "debug": {
                "raw_ocr_text": extracted.get("raw_ocr_text"),
                "raw_shapes_text": extracted.get("raw_shapes_text"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision extract failed: {e}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


@router.post("/advisor")
async def vision_advisor(
    image: UploadFile = File(...),
    symbol: str = "",
    direction: str = "long",
    entry_method: str = "poi50",
    require_grade: str = "A+",
    risk_cap_pct: float = 0.10,
    session: str = "London",
):
    """
    Vision-driven advisor: upload an image (5m chart), auto-extract POI/BOS/IFVG + micro, call advisor, and return both.
    Requires OpenAI Vision access (OPENAI_API_KEY in env).
    """
    if not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")

    # Save upload to temp file
    try:
        with NamedTemporaryFile(delete=False, suffix=Path(image.filename).suffix or ".png") as tmp:
            shutil.copyfileobj(image.file, tmp)
            tmp_path = Path(tmp.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    try:
        extracted = extract_trade_row(tmp_path, use_vision=True)
        micro_flag = classify_micro(tmp_path)
        payload = {
            "trade_id": f"vision-{tmp_path.name}",
            "symbol": symbol,
            "direction": direction,
            "entry_method": entry_method,
            "session": session,
            **extracted,
        }
        if micro_flag is not None:
            payload["micro_shift"] = micro_flag

        advisor_res = evaluate_setup(
            payload,
            remaining_drawdown=500.0,
            risk_cap_pct=risk_cap_pct,
            require_grade=require_grade,
            require_micro=False,
        )

        return {
            "extracted": extracted,
            "micro_shift": micro_flag,
            "payload": payload,
            "advisor": advisor_res,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision advisor failed: {e}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
