"""
Database connection pool management using aiosqlite and sqlite-vec.

Provides a singleton connection for the FastAPI application
and utility functions for database operations.
"""

import os
import asyncio
import sqlite3
from pathlib import Path
from urllib.parse import quote
import aiosqlite
import sqlite_vec
from dotenv import load_dotenv

load_dotenv()

# Global connection
_conn: aiosqlite.Connection | None = None
_read_only_conn: aiosqlite.Connection | None = None
_read_only_lock = asyncio.Lock()
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "discovery_engine.db")

async def get_read_only_pool() -> aiosqlite.Connection:
    """Open the packaged web dataset without creating or modifying any files."""
    global _read_only_conn
    async with _read_only_lock:
        if _read_only_conn is None:
            path = Path(DB_PATH).resolve()
            if not path.is_file():
                raise FileNotFoundError(f"Discovery database is missing: {path}")
            uri = f"file:{quote(str(path))}?mode=ro"
            conn = await aiosqlite.connect(uri, uri=True, check_same_thread=False)
            conn.row_factory = aiosqlite.Row
            try:
                async with conn.execute("SELECT 1 FROM feedback_records LIMIT 1") as cursor:
                    await cursor.fetchone()
            except Exception:
                await conn.close()
                raise
            _read_only_conn = conn
    return _read_only_conn

async def close_read_only_pool():
    global _read_only_conn
    async with _read_only_lock:
        if _read_only_conn is not None:
            await _read_only_conn.close()
            _read_only_conn = None

async def get_pool() -> aiosqlite.Connection:
    """Get or create the database connection."""
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = await aiosqlite.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = aiosqlite.Row
        
        # Load sqlite-vec extension synchronously to the underlying connection
        await _conn.execute("SELECT 1") # Ensure connected
        try:
            _conn._conn.enable_load_extension(True)
            sqlite_vec.load(_conn._conn)
            _conn._conn.enable_load_extension(False)
        except AttributeError:
            print("Warning: sqlite3 build does not support extension loading. sqlite-vec skipped.")
        
    return _conn

async def close_pool():
    """Close the database connection."""
    global _conn
    if _conn is not None:
        await _conn.close()
        _conn = None

async def get_db():
    """
    FastAPI dependency that provides a database connection.
    """
    conn = await get_pool()
    yield conn

async def check_connection() -> bool:
    """Test database connectivity."""
    try:
        conn = await get_pool()
        async with conn.execute("SELECT 1") as cursor:
            result = await cursor.fetchone()
            return result is not None
    except Exception:
        return False

async def check_tables_exist() -> dict[str, bool]:
    """Check if all required tables exist in the database."""
    required_tables = [
        "feedback_records",
        "clusters",
        "synthesis_answers",
        "ingestion_log",
        "pipeline_runs",
    ]
    conn = await get_pool()
    results = {}
    for table in required_tables:
        async with conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ) as cursor:
            row = await cursor.fetchone()
            results[table] = row is not None
    return results
