"""
Self-Healing PathRegistry - 統合版パス解決モジュール
各アプリケーション（ProjectManager, CreateProjectList, ProjectDashBoard）で共通利用
"""
import os
import sys
import logging
import json
import shutil
from datetime import datetime
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set

# ロガーの設定
logger = logging.getLogger(__name__)

class PathRegistry:
    """パス解決とディレクトリ管理のための統合レジストリ"""
    
    # シングルトンインスタンス
    _instance = None
    
    # パス情報を保持する辞書
    _paths: Dict[str, str] = {}
    
    # パス設定ファイル名
    CONFIG_FILE = "path_registry.json"
    
    @classmethod
    def get_instance(cls):
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """初期化 - 基本パスの設定とパス情報の読み込み"""
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # 初期化フラグ
        self._initialized = True
        
        # PyInstallerかどうかの判定
        self.is_frozen = getattr(sys, 'frozen', False)
        
        # 基本ディレクトリの特定
        if self.is_frozen:
            # PyInstallerで実行ファイル化した場合
            self.root_dir = Path(sys._MEIPASS).parent
        else:
            # 通常実行時は現在のスクリプトの位置から判断
            self.root_dir = self._find_project_root()
        
        # 初期パスの設定
        self._setup_base_paths()
        
        # 設定ファイルからパスを読み込む
        self._load_paths_from_config()
        
        # 環境変数からパスをオーバーライド
        self._override_from_env()
        
        logger.info(f"PathRegistry initialized with root: {self.root_dir}")
    
    def _find_project_root(self) -> Path:
        """プロジェクトルートディレクトリを探索"""
        # 現在のスクリプトの位置
        current_path = Path(__file__).resolve().parent
        
        # ルートを特定するためのマーカーファイル
        root_markers = [
            "ProjectManagerSuite.spec",
            "build.py",
            "launcher.py"
        ]
        
        # 上位ディレクトリを探索
        for i in range(5):  # 最大5階層まで探索
            # マーカーファイルが存在するか確認
            for marker in root_markers:
                if (current_path / marker).exists():
                    return current_path
            
            # ProjectManagerSuiteディレクトリかどうか確認
            if current_path.name == "ProjectManagerSuite":
                return current_path
                
            # 各アプリケーションのルートディレクトリかどうか確認
            app_dirs = ["ProjectManager", "CreateProjectList", "ProjectDashBoard"]
            if current_path.name in app_dirs:
                return current_path.parent
            
            # 親ディレクトリに移動
            parent = current_path.parent
            if parent == current_path:  # ルートに到達した場合
                break
            current_path = parent
        
        # 見つからない場合は現在のディレクトリを使用
        return Path.cwd()
    
    def _setup_base_paths(self):
        """基本パスの設定"""
        # 共通ディレクトリ構造
        self._paths.update({
            "ROOT": str(self.root_dir),
            "DATA_DIR": str(self.root_dir / "data"),
            "LOGS_DIR": str(self.root_dir / "logs"),
            "EXPORTS_DIR": str(self.root_dir / "data" / "exports"),
            "TEMPLATES_DIR": str(self.root_dir / "data" / "templates"),
            "PROJECTS_DIR": str(self.root_dir / "data" / "projects"),
            "MASTER_DIR": str(self.root_dir / "data" / "master"),
            "TEMP_DIR": str(self.root_dir / "data" / "temp"),
            "DB_PATH": str(self.root_dir / "data" / "projects.db"),
            "DASHBOARD_FILE": str(self.root_dir / "data" / "exports" / "dashboard.csv"),
            "PROJECTS_FILE": str(self.root_dir / "data" / "exports" / "projects.csv"),
        })
        
        # 各アプリのパス
        for app_name in ["ProjectManager", "CreateProjectList", "ProjectDashBoard"]:
            self._paths[f"{app_name.upper()}_DIR"] = str(self.root_dir / app_name)
    
    def _load_paths_from_config(self):
        """設定ファイルからパス情報を読み込む"""
        # 複数の可能性のある場所を検索
        config_locations = [
            self.root_dir / self.CONFIG_FILE,
            self.root_dir / "config" / self.CONFIG_FILE,
            Path.home() / "ProjectManagerSuite" / self.CONFIG_FILE
        ]
        
        for config_path in config_locations:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        custom_paths = json.load(f)
                        self._paths.update(custom_paths)
                        logger.info(f"Loaded paths from {config_path}")
                        break
                except Exception as e:
                    logger.error(f"Error loading path config from {config_path}: {e}")
    
    def _override_from_env(self):
        """環境変数からパスをオーバーライド"""
        # PMSUITE_PATH_* という形式の環境変数を探す
        prefix = "PMSUITE_PATH_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                path_key = key[len(prefix):].upper()
                self._paths[path_key] = value
                logger.info(f"Path overridden from environment: {path_key}={value}")
        
        # 特別な環境変数も確認
        special_vars = {
            "PMSUITE_DASHBOARD_FILE": "DASHBOARD_FILE",
            "PMSUITE_DASHBOARD_DATA_DIR": "EXPORTS_DIR",
            "PMSUITE_DB_PATH": "DB_PATH",
            "PMSUITE_DATA_DIR": "DATA_DIR"
        }
        
        for env_var, path_key in special_vars.items():
            if env_var in os.environ:
                self._paths[path_key] = os.environ[env_var]
                logger.info(f"Path overridden from special environment variable: {path_key}={os.environ[env_var]}")
    
    def get_path(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        パスを取得し、問題があれば自動修復を試みる
        
        Args:
            key: パスのキー
            default: パスが見つからない場合のデフォルト値
            
        Returns:
            str: 解決されたパス
        """
        path = self._paths.get(key, default)
        if path is None:
            logger.warning(f"Path not found: {key}")
            return default
            
        # パスの存在確認と自動修復
        path_obj = Path(path)
        if not path_obj.exists():
            # ディレクトリの場合は自動作成を試みる
            if key.endswith('_DIR'):
                try:
                    path_obj.mkdir(parents=True, exist_ok=True)
                    logger.info(f"自動修復: ディレクトリ {key} を作成しました: {path}")
                    return path
                except Exception as e:
                    logger.error(f"自動修復失敗: {key} ({path}): {e}")
            
            # ファイルの場合は親ディレクトリの作成を試みる
            elif key.endswith(('_FILE', '_PATH')):
                try:
                    path_obj.parent.mkdir(parents=True, exist_ok=True)
                    logger.info(f"自動修復: {key} の親ディレクトリを作成しました: {path_obj.parent}")
                    # ファイル自体は作成しない（空ファイルの作成は避ける）
                except Exception as e:
                    logger.error(f"自動修復失敗: {key} の親ディレクトリ ({path_obj.parent}): {e}")
            
            # 代替パスの探索を試みる
            alternative = self._find_alternative(key, path)
            if alternative:
                logger.info(f"代替パスを使用: {key}: {alternative}")
                self._paths[key] = str(alternative)  # 見つかった代替パスで更新
                return str(alternative)
        
        return path
    
    def _find_alternative(self, key: str, original_path: str) -> Optional[Path]:
        """
        欠落しているパスの代替を探索
        
        Args:
            key: パスのキー
            original_path: 元のパス
            
        Returns:
            Path or None: 代替パス（見つからない場合はNone）
        """
        path_obj = Path(original_path)
        
        try:
            # 1. 既知のパターンでの置換を試みる
            patterns = {
                # ProjectManagerSuite -> ProjectManager
                r'ProjectManagerSuite': ['ProjectManager', 'ProjectSuite'],
                # data/exports -> exports
                r'data[/\\]exports': ['exports', 'data'],
                # documents/projects -> projects
                r'documents[/\\]projects': ['projects', 'documents']
            }
            
            for pattern, replacements in patterns.items():
                for replacement in replacements:
                    try:
                        alt_path_str = str(path_obj).replace(pattern, replacement)
                        alt_path = Path(alt_path_str)
                        if alt_path.exists():
                            return alt_path
                    except:
                        continue
            
            # 2. 親ディレクトリでの探索
            if path_obj.name:
                try:
                    # 親ディレクトリ内の同名ファイル/フォルダを検索
                    parent = path_obj.parent
                    if parent.exists():
                        for item in parent.iterdir():
                            # 名前の部分一致で検索（大文字小文字を区別しない）
                            if path_obj.name.lower() in item.name.lower():
                                return item
                except:
                    pass
            
            # 3. 共通のフォールバックディレクトリをチェック
            fallback_locations = [
                self.root_dir,
                self.root_dir / "data",
                Path.home() / "ProjectManagerSuite",
                Path.home() / "Documents" / "ProjectManagerSuite"
            ]
            
            filename = path_obj.name
            for location in fallback_locations:
                try:
                    if location.exists():
                        # 直接のファイル
                        direct = location / filename
                        if direct.exists():
                            return direct
                        
                        # サブディレクトリの検索
                        for item in location.glob(f"**/{filename}"):
                            return item
                except:
                    continue
        except Exception as e:
            logger.error(f"代替パス探索エラー: {e}")
            
        return None
    
    def register_path(self, key: str, path: str) -> None:
        """
        新しいパスを登録
        
        Args:
            key: パスのキー
            path: パス
        """
        self._paths[key.upper()] = str(path)
        logger.info(f"Registered path: {key}={path}")
    
    def ensure_directory(self, key: str) -> Optional[str]:
        """
        指定されたパスのディレクトリを確保
        
        Args:
            key: パスのキー
            
        Returns:
            str: 確保したディレクトリのパス
        """
        path = self.get_path(key)
        if path:
            directory = Path(path)
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {directory}")
            return str(directory)
        return None
    
    def diagnose(self) -> Dict[str, Any]:
        """
        パス設定の健全性診断を実行し、問題点と解決策を提案
        
        Returns:
            dict: 診断レポート
        """
        issues = []
        stats = {
            "total": len(self._paths),
            "missing": 0,
            "permission_issues": 0,
            "type_mismatch": 0
        }
        
        for key, path in self._paths.items():
            path_obj = Path(path)
            
            # 存在チェック
            if not path_obj.exists():
                stats["missing"] += 1
                
                # 問題の種類を特定
                if key.endswith('_DIR'):
                    issue_type = "missing_directory"
                    solution = f"mkdir -p \"{path}\""
                elif key.endswith(('_FILE', '_PATH')):
                    issue_type = "missing_file"
                    solution = f"親ディレクトリの確認: mkdir -p \"{path_obj.parent}\""
                else:
                    issue_type = "missing_path"
                    solution = "パスが存在しません。正しいパスを設定してください。"
                
                issues.append({
                    "key": key,
                    "path": path,
                    "type": issue_type,
                    "solution": solution,
                    "severity": "high" if key in ["DB_PATH", "DATA_DIR"] else "medium"
                })
                continue
            
            # タイプミスマッチ
            if key.endswith('_DIR') and not path_obj.is_dir():
                stats["type_mismatch"] += 1
                issues.append({
                    "key": key,
                    "path": path,
                    "type": "not_a_directory",
                    "solution": "ディレクトリとして指定されたパスがファイルです。正しいディレクトリを指定してください。",
                    "severity": "high"
                })
            
            # 権限チェック
            try:
                if key.endswith(('_DIR', '_FILE', '_PATH')):
                    test_access = False
                    if path_obj.is_dir():
                        # ディレクトリの書き込み権限チェック
                        test_file = path_obj / f".pathregistry_test_{datetime.now().timestamp()}"
                        test_file.touch()
                        test_file.unlink()
                        test_access = True
                    elif path_obj.is_file():
                        # ファイルの読み取り権限チェック
                        with open(path_obj, 'r') as f:
                            f.read(1)
                        test_access = True
                        
                    if not test_access:
                        stats["permission_issues"] += 1
                        issues.append({
                            "key": key,
                            "path": path,
                            "type": "permission_denied",
                            "solution": f"アクセス権限を確認: chmod +rw \"{path}\"",
                            "severity": "high"
                        })
            except Exception as e:
                stats["permission_issues"] += 1
                issues.append({
                    "key": key,
                    "path": path,
                    "type": "access_error",
                    "solution": f"アクセスエラー: {str(e)}",
                    "severity": "high"
                })
        
        # レポート作成
        report = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy" if not issues else "issues_found",
            "stats": stats,
            "issues": issues
        }
        
        return report
    
    def auto_repair(self, issues=None) -> Dict[str, List]:
        """
        診断で見つかった問題を自動修復
        
        Args:
            issues: 問題リスト（Noneの場合は診断を実行）
            
        Returns:
            dict: 修復レポート
        """
        if issues is None:
            # 診断を実行
            diagnosis = self.diagnose()
            issues = diagnosis["issues"]
            
        repaired = []
        failed = []
        
        for issue in issues:
            try:
                key = issue["key"]
                path = issue["path"]
                path_obj = Path(path)
                
                if issue["type"] == "missing_directory":
                    # ディレクトリ作成
                    path_obj.mkdir(parents=True, exist_ok=True)
                    repaired.append({"key": key, "action": "created_directory"})
                    
                elif issue["type"] == "missing_file":
                    # 親ディレクトリを作成
                    path_obj.parent.mkdir(parents=True, exist_ok=True)
                    repaired.append({"key": key, "action": "created_parent_directory"})
                    
                elif issue["type"] in ["permission_denied", "access_error"]:
                    # 権限問題は自動修復が難しいのでスキップ
                    failed.append({"key": key, "reason": "permission_issues_require_manual_fix"})
                    
                else:
                    # その他の問題
                    failed.append({"key": key, "reason": "unsupported_issue_type"})
                
            except Exception as e:
                failed.append({"key": issue["key"], "reason": str(e)})
        
        return {
            "repaired": repaired,
            "failed": failed
        }
    
    def export_config(self, path=None) -> bool:
        """
        現在のパス設定をファイルにエクスポート
        
        Args:
            path: 出力先パス（Noneの場合はデフォルト）
            
        Returns:
            bool: 成功したらTrue
        """
        if path is None:
            path = self.root_dir / self.CONFIG_FILE
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._paths, f, indent=2, ensure_ascii=False)
                logger.info(f"Exported path configuration to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export path configuration: {e}")
            return False
    
    def get_all_paths(self) -> Dict[str, str]:
        """
        全パス情報を取得
        
        Returns:
            dict: 全パス情報
        """
        return dict(self._paths)

# 簡易アクセス関数
def get_path(key: str, default: Optional[str] = None) -> Optional[str]:
    """パスを取得する簡易関数"""
    return PathRegistry.get_instance().get_path(key, default)

def ensure_dir(key: str) -> Optional[str]:
    """ディレクトリを確保する簡易関数"""
    return PathRegistry.get_instance().ensure_directory(key)