"""
logging_utils.py

NOTE:
    >>> This is a specialised module for handling errors and logging them as well as tracing them back.
        If needed storing them in a db and rotate them per 14 days or exceeds 10 MB space, which one 
        comes first.
    >>> We are using sqlite3 for the logging purposes, we might needed to shift this to online while shifting.
WARNING:
    >>> Do not delete this or try to edit this file because it might cause other modules to work abnormally. 

"""
from datetime import datetime
from sqlite3 import Cursor
import logging
import sys
import logging
import warnings
import traceback
from dotenv import dotenv_values
from pathlib import Path
from core.paths import DATA_DIR
import sqlite3

 

class SqlliteHandler(logging.Handler):
    __slots__ = ["max_rows","db_path","retention_days","connection"]
    def __init__(
        self, 
        db_path: Path | str = None,
        max_rows:int=10000,
        retention_days:int=30):
        super().__init__()
        self.max_rows = max_rows
        self.db_path = db_path
        self.retention_days = retention_days
        if not self.db_path:
            self.db_path : Path = DATA_DIR/"logging/logs.db"
        self.connection = sqlite3.connect(self.db_path,check_same_thread=False)
        self._create_table()
    
    def _create_table(self):
        self.connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS ERROR_LOGS
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    level TEXT,
                    module TEXT,
                    message TEXT,
                    trace TEXT
                )
            '''
        )

    def emit(self,record):
        self.connection.execute(
            '''
            INSERT INTO ERROR_LOGS (timestamp,level,module,message,trace)
            VALUES(?,?,?,?,?)
            ''',(
            datetime.utcnow().isoformat(),
            record.levelname,
            record.module,
            record.getMessage(),
            getattr(record,"exc_text",None))
        )
        self.connection.commit()
    
    def _rotate(self):
        # by age 
        self.connection.execute(f'''
                DELETE FROM ERROR_LOGS
                WHERE timestamp < datetime('now', '-{self.retention_days} days')
        ''')
        self.connection.commit()


class AppError:
    __slots__ = []
    def __init__(self):
        pass
