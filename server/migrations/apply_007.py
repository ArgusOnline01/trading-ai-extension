#!/usr/bin/env python3
"""Apply migration 007: Add circle_locations column to annotations table"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.session import SessionLocal
from sqlalchemy import text

def apply_migration():
    db = SessionLocal()
    try:
        db.execute(text('ALTER TABLE annotations ADD COLUMN circle_locations JSON'))
        db.commit()
        print('✅ Migration 007 applied successfully: Added circle_locations column')
    except Exception as e:
        if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
            print('ℹ️  Migration 007 already applied: circle_locations column exists')
        else:
            print(f'❌ Error applying migration: {e}')
            db.rollback()
            raise
    finally:
        db.close()

if __name__ == '__main__':
    apply_migration()

