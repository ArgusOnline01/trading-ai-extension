"""
Phase 4E: Strategy Documentation API endpoints
CRUD operations for trading strategy definitions
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Strategy

router = APIRouter(prefix="/strategy", tags=["strategy"])


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    setup_definitions: Optional[dict] = None  # POI, BOS, fractals definitions
    entry_methods: Optional[dict] = None  # Entry methods user uses
    stop_loss_rules: Optional[dict] = None  # Stop loss rules
    good_entry_criteria: Optional[dict] = None  # What makes a good entry
    bad_entry_criteria: Optional[dict] = None  # What makes a bad entry


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    setup_definitions: Optional[dict] = None
    entry_methods: Optional[dict] = None
    stop_loss_rules: Optional[dict] = None
    good_entry_criteria: Optional[dict] = None
    bad_entry_criteria: Optional[dict] = None


class StrategyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    setup_definitions: Optional[dict]
    entry_methods: Optional[dict]
    stop_loss_rules: Optional[dict]
    good_entry_criteria: Optional[dict]
    bad_entry_criteria: Optional[dict]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=StrategyResponse, status_code=201)
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db)):
    """Create a new strategy definition"""
    new_strategy = Strategy(
        name=strategy.name,
        description=strategy.description,
        setup_definitions=strategy.setup_definitions,
        entry_methods=strategy.entry_methods,
        stop_loss_rules=strategy.stop_loss_rules,
        good_entry_criteria=strategy.good_entry_criteria,
        bad_entry_criteria=strategy.bad_entry_criteria
    )
    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)
    
    return StrategyResponse(
        id=new_strategy.id,
        name=new_strategy.name,
        description=new_strategy.description,
        setup_definitions=new_strategy.setup_definitions,
        entry_methods=new_strategy.entry_methods,
        stop_loss_rules=new_strategy.stop_loss_rules,
        good_entry_criteria=new_strategy.good_entry_criteria,
        bad_entry_criteria=new_strategy.bad_entry_criteria,
        created_at=new_strategy.created_at.isoformat(),
        updated_at=new_strategy.updated_at.isoformat()
    )


@router.get("", response_model=List[StrategyResponse])
def get_strategies(db: Session = Depends(get_db)):
    """Get all strategy definitions"""
    strategies = db.query(Strategy).order_by(Strategy.created_at.desc()).all()
    return [
        StrategyResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            setup_definitions=s.setup_definitions,
            entry_methods=s.entry_methods,
            stop_loss_rules=s.stop_loss_rules,
            good_entry_criteria=s.good_entry_criteria,
            bad_entry_criteria=s.bad_entry_criteria,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        )
        for s in strategies
    ]


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Get a specific strategy by ID"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    
    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        setup_definitions=strategy.setup_definitions,
        entry_methods=strategy.entry_methods,
        stop_loss_rules=strategy.stop_loss_rules,
        good_entry_criteria=strategy.good_entry_criteria,
        bad_entry_criteria=strategy.bad_entry_criteria,
        created_at=strategy.created_at.isoformat(),
        updated_at=strategy.updated_at.isoformat()
    )


@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(strategy_id: int, strategy_update: StrategyUpdate, db: Session = Depends(get_db)):
    """Update a strategy definition"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    
    if strategy_update.name is not None:
        strategy.name = strategy_update.name
    if strategy_update.description is not None:
        strategy.description = strategy_update.description
    if strategy_update.setup_definitions is not None:
        strategy.setup_definitions = strategy_update.setup_definitions
    if strategy_update.entry_methods is not None:
        strategy.entry_methods = strategy_update.entry_methods
    if strategy_update.stop_loss_rules is not None:
        strategy.stop_loss_rules = strategy_update.stop_loss_rules
    if strategy_update.good_entry_criteria is not None:
        strategy.good_entry_criteria = strategy_update.good_entry_criteria
    if strategy_update.bad_entry_criteria is not None:
        strategy.bad_entry_criteria = strategy_update.bad_entry_criteria
    
    db.commit()
    db.refresh(strategy)
    
    return StrategyResponse(
        id=strategy.id,
        name=strategy.name,
        description=strategy.description,
        setup_definitions=strategy.setup_definitions,
        entry_methods=strategy.entry_methods,
        stop_loss_rules=strategy.stop_loss_rules,
        good_entry_criteria=strategy.good_entry_criteria,
        bad_entry_criteria=strategy.bad_entry_criteria,
        created_at=strategy.created_at.isoformat(),
        updated_at=strategy.updated_at.isoformat()
    )


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """Delete a strategy definition"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")
    
    db.delete(strategy)
    db.commit()
    
    return {"message": f"Strategy {strategy_id} deleted successfully"}

