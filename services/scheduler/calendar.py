"""
calendar.py — Content calendar for scheduling posts.
"""
import json, logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from db.database import BaseDatabase

logger = logging.getLogger(__name__)


class ContentCalendar(BaseDatabase):
    """Manages scheduled posts in SQLite (dev) / PostgreSQL (prod)."""

    def __init__(self, db_path: str | Path = "data/calendar.db"):
        super().__init__(db_path)
        self._ensure_table()

    def _ensure_table(self):
        with self.get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    caption TEXT,
                    media_paths TEXT,
                    hashtags TEXT,
                    scheduled_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    post_id TEXT,
                    error TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    published_at TEXT
                )
            """)

    def create(self, platform: str, caption: str, scheduled_at: str, **kwargs) -> int:
        with self.get_db_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO scheduled_posts (platform, caption, media_paths, hashtags, scheduled_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (platform, caption,
                 json.dumps(kwargs.get("media_paths", [])),
                 json.dumps(kwargs.get("hashtags", [])),
                 scheduled_at),
            )
            return cursor.lastrowid

    def read(self, post_id: int) -> Optional[Dict]:
        with self.get_db_connection() as conn:
            row = conn.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,)).fetchone()
            return dict(row) if row else None

    def update(self, post_id: int, **kwargs) -> bool:
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        with self.get_db_connection() as conn:
            conn.execute(f"UPDATE scheduled_posts SET {fields} WHERE id = ?", [*kwargs.values(), post_id])
            return True

    def delete(self, post_id: int) -> bool:
        with self.get_db_connection() as conn:
            conn.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
            return True

    def get_pending(self, before: Optional[str] = None) -> List[Dict]:
        """Get posts due for publishing."""
        before = before or datetime.utcnow().isoformat()
        with self.get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM scheduled_posts WHERE status = 'pending' AND scheduled_at <= ? ORDER BY scheduled_at",
                (before,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_published(self, post_id: int, platform_post_id: str):
        self.update(post_id, status="published", post_id=platform_post_id, published_at=datetime.utcnow().isoformat())

    def mark_failed(self, post_id: int, error: str):
        self.update(post_id, status="failed", error=error)
