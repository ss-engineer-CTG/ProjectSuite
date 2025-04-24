"""ファイルロック管理ユーティリティ"""

import os
import portalocker
import logging
import threading
from contextlib import contextmanager
from typing import Dict, Set
import time
from pathlib import Path

from CreateProjectList.utils.log_manager import LogManager
from CreateProjectList.utils.path_manager import PathManager

class FileLock:
    """ファイルロック管理クラス（クロスプラットフォーム対応）"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(FileLock, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初期化（シングルトンなので1回のみ実行）"""
        if self._initialized:
            return
            
        self._initialized = True
        self._locks: Dict[str, object] = {}  # ファイルオブジェクトの保持
        self._active_locks: Set[str] = set()  # アクティブなロックのパス
        self._thread_locks: Dict[str, threading.Lock] = {}  # パスごとのスレッドロック
        self.logger = LogManager().get_logger(__name__)
    
    @contextmanager
    def acquire_lock(self, file_path: str, timeout: int = 30):
        """
        ファイルロックの取得
        
        Args:
            file_path: ロック対象のファイルパス
            timeout: タイムアウト秒数
        """
        normalized_path = str(Path(file_path).resolve())
        lock_path = f"{normalized_path}.lock"
        
        # スレッドロックの取得または作成
        if normalized_path not in self._thread_locks:
            with self._lock:
                if normalized_path not in self._thread_locks:
                    self._thread_locks[normalized_path] = threading.Lock()
        
        thread_lock = self._thread_locks[normalized_path]
        
        # タイムアウト付きでロック取得を試行
        start_time = time.time()
        while True:
            if thread_lock.acquire(timeout=1):  # 1秒ごとにタイムアウトをチェック
                try:
                    # ロックファイルの作成とロック取得
                    lock_file = open(lock_path, 'wb')
                    try:
                        portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
                        self._locks[normalized_path] = lock_file
                        self._active_locks.add(normalized_path)
                        
                        try:
                            yield
                        finally:
                            self._release_lock(normalized_path)
                            
                    except (portalocker.LockException, IOError) as e:
                        lock_file.close()
                        if time.time() - start_time > timeout:
                            raise TimeoutError(f"Lock acquisition timeout for {file_path}")
                        time.sleep(1)
                        continue
                        
                finally:
                    thread_lock.release()
                break
            
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Thread lock acquisition timeout for {file_path}")
    
    def _release_lock(self, normalized_path: str):
        """
        ロックの解放
        
        Args:
            normalized_path: 解放するロックのパス
        """
        try:
            if normalized_path in self._locks:
                lock_file = self._locks[normalized_path]
                portalocker.unlock(lock_file)
                lock_file.close()
                
                lock_path = f"{normalized_path}.lock"
                try:
                    os.unlink(lock_path)
                except OSError:
                    pass
                
                del self._locks[normalized_path]
                self._active_locks.remove(normalized_path)
                
        except Exception as e:
            self.logger.error(f"Error releasing lock for {normalized_path}: {str(e)}")
    
    def is_locked(self, file_path: str) -> bool:
        """
        ファイルがロックされているか確認
        
        Args:
            file_path: 確認するファイルパス
            
        Returns:
            bool: ロックされている場合True
        """
        normalized_path = str(Path(file_path).resolve())
        return normalized_path in self._active_locks
    
    def get_lock_dir(self) -> Path:
        """
        ロックファイル用のディレクトリを取得
        
        Returns:
            Path: ロックファイル用ディレクトリ
        """
        try:
            # ユーザーディレクトリのロックフォルダを使用
            lock_dir = PathManager.get_user_directory() / "CreateProjectList" / "locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            return lock_dir
        except Exception as e:
            self.logger.error(f"ロックディレクトリの作成に失敗: {e}")
            # フォールバック: 一時ディレクトリを使用
            return Path(os.path.join(os.path.expanduser('~'), '.file_locks'))
    
    def __del__(self):
        """デストラクタ - すべてのロックを解放"""
        try:
            # アクティブなロックの一覧をコピー
            active_locks = list(self._active_locks)
            
            # すべてのロックを解放
            for path in active_locks:
                self._release_lock(path)
                
        except Exception as e:
            logging.error(f"Error during FileLock cleanup: {str(e)}")