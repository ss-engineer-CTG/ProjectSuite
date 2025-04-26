"""共通パスレジストリモジュール"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime

class PathRegistry:
    """パス管理の中央レジストリ"""
    
    _instance = None
    
    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super(PathRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """
        シングルトンインスタンスを取得
        
        Returns:
            PathRegistry: インスタンス
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初期化（シングルトンなので一度だけ実行）"""
        if getattr(self, '_initialized', False):
            return
            
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        
        # パス格納用の辞書
        self._paths = {}
        
        # エイリアス定義 - キー：エイリアス名、値：参照先キー
        self._path_aliases = {
            "PROJECTS_DIR": "OUTPUT_BASE_DIR",  # PROJECTS_DIRはOUTPUT_BASE_DIRのエイリアス
            "PM_PROJECTS_DIR": "OUTPUT_BASE_DIR"  # 後方互換性用
        }
        
        # 設定ファイルのパス
        self._config_file = self._get_config_file_path()
        
        # 設定の読み込み
        self._load_paths()
        
        self.logger.debug("PathRegistry initialized")
    
    def _get_config_file_path(self) -> Path:
        """
        設定ファイルのパスを取得
        
        Returns:
            Path: 設定ファイルのパス
        """
        # ユーザードキュメント内の設定ファイル
        user_docs = Path.home() / "Documents" / "ProjectSuite"
        config_file = user_docs / "path_registry.json"
        
        return config_file
    
    def _load_paths(self) -> None:
        """保存されているパス設定を読み込み"""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'paths' in data:
                        self._paths = data['paths']
                        self.logger.debug(f"Loaded {len(self._paths)} paths from {self._config_file}")
        except Exception as e:
            self.logger.error(f"Failed to load paths: {e}")
    
    def _save_paths(self) -> None:
        """パス設定を保存"""
        try:
            # 保存データの準備
            data = {
                'paths': self._paths,
                'last_updated': datetime.now().isoformat()
            }
            
            # ディレクトリ確保
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # ファイル書き込み
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            self.logger.debug(f"Saved {len(self._paths)} paths to {self._config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save paths: {e}")
    
    def register_path(self, key: str, path: str) -> None:
        """
        パスの登録・更新
        
        Args:
            key: パスのキー
            path: パスの値
        """
        if not key:
            self.logger.warning("Cannot register path with empty key")
            return
            
        if not path:
            self.logger.warning(f"Cannot register empty path for key '{key}'")
            return
        
        # 正規化
        normalized_path = str(Path(path).resolve())
        
        # キーとパスの更新
        if key in self._paths and self._paths[key] == normalized_path:
            # 値が変わっていない場合は何もしない
            return
            
        self._paths[key] = normalized_path
        self.logger.debug(f"Registered path '{key}': {normalized_path}")
        
        # エイリアス対象なら、すべてのエイリアスを更新
        for alias_key, target_key in self._path_aliases.items():
            if target_key == key:
                self._paths[alias_key] = normalized_path
                self.logger.debug(f"Updated alias '{alias_key}' to match '{key}': {normalized_path}")
        
        # エイリアスのキーなら実際のキーも更新
        if key in self._path_aliases:
            target_key = self._path_aliases[key]
            self._paths[target_key] = normalized_path
            self.logger.debug(f"Updated target '{target_key}' from alias '{key}': {normalized_path}")
        
        # 設定の保存
        self._save_paths()
    
    def get_path(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        登録されたパスを取得
        
        Args:
            key: パスのキー
            default: パスが見つからない場合のデフォルト値
            
        Returns:
            Optional[str]: パス、見つからない場合はデフォルト値
        """
        # 直接キーで検索
        if key in self._paths:
            return self._paths[key]
        
        # エイリアスの場合は参照先を検索
        if key in self._path_aliases and self._path_aliases[key] in self._paths:
            target_key = self._path_aliases[key]
            value = self._paths[target_key]
            self.logger.debug(f"Retrieved path for '{key}' via alias to '{target_key}': {value}")
            return value
            
        self.logger.debug(f"Path '{key}' not found, using default: {default}")
        return default
    
    def get_all_paths(self) -> Dict[str, str]:
        """
        すべてのパスを取得
        
        Returns:
            Dict[str, str]: すべてのパスの辞書
        """
        return self._paths.copy()
    
    def ensure_directory(self, key: str) -> Optional[str]:
        """
        キーに関連付けられたディレクトリが存在することを確認
        
        Args:
            key: ディレクトリのキー
            
        Returns:
            Optional[str]: 作成されたディレクトリのパス、失敗時はNone
        """
        path = self.get_path(key)
        if not path:
            self.logger.warning(f"Directory key '{key}' not found")
            return None
            
        try:
            # ディレクトリの作成
            directory = Path(path)
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured directory exists: {path}")
            return path
            
        except Exception as e:
            self.logger.error(f"Failed to create directory '{path}': {e}")
            return None
    
    def is_valid_path(self, key: str) -> bool:
        """
        パスが有効かどうかを確認
        
        Args:
            key: パスのキー
            
        Returns:
            bool: パスが存在し有効な場合True
        """
        path = self.get_path(key)
        if not path:
            return False
            
        return Path(path).exists()
    
    def check_first_run(self) -> bool:
        """
        初回実行かどうかを確認
        
        Returns:
            bool: 初回実行の場合True
        """
        # 設定ファイルが存在しない場合は初回実行とみなす
        if not self._config_file.exists():
            return True
        
        # ユーザードキュメントの初期化マーカーがない場合も初回実行
        init_marker = Path.home() / "Documents" / "ProjectSuite" / ".init_complete"
        if not init_marker.exists():
            return True
            
        return False
    
    def migrate_legacy_config(self) -> bool:
        """
        レガシー設定をJSONに移行
        
        Returns:
            bool: 移行成功時True
        """
        # 移行対象のデフォルトファイル
        legacy_files = [
            Path.home() / "Documents" / "ProjectSuite" / "defaults.txt",
            Path(__file__).parent / "defaults.txt"
        ]
        
        migrated = False
        
        for file_path in legacy_files:
            if file_path.exists():
                try:
                    # レガシー設定の読み込み
                    legacy_settings = {}
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                try:
                                    key, value = [x.strip() for x in line.split('=', 1)]
                                    legacy_settings[key] = value
                                except ValueError:
                                    continue
                    
                    # 設定の移行
                    for key, value in legacy_settings.items():
                        if key.startswith('default_'):
                            # デフォルト設定は扱わない（専用の設定クラスで扱う）
                            continue
                        elif key == 'custom_projects_dir':
                            # プロジェクトディレクトリはOUTPUT_BASE_DIRに設定
                            self.register_path("OUTPUT_BASE_DIR", value)
                            migrated = True
                    
                    self.logger.info(f"Migrated legacy settings from {file_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to migrate legacy settings from {file_path}: {e}")
        
        return migrated
    
    def find_data_source(self) -> Optional[Path]:
        """
        データソースディレクトリを検索
        
        Returns:
            Optional[Path]: データソースディレクトリ
        """
        # 検索場所のリスト（優先順位順）
        potential_paths = [
            # アプリケーションのデータディレクトリ
            Path(__file__).parent / "data",
            
            # ProjectManagerのデータディレクトリ（複数の可能性）
            Path(__file__).parent / "ProjectManager" / "data",
            Path(os.getcwd()) / "ProjectManager" / "data",
            
            # 開発環境でよく使われるパス
            Path.home() / "Documents" / "Projects" / "ProjectSuite" / "ProjectManager" / "data",
            Path.home() / "Projects" / "ProjectSuite" / "ProjectManager" / "data"
        ]
        
        # パスが存在するか確認
        for path in potential_paths:
            if path.exists() and path.is_dir():
                # 実際にデータらしきものが存在するか確認
                has_content = any([
                    (path / "projects").exists(),
                    (path / "templates").exists(),
                    (path / "master").exists(),
                    (path / "projects.db").exists()
                ])
                
                if has_content:
                    self.logger.info(f"Found data source directory: {path}")
                    return path
        
        # 見つからない場合
        self.logger.warning("Data source directory not found")
        return None
    
    def diagnose(self) -> Dict[str, Any]:
        """
        パス設定の診断を実行
        
        Returns:
            Dict[str, Any]: 診断結果
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'paths': self.get_all_paths(),
            'aliases': self._path_aliases.copy(),
            'issues': [],
            'conflicts': [],
            'missing_dirs': []
        }
        
        # パスの存在チェック
        for key, path in self._paths.items():
            if path and not Path(path).exists():
                result['missing_dirs'].append({
                    'key': key,
                    'path': path
                })
        
        # エイリアスの一貫性チェック
        for alias_key, target_key in self._path_aliases.items():
            if alias_key in self._paths and target_key in self._paths:
                if self._paths[alias_key] != self._paths[target_key]:
                    result['conflicts'].append({
                        'alias': alias_key,
                        'target': target_key,
                        'alias_value': self._paths[alias_key],
                        'target_value': self._paths[target_key]
                    })
        
        # パスエイリアスの一貫性問題
        if 'OUTPUT_BASE_DIR' in self._paths and 'PROJECTS_DIR' in self._paths:
            if self._paths['OUTPUT_BASE_DIR'] != self._paths['PROJECTS_DIR']:
                result['issues'].append({
                    'type': 'path_inconsistency',
                    'message': 'OUTPUT_BASE_DIR and PROJECTS_DIR have different values',
                    'severity': 'warning',
                    'output_dir': self._paths['OUTPUT_BASE_DIR'],
                    'projects_dir': self._paths['PROJECTS_DIR']
                })
        
        return result
    
    def auto_repair(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        診断で見つかった問題の自動修復を試みる
        
        Args:
            issues: 診断で見つかった問題
            
        Returns:
            Dict[str, Any]: 修復結果
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'repaired': [],
            'failed': []
        }
        
        try:
            # パスの不一致を修復
            for issue in issues:
                if issue.get('type') == 'path_inconsistency':
                    # OUTPUT_BASE_DIRが設定されている場合、それを優先
                    if 'output_dir' in issue and issue['output_dir']:
                        self.register_path('OUTPUT_BASE_DIR', issue['output_dir'])
                        result['repaired'].append({
                            'issue': 'path_inconsistency',
                            'message': 'Synchronized PROJECTS_DIR with OUTPUT_BASE_DIR',
                            'value': issue['output_dir']
                        })
                    # そうでなければPROJECTS_DIRの値を使用
                    elif 'projects_dir' in issue and issue['projects_dir']:
                        self.register_path('PROJECTS_DIR', issue['projects_dir'])
                        result['repaired'].append({
                            'issue': 'path_inconsistency',
                            'message': 'Synchronized OUTPUT_BASE_DIR with PROJECTS_DIR',
                            'value': issue['projects_dir']
                        })
            
            # 欠落しているディレクトリの作成
            for missing in issues:
                if missing.get('key') and missing.get('path'):
                    try:
                        Path(missing['path']).mkdir(parents=True, exist_ok=True)
                        result['repaired'].append({
                            'issue': 'missing_directory',
                            'key': missing['key'],
                            'path': missing['path'],
                            'message': f"Created directory for {missing['key']}"
                        })
                    except Exception as e:
                        result['failed'].append({
                            'issue': 'missing_directory',
                            'key': missing['key'],
                            'path': missing['path'],
                            'error': str(e)
                        })
            
            # エイリアスの一貫性修復
            for conflict in issues:
                if conflict.get('alias') and conflict.get('target'):
                    try:
                        # ターゲットの値を使ってエイリアスを更新
                        target_key = conflict['target']
                        if target_key in self._paths:
                            self.register_path(conflict['alias'], self._paths[target_key])
                            result['repaired'].append({
                                'issue': 'alias_conflict',
                                'message': f"Synchronized {conflict['alias']} with {target_key}",
                                'value': self._paths[target_key]
                            })
                    except Exception as e:
                        result['failed'].append({
                            'issue': 'alias_conflict',
                            'alias': conflict['alias'],
                            'target': conflict['target'],
                            'error': str(e)
                        })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Auto-repair failed: {e}")
            result['failed'].append({
                'issue': 'general',
                'error': str(e)
            })
            return result

    def clear_all_paths(self) -> None:
        """すべてのパス設定をクリア（テスト用）"""
        self._paths.clear()
        self._save_paths()
        self.logger.warning("All paths have been cleared")
        
    def get_aliases_for(self, key: str) -> List[str]:
        """
        特定のキーに対するエイリアスの一覧を取得
        
        Args:
            key: 対象のキー
            
        Returns:
            List[str]: エイリアスのリスト
        """
        return [alias for alias, target in self._path_aliases.items() if target == key]
    
    def is_alias(self, key: str) -> bool:
        """
        指定されたキーがエイリアスかどうかを確認
        
        Args:
            key: 確認するキー
            
        Returns:
            bool: エイリアスの場合True
        """
        return key in self._path_aliases
    
    def get_alias_target(self, alias: str) -> Optional[str]:
        """
        エイリアスの参照先を取得
        
        Args:
            alias: エイリアス名
            
        Returns:
            Optional[str]: 参照先キー、エイリアスでない場合はNone
        """
        return self._path_aliases.get(alias)


def get_path(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    シングルトンからパスを取得する便利関数
    
    Args:
        key: パスのキー
        default: デフォルト値
        
    Returns:
        Optional[str]: パス
    """
    registry = PathRegistry.get_instance()
    return registry.get_path(key, default)


def ensure_dir(key: str) -> Optional[str]:
    """
    シングルトンからディレクトリを確保する便利関数
    
    Args:
        key: ディレクトリのキー
        
    Returns:
        Optional[str]: ディレクトリパス
    """
    registry = PathRegistry.get_instance()
    return registry.ensure_directory(key)