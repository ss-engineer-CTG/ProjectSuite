"""
スタンドアロンモードでDashboardを実行するためのエントリーポイント
PyInstaller環境との互換性を確保
"""
import sys
import os
import logging
import traceback
import importlib.util
from pathlib import Path

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

def setup_environment():
    """
    実行環境のセットアップ - パスの解決と追加
    """
    # 現在のスクリプトの絶対パスを取得
    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parent.parent
    
    logger.info(f"現在のスクリプトパス: {current_script_path}")
    logger.info(f"プロジェクトルート: {project_root}")
    logger.info(f"作業ディレクトリ: {os.getcwd()}")
    
    # プロジェクトルートをパスに追加
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        logger.info(f"PYTHONPATHに追加: {project_root}")
    
    # ダッシュボードディレクトリをパスに追加
    dashboard_dir = project_root / "ProjectDashBoard"
    if str(dashboard_dir) not in sys.path:
        sys.path.insert(0, str(dashboard_dir))
        logger.info(f"PYTHONPATHに追加: {dashboard_dir}")
    
    # 環境変数のパス情報をログに出力
    logger.info(f"環境変数 PYTHONPATH: {os.environ.get('PYTHONPATH', '未設定')}")
    logger.info(f"環境変数 PMSUITE_DASHBOARD_DATA_DIR: {os.environ.get('PMSUITE_DASHBOARD_DATA_DIR', '未設定')}")
    logger.info(f"環境変数 PMSUITE_DASHBOARD_FILE: {os.environ.get('PMSUITE_DASHBOARD_FILE', '未設定')}")
    
    # PathRegistry初期化を試行
    try:
        from PathRegistry import PathRegistry
        registry = PathRegistry.get_instance()
        
        # ダッシュボードのパスを取得して表示
        dashboard_file = registry.get_path("DASHBOARD_FILE")
        if dashboard_file:
            logger.info(f"PathRegistryからダッシュボードファイルパス: {dashboard_file}")
            if Path(dashboard_file).exists():
                logger.info("ファイルは存在します")
            else:
                logger.warning("ファイルが存在しません")
    except Exception as e:
        logger.warning(f"PathRegistry初期化エラー: {e}")

def main():
    """スタンドアロンモードでダッシュボードを実行"""
    try:
        logger.info("スタンドアロンモードでDashboardを起動中")
        
        # 環境のセットアップ
        setup_environment()
        
        # PyInstaller環境かを検出
        if getattr(sys, 'frozen', False):
            logger.info(f"PyInstaller環境を検出: {sys._MEIPASS}")
            # 必要なパスを追加
            dashboard_path = os.path.join(sys._MEIPASS, "ProjectDashBoard")
            if dashboard_path not in sys.path:
                logger.info(f"パスを追加: {dashboard_path}")
                sys.path.insert(0, dashboard_path)
        
        # ★★★ 修正: 動的にモジュールを探索して読み込む ★★★
        try:
            # 直接インポート
            import ProjectDashBoard.app as dashboard
            logger.info("直接インポートに成功しました")
        except ImportError as e:
            logger.warning(f"直接インポートに失敗: {e}")
            
            # 代替方法: appモジュールをプロジェクト内で探す
            app_path = None
            for root_dir in sys.path:
                potential_path = Path(root_dir) / "ProjectDashBoard" / "app.py"
                if potential_path.exists():
                    app_path = potential_path
                    logger.info(f"app.pyが見つかりました: {app_path}")
                    break
            
            if app_path:
                # 見つかったモジュールを読み込む
                spec = importlib.util.spec_from_file_location("dashboard", app_path)
                dashboard = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(dashboard)
                logger.info("ファイルパスからモジュールを読み込みました")
            else:
                raise ImportError("ProjectDashBoard.appモジュールが見つかりません")
        
        # サーバー起動（デバッグモード無効）
        logger.info("ダッシュボードサーバーを起動します")
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