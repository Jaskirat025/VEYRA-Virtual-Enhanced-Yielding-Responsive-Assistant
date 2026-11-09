"""SQLite persistence: conversations, messages, notes, tool log and timers.

The database lives in the per-user data directory. Every public method is
thread-safe and returns plain Python structures so the API layer stays thin.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.paths import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation
    ON messages (conversation_id, id);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL DEFAULT '',
    step INTEGER NOT NULL DEFAULT 0,
    tool TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    risk TEXT NOT NULL DEFAULT '',
    args_redacted TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    output_preview TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS timers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    fire_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kv (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or db_path()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(
            self._path, check_same_thread=False, isolation_level=None
        )
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.executescript(SCHEMA)
            self._connection.execute("PRAGMA journal_mode=WAL")

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    # -- conversations and messages -------------------------------------
    def ensure_conversation(self, conversation_id: str | None, title: str = "") -> str:
        if conversation_id:
            with self._lock:
                row = self._connection.execute(
                    "SELECT id FROM conversations WHERE id = ?", (conversation_id,)
                ).fetchone()
            if row:
                return conversation_id

        new_id = conversation_id or uuid.uuid4().hex
        with self._lock:
            self._connection.execute(
                "INSERT OR IGNORE INTO conversations (id, title, created_at) VALUES (?, ?, ?)",
                (new_id, title[:120], _now()),
            )
        return new_id

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO messages (conversation_id, role, content, created_at)"
                " VALUES (?, ?, ?, ?)",
                (conversation_id, role, content, _now()),
            )

    def messages(self, conversation_id: str, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, role, content, created_at FROM messages"
                " WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, max(1, min(limit, 500))),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def recent_messages(self, conversation_id: str, limit: int = 12) -> list[dict[str, Any]]:
        return self.messages(conversation_id, limit=limit)

    def conversations(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT c.id, c.title, c.created_at,"
                " (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count"
                " FROM conversations c ORDER BY c.created_at DESC LIMIT ?",
                (max(1, min(limit, 200)),),
            ).fetchall()
        return [dict(row) for row in rows]

    # -- notes -----------------------------------------------------------
    def save_note(self, title: str, body: str) -> int:
        now = _now()
        with self._lock:
            cursor = self._connection.execute(
                "INSERT INTO notes (title, body, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (title[:200], body, now, now),
            )
            return int(cursor.lastrowid)

    def search_notes(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        like = f"%{query.strip()[:200]}%"
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, title, body, created_at FROM notes"
                " WHERE title LIKE ? OR body LIKE ? ORDER BY id DESC LIMIT ?",
                (like, like, max(1, min(limit, 50))),
            ).fetchall()
        return [dict(row) for row in rows]

    # -- tool log --------------------------------------------------------
    def log_tool_call(
        self,
        *,
        conversation_id: str,
        step: int,
        tool: str,
        category: str,
        risk: str,
        args_redacted: dict[str, Any],
        status: str,
        duration_ms: int,
        error: str = "",
        output_preview: str = "",
    ) -> int:
        with self._lock:
            cursor = self._connection.execute(
                "INSERT INTO tool_calls (conversation_id, step, tool, category, risk,"
                " args_redacted, status, duration_ms, error, output_preview, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    step,
                    tool,
                    category,
                    risk,
                    json.dumps(args_redacted, ensure_ascii=False)[:2000],
                    status,
                    duration_ms,
                    error[:500],
                    output_preview[:200],
                    _now(),
                ),
            )
            return int(cursor.lastrowid)

    def tool_log(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM tool_calls ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 500)),),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["args_redacted"] = json.loads(item["args_redacted"])
            except ValueError:
                item["args_redacted"] = {}
            result.append(item)
        return result

    # -- timers ----------------------------------------------------------
    def add_timer(self, label: str, fire_at: str) -> int:
        with self._lock:
            cursor = self._connection.execute(
                "INSERT INTO timers (label, fire_at, created_at) VALUES (?, ?, ?)",
                (label[:200], fire_at, _now()),
            )
            return int(cursor.lastrowid)

    def due_timers(self, now: str | None = None) -> list[dict[str, Any]]:
        moment = now or _now()
        with self._lock:
            rows = self._connection.execute(
                "SELECT id, label, fire_at FROM timers"
                " WHERE status = 'pending' AND fire_at <= ? ORDER BY fire_at",
                (moment,),
            ).fetchall()
        return [dict(row) for row in rows]

    def complete_timer(self, timer_id: int) -> None:
        with self._lock:
            self._connection.execute("UPDATE timers SET status = 'done' WHERE id = ?", (timer_id,))

    # -- key/value -------------------------------------------------------
    def get_value(self, key: str, default: str = "") -> str:
        with self._lock:
            row = self._connection.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_value(self, key: str, value: str) -> None:
        with self._lock:
            self._connection.execute(
                "INSERT INTO kv (key, value) VALUES (?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
