"""設定管理クラス"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import os
import shutil
from datetime import datetime
import tempfile
import traceback
from CreateProjectList.utils.path_manager import PathManager
from CreateProjectList.utils.log_manager import LogManager
from CreateProjectList.utils.path_constants import PathKeys

class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初期化
        
        Args:
            config_file: 設定ファイルのパス（省略時はデフォルトパス）
        """
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
        
        # 設定ファイルのパス
        if config_file:
            self.config_file = Path(config_file)
        else:
            # PathRegistryから設定ファイルパスを優先的に取得
            if self.registry:
                registry_path = self.registry.get_path(PathKeys.CPL_CONFIG_PATH)
                if registry_path:
                    self.config_file = Path(registry_path)
                    self.logger.info(f"PathRegistryから設定ファイルパスを取得: {registry_path}")
                else:
                    # ユーザードキュメントフォルダにある設定ファイル
                    user_config = self._get_user_config_path()
                    if user_config.exists():
                        self.config_file = user_config
                        self.logger.info(f"ユーザードキュメントから設定ファイルパスを取得: {user_config}")
                    else:
                        # パッケージ内の設定ファイル
                        self.config_file = self.default_config_path
                        self.logger.info(f"パッケージから設定ファイルパスを取得: {self.config_file}")
            else:
                # デフォルトパス
                self.config_file = self._get_user_config_path()
        
        # configフォルダがない場合は作成を試みる
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # 権限エラーの場合はユーザーフォルダに変更
            user_config = self._get_user_config_path()
            user_config.parent.mkdir(parents=True, exist_ok=True)
            self.config_file = user_config
            self.logger.info(f"設定ファイルをユーザードキュメントに変更: {user_config}")
        except Exception as e:
            self.logger.error(f"設定ディレクトリ作成エラー: {e}")
        
        # 設定ファイルがない場合はデフォルト設定で作成
        if not self.config_file.exists():
            self.config = self._load_default_config()
            self.save_config()
            self.logger.info(f"新しい設定ファイルを作成: {self.config_file}")
        else:
            self.config = self._load_default_config()
            
        self.load_config()
        
        # パスの初期化とレジストリへの登録
        self.initialize_config_paths()
        
        self.logger.info("ConfigManager initialized")

    def _get_user_config_path(self) -> Path:
        """ユーザー設定ファイルのパスを取得"""
        user_docs = Path.home() / "Documents" / "ProjectSuite"
        
        if self.registry:
            user_docs_from_registry = self.registry.get_path(PathKeys.USER_DATA_DIR)
            if user_docs_from_registry:
                user_docs = Path(user_docs_from_registry)
        
        return user_docs / "CreateProjectList" / "config" / "config.json"

    def initialize_config_paths(self):
        """パスを初期化してPathRegistryに登録"""
        try:
            if not self.registry:
                return
            
            # ユーザードキュメントのベースパス
            user_docs = Path.home() / "Documents" / "ProjectSuite"
            if self.registry.get_path(PathKeys.USER_DATA_DIR):
                user_docs = Path(self.registry.get_path(PathKeys.USER_DATA_DIR))
            
            # 基本パスの登録
            paths = {
                PathKeys.CPL_CONFIG_PATH: str(self.config_file),
                PathKeys.CPL_DIR: str(user_docs / "CreateProjectList"),
                PathKeys.CPL_CONFIG_DIR: str(user_docs / "CreateProjectList" / "config"),
                PathKeys.CPL_TEMP_DIR: str(user_docs / "CreateProjectList" / "temp"),
                PathKeys.CPL_TEMPLATES_DIR: str(user_docs / "CreateProjectList" / "templates"),
                PathKeys.CPL_CACHE_DIR: str(user_docs / "CreateProjectList" / "cache")
            }
            
            # パスの登録とディレクトリの作成
            for key, path in paths.items():
                self.registry.register_path(key, path)
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                
            # ConfigからPathRegistryへの同期
            if self.config.get('db_path'):
                self.registry.register_path(PathKeys.PM_DB_PATH, self.config['db_path'])
                
            if self.config.get('last_input_folder'):
                self.registry.register_path(PathKeys.CPL_INPUT_FOLDER, self.config['last_input_folder'])
                
            if self.config.get('last_output_folder'):
                self.registry.register_path(PathKeys.CPL_OUTPUT_FOLDER, self.config['last_output_folder'])
                
            # 一時ディレクトリのパスを更新
            temp_dir = self.get_temp_dir()
            self.config['temp_dir'] = temp_dir
            
        except Exception as e:
            self.logger.error(f"パス初期化エラー: {e}")

    def initialize_with_parent_config(self, parent_config: Dict[str, Any]) -> None:
        """
        親アプリケーションの設定で初期化
        
        Args:
            parent_config: 親アプリケーションの設定
        """
        try:
            self.parent_config = parent_config
            self._merge_parent_settings()
            self.logger.info("親アプリケーションの設定で初期化しました")
        except Exception as e:
            self.logger.error(f"親設定初期化エラー: {e}")
            raise
    
    def _merge_parent_settings(self) -> None:
        """親アプリケーションの設定をマージ"""
        try:
            if not self.parent_config:
                return
                
            # パス設定の更新
            if 'paths' in self.parent_config:
                self.config['last_input_folder'] = self.parent_config['paths'].get('template_dir', '')
                self.config['last_output_folder'] = self.parent_config['paths'].get('output_dir', '')
            
            # データベース設定の更新
            if 'db_path' in self.parent_config:
                self.config['db_path'] = self.parent_config['db_path']
            
            # 一時ディレクトリの設定
            temp_dir = self.get_temp_dir()
            self.config['temp_dir'] = temp_dir
            
            self.save_config()
            
        except Exception as e:
            self.logger.error(f"親設定マージエラー: {e}")
            raise
    
    def _load_default_config(self) -> dict:
        """
        デフォルト設定を取得
        
        Returns:
            dict: デフォルト設定
        """
        default_config = {
            'db_path': '',
            'last_input_folder': '',
            'last_output_folder': '',
            'replacement_rules': self._get_default_rules(),
            'last_update': datetime.now().isoformat(),
            'temp_dir': self.get_temp_dir()
        }
        self.logger.debug(f"デフォルト設定を作成: {default_config}")
        return default_config
    
    def _get_default_rules(self) -> List[Dict[str, str]]:
        """
        デフォルトの置換ルールをconfig.jsonから読み込む
        
        Returns:
            List[Dict[str, str]]: デフォルト置換ルール
        """
        try:
            if self.default_config_path.exists():
                with open(self.default_config_path, 'r', encoding='utf-8') as f:
                    default_config = json.load(f)
                    if 'replacement_rules' in default_config:
                        self.logger.debug(f"デフォルトルールを読み込み: {self.default_config_path}")
                        return default_config['replacement_rules']
            
            # デフォルトconfig.jsonが存在しない場合のフォールバック
            self.logger.warning(f"デフォルト設定ファイルが見つかりません: {self.default_config_path}")
            return [
                {"search": "#案件名#", "replace": "project_name"},
                {"search": "#作成日#", "replace": "start_date"},
                {"search": "#工場#", "replace": "factory"},
                {"search": "#工程#", "replace": "process"},
                {"search": "#ライン#", "replace": "line"},
                {"search": "#作成者#", "replace": "manager"},
                {"search": "#確認者#", "replace": "reviewer"},
                {"search": "#承認者#", "replace": "approver"},
                {"search": "#事業部#", "replace": "division"}
            ]
        except Exception as e:
            self.logger.error(f"デフォルトルール読み込みエラー: {e}")
            return []
    
    def load_config(self) -> None:
        """設定ファイルの読み込み"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 必須キーの存在確認と追加
                    for key in self._load_default_config().keys():
                        if key not in loaded_config:
                            loaded_config[key] = self._load_default_config()[key]
                    self.config.update(loaded_config)
                self.logger.info(f"設定を読み込み: {self.config_file}")
            else:
                self.save_config()
                self.logger.info("デフォルト設定で新規作成")
        except Exception as e:
            self.logger.error(f"設定読み込みエラー: {e}")
            self.save_config()
    
    def save_config(self) -> None:
        """設定ファイルの保存"""
        try:
            # バックアップの作成
            if self.config_file.exists():
                try:
                    backup_path = self.config_file.with_suffix('.bak')
                    shutil.copy2(self.config_file, backup_path)
                    self.logger.info(f"設定ファイルのバックアップを作成: {backup_path}")
                except Exception as e:
                    self.logger.warning(f"バックアップ作成エラー: {e}")

            # 設定ディレクトリの作成
            try:
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                # 権限エラーの場合はユーザードキュメントを使用
                self.logger.warning(f"設定ディレクトリ作成エラー: {e}")
                user_config = self._get_user_config_path()
                user_config.parent.mkdir(parents=True, exist_ok=True)
                self.config_file = user_config
                self.logger.info(f"設定ファイルをユーザードキュメントに変更: {user_config}")
            
            # パスの正規化
            if self.config.get('last_input_folder'):
                self.config['last_input_folder'] = str(Path(self.config['last_input_folder']).resolve())
            if self.config.get('last_output_folder'):
                self.config['last_output_folder'] = str(Path(self.config['last_output_folder']).resolve())
            
            # 最終更新日時の更新
            self.config['last_update'] = datetime.now().isoformat()
            
            # 設定の保存
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
                self.logger.info(f"設定を保存: {self.config_file}")
                
                # レジストリにパスを登録
                if self.registry:
                    self.registry.register_path(PathKeys.CPL_CONFIG_PATH, str(self.config_file))
            except Exception as e:
                self.logger.error(f"設定保存エラー: {e}")
                # ユーザードキュメントにフォールバック
                try:
                    user_config = self._get_user_config_path()
                    user_config.parent.mkdir(parents=True, exist_ok=True)
                    with open(user_config, 'w', encoding='utf-8') as f:
                        json.dump(self.config, f, ensure_ascii=False, indent=2)
                    self.logger.info(f"設定をユーザードキュメントに保存: {user_config}")
                    self.config_file = user_config
                    
                    # レジストリにパスを登録
                    if self.registry:
                        self.registry.register_path(PathKeys.CPL_CONFIG_PATH, str(self.config_file))
                except Exception as fallback_e:
                    self.logger.error(f"フォールバック保存エラー: {fallback_e}")
                    raise
            
            # バックアップの削除
            try:
                if 'backup_path' in locals() and backup_path.exists():
                    backup_path.unlink()
            except Exception as e:
                self.logger.warning(f"バックアップ削除エラー: {e}")
                
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
            # バックアップからの復元を試行
            if 'backup_path' in locals() and backup_path.exists():
                try:
                    shutil.copy2(backup_path, self.config_file)
                    self.logger.info("バックアップから設定を復元しました")
                except Exception as restore_e:
                    self.logger.error(f"バックアップ復元エラー: {restore_e}")
            raise
    
    def validate_config(self) -> bool:
        """
        設定の妥当性を検証
        
        Returns:
            bool: 設定が有効な場合True
        """
        try:
            # 必須キーの存在確認
            required_keys = {'replacement_rules'}
            if not all(key in self.config for key in required_keys):
                self.logger.error("必須キーが不足しています")
                return False
            
            # パスの妥当性確認
            paths_to_check = [
                ('db_path', self.get_db_path()),
                ('last_input_folder', self.get_input_folder()),
                ('last_output_folder', self.get_output_folder())
            ]
            
            for key, path in paths_to_check:
                if path and not PathManager.is_valid_path(path):
                    self.logger.warning(f"不正なパス {key}: {path}")
            
            # 置換ルールの妥当性確認
            for rule in self.config['replacement_rules']:
                if not isinstance(rule, dict) or 'search' not in rule or 'replace' not in rule:
                    self.logger.error(f"不正な置換ルール: {rule}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"設定検証エラー: {e}")
            return False
    
    def get_db_path(self) -> str:
        """
        データベースパスを取得
        
        Returns:
            str: データベースファイルのパス
        """
        # PathRegistryからの取得を試みる
        if self.registry:
            db_path = self.registry.get_path(PathKeys.PM_DB_PATH)
            if db_path:
                return db_path
        
        # 親設定のパスを優先
        if self.parent_config and 'db_path' in self.parent_config:
            return self.parent_config['db_path']
        
        # 構成ファイルから取得
        return self.config.get('db_path', '')
    
    def set_db_path(self, path: str) -> None:
        """
        データベースパスを設定
        
        Args:
            path: データベースファイルのパス
        """
        try:
            normalized_path = PathManager.normalize_path(path)
            self.config['db_path'] = normalized_path
            
            # PathRegistryにも登録
            if self.registry:
                self.registry.register_path(PathKeys.PM_DB_PATH, normalized_path)
                
            self.save_config()
            self.logger.info(f"データベースパスを更新: {normalized_path}")
        except Exception as e:
            self.logger.error(f"データベースパス設定エラー: {e}")
            raise
    
    def get_input_folder(self) -> str:
        """
        入力フォルダパスを取得
        
        Returns:
            str: 入力フォルダのパス
        """
        # PathRegistryからの取得を試みる
        if self.registry:
            input_folder = self.registry.get_path(PathKeys.CPL_INPUT_FOLDER)
            if input_folder:
                return input_folder
                
            # 代替としてテンプレートディレクトリを試す
            templates_dir = self.registry.get_path(PathKeys.PM_TEMPLATES_DIR)
            if templates_dir:
                return templates_dir
        
        # 親設定のパスを優先
        if self.parent_config and 'paths' in self.parent_config:
            return self.parent_config['paths'].get('template_dir', '')
            
        # 構成ファイルから取得
        return self.config.get('last_input_folder', '')
    
    def set_input_folder(self, path: str) -> None:
        """
        入力フォルダパスを設定
        
        Args:
            path: 入力フォルダのパス
        """
        try:
            normalized_path = PathManager.normalize_path(path)
            self.config['last_input_folder'] = normalized_path
            
            # PathRegistryにも登録
            if self.registry:
                self.registry.register_path(PathKeys.CPL_INPUT_FOLDER, normalized_path)
                
            self.save_config()
            self.logger.info(f"入力フォルダを更新: {normalized_path}")
        except Exception as e:
            self.logger.error(f"入力フォルダ設定エラー: {e}")
            raise
    
    def get_output_folder(self) -> str:
        """
        出力フォルダパスを取得
        
        Returns:
            str: 出力フォルダのパス
        """
        # PathRegistryからの取得を試みる
        if self.registry:
            output_folder = self.registry.get_path(PathKeys.CPL_OUTPUT_FOLDER)
            if output_folder:
                return output_folder
                
            # 代替としてプロジェクトディレクトリを試す
            projects_dir = self.registry.get_path(PathKeys.PM_PROJECTS_DIR)
            if projects_dir:
                return projects_dir
        
        # 親設定のパスを優先
        if self.parent_config and 'paths' in self.parent_config:
            return self.parent_config['paths'].get('output_dir', '')
            
        # 構成ファイルから取得
        return self.config.get('last_output_folder', '')
    
    def set_output_folder(self, path: str) -> None:
        """
        出力フォルダパスを設定
        
        Args:
            path: 出力フォルダのパス
        """
        try:
            normalized_path = PathManager.normalize_path(path)
            self.config['last_output_folder'] = normalized_path
            
            # PathRegistryにも登録
            if self.registry:
                self.registry.register_path(PathKeys.CPL_OUTPUT_FOLDER, normalized_path)
                
            self.save_config()
            self.logger.info(f"出力フォルダを更新: {normalized_path}")
        except Exception as e:
            self.logger.error(f"出力フォルダ設定エラー: {e}")
            raise
    
    def get_temp_dir(self) -> str:
        """
        一時ディレクトリのパスを取得
        
        Returns:
            str: 一時ディレクトリのパス
        """
        # PathRegistryからの取得を試みる
        if self.registry:
            temp_dir = self.registry.get_path(PathKeys.CPL_TEMP_DIR)
            if temp_dir:
                return temp_dir
        
        # ユーザードキュメント下の一時ディレクトリをデフォルトとする
        user_docs = Path.home() / "Documents" / "ProjectSuite" / "CreateProjectList" / "temp"
        try:
            user_docs.mkdir(parents=True, exist_ok=True)
            return str(user_docs)
        except Exception as e:
            self.logger.warning(f"ユーザー一時ディレクトリ作成エラー: {e}")
            return str(Path(tempfile.gettempdir()) / "doc_processor")
    
    def get_replacement_rules(self) -> List[Dict[str, str]]:
        """
        置換ルールを取得
        
        Returns:
            List[Dict[str, str]]: 置換ルールのリスト
        """
        return self.config.get('replacement_rules', self._get_default_rules())
    
    def set_replacement_rules(self, rules: List[Dict[str, str]]) -> None:
        """
        置換ルールを設定
        
        Args:
            rules: 置換ルールのリスト
        """
        try:
            # ルールの妥当性を確認
            for rule in rules:
                if not isinstance(rule, dict) or 'search' not in rule or 'replace' not in rule:
                    raise ValueError(f"不正なルール形式: {rule}")
            
            self.config['replacement_rules'] = rules
            self.save_config()
            self.logger.info(f"置換ルールを更新: {len(rules)} 件")
        except Exception as e:
            self.logger.error(f"置換ルール設定エラー: {e}")
            raise