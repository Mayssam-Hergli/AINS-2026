"""
Supabase PostgreSQL database layer — replaces the previous SQLite module.

Tables already exist in Supabase (users, projects, diagnostics, roadmaps,
roadmap_steps, chat_sessions, chat_messages, knowledge_base) — this file
never creates or alters schema, only connects and runs parameterized
queries against it.

Connects via SUPABASE_DB_URL (read from .env, never logged or printed).
Uses psycopg2 with RealDictCursor so rows behave like dicts, matching the
sqlite3.Row interface the rest of the codebase was already written against
(row["column_name"] works the same way it did before).
"""
import os
from contextlib import contextmanager
from typing import Generator, Optional

import psycopg2
import psycopg2.extras

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")


def get_connection() -> Optional[psycopg2.extensions.connection]:
    """
    Returns a raw psycopg2 connection, or None if it can't connect.
    Used for one-off/manual checks (e.g. `python -c "from database import
    get_connection; ..."`). Route code should use get_db() instead, which
    manages commit/rollback/close automatically.
    """
    if not SUPABASE_DB_URL:
        return None
    try:
        return psycopg2.connect(SUPABASE_DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    except psycopg2.OperationalError:
        return None


def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
    """FastAPI dependency that yields an open Supabase connection per request."""
    conn = psycopg2.connect(SUPABASE_DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def db_cursor(conn: psycopg2.extensions.connection):
    """Small helper: route files were written against sqlite3's
    conn.execute(...).fetchone()/.fetchall() API. psycopg2 requires a
    cursor. This wraps cursor creation/closing so call sites read
    `with db_cursor(db) as cur: cur.execute(...)` instead of restructuring
    every route to manage cursors by hand."""
    cur = conn.cursor()
    try:
        yield cur
    finally:
        cur.close()


def init_db() -> None:
    """
    No-op — kept only so main.py's existing startup hook doesn't need to
    change. Supabase tables already exist; this layer must never create or
    alter them.
    """
    return None
