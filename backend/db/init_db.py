"""
Database initialization and migration runner.
Applies all SQL migrations and seeds default discovery records.
"""

import os
import glob
import logging
import aiosqlite
from db.connection import get_pool, DB_PATH

logger = logging.getLogger(__name__)

async def run_migrations(db: aiosqlite.Connection):
    """Executes all migration SQL files in order."""
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    sql_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))

    for sql_file in sql_files:
        logger.info(f"Applying migration: {os.path.basename(sql_file)}")
        with open(sql_file, "r", encoding="utf-8") as f:
            sql_script = f.read()
        await db.executescript(sql_script)

    await db.commit()
    logger.info("All database migrations applied.")

async def init_and_seed():
    """Initializes the database, runs migrations, and seeds records."""
    db = await get_pool()
    await run_migrations(db)
    logger.info("Database initialized.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(init_and_seed())
