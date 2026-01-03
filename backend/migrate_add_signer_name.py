"""
Migration script to add signer_name column to signatures table.
Run this once to update existing database.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'medical_docs.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(signatures)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'signer_name' in columns:
        print("Column 'signer_name' already exists. Migration not needed.")
        conn.close()
        return

    # Add the column
    try:
        cursor.execute("ALTER TABLE signatures ADD COLUMN signer_name VARCHAR(100)")
        conn.commit()
        print("Successfully added 'signer_name' column to signatures table.")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
