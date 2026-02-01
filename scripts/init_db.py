#!/usr/bin/env python3
"""
Initialize the database.
Run this once before starting the bot.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.database import Database
from src.core.config import get_config


async def main():
    """Initialize the database."""
    print("=" * 50)
    print("INITIALIZING DATABASE")
    print("=" * 50)
    
    config = get_config()
    db_path = config.database_path
    
    # Ensure directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Database path: {db_path}")
    
    # Connect and initialize
    db = Database(db_path)
    await db.connect()
    
    print("✓ Database tables created")
    
    # Verify tables exist
    cursor = await db._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    tables = await cursor.fetchall()
    
    print(f"✓ Tables: {', '.join(t['name'] for t in tables)}")
    
    await db.close()
    
    print("=" * 50)
    print("DATABASE READY!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Copy config/.env.example to config/.env")
    print("  2. Run: python main.py")


if __name__ == "__main__":
    asyncio.run(main())
