"""
設定アダプター - CreateProjectList の設定とPathRegistryを連携
"""
import sys
import os
import json  # 追加: jsonモジュールのインポート
from pathlib import Path
import logging
import shutil
import traceback

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
    
    from PathRegistry import PathRegistry
except ImportError as e:
    # フォールバックとして相対的な検索
    import importlib.util
    
    logging.error(f"PathRegistry インポートエラー: {e}")
    
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
                
            def get_all_paths(self):
                return {}
                
            def ensure_directory(self, key):
                return None
                
            def register_path(self, key, path):
                pass

try:
    from CreateProjectList.utils.path_constants import PathKeys
except ImportError:
    # パス定数のダミー定義
    class PathKeys:
        USER_DATA_DIR = "USER_DATA_DIR"
        CPL_DIR = "CPL_DIR"
        CPL_CONFIG_DIR = "CPL_CONFIG_DIR"
        CPL_CONFIG_PATH = "CPL_CONFIG_PATH"
        CPL_TEMP_DIR = "CPL_TEMP_DIR"
        CPL_TEMPLATES_DIR = "CPL_TEMPLATES_DIR"
        CPL_CACHE_DIR = "CPL_CACHE_DIR"
        CPL_INPUT_FOLDER = "CPL_INPUT_FOLDER"
        CPL_OUTPUT_FOLDER = "CPL_OUTPUT_FOLDER"
        PM_DB_PATH = "DB_PATH"
        PM_TEMPLATES_DIR = "TEMPLATES_DIR"
        PM_PROJECTS_DIR = "PROJECTS_DIR"
        LOGS_DIR = "LOGS_DIR"

# ロガー
logger = logging.getLogger(__name__)

def adapt_create_project_list_config():
    """
    CreateProjectListの設定をPathRegistryと連携
    """
    try:
        registry = PathRegistry.get_instance()
        
        # アプリケーションのルートディレクトリ
        app_root = registry.get_path("ROOT")
        if not app_root:
            app_root = str(Path(__file__).parent.parent)
            registry.register_path("ROOT", app_root)
            
        # ユーザードキュメントディレクトリ
        user_docs = registry.get_path(PathKeys.USER_DATA_DIR)
        if not user_docs:
            user_docs = str(Path.home() / "Documents" / "ProjectSuite")
            registry.register_path(PathKeys.USER_DATA_DIR, user_docs)
        
        # CreateProjectList関連のパスを登録
        cpl_paths = {
            PathKeys.CPL_DIR: os.path.join(user_docs, "CreateProjectList"),
            PathKeys.CPL_CONFIG_DIR: os.path.join(user_docs, "CreateProjectList", "config"),
            PathKeys.CPL_TEMP_DIR: os.path.join(user_docs, "CreateProjectList", "temp"),
            PathKeys.CPL_TEMPLATES_DIR: os.path.join(user_docs, "CreateProjectList", "templates"),
            PathKeys.CPL_CACHE_DIR: os.path.join(user_docs, "CreateProjectList", "cache"),
        }
        
        # パスの登録
        for key, path in cpl_paths.items():
            registry.register_path(key, path)
            os.makedirs(path, exist_ok=True)
        
        # 必要なパスをProjectManagerから取得
        db_path = registry.get_path(PathKeys.PM_DB_PATH)
        templates_dir = registry.get_path(PathKeys.PM_TEMPLATES_DIR) 
        projects_dir = registry.get_path(PathKeys.PM_PROJECTS_DIR)
        
        # 追加: ProjectManagerのテンプレートディレクトリを入力フォルダとして設定
        if templates_dir:
            registry.register_path(PathKeys.CPL_INPUT_FOLDER, templates_dir)
            logger.info(f"入力フォルダをProjectManagerのテンプレートディレクトリに設定: {templates_dir}")
        else:
            # ProjectManagerのテンプレートディレクトリが未設定の場合は明示的に設定
            pm_templates_dir = os.path.join(user_docs, "ProjectManager", "data", "templates")
            registry.register_path(PathKeys.PM_TEMPLATES_DIR, pm_templates_dir)
            registry.register_path(PathKeys.CPL_INPUT_FOLDER, pm_templates_dir)
            logger.info(f"入力フォルダを明示的に設定: {pm_templates_dir}")
        
        # ConfigManagerモンキーパッチを適用
        _apply_config_manager_patch()
        
        return registry

