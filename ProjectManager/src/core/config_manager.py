"""統合設定管理クラス"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

class ConfigManager:
    """統合設定管理クラス"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス（省略時はデフォルトパス）
        """
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
        # PathRegistryを初期化
        try:
            from PathRegistry import PathRegistry
            self.registry = PathRegistry.get_instance()
        except ImportError:
            self.registry = None
            self.logger.warning("PathRegistryを読み込めませんでした")
        
        # 設定ファイルのパス
        if config_path:
            self.config_file = Path(config_path)
        else:
            # デフォルトの設定ファイルパス
            self.config_file = Path.home() / "Documents" / "ProjectSuite" / "config.json"
        
        # configフォルダがない場合は作成を試みる
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # 権限エラーの場合は一時ディレクトリに変更
            import tempfile
            self.config_file = Path(tempfile.gettempdir()) / "projectsuite_config.json"
            self.logger.warning(f"設定ファイルを一時ディレクトリに変更: {self.config_file}")
        
        # 設定の読み込み
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        設定ファイルから設定を読み込む
        
        Returns:
            Dict[str, Any]: 設定データ
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.logger.info(f"設定を読み込みました: {self.config_file}")
                    return config
            except Exception as e:
                self.logger.error(f"設定読み込みエラー: {e}")
        
        # デフォルト設定
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        デフォルト設定を取得
        
        Returns:
            Dict[str, Any]: デフォルト設定
        """
        user_doc_dir = Path.home() / "Documents" / "ProjectSuite"
        
        return {
            'paths': {
                'output_base_dir': str(Path.home() / "Desktop" / "projects"),
                'user_data_dir': str(user_doc_dir),
                'logs_dir': str(user_doc_dir / "logs"),
                'master_dir': str(user_doc_dir / "ProjectManager" / "data" / "master"),
                'templates_dir': str(user_doc_dir / "ProjectManager" / "data" / "templates"),
                'exports_dir': str(user_doc_dir / "ProjectManager" / "data" / "exports"),
                'db_path': str(user_doc_dir / "ProjectManager" / "data" / "projects.db")
            },
            'defaults': {
                'project_name': '新規プロジェクト',
                'manager': '山田太郎',
                'reviewer': '鈴木一郎',
                'approver': '佐藤部長',
                'division': 'D001',
                'factory': 'F001',
                'process': 'P001',
                'line': 'L001'
            },
            'app': {
                'appearance': 'dark',
                'language': 'ja',
                'last_updated': datetime.now().isoformat()
            }
        }
    
    def save_config(self) -> None:
        """設定ファイルの保存"""
        try:
            # 最終更新日時の更新
            if 'app' not in self.config:
                self.config['app'] = {}
            self.config['app']['last_updated'] = datetime.now().isoformat()
            
            # 設定の保存
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"設定を保存しました: {self.config_file}")
            
            # PathRegistryに通知
            if self.registry:
                try:
                    # パス設定のコピー
                    if 'paths' in self.config:
                        for key, value in self.config['paths'].items():
                            normalized_key = key.upper()
                            # output_base_dirの場合はOUTPUT_BASE_DIRとして登録
                            if key == 'output_base_dir':
                                self.registry.register_path("OUTPUT_BASE_DIR", value)
                            else:
                                # その他のパスはそのまま登録
                                self.registry.register_path(normalized_key, value)
                except Exception as e:
                    self.logger.error(f"PathRegistry更新エラー: {e}")
                    
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
            raise
    
    def get_config(self) -> Dict[str, Any]:
        """
        現在の設定を取得
        
        Returns:
            Dict[str, Any]: 現在の設定
        """
        return self.config
    
    def get_setting(self, section: str, key: str, default: Any = None) -> Any:
        """
        設定値を取得
        
        Args:
            section: 設定セクション
            key: 設定キー
            default: デフォルト値
            
        Returns:
            Any: 設定値
        """
        if section in self.config and key in self.config[section]:
            return self.config[section][key]
        return default
    
    def set_setting(self, section: str, key: str, value: Any) -> None:
        """
        設定値を設定
        
        Args:
            section: 設定セクション
            key: 設定キー
            value: 設定値
        """
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        
        # 特定の設定はPathRegistryにも反映
        if section == 'paths':
            if self.registry:
                normalized_key = key.upper()
                # output_base_dirの場合はOUTPUT_BASE_DIRとして登録
                if key == 'output_base_dir':
                    self.registry.register_path("OUTPUT_BASE_DIR", value)
                else:
                    self.registry.register_path(normalized_key, value)
        
        self.save_config()
    
    def update_output_dir(self, output_dir: str) -> None:
        """
        出力ディレクトリを更新
        
        Args:
            output_dir: 新しい出力ディレクトリパス
        """
        # 設定更新
        self.set_setting('paths', 'output_base_dir', output_dir)
        
        # PathRegistryにも反映（エイリアスの更新はPathRegistry内部で処理）
        if self.registry:
            self.registry.register_path("OUTPUT_BASE_DIR", output_dir)
            
        self.logger.info(f"出力ディレクトリを更新しました: {output_dir}")