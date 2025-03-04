# transaction_context.py

import sqlite3
from contextlib import contextmanager
from typing import Optional, List
import logging
from CreateProjectList.utils.log_manager import LogManager

class TransactionContext:
    """データベーストランザクション管理クラス"""
    
    def __init__(self, connection: sqlite3.Connection):
        """
        初期化
        
        Args:
            connection: SQLite接続オブジェクト
        """
        self.logger = LogManager().get_logger(__name__)
        self.connection = connection
        self._savepoints: List[str] = []
    
    @contextmanager
    def transaction(self, name: Optional[str] = None):
        """
        トランザクションコンテキスト
        
        Args:
            name: セーブポイント名（ネストトランザクション用）
        """
        if name and self._savepoints:
            # ネストトランザクション（セーブポイント）
            savepoint = f"SP_{name}_{len(self._savepoints)}"
            try:
                self.connection.execute(f"SAVEPOINT {savepoint}")
                self._savepoints.append(savepoint)
                yield
                self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
                self._savepoints.remove(savepoint)
            except Exception as e:
                self.logger.error(f"Transaction error at savepoint {savepoint}: {str(e)}")
                if savepoint in self._savepoints:
                    self.connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
                    self._savepoints.remove(savepoint)
                raise
        else:
            # 通常トランザクション
            try:
                self.connection.execute("BEGIN TRANSACTION")
                yield
                self.connection.commit()
            except Exception as e:
                logging.error(f"Transaction error: {str(e)}")
                self.connection.rollback()
                raise
    
    @contextmanager
    def savepoint(self, name: str):
        """
        セーブポイントコンテキスト
        
        Args:
            name: セーブポイント名
        """
        with self.transaction(name):
            yield
    
    def commit(self):
        """コミット"""
        if not self._savepoints:
            try:
                self.connection.commit()
            except sqlite3.Error as e:
                logging.error(f"Commit error: {str(e)}")
                raise
    
    def rollback(self):
        """ロールバック"""
        if not self._savepoints:
            try:
                self.connection.rollback()
            except sqlite3.Error as e:
                logging.error(f"Rollback error: {str(e)}")
                raise
        
    def __enter__(self):
        """コンテキストマネージャのエントリーポイント"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャの終了処理"""
        if exc_type is None:
            self.commit()
        else:
            self.rollback()