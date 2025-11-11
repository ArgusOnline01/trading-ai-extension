#!/usr/bin/env python3
"""Apply migration 008: Add AI learning tables."""

import sqlite3
import sys
from pathlib import Path

# Get database path
db_path = Path(__file__).parent.parent / "data" / "vtc.db"

if not db_path.exists():
    print(f"Error: Database not found at {db_path}")
    sys.exit(1)

# Read migration SQL
migration_file = Path(__file__).parent / "008_add_ai_learning_tables.sql"
if not migration_file.exists():
    print(f"Error: Migration file not found at {migration_file}")
    sys.exit(1)

with open(migration_file, "r") as f:
    migration_sql = f.read()

# Apply migration
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

try:
    cursor.executescript(migration_sql)
    conn.commit()
    print("[OK] Migration 008 applied successfully!")
    print("   Created tables: ai_lessons, ai_progress, ai_verification_tests")
except Exception as e:
    conn.rollback()
    print(f"[ERROR] Error applying migration: {e}")
    sys.exit(1)
finally:
    conn.close()

