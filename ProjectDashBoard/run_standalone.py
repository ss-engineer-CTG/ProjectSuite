"""
スタンドアロンモードでDashboardを実行するためのエントリーポイント
PyInstaller環境との互換性を確保
"""
import sys
import os
import logging
import traceback

# ログ設定
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(log_dir, 'dashboard_standalone.log'),
    filemode='w'
)
logger = logging.getLogger("dashboard_standalone")

def main():
    """スタンドアロンモードでダッシュボードを実行"""
    try:
        logger.info("スタンドアロンモードでDashboardを起動中")
        
        # PyInstaller環境かを検出
        if getattr(sys, 'frozen', False):
            logger.info(f"PyInstaller環境を検出: {sys._MEIPASS}")
            # 必要なパスを追加
            dashboard_path = os.path.join(sys._MEIPASS, "ProjectDashBoard")
            if dashboard_path not in sys.path:
                logger.info(f"パスを追加: {dashboard_path}")
                sys.path.insert(0, dashboard_path)
        
        # Dashアプリをインポート
        import ProjectDashBoard.app as dashboard
        
        # サーバー起動（デバッグモード無効）
        dashboard.app.run_server(
            debug=False, 
            port=8050, 
            host='127.0.0.1',
            use_reloader=False  # PyInstaller環境で重要
        )
        
    except Exception as e:
        logger.error(f"起動エラー: {e}\n{traceback.format_exc()}")
        print(f"Dashboard起動失敗: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()