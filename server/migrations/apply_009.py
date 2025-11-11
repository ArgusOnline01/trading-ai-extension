import sqlite3
import os
import sys
from pathlib import Path

# Add the server directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Define paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "server" / "data" / "vtc.db"
MIGRATION_SQL_PATH = Path(__file__).parent / "009_add_corrected_reasoning.sql"

def apply_migration(db_path: Path, migration_sql_path: Path):
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
    
    if not migration_sql_path.exists():
        print(f"Error: Migration SQL file not found at {migration_sql_path}")
        sys.exit(1)
    
    with open(migration_sql_path, 'r') as f:
        migration_sql = f.read()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        cursor.executescript(migration_sql)
        conn.commit()
        print("[OK] Migration 009 applied successfully!")
        print("   Added corrected_reasoning column to ai_lessons table")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error applying migration: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration(DB_PATH, MIGRATION_SQL_PATH)

