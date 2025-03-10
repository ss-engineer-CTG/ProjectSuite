"""
設定アダプター - CreateProjectList の設定とPathRegistryを連携
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
        if current_dir.name == "CreateProjectList":
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

def adapt_create_project_list_config():
    """
    CreateProjectListの設定をPathRegistryと連携
    
    Returns:
        PathRegistry: PathRegistryのインスタンス
    """
    try:
        registry = PathRegistry.get_instance()
        
        from CreateProjectList.utils.config_manager import ConfigManager
        
        # オリジナルの初期化関数を保存
        original_init = ConfigManager.__init__
        
        def patched_init(self, config_file=None):
            """パス解決をレジストリ経由に切り替えつつ、元の処理も実行"""
            # オリジナルの処理を呼び出し
            original_init(self, config_file)
            
            # レジストリからDBパスを取得
            db_path = registry.get_path("DB_PATH", self.config.get('db_path', ''))
            if db_path:
                self.config['db_path'] = db_path
            
            # 入力/出力フォルダをレジストリから取得
            input_folder = registry.get_path("TEMPLATES_DIR", self.config.get('last_input_folder', ''))
            output_folder = registry.get_path("PROJECTS_DIR", self.config.get('last_output_folder', ''))
            
            if input_folder:
                self.config['last_input_folder'] = input_folder
            if output_folder:
                self.config['last_output_folder'] = output_folder
            
            # レジストリにパスを登録
            registry.register_path("CPL_CONFIG_PATH", self.config_file)
            registry.register_path("CPL_TEMP_DIR", self.config.get('temp_dir', ''))
            registry.register_path("CPL_INPUT_FOLDER", self.config.get('last_input_folder', ''))
            registry.register_path("CPL_OUTPUT_FOLDER", self.config.get('last_output_folder', ''))
        
        # 初期化関数を置き換え
        ConfigManager.__init__ = patched_init
        
        # path_managerのアダプター追加
        from CreateProjectList.utils.path_manager import PathManager
        
        # オリジナルのメソッドをバックアップ
        original_normalize_path = PathManager.normalize_path
        
        def patched_normalize_path(path: str) -> str:
            """
            レジストリを使用したパス正規化
            """
            # まずレジストリでパスキーを探す
            registry_key = None
            for key, value in registry.get_all_paths().items():
                if str(value) == str(path):
                    registry_key = key
                    break
            
            # レジストリキーが見つかった場合
            if registry_key:
                resolved_path = registry.get_path(registry_key)
                if resolved_path and Path(resolved_path).exists():
                    return resolved_path
            
            # 元の実装を使用
            return original_normalize_path(path)
        
        # メソッドを置き換え
        PathManager.normalize_path = staticmethod(patched_normalize_path)
        
        logger.info("CreateProjectList設定アダプターを適用しました")
        
        return registry
        
    except Exception as e:
        logger.error(f"CreateProjectList設定アダプターエラー: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# 初期化時に自動適用（オプション）
if __name__ != "__main__":
    try:
        adapt_create_project_list_config()
        logger.info("CreateProjectList設定アダプターを自動適用しました")
    except Exception as e:
        logger.error(f"設定アダプターの自動適用に失敗: {e}")