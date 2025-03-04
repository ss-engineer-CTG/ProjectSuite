# db_context.py

import sqlite3
from contextlib import contextmanager
from typing import Generator
import logging
import threading
from pathlib import Path
from CreateProjectList.utils.log_manager import LogManager

class DatabaseContext:
    """データベース接続管理クラス"""
    
    def __init__(self, db_path: str):
        """
        初期化
        
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = str(Path(db_path).resolve())
        self._connection = None
        self._lock = threading.Lock()
        self._local = threading.local()
        self.logger = LogManager().get_logger(__name__)

    def test_connection(self) -> bool:
        """
        データベース接続をテスト
        
        Returns:
            bool: 接続成功時True
        """
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """
        データベース接続を取得（コンテキストマネージャー）
        
        Yields:
            sqlite3.Connection: データベース接続
        """
        try:
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            yield connection
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """
        データベース接続を取得
        
        Returns:
            sqlite3.Connection: データベース接続
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            try:
                connection = sqlite3.connect(self.db_path)
                connection.row_factory = sqlite3.Row
                self._local.connection = connection
            except sqlite3.Error as e:
                logging.error(f"Database connection error: {str(e)}")
                raise
        return self._local.connection
    
    def close(self) -> None:
        """接続を閉じる"""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            try:
                self._local.connection.close()
                self._local.connection = None
            except sqlite3.Error as e:
                logging.error(f"Database close error: {str(e)}")
                raise