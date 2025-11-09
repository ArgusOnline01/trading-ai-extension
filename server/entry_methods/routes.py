"""
Phase 4B: Entry Methods API endpoints
CRUD operations for entry method definitions
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import EntryMethod, Setup


router = APIRouter(prefix="/entry-methods", tags=["entry-methods"])


class EntryMethodCreate(BaseModel):
    name: str
    description: Optional[str] = None
    setup_id: Optional[int] = None


class EntryMethodUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    setup_id: Optional[int] = None


class EntryMethodResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    setup_id: Optional[int]
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=EntryMethodResponse, status_code=201)
def create_entry_method(entry_method: EntryMethodCreate, db: Session = Depends(get_db)):
    """Create a new entry method"""
    # Check if entry method with same name already exists
    existing = db.query(EntryMethod).filter(EntryMethod.name == entry_method.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Entry method with name '{entry_method.name}' already exists")
    
    # Verify setup exists if provided
    if entry_method.setup_id:
        setup = db.query(Setup).filter(Setup.id == entry_method.setup_id).first()
        if not setup:
            raise HTTPException(status_code=404, detail=f"Setup {entry_method.setup_id} not found")
    
    new_entry_method = EntryMethod(
        name=entry_method.name,
        description=entry_method.description,
        setup_id=entry_method.setup_id
    )
    db.add(new_entry_method)
    db.commit()
    db.refresh(new_entry_method)
    
    return EntryMethodResponse(
        id=new_entry_method.id,
        name=new_entry_method.name,
        description=new_entry_method.description,
        setup_id=new_entry_method.setup_id,
        created_at=new_entry_method.created_at.isoformat()
    )


@router.get("", response_model=List[EntryMethodResponse])
def list_entry_methods(setup_id: Optional[int] = None, db: Session = Depends(get_db)):
    """List all entry methods, optionally filtered by setup"""
    query = db.query(EntryMethod)
    if setup_id:
        query = query.filter(EntryMethod.setup_id == setup_id)
    
    entry_methods = query.order_by(EntryMethod.created_at.desc()).all()
    return [
        EntryMethodResponse(
            id=em.id,
            name=em.name,
            description=em.description,
            setup_id=em.setup_id,
            created_at=em.created_at.isoformat()
        )
        for em in entry_methods
    ]


@router.get("/{entry_method_id}", response_model=EntryMethodResponse)
def get_entry_method(entry_method_id: int, db: Session = Depends(get_db)):
    """Get a specific entry method"""
    entry_method = db.query(EntryMethod).filter(EntryMethod.id == entry_method_id).first()
    if not entry_method:
        raise HTTPException(status_code=404, detail="Entry method not found")
    
    return EntryMethodResponse(
        id=entry_method.id,
        name=entry_method.name,
        description=entry_method.description,
        setup_id=entry_method.setup_id,
        created_at=entry_method.created_at.isoformat()
    )


@router.put("/{entry_method_id}", response_model=EntryMethodResponse)
def update_entry_method(entry_method_id: int, update: EntryMethodUpdate, db: Session = Depends(get_db)):
    """Update an entry method"""
    entry_method = db.query(EntryMethod).filter(EntryMethod.id == entry_method_id).first()
    if not entry_method:
        raise HTTPException(status_code=404, detail="Entry method not found")
    
    if update.name is not None:
        # Check if new name conflicts with existing entry method
        existing = db.query(EntryMethod).filter(EntryMethod.name == update.name, EntryMethod.id != entry_method_id).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Entry method with name '{update.name}' already exists")
        entry_method.name = update.name
    
    if update.description is not None:
        entry_method.description = update.description
    
    if update.setup_id is not None:
        # Verify setup exists if provided
        if update.setup_id:
            setup = db.query(Setup).filter(Setup.id == update.setup_id).first()
            if not setup:
                raise HTTPException(status_code=404, detail=f"Setup {update.setup_id} not found")
        entry_method.setup_id = update.setup_id
    
    db.commit()
    db.refresh(entry_method)
    
    return EntryMethodResponse(
        id=entry_method.id,
        name=entry_method.name,
        description=entry_method.description,
        setup_id=entry_method.setup_id,
        created_at=entry_method.created_at.isoformat()
    )


@router.delete("/{entry_method_id}")
def delete_entry_method(entry_method_id: int, db: Session = Depends(get_db)):
    """Delete an entry method"""
    entry_method = db.query(EntryMethod).filter(EntryMethod.id == entry_method_id).first()
    if not entry_method:
        raise HTTPException(status_code=404, detail="Entry method not found")
    
    # Check if any trades are linked to this entry method
    from db.models import Trade
    linked_trades = db.query(Trade).filter(Trade.entry_method_id == entry_method_id).count()
    if linked_trades > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete entry method: {linked_trades} trade(s) are linked to it. Unlink trades first."
        )
    
    db.delete(entry_method)
    db.commit()
    
    return {"message": "Entry method deleted", "id": entry_method_id}

