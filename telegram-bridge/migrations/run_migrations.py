#!/usr/bin/env python3
"""
Run database migrations for the Telegram bridge.

This script adds media columns to the messages table if they don't exist.
"""

import sqlite3
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'store', 'messages.db'
)


def column_exists(cursor, table, column):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns


def run_migrations():
    """Run all necessary migrations."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        print("The database will be created when you first run the Telegram bridge.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if migrations are needed
        new_columns = [
            ('has_media', 'BOOLEAN DEFAULT 0'),
            ('media_type', 'VARCHAR'),
            ('file_id', 'VARCHAR'),
            ('file_name', 'VARCHAR'),
            ('file_size', 'INTEGER'),
            ('mime_type', 'VARCHAR'),
            ('local_path', 'VARCHAR'),
        ]

        migrations_needed = False
        for col_name, col_type in new_columns:
            if not column_exists(cursor, 'messages', col_name):
                migrations_needed = True
                print(f"Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}")

        if migrations_needed:
            # Create index for media queries
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_has_media ON messages(has_media)"
            )
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("Database is already up to date.")

    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migrations()
