"""設定管理クラス"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

class Config:
    # プロジェクトのルートディレクトリを取得
    ROOT_DIR = Path(__file__).parent.parent.parent
    
    # データディレクトリ
    DATA_DIR = ROOT_DIR
    
    # プロジェクトルートパスを定義
    PROJECT_ROOT = Path('C:/Users/gbrai/Documents/Projects/app_Task_Management/ProjectManager')

    # デフォルト値設定ファイルのパス
    DEFAULT_VALUE_PATHS = [
        PROJECT_ROOT / 'defaults.txt',  # プロジェクトルート直下のdefaults.txt
        PROJECT_ROOT / 'data' / 'defaults.txt',  # dataフォルダ内
        PROJECT_ROOT / 'config' / 'defaults.txt',  # configフォルダ内
        Path.home() / 'ProjectManager/defaults.txt'  # ユーザーホームディレクトリ
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
        return cls.DEFAULT_VALUE_PATHS

    @classmethod
    def setup_directories(cls):
        """必要なディレクトリを作成"""
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
        
        for path in cls.DEFAULT_VALUE_PATHS:
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
        # マスタデータファイルの存在確認
        if not cls.MASTER_DATA_FILE.exists():
            raise FileNotFoundError(
                f"マスタデータファイルが見つかりません: {cls.MASTER_DATA_FILE}"
            )
        
        # マスターテンプレートフォルダの存在確認
        if not cls.MASTER_FOLDER.exists():
            raise FileNotFoundError(
                f"マスターテンプレートフォルダが見つかりません: {cls.MASTER_FOLDER}"
            )
        
        # プロジェクト出力ディレクトリの存在確認と作成
        if not cls.OUTPUT_BASE_DIR.exists():
            try:
                os.makedirs(cls.OUTPUT_BASE_DIR)
                logging.info(f"プロジェクト出力ディレクトリを作成しました: {cls.OUTPUT_BASE_DIR}")
            except Exception as e:
                raise PermissionError(f"プロジェクト出力ディレクトリの作成に失敗しました: {e}")
            
        # 書き込み権限の確認
        try:
            test_file = cls.DATA_DIR / 'data' / '.write_test'
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            raise PermissionError(f"データディレクトリへの書き込み権限がありません: {e}")

    @classmethod
    def get_project_metadata_path(cls, project_name: str) -> Path:
        """
        プロジェクトのメタデータディレクトリパスを取得
        
        Args:
            project_name: プロジェクト名
            
        Returns:
            Path: メタデータディレクトリのパス
        """
        return cls.OUTPUT_BASE_DIR / project_name / cls.METADATA_FOLDER_NAME

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
        return {
            'base_dir': str(cls.ROOT_DIR),
            'data_dir': str(cls.DATA_DIR / 'data'),
            'master_dir': str(cls.MASTER_DIR),
            'output_dir': str(cls.OUTPUT_BASE_DIR),
            'db_path': str(cls.DB_PATH),
            'log_file': str(cls.LOG_FILE),
            'document_processor': cls.DOCUMENT_PROCESSOR
        }