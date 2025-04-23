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
            # 設定ファイルの処理を変更
            if config_file:
                self.config_file = Path(config_file)
            else:
                # PathRegistryから設定ファイルパスを優先的に取得
                registry_path = registry.get_path("CPL_CONFIG_PATH")
                if registry_path:
                    self.config_file = Path(registry_path)
                    self.logger.info(f"PathRegistryから設定ファイルパスを取得: {registry_path}")
                else:
                    # フォールバック: ユーザーのドキュメントフォルダにある設定ファイル
                    user_config = Path.home() / "Documents" / "ProjectSuite" / "CreateProjectList" / "config" / "config.json"
                    if user_config.exists():
                        self.config_file = user_config
                        self.logger.info(f"ユーザードキュメントから設定ファイルパスを取得: {user_config}")
                    else:
                        # 最終フォールバック: パッケージ内の設定ファイル
                        self.config_file = self.package_root / "config" / "config.json"
                        self.logger.info(f"パッケージから設定ファイルパスを取得: {self.config_file}")
            
            # 設定ファイルのパスを準備
            if not self.config_file.parent.exists():
                try:
                    self.config_file.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    # 書き込み権限がない場合、ユーザードキュメントフォルダに変更
                    self.logger.warning(f"設定ディレクトリの作成に失敗: {e}")
                    user_config = Path.home() / "Documents" / "ProjectSuite" / "CreateProjectList" / "config" / "config.json"
                    user_config.parent.mkdir(parents=True, exist_ok=True)
                    self.config_file = user_config
                    self.logger.info(f"設定ファイルをユーザードキュメントに変更: {user_config}")
            
            # オリジナルの処理を呼び出し
            try:
                self.logger = LogManager().get_logger(__name__)
                
                # PathRegistryを初期化
                try:
                    from PathRegistry import PathRegistry
                    self.registry = PathRegistry.get_instance()
                except ImportError:
                    self.registry = None
                    self.logger.warning("PathRegistryを読み込めませんでした")
                
                # パッケージのルートディレクトリを取得
                self.package_root = Path(__file__).parent.parent
                
                # デフォルトの設定ファイルパス
                self.default_config_path = self.package_root / "config" / "config.json"
                
                # 親アプリケーションの設定
                self.parent_config = None
                
                # 設定ファイルがない場合はデフォルト設定で作成
                if not self.config_file.exists():
                    self.config = self._load_default_config()
                    self.save_config()
                    self.logger.info(f"新しい設定ファイルを作成: {self.config_file}")
                else:
                    self.config = self._load_default_config()
                    
                self.load_config()
                self.logger.info("ConfigManager initialized")
            except Exception as init_error:
                self.logger.error(f"初期化エラー: {init_error}")
                logging.error(f"初期化エラー: {init_error}")
                # 基本的なオブジェクト初期化
                self.config = {}
                self.config_file = Path()
            
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
            if hasattr(self, 'config_file') and self.config_file:
                registry.register_path("CPL_CONFIG_PATH", str(self.config_file))
            
            # 一時ディレクトリの設定
            temp_dir = registry.get_path("CPL_TEMP_DIR", self.config.get('temp_dir', ''))
            if temp_dir:
                self.config['temp_dir'] = temp_dir
            else:
                # 一時ディレクトリがない場合は作成
                default_temp = Path.home() / "Documents" / "ProjectSuite" / "CreateProjectList" / "temp"
                default_temp.mkdir(parents=True, exist_ok=True)
                self.config['temp_dir'] = str(default_temp)
            
            # レジストリに登録
            registry.register_path("CPL_TEMP_DIR", self.config.get('temp_dir', ''))
            registry.register_path("CPL_INPUT_FOLDER", self.config.get('last_input_folder', ''))
            registry.register_path("CPL_OUTPUT_FOLDER", self.config.get('last_output_folder', ''))
        
        # 初期化関数を置き換え
        ConfigManager.__init__ = patched_init
        
        # オリジナルの保存関数を保存
        original_save = ConfigManager.save_config
        
        def patched_save_config(self) -> None:
            """設定ファイルの保存処理を修正"""
            try:
                # バックアップの作成
                if self.config_file.exists():
                    try:
                        backup_path = self.config_file.with_suffix('.bak')
                        shutil.copy2(self.config_file, backup_path)
                        self.logger.info(f"設定ファイルのバックアップを作成: {backup_path}")
                    except Exception as backup_error:
                        self.logger.warning(f"バックアップ作成エラー: {backup_error}")

                # 設定ディレクトリの作成
                try:
                    self.config_file.parent.mkdir(parents=True, exist_ok=True)
                except Exception as dir_error:
                    # 権限エラーの場合はユーザードキュメントを使用
                    self.logger.warning(f"設定ディレクトリ作成エラー: {dir_error}")
                    user_config = Path.home() / "Documents" / "ProjectSuite" / "CreateProjectList" / "config" / "config.json"
                    user_config.parent.mkdir(parents=True, exist_ok=True)
                    self.config_file = user_config
                    self.logger.info(f"設定ファイルをユーザードキュメントに変更: {user_config}")
                
                # パスの正規化
                if self.config.get('last_input_folder'):
                    self.config['last_input_folder'] = str(Path(self.config['last_input_folder']).resolve())
                if self.config.get('last_output_folder'):
                    self.config['last_output_folder'] = str(Path(self.config['last_output_folder']).resolve())
                
                # 最終更新日時の更新
                from datetime import datetime
                self.config['last_update'] = datetime.now().isoformat()
                
                # 設定の保存
                try:
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(self.config, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"設定を保存: {self.config_file}")
                    
                    # レジストリにパスを登録
                    registry = PathRegistry.get_instance()
                    registry.register_path("CPL_CONFIG_PATH", str(self.config_file))
                except Exception as save_error:
                    self.logger.error(f"設定ファイル保存エラー: {save_error}")
                    # ユーザードキュメントにフォールバック
                    try:
                        user_config = Path.home() / "Documents" / "ProjectSuite" / "CreateProjectList" / "config" / "config.json"
                        user_config.parent.mkdir(parents=True, exist_ok=True)
                        with open(user_config, 'w', encoding='utf-8') as f:
                            import json
                            json.dump(self.config, f, ensure_ascii=False, indent=2)
                        self.logger.info(f"設定をユーザードキュメントに保存: {user_config}")
                        self.config_file = user_config
                        
                        # レジストリにパスを登録
                        registry = PathRegistry.get_instance()
                        registry.register_path("CPL_CONFIG_PATH", str(self.config_file))
                    except Exception as fallback_error:
                        self.logger.error(f"フォールバック保存エラー: {fallback_error}")
                        raise
                
                # バックアップの削除
                try:
                    if 'backup_path' in locals() and backup_path.exists():
                        backup_path.unlink()
                except Exception as backup_delete_error:
                    self.logger.warning(f"バックアップ削除エラー: {backup_delete_error}")
                    
            except Exception as e:
                self.logger.error(f"設定保存エラー: {e}")
                raise
        
        # 保存関数を置き換え
        ConfigManager.save_config = patched_save_config
        
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
        
        # LogManagerを修正して、ユーザードキュメントのログディレクトリを使用
        from CreateProjectList.utils.log_manager import LogManager
        
        original_setup_logging = LogManager.setup_logging
        
        def patched_setup_logging(self, level: int = logging.INFO) -> None:
            """ログ設定をユーザードキュメントフォルダに変更"""
            try:
                # ユーザードキュメントにログディレクトリを設定
                user_log_dir = Path.home() / "Documents" / "ProjectSuite" / "logs"
                user_log_file = user_log_dir / "document_processor.log"
                
                # ログディレクトリの保存
                self.log_dir = user_log_dir
                self.log_file = user_log_file
                
                # 元の処理を継続
                original_setup_logging(self, level)
                
            except Exception as e:
                # エラーが発生した場合は元の処理を呼び出す
                print(f"ユーザーログディレクトリの設定に失敗: {e}")
                original_setup_logging(self, level)
        
        # メソッドを置き換え
        LogManager.setup_logging = patched_setup_logging
        
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