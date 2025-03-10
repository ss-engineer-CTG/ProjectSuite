"""
設定アダプター - ProjectDashBoardの設定とPathRegistryを連携
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
        if current_dir.name == "ProjectDashBoard":
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

def adapt_project_dashboard_config():
    """
    ProjectDashBoardの設定をPathRegistryと連携
    
    Returns:
        PathRegistry: PathRegistryのインスタンス
    """
    try:
        registry = PathRegistry.get_instance()
        
        # callbacks.pyの関数を置き換え
        from ProjectDashBoard import callbacks
        
        # オリジナルのパス解決関数をバックアップ
        original_resolve_dashboard_path = callbacks.resolve_dashboard_path
        
        # レジストリ経由でダッシュボードパスを解決
        def patched_resolve_dashboard_path():
            """レジストリを使用したダッシュボードパス解決"""
            # 環境変数を最優先
            if 'PMSUITE_DASHBOARD_FILE' in os.environ:
                dashboard_path = os.environ['PMSUITE_DASHBOARD_FILE']
                if Path(dashboard_path).exists():
                    logger.info(f"環境変数からダッシュボードパスを解決: {dashboard_path}")
                    return dashboard_path
            
            # レジストリからパスを取得（優先度高い順）
            for key in ["DASHBOARD_FILE", "PM_DASHBOARD_EXPORT_FILE"]:
                dashboard_path = registry.get_path(key)
                if dashboard_path and Path(dashboard_path).exists():
                    logger.info(f"レジストリからダッシュボードパスを解決: {dashboard_path} (key={key})")
                    return dashboard_path
            
            # レジストリからエクスポートディレクトリを取得して結合
            for key in ["EXPORTS_DIR", "PM_DASHBOARD_EXPORT_DIR"]:
                export_dir = registry.get_path(key)
                if export_dir:
                    full_path = Path(export_dir) / "dashboard.csv"
                    if full_path.exists():
                        logger.info(f"エクスポートディレクトリからダッシュボードパスを解決: {full_path}")
                        return str(full_path)
            
            # フォールバック: 元の実装を使用
            logger.warning("PathRegistry経由でダッシュボードパスを解決できず、元の実装を使用します")
            return original_resolve_dashboard_path()
        
        # 関数を置き換え
        callbacks.resolve_dashboard_path = patched_resolve_dashboard_path
        
        # グローバル変数を確実に設定
        callbacks.DASHBOARD_FILE_PATH = patched_resolve_dashboard_path()
        logger.info(f"DASHBOARD_FILE_PATH を設定: {callbacks.DASHBOARD_FILE_PATH}")
        
        # data_processing.pyのパス解決も改善
        from ProjectDashBoard import data_processing
        
        # オリジナルの関数をバックアップ
        original_load_and_process_data = data_processing.load_and_process_data
        
        def patched_load_and_process_data(dashboard_file_path: str) -> 'pd.DataFrame':
            """
            レジストリを使用したデータ処理
            """
            # ダッシュボードパスの確認・修復
            if not Path(dashboard_file_path).exists():
                # レジストリから再取得
                new_path = patched_resolve_dashboard_path()
                if new_path and new_path != dashboard_file_path:
                    logger.info(f"ダッシュボードパスを修復: {dashboard_file_path} -> {new_path}")
                    dashboard_file_path = new_path
            
            # プロジェクトデータパスの解決（予め準備）
            if Path(dashboard_file_path).exists():
                projects_file_path = str(dashboard_file_path).replace('dashboard.csv', 'projects.csv')
                registry.register_path("PROJECTS_FILE", projects_file_path)
            
            # 元の実装を使用
            return original_load_and_process_data(dashboard_file_path)
        
        # 関数を置き換え
        data_processing.load_and_process_data = patched_load_and_process_data
        
        logger.info("ProjectDashBoard設定アダプターを適用しました")
        
        return registry
        
    except Exception as e:
        logger.error(f"ProjectDashBoard設定アダプターエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# 初期化時に自動適用（オプション）
if __name__ != "__main__":
    try:
        adapt_project_dashboard_config()
        logger.info("ProjectDashBoard設定アダプターを自動適用しました")
    except Exception as e:
        logger.error(f"設定アダプターの自動適用に失敗: {e}")