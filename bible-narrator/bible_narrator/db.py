"""SQLite storage for the local library (with FTS5 full-text indexes)."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id            INTEGER PRIMARY KEY,
    kind          TEXT NOT NULL CHECK (kind IN ('scripture','commentary','dictionary','reference')),
    title         TEXT NOT NULL,
    abbreviation  TEXT NOT NULL DEFAULT '',
    edition       TEXT NOT NULL DEFAULT '',
    language      TEXT NOT NULL DEFAULT 'en',
    license       TEXT NOT NULL DEFAULT '',
    attribution   TEXT NOT NULL DEFAULT '',
    source_url    TEXT NOT NULL DEFAULT '',
    notes         TEXT NOT NULL DEFAULT '',
    format        TEXT NOT NULL DEFAULT '',
    builtin_key   TEXT NOT NULL DEFAULT '',
    enabled       INTEGER NOT NULL DEFAULT 1,
    item_count    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Scripture text: one row per verse.
CREATE TABLE IF NOT EXISTS verses (
    id         INTEGER PRIMARY KEY,
    source_id  INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    book       INTEGER NOT NULL,
    chapter    INTEGER NOT NULL,
    verse      INTEGER NOT NULL,
    text       TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS verses_ref ON verses(source_id, book, chapter, verse);

CREATE VIRTUAL TABLE IF NOT EXISTS verses_fts USING fts5(
    text, content='verses', content_rowid='id', tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS verses_ai AFTER INSERT ON verses BEGIN
    INSERT INTO verses_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS verses_ad AFTER DELETE ON verses BEGIN
    INSERT INTO verses_fts(verses_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;

-- Commentary / dictionary / other reference books: one row per chunk, with
-- the location inside the book (page, article heading, or verse range).
CREATE TABLE IF NOT EXISTS ref_entries (
    id           INTEGER PRIMARY KEY,
    source_id    INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    heading      TEXT NOT NULL DEFAULT '',
    location     TEXT NOT NULL DEFAULT '',
    page         INTEGER,
    book         INTEGER,
    chapter      INTEGER,
    verse_start  INTEGER,
    verse_end    INTEGER,
    text         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ref_entries_src ON ref_entries(source_id);
CREATE INDEX IF NOT EXISTS ref_entries_bcv ON ref_entries(book, chapter);
CREATE INDEX IF NOT EXISTS ref_entries_heading ON ref_entries(heading COLLATE NOCASE);

CREATE VIRTUAL TABLE IF NOT EXISTS ref_fts USING fts5(
    heading, text, content='ref_entries', content_rowid='id', tokenize='porter unicode61'
);
CREATE TRIGGER IF NOT EXISTS ref_ai AFTER INSERT ON ref_entries BEGIN
    INSERT INTO ref_fts(rowid, heading, text) VALUES (new.id, new.heading, new.text);
END;
CREATE TRIGGER IF NOT EXISTS ref_ad AFTER DELETE ON ref_entries BEGIN
    INSERT INTO ref_fts(ref_fts, rowid, heading, text) VALUES ('delete', old.id, old.heading, old.text);
END;
"""


class Database:
    """Thread-safe wrapper: one connection guarded by a lock (SQLite is fast enough
    for a single desktop user, and this keeps transactions simple)."""

    def __init__(self, path: Path | str):
        self.path = str(path)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.lock:
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def query(self, sql: str, params: tuple | dict = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, params).fetchall()

    def one(self, sql: str, params: tuple | dict = ()) -> sqlite3.Row | None:
        with self.lock:
            return self.conn.execute(sql, params).fetchone()

    def execute(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        with self.lock:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur

    def close(self) -> None:
        with self.lock:
            self.conn.close()
