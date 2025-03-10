"""設定管理クラス"""

import os
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# PathRegistry をインポート
from PathRegistry import PathRegistry, get_path, ensure_dir

class Config:
    # 実行パスに関わらず動作するように設定
    if getattr(sys, 'frozen', False):
        # PyInstallerで実行ファイル化した場合
        ROOT_DIR = Path(sys._MEIPASS)
    else:
        # 通常のPython実行の場合
        ROOT_DIR = Path(__file__).parent.parent.parent
    
    # データディレクトリ
    DATA_DIR = ROOT_DIR
    
    # プロジェクトルートパスを定義（柔軟に対応）
    PROJECT_ROOT = ROOT_DIR
    
    # デフォルト値設定ファイルのパス（検索順）
    # 1. アプリケーションディレクトリ直下
    # 2. dataフォルダ内
    # 3. configフォルダ内
    # 4. ユーザーホームディレクトリ
    DEFAULT_VALUE_PATHS = [
        ROOT_DIR / 'defaults.txt',
        ROOT_DIR / 'data' / 'defaults.txt',
        ROOT_DIR / 'config' / 'defaults.txt',
        Path.home() / 'ProjectManager/defaults.txt'
    ]
    
    # マスターディレクトリ
    MASTER_DIR = DATA_DIR / 'data' / 'master'
    
    # マスタデータファイル
    MASTER_DATA_FILE = MASTER_DIR / 'factory_info.csv'
    
    # データベース設定
    DB_PATH = DATA_DIR / 'data' / 'projects.db'
    
    # マスターフォルダのパス
    MASTER_FOLDER = DATA_DIR / 'data' / 'templates' / 'project'
    
    # 出力先ベースディレクトリ
    OUTPUT_BASE_DIR = DATA_DIR / 'data' / 'projects'
    
    # ダッシュボードCSV出力設定
    DASHBOARD_EXPORT_DIR = DATA_DIR / 'data' / 'exports'
    DASHBOARD_EXPORT_FILE = DASHBOARD_EXPORT_DIR / 'dashboard.csv'
    PROJECTS_EXPORT_FILE = DASHBOARD_EXPORT_DIR / 'projects.csv'
    
    # メタデータ関連の設定
    METADATA_FOLDER_NAME = "999. metadata"
    TASK_FILE_NAME = "tasks.csv"
    
    # ログファイルパス
    LOG_FILE = ROOT_DIR / 'logs' / 'app.log'
    
    # ログ設定
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    LOG_LEVEL = 'INFO'
    
    # アプリケーション設定
    APP_NAME = "案件管理フォルダ自動生成システム"
    APP_VERSION = "1.0.0"
    
    # フォルダ作成関連の設定
    MAX_FOLDER_NAME_LENGTH = 255  # Windowsの制限に合わせる
    FOLDER_NAME_SEPARATOR = '_'   # フォルダ名の区切り文字
    
    # ドキュメント処理関連の設定
    DOCUMENT_PROCESSOR = {
        'template_dir': MASTER_FOLDER,
        'output_dir': OUTPUT_BASE_DIR,
        'temp_dir': DATA_DIR / 'data' / 'temp',
        'supported_extensions': ['.doc', '.docx', '.xls', '.xlsx', '.xlsm'],
        'default_encoding': 'utf-8',
        'backup_enabled': True,
        'backup_dir': DATA_DIR / 'data' / 'backup'
    }
    
    @classmethod
    def _get_default_paths(cls) -> List[Path]:
        """優先順位付きのデフォルトファイルパスリストを取得"""
        # PathRegistryからのパス取得を試みる
        registry = PathRegistry.get_instance()
        default_paths = []
        
        # 登録されたパスから検索
        for key in ["DEFAULTS_FILE", "ROOT_DEFAULTS_FILE"]:
            path = registry.get_path(key)
            if path:
                default_paths.append(Path(path))
        
        # 従来のパスも追加
        default_paths.extend(cls.DEFAULT_VALUE_PATHS)
        return default_paths

    @classmethod
    def setup_directories(cls):
        """必要なディレクトリを作成"""
        # PathRegistryに登録
        registry = PathRegistry.get_instance()
        
        # 基本パス登録
        registry.register_path("DATA_DIR", cls.DATA_DIR / 'data')
        registry.register_path("MASTER_DIR", cls.MASTER_DIR)
        registry.register_path("MASTER_FOLDER", cls.MASTER_FOLDER)
        registry.register_path("OUTPUT_BASE_DIR", cls.OUTPUT_BASE_DIR)
        registry.register_path("DASHBOARD_EXPORT_DIR", cls.DASHBOARD_EXPORT_DIR)
        registry.register_path("DASHBOARD_EXPORT_FILE", cls.DASHBOARD_EXPORT_FILE)
        registry.register_path("PROJECTS_EXPORT_FILE", cls.PROJECTS_EXPORT_FILE)
        registry.register_path("DB_PATH", cls.DB_PATH)
        registry.register_path("LOG_FILE", cls.LOG_FILE)
        
        # 環境変数にも登録
        os.environ["PMSUITE_DASHBOARD_FILE"] = str(cls.DASHBOARD_EXPORT_FILE)
        os.environ["PMSUITE_DASHBOARD_DATA_DIR"] = str(cls.DASHBOARD_EXPORT_DIR)
        os.environ["PMSUITE_DB_PATH"] = str(cls.DB_PATH)
        
        # ディレクトリ作成（PathRegistryを使用）
        directories = [
            "DATA_DIR",
            "MASTER_DIR",
            "MASTER_FOLDER",
            "OUTPUT_BASE_DIR",
            "DASHBOARD_EXPORT_DIR",
            "TEMP_DIR",
            "BACKUP_DIR",
            "LOGS_DIR"
        ]
        
        for directory in directories:
            registry.ensure_directory(directory)
            
        # 従来の方法でも作成（後方互換性のため）
        directories = [
            cls.DATA_DIR / 'data',
            cls.MASTER_DIR,
            cls.MASTER_FOLDER,
            cls.OUTPUT_BASE_DIR,
            cls.DASHBOARD_EXPORT_DIR,
            cls.DOCUMENT_PROCESSOR['temp_dir'],
            cls.DOCUMENT_PROCESSOR['backup_dir']
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        """
        設定値を取得する
        
        Args:
            key: 設定キー
            default: デフォルト値（設定が存在しない場合に返される）
            
        Returns:
            設定値（存在しない場合はデフォルト値）
        """
        try:
            settings = cls.load_settings()
            return settings.get(key, default)
        except Exception as e:
            logging.warning(f"設定の読み込みに失敗しました: {e}")
            return default
    
    @classmethod
    def load_settings(cls) -> Dict[str, str]:
        """初期値設定ファイルから設定を読み込む"""
        settings = {}
        
        for path in cls._get_default_paths():
            logging.info(f"Checking settings file: {path}")
            if path.exists():
                logging.info(f"Found settings file: {path}")
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        logging.info(f"File content:\n{content}")
                        
                        # ファイルの内容を行ごとに処理
                        for line in content.splitlines():
                            line = line.strip()
                            if line and not line.startswith('#'):
                                try:
                                    key, value = [x.strip() for x in line.split('=', 1)]
                                    settings[key] = value
                                    logging.info(f"Loaded setting: {key}={value}")
                                except ValueError:
                                    logging.warning(f"Invalid setting line: {line}")
                    
                    logging.info(f"Final settings: {settings}")
                    break
                    
                except Exception as e:
                    logging.error(f"設定ファイル読み込みエラー {path}: {e}")
                    continue
        
        return settings

    @classmethod
    def validate_environment(cls):
        """環境の検証"""
        # PathRegistryを使った検証
        registry = PathRegistry.get_instance()
        issues = []
        
        # マスタデータファイルの存在確認
        master_data_file = registry.get_path("MASTER_DATA_FILE", cls.MASTER_DATA_FILE)
        if not Path(master_data_file).exists():
            issues.append(f"マスタデータファイルが見つかりません: {master_data_file}")
        
        # マスターテンプレートフォルダの存在確認
        master_folder = registry.get_path("MASTER_FOLDER", cls.MASTER_FOLDER)
        if not Path(master_folder).exists():
            issues.append(f"マスターテンプレートフォルダが見つかりません: {master_folder}")
        
        # プロジェクト出力ディレクトリの存在確認と作成
        output_dir = registry.get_path("OUTPUT_BASE_DIR", cls.OUTPUT_BASE_DIR)
        if not Path(output_dir).exists():
            try:
                os.makedirs(output_dir)
                logging.info(f"プロジェクト出力ディレクトリを作成しました: {output_dir}")
            except Exception as e:
                issues.append(f"プロジェクト出力ディレクトリの作成に失敗しました: {e}")
            
        # 書き込み権限の確認
        data_dir = registry.get_path("DATA_DIR", cls.DATA_DIR / 'data')
        try:
            test_file = Path(data_dir) / '.write_test'
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            issues.append(f"データディレクトリへの書き込み権限がありません: {e}")
            
        # 問題がある場合は例外を発生
        if issues:
            raise ValueError("\n".join(issues))

    @classmethod
    def get_project_metadata_path(cls, project_name: str) -> Path:
        """
        プロジェクトのメタデータディレクトリパスを取得
        
        Args:
            project_name: プロジェクト名
            
        Returns:
            Path: メタデータディレクトリのパス
        """
        # PathRegistryを使用
        registry = PathRegistry.get_instance()
        output_dir = registry.get_path("OUTPUT_BASE_DIR", cls.OUTPUT_BASE_DIR)
        return Path(output_dir) / project_name / cls.METADATA_FOLDER_NAME

    @classmethod
    def get_project_task_file_path(cls, project_name: str) -> Path:
        """
        プロジェクトのタスクファイルパスを取得
        
        Args:
            project_name: プロジェクト名
            
        Returns:
            Path: タスクファイルのパス
        """
        return cls.get_project_metadata_path(project_name) / cls.TASK_FILE_NAME

    @classmethod
    def get_config_as_dict(cls) -> Dict[str, Any]:
        """
        設定を辞書形式で取得
        
        Returns:
            Dict[str, Any]: 設定辞書
        """
        # PathRegistryから最新の値を取得
        registry = PathRegistry.get_instance()
        
        return {
            'base_dir': registry.get_path("ROOT", str(cls.ROOT_DIR)),
            'data_dir': registry.get_path("DATA_DIR", str(cls.DATA_DIR / 'data')),
            'master_dir': registry.get_path("MASTER_DIR", str(cls.MASTER_DIR)),
            'output_dir': registry.get_path("OUTPUT_BASE_DIR", str(cls.OUTPUT_BASE_DIR)),
            'db_path': registry.get_path("DB_PATH", str(cls.DB_PATH)),
            'log_file': registry.get_path("LOG_FILE", str(cls.LOG_FILE)),
            'document_processor': cls.DOCUMENT_PROCESSOR
        }