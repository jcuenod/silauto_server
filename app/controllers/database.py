"""
Database controller for SQLite operations.
"""

import sqlite3
import json
from contextlib import contextmanager
from typing import Any
from pathlib import Path
import threading

from app.config import DATABASE_PATH

# Thread-local storage for database connections
_local = threading.local()


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection from thread-local storage."""
    if not hasattr(_local, 'connection'):
        # Ensure the directory exists        
        _local.connection = sqlite3.connect(Path(DATABASE_PATH) / "silauto.db", check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
        _local.connection.execute("PRAGMA foreign_keys = ON")
        _local.connection.execute("PRAGMA journal_mode = WAL")
    
    return _local.connection


@contextmanager
def get_db():
    """Context manager for database operations."""
    conn = get_db_connection()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()


def init_database():
    """Initialize the database with required tables and populate caches if tables are created."""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('tasks', 'projects', 'scriptures', 'drafts', 'lang_codes')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
    
        # Tasks table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                created_at TEXT NOT NULL,
                started_at TEXT,
                ended_at TEXT,
                error TEXT,
                parameters TEXT NOT NULL
            )
        """)

        # Projects table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                full_name TEXT NOT NULL,
                iso_code TEXT NOT NULL,
                lang TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                extract_task_id TEXT,
                FOREIGN KEY (extract_task_id) REFERENCES tasks(id)
            )
        """)

        # Scripture table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scriptures (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                lang_code TEXT NOT NULL,
                path TEXT NOT NULL,
                stats TEXT NOT NULL
            )
        """)

        # Drafts table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                train_experiment_name TEXT NOT NULL,
                source_scripture_name TEXT NOT NULL,
                book_name TEXT NOT NULL,
                path TEXT NOT NULL,
                has_pdf BOOLEAN NOT NULL,
                UNIQUE(project_id, train_experiment_name, source_scripture_name, book_name)
            )
        """)

        # Lang codes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lang_codes (
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                PRIMARY KEY (code, name)
            )
        """)

        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_kind ON tasks(kind)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_iso_code ON projects(iso_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scriptures_lang_code ON scriptures(lang_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_drafts_project_id ON drafts(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lang_codes_code ON lang_codes(code)")

    return len(existing_tables) == 0


def serialize_json(data: Any) -> str:
    """Serialize data to JSON string."""
    return json.dumps(data, default=str)


def deserialize_json(data: str) -> Any:
    """Deserialize JSON string to data."""
    return json.loads(data)