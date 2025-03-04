"""統合アプリケーション設定管理"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

class IntegratedConfig:
    """統合アプリケーション設定管理クラス"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初期化
        
        Args:
            config_path: 設定ファイルのパス（省略時は環境変数またはデフォルト）
        """
        self.logger = logging.getLogger(__name__)
        
        # 設定ファイルパスの決定
        if config_path:
            self.config_path = Path(config_path)
        elif 'PM_CONFIG_PATH' in os.environ:
            self.config_path = Path(os.environ['PM_CONFIG_PATH'])
        else:
            # デフォルトパス
            self.config_path = Path.home() / '.project_manager' / 'integrated_config.json'
        
        # 設定ディレクトリの作成
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 設定の初期化
        self.config = self._load_or_create_config()
    
    def _load_or_create_config(self) -> Dict[str, Any]:
        """
        設定の読み込みまたは新規作成
        
        Returns:
            Dict[str, Any]: 設定内容
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"設定ファイル読み込みエラー: {e}")
                # 読み込み失敗時は新規作成
        
        # デフォルト設定
        default_config = {
            'app_paths': {
                'project_manager': str(Path(__file__).parent.parent.parent),
                'create_project_list': None,  # 自動検出予定
                'project_dashboard': None,    # 自動検出予定
            },
            'data_paths': {
                'data_dir': str(Path(__file__).parent.parent.parent / 'data'),
                'templates_dir': str(Path(__file__).parent.parent.parent / 'data' / 'templates'),
                'projects_dir': str(Path(__file__).parent.parent.parent / 'data' / 'projects'),
                'exports_dir': str(Path(__file__).parent.parent.parent / 'data' / 'exports'),
                'master_dir': str(Path(__file__).parent.parent.parent / 'data' / 'master'),
                'temp_dir': str(Path(__file__).parent.parent.parent / 'data' / 'temp'),
                'log_dir': str(Path(__file__).parent.parent.parent / 'logs'),
            },
            'db_config': {
                'db_path': str(Path(__file__).parent.parent.parent / 'data' / 'projects.db'),
            },
            'ui_config': {
                'theme': 'dark',
                'language': 'ja',
            }
        }
        
        # 自動検出処理
        self._auto_detect_app_paths(default_config)
        
        # 設定ファイルの保存
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"設定ファイル保存エラー: {e}")
        
        return default_config
    
    def _auto_detect_app_paths(self, config: Dict[str, Any]) -> None:
        """
        アプリケーションパスの自動検出
        
        Args:
            config: 設定辞書
        """
        try:
            base_dir = Path(config['app_paths']['project_manager'])
            
            # 隣接ディレクトリの検索
            parent_dir = base_dir.parent
            for app_id in ['create_project_list', 'project_dashboard']:
                possible_paths = [
                    parent_dir / app_id.replace('_', ''),
                    parent_dir / app_id,
                    base_dir.parent / app_id.replace('_', ''),
                    base_dir.parent / app_id,
                ]
                
                for path in possible_paths:
                    if path.exists() and path.is_dir():
                        config['app_paths'][app_id] = str(path)
                        break
        
        except Exception as e:
            self.logger.error(f"アプリケーションパスの自動検出エラー: {e}")
    
    def get_config_path(self) -> Path:
        """
        設定ファイルのパスを取得
        
        Returns:
            Path: 設定ファイルのパス
        """
        return self.config_path
    
    def get_app_path(self, app_id: str) -> Optional[str]:
        """
        アプリケーションのパスを取得
        
        Args:
            app_id: アプリケーションID
            
        Returns:
            Optional[str]: アプリケーションのパス
        """
        return self.config.get('app_paths', {}).get(app_id)
    
    def get_data_path(self, path_id: str) -> Optional[str]:
        """
        データパスを取得
        
        Args:
            path_id: パスID
            
        Returns:
            Optional[str]: データパス
        """
        return self.config.get('data_paths', {}).get(path_id)
    
    def get_db_path(self) -> Optional[str]:
        """
        データベースパスを取得
        
        Returns:
            Optional[str]: データベースパス
        """
        return self.config.get('db_config', {}).get('db_path')
    
    def save(self) -> bool:
        """
        設定を保存
        
        Returns:
            bool: 保存成功時True
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"設定保存エラー: {e}")
            return False
    
    def update(self, section: str, key: str, value: Any) -> bool:
        """
        設定値を更新
        
        Args:
            section: セクション名
            key: キー
            value: 値
            
        Returns:
            bool: 更新成功時True
        """
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section][key] = value
            return self.save()
        except Exception as e:
            self.logger.error(f"設定更新エラー: {e}")
            return False