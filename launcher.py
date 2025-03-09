# launcher.py 改善実装
import os
import sys
import logging
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

# パッケージング時のパス解決
if getattr(sys, 'frozen', False):
    APP_ROOT = Path(sys._MEIPASS)
else:
    APP_ROOT = Path(__file__).parent

# ユーザーデータディレクトリを設定
USER_DATA_DIR = Path(os.environ.get("APPDATA", ".")) / "ProjectManagerSuite"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ログディレクトリの設定
log_dir = USER_DATA_DIR / "logs"
log_dir.mkdir(exist_ok=True)

# デバッグログの初期化
debug_log_path = log_dir / "startup_debug.log"

def setup_logging():
    """詳細なログ設定を初期化"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=str(log_dir / "app.log"),
        filemode='w'
    )
    return logging.getLogger("launcher")

# メイン関数
def main():
    # 詳細なデバッグログを開始
    with open(debug_log_path, "w", encoding="utf-8") as debug_file:
        debug_file.write("=== アプリケーション起動診断 ===\n")
        debug_file.write(f"日時: {logging.Formatter('%(asctime)s').format(logging.LogRecord('', 0, '', 0, '', (), None))}\n")
        debug_file.write(f"Python: {sys.version}\n")
        debug_file.write(f"実行パス: {sys.executable}\n")
        debug_file.write(f"APP_ROOT: {APP_ROOT}\n")
        debug_file.write(f"作業ディレクトリ: {os.getcwd()}\n")
        debug_file.write(f"sys.path: {sys.path}\n")
        
        try:
            # ロギングを初期化
            logger = setup_logging()
            debug_file.write("ロギングを初期化しました\n")
            
            # モジュールをインポート
            debug_file.write("モジュールのインポートを開始...\n")
            from ProjectManager.src.main import main as pm_main
            debug_file.write("ProjectManager.src.main をインポートしました\n")
            
            # アプリケーション起動
            debug_file.write("メイン関数を実行します\n")
            return pm_main()
            
        except Exception as e:
            error_details = traceback.format_exc()
            debug_file.write(f"起動エラー: {e}\n")
            debug_file.write(error_details)
            
            # GUIでエラーを表示
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "ProjectManagerSuite 起動エラー", 
                    f"アプリケーションの起動中にエラーが発生しました:\n\n{str(e)}\n\n"
                    f"詳細なエラー情報は次の場所に保存されています:\n{debug_log_path}"
                )
            except Exception as gui_error:
                debug_file.write(f"GUI表示エラー: {gui_error}\n")
            
            return 1

if __name__ == "__main__":
    sys.exit(main())