"""
base.py — Re-exports BaseDatabase from database.py for backward compatibility.
"""
from db.database import BaseDatabase

__all__ = ["BaseDatabase"]
