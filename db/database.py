"""
database.py
===========
Base database class with SQLite (dev) and PostgreSQL (prod) support.

All database classes should inherit from BaseDatabase.
"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

import sqlite3


class BaseDatabase(ABC):
    """Abstract base for all database access classes."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None

    @abstractmethod
    def create(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def read(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def update(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def delete(self, *args, **kwargs) -> Any:
        pass

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            self.conn.close()
            self.conn = None

    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()