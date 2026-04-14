#!/usr/bin/env python3
"""
Database Migration: Add Obsidian sync columns to content_items table
Run this after updating models.py to add the new columns
"""

import sqlite3
import os

def migrate_database():
    db_path = os.path.join(os.path.dirname(__file__), 'curator.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    print(f"🔄 Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check which columns already exist
    cursor.execute("PRAGMA table_info(content_items)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    new_columns = [
        ("obsidian_synced", "BOOLEAN DEFAULT 0"),
        ("obsidian_path", "TEXT"),
        ("entities_json", "TEXT"),
        ("concepts_json", "TEXT")
    ]
    
    added = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            print(f"   Adding column: {col_name}")
            cursor.execute(f"ALTER TABLE content_items ADD COLUMN {col_name} {col_type}")
            added += 1
        else:
            print(f"   Column already exists: {col_name}")
    
    conn.commit()
    conn.close()
    
    if added > 0:
        print(f"✅ Migration complete: {added} columns added")
    else:
        print(f"✅ All columns already exist")
    
    return True

if __name__ == "__main__":
    migrate_database()
