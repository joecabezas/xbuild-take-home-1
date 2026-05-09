import os
import sqlite3
from contextlib import contextmanager

DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/proposals.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def transaction():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    with transaction() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS reports (
                id         TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                raw_json   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS findings (
                id          TEXT PRIMARY KEY,
                report_id   TEXT NOT NULL REFERENCES reports(id),
                seq         INTEGER NOT NULL,
                title       TEXT NOT NULL,
                severity    TEXT NOT NULL,
                notes       TEXT NOT NULL DEFAULT '',
                photos_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS proposals (
                id         TEXT PRIMARY KEY,
                report_id  TEXT NOT NULL REFERENCES reports(id),
                version    INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                summary    TEXT NOT NULL,
                total      INTEGER NOT NULL,
                UNIQUE (report_id, version)
            );

            CREATE TABLE IF NOT EXISTS proposal_line_items (
                id             TEXT PRIMARY KEY,
                proposal_id    TEXT NOT NULL REFERENCES proposals(id),
                seq            INTEGER NOT NULL,
                finding_id     TEXT NOT NULL REFERENCES findings(id),
                code           TEXT NOT NULL,
                category       TEXT NOT NULL,
                description    TEXT NOT NULL,
                estimated_cost INTEGER NOT NULL,
                source_finding TEXT NOT NULL,
                match_reason   TEXT NOT NULL
            );
        """)
