-- Phase 4B: Strategy Documentation - Add entry_methods table and trade links
-- Date: 2025-11-05

-- Create entry_methods table
CREATE TABLE IF NOT EXISTS entry_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    setup_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (setup_id) REFERENCES setups(id)
);

-- Add setup_id and entry_method_id columns to trades table
ALTER TABLE trades ADD COLUMN setup_id INTEGER;
ALTER TABLE trades ADD COLUMN entry_method_id INTEGER;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_trades_setup_id ON trades(setup_id);
CREATE INDEX IF NOT EXISTS idx_trades_entry_method_id ON trades(entry_method_id);

