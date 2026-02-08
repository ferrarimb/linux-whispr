"""Transcription history manager (SQLite)."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from linux_whispr.constants import HISTORY_DB, HISTORY_RETENTION_DAYS

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    refined_text TEXT,
    duration REAL NOT NULL DEFAULT 0.0,
    app_context TEXT,
    word_count INTEGER NOT NULL DEFAULT 0,
    language TEXT
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp);
"""


@dataclass
class HistoryEntry:
    """A single transcription history entry."""

    id: int
    timestamp: str
    raw_text: str
    refined_text: str | None
    duration: float
    app_context: str | None
    word_count: int
    language: str | None


class HistoryManager:
    """Manages the transcription history database."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or HISTORY_DB
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        """Open the database and create tables if needed."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.execute(CREATE_TABLE_SQL)
        self._conn.execute(CREATE_INDEX_SQL)
        self._conn.commit()
        logger.info("History database opened at %s", self._db_path)

    def close(self) -> None:
        """Close the database."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def add(
        self,
        raw_text: str,
        refined_text: str | None = None,
        duration: float = 0.0,
        app_context: str | None = None,
        language: str | None = None,
    ) -> int:
        """Add a transcription to history. Returns the entry ID."""
        assert self._conn is not None

        word_count = len(raw_text.split())
        timestamp = datetime.now().isoformat()

        cursor = self._conn.execute(
            """
            INSERT INTO history (timestamp, raw_text, refined_text, duration, app_context, word_count, language)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (timestamp, raw_text, refined_text, duration, app_context, word_count, language),
        )
        self._conn.commit()
        entry_id = cursor.lastrowid or 0
        logger.debug("Added history entry #%d: %s...", entry_id, raw_text[:50])
        return entry_id

    def search(self, query: str, limit: int = 50) -> list[HistoryEntry]:
        """Search history by text content."""
        assert self._conn is not None

        rows = self._conn.execute(
            """
            SELECT id, timestamp, raw_text, refined_text, duration, app_context, word_count, language
            FROM history
            WHERE raw_text LIKE ? OR refined_text LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()

        return [HistoryEntry(*row) for row in rows]

    def get_recent(self, limit: int = 20) -> list[HistoryEntry]:
        """Get most recent history entries."""
        assert self._conn is not None

        rows = self._conn.execute(
            """
            SELECT id, timestamp, raw_text, refined_text, duration, app_context, word_count, language
            FROM history
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        return [HistoryEntry(*row) for row in rows]

    def delete(self, entry_id: int) -> bool:
        """Delete a history entry. Returns True if found."""
        assert self._conn is not None

        cursor = self._conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))
        self._conn.commit()
        return cursor.rowcount > 0

    def clear(self) -> int:
        """Delete all history entries. Returns count deleted."""
        assert self._conn is not None

        cursor = self._conn.execute("DELETE FROM history")
        self._conn.commit()
        return cursor.rowcount

    def purge_old(self, retention_days: int = HISTORY_RETENTION_DAYS) -> int:
        """Delete entries older than retention_days. Returns count deleted."""
        assert self._conn is not None

        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        cursor = self._conn.execute(
            "DELETE FROM history WHERE timestamp < ?", (cutoff,)
        )
        self._conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Purged %d history entries older than %d days", deleted, retention_days)
        return deleted
