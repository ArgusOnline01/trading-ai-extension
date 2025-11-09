"""
Phase 4B: Annotations API endpoints
CRUD operations for chart annotations (POI/BOS marking)
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Annotation, Trade


router = APIRouter(prefix="/annotations", tags=["annotations"])


class AnnotationCreate(BaseModel):
    trade_id: str
    chart_id: Optional[int] = None
    poi_locations: Optional[List[dict]] = None  # [{x, y, price, timestamp}]
    bos_locations: Optional[List[dict]] = None  # [{x, y, price, timestamp}]
    notes: Optional[str] = None
    ai_detected: bool = False
    user_corrected: bool = False


class AnnotationUpdate(BaseModel):
    poi_locations: Optional[List[dict]] = None
    bos_locations: Optional[List[dict]] = None
    notes: Optional[str] = None
    user_corrected: Optional[bool] = None


class AnnotationResponse(BaseModel):
    id: int
    trade_id: str
    chart_id: Optional[int]
    poi_locations: Optional[List[dict]]
    bos_locations: Optional[List[dict]]
    notes: Optional[str]
    ai_detected: bool
    user_corrected: bool
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=AnnotationResponse, status_code=201)
def create_annotation(annotation: AnnotationCreate, db: Session = Depends(get_db)):
    """Create a new annotation for a trade"""
    # Verify trade exists
    trade = db.query(Trade).filter(Trade.trade_id == annotation.trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {annotation.trade_id} not found")
    
    new_annotation = Annotation(
        trade_id=annotation.trade_id,
        chart_id=annotation.chart_id,
        poi_locations=annotation.poi_locations,
        bos_locations=annotation.bos_locations,
        notes=annotation.notes,
        ai_detected=annotation.ai_detected,
        user_corrected=annotation.user_corrected
    )
    db.add(new_annotation)
    db.commit()
    db.refresh(new_annotation)
    
    return AnnotationResponse(
        id=new_annotation.id,
        trade_id=new_annotation.trade_id,
        chart_id=new_annotation.chart_id,
        poi_locations=new_annotation.poi_locations,
        bos_locations=new_annotation.bos_locations,
        notes=new_annotation.notes,
        ai_detected=new_annotation.ai_detected,
        user_corrected=new_annotation.user_corrected,
        created_at=new_annotation.created_at.isoformat()
    )


@router.get("/trade/{trade_id}", response_model=List[AnnotationResponse])
def get_annotations_by_trade(trade_id: str, db: Session = Depends(get_db)):
    """Get all annotations for a specific trade"""
    # Verify trade exists
    trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} not found")
    
    annotations = db.query(Annotation).filter(Annotation.trade_id == trade_id).order_by(Annotation.created_at.desc()).all()
    
    return [
        AnnotationResponse(
            id=a.id,
            trade_id=a.trade_id,
            chart_id=a.chart_id,
            poi_locations=a.poi_locations,
            bos_locations=a.bos_locations,
            notes=a.notes,
            ai_detected=a.ai_detected,
            user_corrected=a.user_corrected,
            created_at=a.created_at.isoformat()
        )
        for a in annotations
    ]


@router.get("/{annotation_id}", response_model=AnnotationResponse)
def get_annotation(annotation_id: int, db: Session = Depends(get_db)):
    """Get a specific annotation"""
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    return AnnotationResponse(
        id=annotation.id,
        trade_id=annotation.trade_id,
        chart_id=annotation.chart_id,
        poi_locations=annotation.poi_locations,
        bos_locations=annotation.bos_locations,
        notes=annotation.notes,
        ai_detected=annotation.ai_detected,
        user_corrected=annotation.user_corrected,
        created_at=annotation.created_at.isoformat()
    )


@router.put("/{annotation_id}", response_model=AnnotationResponse)
def update_annotation(annotation_id: int, update: AnnotationUpdate, db: Session = Depends(get_db)):
    """Update an annotation"""
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    if update.poi_locations is not None:
        annotation.poi_locations = update.poi_locations
    if update.bos_locations is not None:
        annotation.bos_locations = update.bos_locations
    if update.notes is not None:
        annotation.notes = update.notes
    if update.user_corrected is not None:
        annotation.user_corrected = update.user_corrected
    
    db.commit()
    db.refresh(annotation)
    
    return AnnotationResponse(
        id=annotation.id,
        trade_id=annotation.trade_id,
        chart_id=annotation.chart_id,
        poi_locations=annotation.poi_locations,
        bos_locations=annotation.bos_locations,
        notes=annotation.notes,
        ai_detected=annotation.ai_detected,
        user_corrected=annotation.user_corrected,
        created_at=annotation.created_at.isoformat()
    )


@router.delete("/{annotation_id}")
def delete_annotation(annotation_id: int, db: Session = Depends(get_db)):
    """Delete an annotation"""
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")
    
    db.delete(annotation)
    db.commit()
    
    return {"message": "Annotation deleted", "id": annotation_id}

