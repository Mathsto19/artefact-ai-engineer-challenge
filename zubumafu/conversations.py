"""Local, read-only-to-business-data conversation history for the demo UI.

Chat messages are saved on this computer in a SQLite file that is ignored by
Git. This is not an account system; use only in a trusted, single-user demo.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path(__file__).resolve().parents[1] / ".local" / "conversations.sqlite3"
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")
_TRACE_FIELDS = {"tool", "status", "matches", "pages", "chapters", "product_id", "via",
                 "source", "sources", "filters", "promotion_source", "pricing", "order_id",
                 "next_field", "source_type", "reply_origin", "added_price_fields", "references",
                 "ambiguities", "clarification_field"}
_TRACE_FIELDS.add("argument_overrides")
_TRACE_FIELDS.add("invoked_by")
_DETAIL_FIELDS = {"category", "query", "max_price_brl", "budget_applies_to", "available_only",
                  "payment_method", "chapter", "pages", "list_price_brl", "final_price_brl",
                  "discount_amount_brl", "list_price_display_brl", "final_price_display_brl",
                  "discount_amount_display_brl", "discount_percent", "discount_type", "status",
                  "active_promotion", "promotion_id", "description", "pix_discount_applied",
                  "pix_non_cumulative", "promotion_validity_dates", "code", "message", "issue", "note",
                  "reference_names", "strings_material"}


def _safe_detail(value):
    if isinstance(value, dict):
        return {key: _safe_detail(item) for key, item in value.items() if key in _DETAIL_FIELDS}
    if isinstance(value, list):
        return [_safe_detail(item) for item in value]
    if isinstance(value, str):
        return _EMAIL_PATTERN.sub("[e-mail oculto]", value)
    return value if value is None or isinstance(value, (bool, int, float)) else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _title_from_text(text: str) -> str:
    safe = _EMAIL_PATTERN.sub("[e-mail oculto]", " ".join(text.split()))
    if not safe:
        return "Nova conversa"
    return safe[:48] + ("…" if len(safe) > 48 else "")


class ConversationStore:
    """Tiny stdlib storage; each operation uses a fresh SQLite connection."""

    def __init__(self, path: Path = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL CHECK(kind IN ('personal', 'test')),
                    scenario_id TEXT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    trace_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id, id);
            """)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path, timeout=5)
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            with conn:
                yield conn
        finally:
            conn.close()

    def create(self, *, kind: str = "personal", scenario_id: str | None = None, title: str = "Nova conversa") -> str:
        if kind not in {"personal", "test"}:
            raise ValueError("invalid conversation type")
        if kind == "personal" and scenario_id is not None:
            raise ValueError("personal conversation cannot have a scenario")
        chat_id = str(uuid.uuid4())
        at = _now()
        with self._connect() as conn:
            conn.execute("INSERT INTO conversations VALUES (?, ?, ?, ?, ?, ?)",
                         (chat_id, kind, scenario_id, _title_from_text(title), at, at))
        return chat_id

    def list_all(self) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT c.id, c.kind, c.scenario_id, c.title, c.created_at,
                       c.updated_at, COUNT(m.id) AS message_count
                  FROM conversations c
                  LEFT JOIN messages m ON m.conversation_id = c.id
                 GROUP BY c.id
                 ORDER BY c.updated_at DESC, c.created_at DESC
            """).fetchall()
        return [dict(row) for row in rows]

    def get(self, chat_id: str) -> dict[str, object] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id = ?", (chat_id,)).fetchone()
        return dict(row) if row else None

    def messages(self, chat_id: str) -> list[dict[str, object]]:
        if self.get(chat_id) is None:
            raise KeyError("unknown conversation")
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT role, content, trace_json FROM messages
                 WHERE conversation_id = ? ORDER BY id
            """, (chat_id,)).fetchall()
        return [{"role": row["role"], "content": row["content"],
                 "trace": json.loads(row["trace_json"])} for row in rows]

    def add_exchange(self, chat_id: str, question: str, answer: str, trace: list[dict] | None = None) -> None:
        """Save user/assistant messages atomically; never persist raw tool payloads."""
        if not isinstance(question, str) or not question.strip() or not isinstance(answer, str):
            raise ValueError("invalid exchange")
        safe_trace = [{key: _safe_detail(value) for key, value in item.items() if key in _TRACE_FIELDS}
                      for item in (trace or []) if isinstance(item, dict)]
        at = _now()
        with self._connect() as conn:
            row = conn.execute("SELECT title FROM conversations WHERE id = ?", (chat_id,)).fetchone()
            if row is None:
                raise KeyError("unknown conversation")
            count = conn.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (chat_id,)).fetchone()[0]
            for role, content, details in (("user", question, []), ("assistant", answer, safe_trace)):
                conn.execute("""
                    INSERT INTO messages(conversation_id, role, content, trace_json, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (chat_id, role, content, json.dumps(details, ensure_ascii=False), at))
            next_title = _title_from_text(question) if count == 0 and row["title"] == "Nova conversa" else row["title"]
            conn.execute("UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                         (next_title, at, chat_id))

    def delete(self, chat_id: str) -> bool:
        """Delete only the requested conversation, including its messages."""
        with self._connect() as conn:
            result = conn.execute("DELETE FROM conversations WHERE id = ?", (chat_id,))
        return result.rowcount > 0
