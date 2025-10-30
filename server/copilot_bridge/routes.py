from fastapi import APIRouter, Query
from .performance_sync import summarize_performance, list_teaching_examples, get_example_by_id

router = APIRouter(prefix="/copilot", tags=["Copilot Bridge"])

@router.get("/performance")
def get_performance():
    return {"success": True, "data": summarize_performance()}

@router.get("/teach/examples")
def get_examples(limit: int = Query(10, ge=1, le=50)):
    return {"success": True, "examples": list_teaching_examples(limit)}

@router.get("/teach/example/{trade_id}")
def get_example(trade_id: str):
    example = get_example_by_id(trade_id)
    if not example:
        return {"success": False, "message": f"Trade {trade_id} not found"}
    return {"success": True, "example": example}
