-- Migration 010: Add Phase 4E Entry Suggestion & Learning System tables
-- Date: 2025-01-XX
-- Phase: Phase 4E - Entry Suggestion & Learning System

-- Strategies table: Store user's trading strategy definitions
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    setup_definitions JSON,  -- POI, BOS, fractals definitions
    entry_methods JSON,      -- Entry methods user uses
    stop_loss_rules JSON,    -- Stop loss rules
    good_entry_criteria JSON, -- What makes a good entry
    bad_entry_criteria JSON,  -- What makes a bad entry
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Chat sessions table: Multi-turn chat sessions with state tracking
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    trade_id TEXT,
    state_json JSON,  -- Current setup status, waiting for confluences, progress
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_trade_id ON chat_sessions(trade_id);

-- Entry suggestions table: AI's entry suggestions
CREATE TABLE IF NOT EXISTS entry_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    entry_price REAL,
    stop_loss REAL,
    stop_loss_type TEXT,  -- 'strategy_based' | 'fixed'
    stop_loss_reasoning TEXT,
    reasoning TEXT,  -- Why this entry was suggested
    confluences_met JSON,  -- List of confluences that were met
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_entry_suggestions_session_id ON entry_suggestions(session_id);

-- Entry outcomes table: Track outcomes of entry suggestions
CREATE TABLE IF NOT EXISTS entry_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suggestion_id INTEGER NOT NULL,
    outcome TEXT NOT NULL,  -- 'win' | 'loss' | 'skipped'
    actual_entry_price REAL,
    actual_exit_price REAL,
    r_multiple REAL,
    notes TEXT,
    chart_sequence JSON,  -- All images in the session
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (suggestion_id) REFERENCES entry_suggestions(id)
);

CREATE INDEX IF NOT EXISTS idx_entry_outcomes_suggestion_id ON entry_outcomes(suggestion_id);
CREATE INDEX IF NOT EXISTS idx_entry_outcomes_outcome ON entry_outcomes(outcome);

