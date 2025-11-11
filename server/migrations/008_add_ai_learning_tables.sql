-- Phase 4D: AI Learning System Tables
-- Migration: 008_add_ai_learning_tables.sql

-- Table: ai_lessons
-- Stores AI lessons from annotated trades
CREATE TABLE IF NOT EXISTS ai_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT,
    ai_annotations TEXT,  -- JSON: AI's original annotations
    corrected_annotations TEXT,  -- JSON: User's corrections
    questions TEXT,  -- JSON: AI's questions
    answers TEXT,  -- JSON: User's answers
    accuracy_score REAL,  -- Accuracy for this lesson
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_lessons_trade_id ON ai_lessons(trade_id);
CREATE INDEX IF NOT EXISTS idx_ai_lessons_created_at ON ai_lessons(created_at);

-- Table: ai_progress
-- Tracks overall AI learning progress
CREATE TABLE IF NOT EXISTS ai_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_lessons INTEGER DEFAULT 0 NOT NULL,
    poi_accuracy REAL DEFAULT 0.0 NOT NULL,
    bos_accuracy REAL DEFAULT 0.0 NOT NULL,
    setup_type_accuracy REAL DEFAULT 0.0 NOT NULL,
    overall_accuracy REAL DEFAULT 0.0 NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial progress record
INSERT OR IGNORE INTO ai_progress (id, total_lessons, poi_accuracy, bos_accuracy, setup_type_accuracy, overall_accuracy)
VALUES (1, 0, 0.0, 0.0, 0.0, 0.0);

-- Table: ai_verification_tests
-- Stores verification tests for AI accuracy
CREATE TABLE IF NOT EXISTS ai_verification_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_chart_url TEXT,
    ai_annotations TEXT,  -- JSON: AI's annotations
    ground_truth TEXT,  -- JSON: User's annotations (ground truth)
    accuracy_score REAL,
    test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_verification_tests_test_date ON ai_verification_tests(test_date);

