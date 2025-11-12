#!/usr/bin/env python3
"""
Apply migration 010: Add Phase 4E Entry Suggestion & Learning System tables
"""
import sqlite3
import sys
from pathlib import Path

# Get database path
db_path = Path(__file__).parent.parent / "data" / "vtc.db"

if not db_path.exists():
    print(f"Error: Database not found at {db_path}")
    sys.exit(1)

# Read SQL migration
sql_file = Path(__file__).parent / "010_add_phase4e_tables.sql"
with open(sql_file, 'r') as f:
    sql = f.read()

# Apply migration
conn = sqlite3.connect(str(db_path))
try:
    conn.executescript(sql)
    conn.commit()
    print("Migration 010 applied successfully!")
except Exception as e:
    conn.rollback()
    print(f"Error applying migration: {e}")
    sys.exit(1)
finally:
    conn.close()

