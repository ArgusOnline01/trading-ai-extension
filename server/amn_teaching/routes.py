from fastapi import APIRouter
from .teach_utils import update_teaching_example
from pathlib import Path
import json

router = APIRouter(prefix="/amn/teach", tags=["AMN Teaching"])
DATA_DIR = Path(__file__).parent.parent / "data" / "amn_training_examples"

@router.get("/list")
def list_examples():
    return [json.loads(f.read_text()) for f in DATA_DIR.glob("*.json")]

@router.post("/update")
def update_example(payload: dict):
    return update_teaching_example(payload)
