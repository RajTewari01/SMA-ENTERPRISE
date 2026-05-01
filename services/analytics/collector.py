"""
collector.py — Pull analytics from all connected platforms.
"""
import logging
from datetime import datetime
from typing import Dict, List
from db.database import BaseDatabase
from services.social.manager import SocialManager

logger = logging.getLogger(__name__)


class AnalyticsDB(BaseDatabase):
    """Store collected analytics in SQLite."""

    def __init__(self, db_path="data/analytics.db"):
        super().__init__(db_path)
        self._ensure_table()

    def _ensure_table(self):
        with self.get_db_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS post_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT, post_id TEXT,
                    likes INTEGER DEFAULT 0, comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0, saves INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0, reach INTEGER DEFAULT 0,
                    engagement_rate REAL DEFAULT 0,
                    collected_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(platform, post_id, collected_at)
                )
            """)

    def create(self, platform: str, post_id: str, **metrics) -> int:
        with self.get_db_connection() as conn:
            c = conn.execute(
                """INSERT OR REPLACE INTO post_analytics
                   (platform, post_id, likes, comments, shares, saves, views, reach, engagement_rate)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (platform, post_id,
                 metrics.get("likes", 0), metrics.get("comments", 0),
                 metrics.get("shares", 0), metrics.get("saves", 0),
                 metrics.get("views", 0), metrics.get("reach", 0),
                 metrics.get("engagement_rate", 0)),
            )
            return c.lastrowid

    def read(self, post_id: str) -> List[Dict]:
        with self.get_db_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM post_analytics WHERE post_id = ? ORDER BY collected_at DESC", (post_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def update(self, record_id: int, **kwargs) -> bool:
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        with self.get_db_connection() as conn:
            conn.execute(f"UPDATE post_analytics SET {fields} WHERE id = ?", [*kwargs.values(), record_id])
            return True

    def delete(self, record_id: int) -> bool:
        with self.get_db_connection() as conn:
            conn.execute("DELETE FROM post_analytics WHERE id = ?", (record_id,))
            return True


def collect_analytics(manager: SocialManager, post_ids: Dict[str, List[str]]):
    """Collect analytics for all given post IDs across platforms."""
    db = AnalyticsDB()
    for platform, ids in post_ids.items():
        connector = manager.get_connector(platform)
        if not connector:
            continue
        for pid in ids:
            data = connector.get_analytics(pid)
            db.create(platform, pid, likes=data.likes, comments=data.comments,
                      shares=data.shares, views=data.views, engagement_rate=data.engagement_rate)
            logger.info("Collected analytics: %s/%s", platform, pid)
