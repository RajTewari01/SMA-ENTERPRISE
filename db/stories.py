"""
stories.py
==========
Database access layer for AI-generated story scripts.
"""

from pathlib import Path
from typing import Dict, List, Optional

from db.database import BaseDatabase


class StoriesDatabase(BaseDatabase):
    """CRUD operations for the stories table."""

    def __init__(self, db_path: str | Path):
        super().__init__(db_path)
        self._ensure_table()

    def _ensure_table(self):
        with self.get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    hook TEXT,
                    body TEXT,
                    twist TEXT,
                    full_script TEXT,
                    style TEXT DEFAULT 'horror',
                    platform TEXT DEFAULT 'instagram',
                    duration_seconds INTEGER DEFAULT 60,
                    hashtags TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)

    def create(self, title: str, full_script: str, **kwargs) -> int:
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO stories (title, hook, body, twist, full_script, style, platform, duration_seconds, hashtags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    title,
                    kwargs.get("hook", ""),
                    kwargs.get("body", ""),
                    kwargs.get("twist", ""),
                    full_script,
                    kwargs.get("style", "horror"),
                    kwargs.get("platform", "instagram"),
                    kwargs.get("duration_seconds", 60),
                    kwargs.get("hashtags", ""),
                ),
            )
            return cursor.lastrowid

    def read(self, story_id: int) -> Optional[Dict]:
        with self.get_db_connection() as conn:
            row = conn.execute("SELECT * FROM stories WHERE id = ?", (story_id,)).fetchone()
            return dict(row) if row else None

    def read_all(self, limit: int = 50) -> List[Dict]:
        with self.get_db_connection() as conn:
            rows = conn.execute("SELECT * FROM stories ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def update(self, story_id: int, **kwargs) -> bool:
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [story_id]
        with self.get_db_connection() as conn:
            conn.execute(f"UPDATE stories SET {fields}, updated_at = datetime('now') WHERE id = ?", values)
            return True

    def delete(self, story_id: int) -> bool:
        with self.get_db_connection() as conn:
            conn.execute("DELETE FROM stories WHERE id = ?", (story_id,))
            return True