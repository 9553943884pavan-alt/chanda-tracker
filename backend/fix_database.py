"""
Script to fix the database schema by adding missing columns.
Run with: .venv\Scripts\activate; python fix_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text
from database import engine


async def fix_database():
    """Add missing google_sub column to users table if it doesn't exist."""

    async with engine.begin() as conn:
        # Check if google_sub column exists
        result = await conn.execute(
            text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'google_sub'
            """)
        )
        column_exists = result.fetchone()

        if column_exists:
            print("✓ google_sub column already exists")
        else:
            # Add the google_sub column
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN google_sub VARCHAR(255) UNIQUE")
            )
            print("✓ Added google_sub column to users table")

        # Check if password_hash column is nullable
        result = await conn.execute(
            text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'password_hash'
            """)
        )
        row = result.fetchone()
        if row and row[0] == 'NO':
            await conn.execute(
                text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
            )
            print("✓ Made password_hash nullable (for Google-only accounts)")
        else:
            print("✓ password_hash is already nullable")

    print("\n✅ Database schema has been fixed!")


if __name__ == "__main__":
    asyncio.run(fix_database())
