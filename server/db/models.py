from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String, unique=True, index=True, nullable=False)
    symbol = Column(String, index=True, nullable=True)
    entry_time = Column(DateTime, nullable=True)
    exit_time = Column(DateTime, nullable=True)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    direction = Column(String, nullable=True)  # 'long' | 'short'
    outcome = Column(String, index=True, nullable=True)  # 'win' | 'loss' | 'breakeven'
    pnl = Column(Float, nullable=True)
    r_multiple = Column(Float, nullable=True)
    chart_url = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    charts = relationship("Chart", back_populates="trade", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="trade", cascade="all, delete-orphan")


class Chart(Base):
    __tablename__ = "charts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String, ForeignKey("trades.trade_id"), index=True, nullable=True)
    chart_url = Column(String, nullable=True)
    chart_path = Column(String, nullable=True)
    chart_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    trade = relationship("Trade", back_populates="charts")


class Setup(Base):
    __tablename__ = "setups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    setup_type = Column(String, nullable=True)  # 'bullish' | 'bearish'
    definition = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String, ForeignKey("trades.trade_id"), index=True, nullable=True)
    chart_id = Column(Integer, ForeignKey("charts.id"), nullable=True)
    poi_locations = Column(JSON, nullable=True)  # [{x, y, price, timestamp}]
    bos_locations = Column(JSON, nullable=True)  # [{x, y, price, timestamp}]
    notes = Column(String, nullable=True)
    ai_detected = Column(Boolean, default=False, nullable=False)
    user_corrected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    trade = relationship("Trade", back_populates="annotations")
    chart = relationship("Chart")


class TeachingSession(Base):
    __tablename__ = "teaching_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String, nullable=False)
    trades_reviewed = Column(Integer, default=0, nullable=False)
    ai_accuracy = Column(Float, default=0.0, nullable=False)
    status = Column(String, default="in_progress", nullable=False)  # 'in_progress' | 'completed'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


