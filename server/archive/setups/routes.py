"""
Phase 4B: Setups API endpoints
CRUD operations for setup definitions
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Setup


router = APIRouter(prefix="/setups", tags=["setups"])


class SetupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    setup_type: Optional[str] = None  # 'bullish' | 'bearish'
    definition: Optional[dict] = None


class SetupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    setup_type: Optional[str] = None
    definition: Optional[dict] = None


class SetupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    setup_type: Optional[str]
    definition: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=SetupResponse, status_code=201)
def create_setup(setup: SetupCreate, db: Session = Depends(get_db)):
    """Create a new setup definition"""
    # Check if setup with same name already exists
    existing = db.query(Setup).filter(Setup.name == setup.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Setup with name '{setup.name}' already exists")
    
    new_setup = Setup(
        name=setup.name,
        description=setup.description,
        setup_type=setup.setup_type,
        definition=setup.definition
    )
    db.add(new_setup)
    db.commit()
    db.refresh(new_setup)
    
    return SetupResponse(
        id=new_setup.id,
        name=new_setup.name,
        description=new_setup.description,
        setup_type=new_setup.setup_type,
        definition=new_setup.definition,
        created_at=new_setup.created_at.isoformat()
    )


@router.get("", response_model=List[SetupResponse])
def list_setups(db: Session = Depends(get_db)):
    """List all setup definitions"""
    setups = db.query(Setup).order_by(Setup.created_at.desc()).all()
    return [
        SetupResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            setup_type=s.setup_type,
            definition=s.definition,
            created_at=s.created_at.isoformat()
        )
        for s in setups
    ]


@router.get("/{setup_id}", response_model=SetupResponse)
def get_setup(setup_id: int, db: Session = Depends(get_db)):
    """Get a specific setup definition"""
    setup = db.query(Setup).filter(Setup.id == setup_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")
    
    return SetupResponse(
        id=setup.id,
        name=setup.name,
        description=setup.description,
        setup_type=setup.setup_type,
        definition=setup.definition,
        created_at=setup.created_at.isoformat()
    )


@router.put("/{setup_id}", response_model=SetupResponse)
def update_setup(setup_id: int, update: SetupUpdate, db: Session = Depends(get_db)):
    """Update a setup definition"""
    setup = db.query(Setup).filter(Setup.id == setup_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")
    
    if update.name is not None:
        # Check if new name conflicts with existing setup
        existing = db.query(Setup).filter(Setup.name == update.name, Setup.id != setup_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Setup with name '{update.name}' already exists")
        setup.name = update.name
    
    if update.description is not None:
        setup.description = update.description
    if update.setup_type is not None:
        setup.setup_type = update.setup_type
    if update.definition is not None:
        setup.definition = update.definition
    
    db.commit()
    db.refresh(setup)
    
    return SetupResponse(
        id=setup.id,
        name=setup.name,
        description=setup.description,
        setup_type=setup.setup_type,
        definition=setup.definition,
        created_at=setup.created_at.isoformat()
    )


@router.delete("/{setup_id}")
def delete_setup(setup_id: int, db: Session = Depends(get_db)):
    """Delete a setup definition"""
    setup = db.query(Setup).filter(Setup.id == setup_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")
    
    # Check if any trades are linked to this setup
    from db.models import Trade
    linked_trades = db.query(Trade).filter(Trade.setup_id == setup_id).count()
    if linked_trades > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete setup: {linked_trades} trade(s) are linked to it. Unlink trades first."
        )
    
    db.delete(setup)
    db.commit()
    
    return {"message": "Setup deleted", "id": setup_id}

