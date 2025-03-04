import os
import sys
import logging
import traceback
from pathlib import Path
from typing import Optional
from tkinter import messagebox

from ProjectManager.src.core.config import Config
from ProjectManager.src.core.database import DatabaseManager
from ProjectManager.src.ui.dashboard import DashboardGUI
from ProjectManager.src.services.task_loader import TaskLoader

def setup_logging() -> None:
    """
    ログ設定を初期化する
    
    ログファイルとコンソールの両方に出力を設定
    """
    try:
        # ログディレクトリの作成
        log_dir = os.path.dirname(Config.LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)
        
        # ログハンドラーの設定
        handlers = [
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
        
        # ログフォーマットの設定
        formatter = logging.Formatter(Config.LOG_FORMAT)
        for handler in handlers:
            handler.setFormatter(formatter)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # 既存のハンドラーをクリア
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # 新しいハンドラーを追加
        for handler in handlers:
            root_logger.addHandler(handler)
            
        logging.info("ログ設定を初期化しました")
        
    except Exception as e:
        print(f"ログ設定の初期化に失敗しました: {e}")
        raise

def initialize_app() -> Optional[DatabaseManager]:
    """
    アプリケーションの初期化処理
    
    Returns:
        Optional[DatabaseManager]: 初期化されたデータベースマネージャー。
                                 エラー時はNone
    """
    try:
        # ディレクトリ構造の作成
        Config.setup_directories()
        
        # ログ設定
        setup_logging()
        logging.info("アプリケーションを開始します")
        
        # 環境の検証
        Config.validate_environment()
        
        # データベースマネージャーの初期化とマイグレーション
        db_manager = DatabaseManager(Config.DB_PATH)
        logging.info("データベースマネージャーを初期化しました")
        
        # タスクデータの読み込み
        try:
            task_loader = TaskLoader(db_manager)
            task_loader.load_tasks()
            logging.info("タスクデータを読み込みました")
            
        except Exception as e:
            logging.error(f"データ読み込みエラー: {e}\n{traceback.format_exc()}")
            messagebox.showwarning(
                "警告",
                "データの読み込み中にエラーが発生しました。\n"
                "アプリケーションは起動しますが、データが正しく反映されていない可能性があります。"
            )
        
        return db_manager
        
    except FileNotFoundError as e:
        error_msg = f"必要なファイルが見つかりません: {e}"
        logging.error(error_msg)
        messagebox.showerror("初期化エラー", error_msg)
    except PermissionError as e:
        error_msg = f"アクセス権限がありません: {e}"
        logging.error(error_msg)
        messagebox.showerror("初期化エラー", error_msg)
    except ValueError as e:
        error_msg = f"設定値が不正です: {e}"
        logging.error(error_msg)
        messagebox.showerror("初期化エラー", error_msg)
    except Exception as e:
        error_msg = f"予期せぬエラーが発生しました: {e}"
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        messagebox.showerror("初期化エラー", error_msg)
    
    return None

def main() -> None:
    """
    アプリケーションのメインエントリーポイント
    """
    db_manager = None
    try:
        # アプリケーションの初期化
        db_manager = initialize_app()
        if not db_manager:
            return
        
        # GUIの起動
        app = DashboardGUI(db_manager)
        
        try:
            app.run()
        except Exception as e:
            error_msg = f"GUIの実行中にエラーが発生しました: {e}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            messagebox.showerror("エラー", error_msg)
        
    except Exception as e:
        error_msg = f"アプリケーション実行中にエラーが発生しました: {e}"
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        messagebox.showerror("エラー", error_msg)
        
    finally:
        # クリーンアップ処理
        if db_manager:
            logging.info("アプリケーションを終了します")

if __name__ == "__main__":
    main()