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
from sqlalchemy.sql import func


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
    setup_id = Column(Integer, ForeignKey("setups.id"), index=True, nullable=True)  # Phase 4B: link to setup
    entry_method_id = Column(Integer, ForeignKey("entry_methods.id"), index=True, nullable=True)  # Phase 4B: link to entry method
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    charts = relationship("Chart", back_populates="trade", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="trade", cascade="all, delete-orphan")
    setup = relationship("Setup")
    entry_method = relationship("EntryMethod")


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
    poi_locations = Column(JSON, nullable=True)  # [{left, top, width, height, price, color, timestamp}]
    bos_locations = Column(JSON, nullable=True)  # [{x1, y1, x2, y2, price, color, timestamp}]
    circle_locations = Column(JSON, nullable=True)  # [{x, y, radius, color, timestamp}]
    notes = Column(String, nullable=True)
    ai_detected = Column(Boolean, default=False, nullable=False)
    user_corrected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    trade = relationship("Trade", back_populates="annotations")
    chart = relationship("Chart")


class EntryMethod(Base):
    __tablename__ = "entry_methods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    setup_id = Column(Integer, ForeignKey("setups.id"), nullable=True)  # Optional link to setup
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    setup = relationship("Setup")


class TeachingSession(Base):
    __tablename__ = "teaching_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String, nullable=False)
    trades_reviewed = Column(Integer, default=0, nullable=False)
    ai_accuracy = Column(Float, default=0.0, nullable=False)
    status = Column(String, default="in_progress", nullable=False)  # 'in_progress' | 'completed'
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# Phase 4D: AI Learning System Tables

class AILesson(Base):
    __tablename__ = "ai_lessons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String, ForeignKey("trades.trade_id"), index=True, nullable=True)
    ai_annotations = Column(JSON, nullable=True)  # AI's original annotations
    corrected_annotations = Column(JSON, nullable=True)  # User's corrections
    corrected_reasoning = Column(String, nullable=True)  # User's correction to AI's reasoning
    questions = Column(JSON, nullable=True)  # AI's questions
    answers = Column(JSON, nullable=True)  # User's answers
    accuracy_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    trade = relationship("Trade")


class AIProgress(Base):
    __tablename__ = "ai_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    total_lessons = Column(Integer, default=0, nullable=False)
    poi_accuracy = Column(Float, default=0.0, nullable=False)
    bos_accuracy = Column(Float, default=0.0, nullable=False)
    setup_type_accuracy = Column(Float, default=0.0, nullable=False)
    overall_accuracy = Column(Float, default=0.0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AIVerificationTest(Base):
    __tablename__ = "ai_verification_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_chart_url = Column(String, nullable=True)
    ai_annotations = Column(JSON, nullable=True)  # AI's annotations
    ground_truth = Column(JSON, nullable=True)  # User's annotations (ground truth)
    accuracy_score = Column(Float, nullable=True)
    test_date = Column(DateTime, default=datetime.utcnow, nullable=False)
