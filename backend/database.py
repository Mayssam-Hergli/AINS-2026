"""
SQLite database layer.

Uses Python's built-in sqlite3 — no additional packages required.
FastAPI runs sync route functions in a thread pool via anyio, so blocking
sqlite3 calls are safe inside sync route handlers.

To migrate to PostgreSQL later, swap this module for one that provides
an equivalent get_db() generator yielding a psycopg2/asyncpg connection.
The rest of the codebase only imports get_db and init_db from here.
"""
import sqlite3
import os
from typing import Generator

DATABASE_PATH = os.getenv("DATABASE_PATH", "ains.db")


def init_db(path: str = DATABASE_PATH) -> None:
    """Create all tables if they don't exist. Called once at app startup."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript("""
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                id               TEXT PRIMARY KEY,
                email            TEXT UNIQUE NOT NULL,
                hashed_password  TEXT NOT NULL,
                created_at       TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS project_profiles (
                id                     TEXT PRIMARY KEY,
                user_id                TEXT NOT NULL REFERENCES users(id),
                name                   TEXT,
                diagnostic_answers     TEXT,
                market_score           TEXT,
                commercial_score       TEXT,
                innovation_score       TEXT,
                scalability_score      TEXT,
                green_score            TEXT,
                anomaly_flags          TEXT,
                low_scoring_dimensions TEXT,
                green_pillars_flagged  TEXT,
                justifications         TEXT,
                anomaly_summary        TEXT,
                created_at             TEXT DEFAULT (datetime('now')),
                updated_at             TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS scores_history (
                id          TEXT PRIMARY KEY,
                profile_id  TEXT NOT NULL REFERENCES project_profiles(id),
                market      REAL,
                commercial  REAL,
                innovation  REAL,
                scalability REAL,
                green       REAL,
                computed_at TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
        # Migration: add name column to existing databases
        try:
            conn.execute("ALTER TABLE project_profiles ADD COLUMN name TEXT")
            conn.commit()
        except Exception:
            pass  # column already exists
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency that yields an open SQLite connection per request."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
