"""
設定アダプター - ProjectManager の設定とPathRegistryを連携
"""
import sys
import os
from pathlib import Path
import logging

# パスレジストリをインポート
try:
    # まずSystemPathで試す
    if getattr(sys, 'frozen', False):
        sys.path.insert(0, str(Path(sys._MEIPASS).parent))
    else:
        # 開発環境では相対パスを探索
        current_dir = Path(__file__).parent
        parent_dir = current_dir.parent
        if current_dir.name == "ProjectManager":
            sys.path.insert(0, str(parent_dir))
        else:
            # アプリ内部のモジュールの場合
            sys.path.insert(0, str(parent_dir.parent))
    
    from PathRegistry import PathRegistry, get_path, ensure_dir
except ImportError as e:
    # フォールバックとして相対的な検索
    import importlib.util
    import traceback
    
    logging.error(f"PathRegistry インポートエラー: {e}")
    logging.error(traceback.format_exc())
    
    # パスレジストリを検索して動的にインポート
    registry_paths = [
        Path(__file__).parent / "PathRegistry.py",
        Path(__file__).parent.parent / "PathRegistry.py",
        Path(__file__).parent.parent.parent / "PathRegistry.py"
    ]
    
    for path in registry_paths:
        if path.exists():
            try:
                spec = importlib.util.spec_from_file_location("PathRegistry", path)
                PathRegistry_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(PathRegistry_module)
                PathRegistry = PathRegistry_module.PathRegistry
                get_path = PathRegistry_module.get_path
                ensure_dir = PathRegistry_module.ensure_dir
                break
            except Exception as err:
                logging.error(f"PathRegistry動的読込エラー {path}: {err}")
    else:
        # インポートできない場合はダミーのPathRegistryを定義
        class PathRegistry:
            @classmethod
            def get_instance(cls):
                return cls()
                
            def get_path(self, key, default=None):
                return default
                
            def ensure_directory(self, key):
                return None
        
        def get_path(key, default=None):
            return default
            
        def ensure_dir(key):
            return None

# ロガー
logger = logging.getLogger(__name__)

def adapt_project_manager_config():
    """
    ProjectManagerの設定をPathRegistryと連携
    
    Returns:
        PathRegistry: PathRegistryのインスタンス
    """
    try:
        registry = PathRegistry.get_instance()
        
        # ProjectManagerの設定とパスレジストリを連携
        from ProjectManager.src.core.config import Config
        
        # レジストリにProjectManagerの設定を登録
        registry.register_path("PM_DATA_DIR", Config.DATA_DIR)
        registry.register_path("PM_MASTER_DIR", Config.MASTER_DIR)
        registry.register_path("PM_DB_PATH", Config.DB_PATH)
        
        # 設定クラスを上書きするのではなく、必要なパスだけをレジストリと連携
        original_setup = Config.setup_directories
        
        def patched_setup_directories():
            """パス解決をレジストリ経由に切り替えつつ、元の処理も実行"""
            # オリジナルの処理を呼び出し
            original_setup()
            
            # 追加: レジストリにパスを登録
            registry.register_path("PM_OUTPUT_BASE_DIR", Config.OUTPUT_BASE_DIR)
            registry.register_path("PM_DASHBOARD_EXPORT_DIR", Config.DASHBOARD_EXPORT_DIR)
            registry.register_path("PM_DASHBOARD_EXPORT_FILE", Config.DASHBOARD_EXPORT_FILE)
            registry.register_path("PM_PROJECTS_EXPORT_FILE", Config.PROJECTS_EXPORT_FILE)
            
            # 環境変数にも登録（他アプリからのアクセス用）
            os.environ["PMSUITE_DASHBOARD_FILE"] = str(Config.DASHBOARD_EXPORT_FILE)
            os.environ["PMSUITE_DASHBOARD_DATA_DIR"] = str(Config.DASHBOARD_EXPORT_DIR)
            os.environ["PMSUITE_DB_PATH"] = str(Config.DB_PATH)
        
        # セットアップ関数を置き換え
        Config.setup_directories = patched_setup_directories
        
        # 検証
        logger.info(f"ProjectManager設定アダプター適用: {Config.DB_PATH}")
        
        return registry
        
    except Exception as e:
        logger.error(f"ProjectManager設定アダプターエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# DashboardConnectorのアダプター
def adapt_dashboard_connector():
    """
    dashboard_connectorのパス解決を改善
    
    Returns:
        PathRegistry: PathRegistryのインスタンス
    """
    try:
        registry = PathRegistry.get_instance()
        
        from ProjectManager.src.integration.dashboard_connector import DashboardConnector
        
        # オリジナルのメソッドをバックアップ
        original_get_dashboard_path = DashboardConnector._get_dashboard_path
        
        def patched_get_dashboard_path(self) -> Path:
            """レジストリを使用したダッシュボードパス解決"""
            try:
                # レジストリからパスを取得
                dashboard_path = registry.get_path("DASHBOARD_FILE")
                if dashboard_path:
                    dashboard_path_obj = Path(dashboard_path)
                    if dashboard_path_obj.exists() or dashboard_path_obj.parent.exists():
                        return dashboard_path_obj
                
                # 元の実装を使用
                return original_get_dashboard_path(self)
                
            except Exception as e:
                logger.error(f"ダッシュボードパス解決エラー: {e}")
                # 元の実装を使用
                return original_get_dashboard_path(self)
        
        # メソッドを置き換え
        DashboardConnector._get_dashboard_path = patched_get_dashboard_path
        
        logger.info("DashboardConnectorのパス解決をPathRegistryに統合しました")
        
        return registry
        
    except Exception as e:
        logger.error(f"DashboardConnector設定アダプターエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# 初期化時に自動適用（オプション）
if __name__ != "__main__":
    try:
        adapt_project_manager_config()
        adapt_dashboard_connector()
        logger.info("ProjectManager設定アダプターを自動適用しました")
    except Exception as e:
        logger.error(f"設定アダプターの自動適用に失敗: {e}")