def _apply_config_manager_patch():
    """ConfigManager クラスにモンキーパッチを適用"""
    try:
        from CreateProjectList.utils.config_manager import ConfigManager
        from CreateProjectList.utils.log_manager import LogManager
        
        # オリジナルの初期化関数を保存
        original_init = ConfigManager.__init__
        
        def patched_init(self, config_file=None):
            """パス解決をレジストリ経由に切り替えつつ、元の処理も実行"""
            # オリジナルの初期化を呼び出し
            original_init(self, config_file)
            
            try:
                # PathRegistryからの取得を試みる
                if hasattr(self, 'registry') and self.registry:
                    # DB_PATHをレジストリから取得
                    db_path = self.registry.get_path(PathKeys.PM_DB_PATH)
                    if db_path and not self.config.get('db_path'):
                        self.config['db_path'] = db_path
                        self.logger.info(f"PathRegistryからDBパスを取得: {db_path}")
                    
                    # テンプレートディレクトリをレジストリから取得
                    template_dir = self.registry.get_path(PathKeys.PM_TEMPLATES_DIR
                    if template_dir and not self.config.get('last_input_folder'):
                        self.config['last_input_folder'] = template_dir
                        self.logger.info(f"PathRegistryからテンプレートディレクトリを取得: {template_dir}")
                    
                    # プロジェクトディレクトリをレジストリから取得
                    projects_dir = self.registry.get_path(PathKeys.PM_PROJECTS_DIR)
                    if projects_dir and not self.config.get('last_output_folder'):
                        self.config['last_output_folder'] = projects_dir
                        self.logger.info(f"PathRegistryからプロジェクトディレクトリを取得: {projects_dir}")
                    
                    # 一時ディレクトリをレジストリから取得
                    temp_dir = self.registry.get_path(PathKeys.CPL_TEMP_DIR)
                    if temp_dir:
                        self.config['temp_dir'] = temp_dir
                        self.logger.info(f"PathRegistryから一時ディレクトリを取得: {temp_dir}")
                    
                    # 変更があれば保存
                    self.save_config()
            except Exception as e:
                self.logger.warning(f"設定の更新でエラー: {e}")
        
        # 初期化関数を置き換え
        ConfigManager.__init__ = patched_init
        
        logger.info("ConfigManager パッチを適用しました")
        
    except ImportError as e:
        logger.error(f"ConfigManager パッチの適用に失敗: インポートエラー {e}")
    except Exception as e:
        logger.error(f"ConfigManager パッチの適用でエラー: {e}")
        logger.error(traceback.format_exc())

def _ensure_default_config():
    """デフォルト設定ファイルを確保"""
    try:
        # ユーザーディレクトリの設定ファイルのパス
        user_docs = Path.home() / "Documents" / "ProjectSuite"
        config_path = user_docs / "CreateProjectList" / "config" / "config.json"
        
        # 設定ファイルが存在しない場合のみコピー
        if not config_path.exists():
            # ディレクトリ作成
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # パッケージ内のデフォルト設定ファイルを探す
            package_root = Path(__file__).parent
            default_config = package_root / "config" / "config.json"
            
            if default_config.exists():
                shutil.copy2(default_config, config_path)
                logger.info(f"デフォルト設定ファイルをコピー: {default_config} -> {config_path}")
            else:
                # デフォルト設定ファイルを探す別の場所
                alt_config = package_root / "CreateProjectList" / "config" / "config.json"
                if alt_config.exists():
                    shutil.copy2(alt_config, config_path)
                    logger.info(f"代替デフォルト設定ファイルをコピー: {alt_config} -> {config_path}")
                else:
                    # デフォルト設定を新規作成
                    import json
                    from datetime import datetime
                    
                    default_config_data = {
                        "db_path": "",
                        "last_input_folder": "",
                        "last_output_folder": "",
                        "replacement_rules": [
                            {"search": "#案件名#", "replace": "project_name"},
                            {"search": "#作成日#", "replace": "start_date"},
                            {"search": "#工場#", "replace": "factory"},
                            {"search": "#工程#", "replace": "process"},
                            {"search": "#ライン#", "replace": "line"},
                            {"search": "#作成者#", "replace": "manager"},
                            {"search": "#確認者#", "replace": "reviewer"},
                            {"search": "#承認者#", "replace": "approver"},
                            {"search": "#事業部#", "replace": "division"}
                        ],
                        "last_update": datetime.now().isoformat(),
                        "temp_dir": ""
                    }
                    
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(default_config_data, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"デフォルト設定ファイルを作成: {config_path}")
            
            registry = PathRegistry.get_instance()
            registry.register_path(PathKeys.CPL_CONFIG_PATH, str(config_path))
            
    except Exception as e:
        logger.error(f"デフォルト設定ファイルの確保に失敗: {e}")
        logger.error(traceback.format_exc())

# 初期化時に自動適用
if __name__ != "__main__":
    try:
        # デフォルト設定を確保
        _ensure_default_config()
        
        # 設定のアダプテーション
        adapt_create_project_list_config()
        logger.info("CreateProjectList設定アダプターを自動適用しました")
    except Exception as e:
        logger.error(f"設定アダプターの自動適用に失敗: {e}")