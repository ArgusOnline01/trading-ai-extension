#!/usr/bin/env python3
"""Apply migration 011: Add deleted_annotations to ai_lessons table."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "vtc.db"
MIGRATION_FILE = Path(__file__).parent / "011_add_deleted_annotations.sql"

def apply_migration():
    """Apply the migration."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(ai_lessons)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "deleted_annotations" in columns:
            print("[SKIP] Migration 011 already applied (deleted_annotations column exists)")
            return False

        # Read and execute migration
        with open(MIGRATION_FILE, "r") as f:
            migration_sql = f.read()

        cursor.executescript(migration_sql)
        conn.commit()

        print("[SUCCESS] Migration 011 applied successfully")
        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration 011 failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration()

