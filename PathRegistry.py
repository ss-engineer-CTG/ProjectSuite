"""
パス管理のための統一インターフェース
アプリケーション全体でパスを一元管理し、
環境依存のパス問題を解決する
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Set, Any

class PathRegistry:
    """パス管理クラス（シングルトン）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super(PathRegistry, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        """シングルトンインスタンスの取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初期化（シングルトンなので1回のみ実行）"""
        if self._initialized:
            return
            
        self._initialized = True
        self._paths = {}
        self._user_paths = set()  # ユーザーが明示的に設定したパス
        self._app_base_path = self._get_app_base_path()
        self._config = None  # 遅延ロード用
        
        # デフォルトのパス登録
        self._register_default_paths()
        
        # ロガーの初期化
        self.logger = logging.getLogger(__name__)
    
    def _get_app_base_path(self) -> str:
        """
        アプリケーションの基本パスを取得
        
        Returns:
            str: アプリケーションのルートディレクトリ
        """
        if getattr(sys, 'frozen', False):
            # PyInstallerで実行ファイル化した場合
            return os.path.dirname(sys.executable)
        else:
            # 通常の実行の場合
            current_file = os.path.abspath(__file__)
            return os.path.dirname(current_file)
    
    def _register_default_paths(self) -> None:
        """デフォルトのパスを登録"""
        # アプリケーションルートパス
        self.register_path("ROOT", self._app_base_path)
        
        # ユーザーデータディレクトリ
        user_doc_dir = os.path.join(os.path.expanduser("~"), "Documents", "ProjectSuite")
        self.register_path("USER_DATA_DIR", user_doc_dir)
        
        # ログディレクトリ
        self.register_path("LOGS_DIR", os.path.join(user_doc_dir, "logs"))
        
        # データディレクトリ
        self.register_path("DATA_DIR", user_doc_dir)
        
        # エクスポートディレクトリ
        self.register_path("EXPORTS_DIR", os.path.join(user_doc_dir, "ProjectManager", "data", "exports"))
        
        # テンプレートディレクトリ
        self.register_path("TEMPLATES_DIR", os.path.join(user_doc_dir, "ProjectManager", "data", "templates"))
        
        # デフォルトのプロジェクトディレクトリ
        default_projects_dir = os.path.join(user_doc_dir, "ProjectManager", "data", "projects")
        self.register_path("PROJECTS_DIR", default_projects_dir)
        
        # マスターデータディレクトリ
        self.register_path("MASTER_DIR", os.path.join(user_doc_dir, "ProjectManager", "data", "master"))
        
        # 一時ファイルディレクトリ
        self.register_path("TEMP_DIR", os.path.join(user_doc_dir, "temp"))
        
        # バックアップディレクトリ
        self.register_path("BACKUP_DIR", os.path.join(user_doc_dir, "backup"))
        
        # CreateProjectList用ディレクトリ
        self.register_path("CPL_DIR", os.path.join(user_doc_dir, "CreateProjectList"))
        self.register_path("CPL_CONFIG_DIR", os.path.join(user_doc_dir, "CreateProjectList", "config"))
        self.register_path("CPL_TEMP_DIR", os.path.join(user_doc_dir, "CreateProjectList", "temp"))
        self.register_path("CPL_TEMPLATES_DIR", os.path.join(user_doc_dir, "CreateProjectList", "templates"))
        self.register_path("CPL_CACHE_DIR", os.path.join(user_doc_dir, "CreateProjectList", "cache"))
        
        # デフォルトのデータベースパス
        self.register_path("DB_PATH", os.path.join(user_doc_dir, "ProjectManager", "data", "projects.db"))
    
    def register_path(self, key: str, path: str) -> None:
        """
        パスを登録
        
        Args:
            key: パスのキー
            path: パスの値
        """
        self._paths[key] = path
        self._user_paths.add(key)  # ユーザー登録パスとして記録
    
    def get_path(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        登録されたパスを取得（拡張版）
        
        優先順位:
        1. 明示的に登録されたパス
        2. 設定ファイルからのカスタムパス
        3. デフォルト値
        
        Args:
            key: パスキー
            default: デフォルト値
            
        Returns:
            Optional[str]: 解決されたパス
        """
        # 1. 登録済みパスをチェック
        if key in self._paths:
            return self._paths[key]
        
        # 2. PROJECTSキーの特別処理
        if key == "PROJECTS_DIR" or key == "OUTPUT_BASE_DIR":
            # 設定ファイルからカスタムパスを取得
            custom_path = self.get_custom_projects_path()
            if custom_path:
                # パスを登録して今後の参照を簡素化
                self.register_path(key, custom_path)
                return custom_path
        
        # 3. デフォルト値を返す
        return default
    
    def get_custom_projects_path(self) -> Optional[str]:
        """
        カスタムプロジェクトパスを設定ファイルから取得
        
        Returns:
            Optional[str]: カスタムプロジェクトパス。設定されていない場合はNone
        """
        # 設定の読み込み
        if not self._config:
            self._config = self._load_config()
        
        # カスタムパスの取得
        custom_path = self._config.get('custom_projects_dir')
        
        if custom_path and os.path.exists(custom_path):
            return custom_path
        
        return None
    
    def _load_config(self) -> Dict[str, str]:
        """
        設定ファイルから設定を読み込む
        
        Returns:
            Dict[str, str]: 設定データ
        """
        config = {}
        
        # 設定ファイルのパス
        default_paths = [
            os.path.join(os.path.expanduser("~"), "Documents", "ProjectSuite", "defaults.txt"),
            os.path.join(self._app_base_path, "defaults.txt")
        ]
        
        # 最初に見つかった設定ファイルを読み込む
        for path in default_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                try:
                                    key, value = [x.strip() for x in line.split('=', 1)]
                                    config[key] = value
                                except ValueError:
                                    continue
                    break
                except Exception as e:
                    self.logger.warning(f"設定ファイル読み込みエラー: {e}")
        
        return config
    
    def get_config(self) -> Dict[str, str]:
        """
        設定を取得
        
        Returns:
            Dict[str, str]: 設定データ
        """
        if not self._config:
            self._config = self._load_config()
        
        return self._config
    
    def ensure_directory(self, key: str) -> bool:
        """
        指定キーのディレクトリが存在することを確認し、なければ作成
        
        Args:
            key: ディレクトリのキー
            
        Returns:
            bool: 作成成功時はTrue
        """
        path = self.get_path(key)
        if not path:
            self.logger.warning(f"ディレクトリキーが未登録: {key}")
            return False
            
        path_obj = Path(path)
        if path_obj.exists() and path_obj.is_dir():
            return True
            
        try:
            path_obj.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"ディレクトリを作成: {path}")
            return True
        except Exception as e:
            self.logger.error(f"ディレクトリ作成エラー {path}: {e}")
            return False
    
    def get_all_paths(self) -> Dict[str, str]:
        """
        登録されている全パスを取得
        
        Returns:
            Dict[str, str]: パス一覧
        """
        return self._paths.copy()
    
    def diagnose(self) -> Dict[str, Any]:
        """
        パス診断を実行
        
        Returns:
            Dict[str, Any]: 診断結果
        """
        issues = []
        
        # 基本ディレクトリの存在チェック
        essential_dirs = ["USER_DATA_DIR", "LOGS_DIR", "DATA_DIR", "PROJECTS_DIR"]
        for key in essential_dirs:
            path = self.get_path(key)
            if not path:
                issues.append({
                    "type": "missing_key",
                    "key": key,
                    "severity": "error"
                })
                continue
                
            path_obj = Path(path)
            if not path_obj.exists():
                issues.append({
                    "type": "missing_dir",
                    "key": key,
                    "path": path,
                    "severity": "warning",
                    "fixable": True
                })
            elif not path_obj.is_dir():
                issues.append({
                    "type": "not_dir",
                    "key": key,
                    "path": path,
                    "severity": "error"
                })
        
        # DBファイルの確認
        db_path = self.get_path("DB_PATH")
        if db_path:
            db_obj = Path(db_path)
            if not db_obj.parent.exists():
                issues.append({
                    "type": "db_parent_missing",
                    "path": str(db_obj.parent),
                    "severity": "warning",
                    "fixable": True
                })
        
        # プロジェクトパスの検証
        projects_dir = self.get_path("PROJECTS_DIR")
        if projects_dir:
            try:
                projects_obj = Path(projects_dir)
                if not projects_obj.exists():
                    issues.append({
                        "type": "projects_dir_missing",
                        "path": projects_dir,
                        "severity": "warning",
                        "fixable": True
                    })
                else:
                    # 書き込み権限の確認
                    test_file = projects_obj / ".write_test"
                    try:
                        test_file.touch()
                        test_file.unlink()
                    except (PermissionError, OSError):
                        issues.append({
                            "type": "permission_error",
                            "path": projects_dir,
                            "severity": "error"
                        })
            except Exception as e:
                issues.append({
                    "type": "validation_error",
                    "path": projects_dir,
                    "error": str(e),
                    "severity": "error"
                })
        
        # 診断結果の返却
        return {
            "issues": issues,
            "total_issues": len(issues),
            "error_count": sum(1 for i in issues if i["severity"] == "error"),
            "warning_count": sum(1 for i in issues if i["severity"] == "warning")
        }
    
    def auto_repair(self, issues: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        診断結果に基づく自動修復
        
        Args:
            issues: 診断結果の問題リスト
            
        Returns:
            Dict[str, List[str]]: 修復結果
        """
        repaired = []
        failed = []
        
        for issue in issues:
            if issue.get("fixable", False):
                if issue["type"] == "missing_dir":
                    try:
                        path = Path(issue["path"])
                        path.mkdir(parents=True, exist_ok=True)
                        repaired.append(f"ディレクトリを作成: {path}")
                    except Exception as e:
                        failed.append(f"ディレクトリ作成失敗 {issue['path']}: {e}")
                
                elif issue["type"] == "db_parent_missing":
                    try:
                        path = Path(issue["path"])
                        path.mkdir(parents=True, exist_ok=True)
                        repaired.append(f"DBパス親ディレクトリを作成: {path}")
                    except Exception as e:
                        failed.append(f"DBパス親ディレクトリ作成失敗 {issue['path']}: {e}")
                
                elif issue["type"] == "projects_dir_missing":
                    try:
                        path = Path(issue["path"])
                        path.mkdir(parents=True, exist_ok=True)
                        repaired.append(f"プロジェクトディレクトリを作成: {path}")
                    except Exception as e:
                        failed.append(f"プロジェクトディレクトリ作成失敗 {issue['path']}: {e}")
        
        return {
            "repaired": repaired,
            "failed": failed
        }
    
    def check_first_run(self) -> bool:
        """
        初回起動チェック
        
        Returns:
            bool: 初回起動の場合True
        """
        # 初期化完了マークファイルの確認
        user_data_dir = self.get_path("USER_DATA_DIR")
        if not user_data_dir:
            return True
            
        init_file = os.path.join(user_data_dir, ".init_complete")
        return not os.path.exists(init_file)

def get_path(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    グローバルユーティリティ: パスを取得
    
    Args:
        key: パスのキー
        default: デフォルト値
    
    Returns:
        Optional[str]: パス
    """
    registry = PathRegistry.get_instance()
    return registry.get_path(key, default)

def ensure_dir(key: str) -> bool:
    """
    グローバルユーティリティ: ディレクトリを確保
    
    Args:
        key: ディレクトリのキー
    
    Returns:
        bool: 成功したらTrue
    """
    registry = PathRegistry.get_instance()
    return registry.ensure_directory(key)