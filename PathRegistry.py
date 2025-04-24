"""
パス管理のための統一インターフェース
アプリケーション全体でパスを一元管理し、
環境依存のパス問題を解決する
"""

import os
import sys
import logging
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Set, Any, Union
from datetime import datetime

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
        self._settings_cache = {}  # 設定キャッシュ
        
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
        
        # デフォルトのプロジェクトディレクトリ（修正：Desktopに変更）
        default_projects_dir = os.path.join(os.path.expanduser("~"), "Desktop", "projects")
        self.register_path("PROJECTS_DIR", default_projects_dir)
        self.register_path("OUTPUT_BASE_DIR", default_projects_dir)  # エイリアス
        
        # マスターデータディレクトリ
        self.register_path("MASTER_DIR", os.path.join(user_doc_dir, "ProjectManager", "data", "master"))
        
        # ビルドとデプロイ用
        self.register_path("TEMP_DIR", os.path.join(user_doc_dir, "temp"))
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
        
        # 関連ディレクトリも自動的に作成
        if key.endswith("_DIR") or key.endswith("_FOLDER"):
            try:
                path_obj = Path(path)
                path_obj.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.logger.warning(f"ディレクトリ作成エラー {key}: {e}")
    
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
        
        # 3. エイリアスの処理
        aliases = {
            "PROJECTS_DIR": "OUTPUT_BASE_DIR",
            "OUTPUT_BASE_DIR": "PROJECTS_DIR"
        }
        if key in aliases and aliases[key] in self._paths:
            return self._paths[aliases[key]]
        
        # 4. デフォルト値を返す
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
        if self._settings_cache:
            return self._settings_cache
            
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
                    self._settings_cache = config
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
                    "path": None,
                    "severity": "high",
                    "solution": f"{key}のパスが設定されていません。アプリケーションを再初期化してください。"
                })
                continue
                
            path_obj = Path(path)
            if not path_obj.exists():
                issues.append({
                    "type": "missing_dir",
                    "key": key,
                    "path": path,
                    "severity": "warning",
                    "fixable": True,
                    "solution": f"ディレクトリ {path} が存在しません。自動修復機能で作成できます。"
                })
            elif not path_obj.is_dir():
                issues.append({
                    "type": "not_dir",
                    "key": key,
                    "path": path,
                    "severity": "error",
                    "solution": f"{path} はディレクトリではありません。別のパスを指定してください。"
                })
        
        # DBファイルの確認
        db_path = self.get_path("DB_PATH")
        if db_path:
            db_obj = Path(db_path)
            if not db_obj.parent.exists():
                issues.append({
                    "type": "db_parent_missing",
                    "key": "DB_PATH",
                    "path": str(db_obj.parent),
                    "severity": "warning",
                    "fixable": True,
                    "solution": f"データベースの親ディレクトリ {db_obj.parent} が存在しません。自動修復機能で作成できます。"
                })
        
        # プロジェクトパスの検証
        projects_dir = self.get_path("PROJECTS_DIR")
        if projects_dir:
            try:
                projects_obj = Path(projects_dir)
                if not projects_obj.exists():
                    issues.append({
                        "type": "projects_dir_missing",
                        "key": "PROJECTS_DIR",
                        "path": projects_dir,
                        "severity": "warning",
                        "fixable": True,
                        "solution": f"プロジェクトディレクトリ {projects_dir} が存在しません。自動修復機能で作成できます。"
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
                            "key": "PROJECTS_DIR",
                            "path": projects_dir,
                            "severity": "error",
                            "solution": f"プロジェクトディレクトリ {projects_dir} への書き込み権限がありません。"
                        })
            except Exception as e:
                issues.append({
                    "type": "validation_error",
                    "key": "PROJECTS_DIR",
                    "path": projects_dir,
                    "error": str(e),
                    "severity": "error",
                    "solution": f"プロジェクトディレクトリの検証に失敗しました: {e}"
                })
        
        # 診断結果の返却
        return {
            "issues": issues,
            "total_issues": len(issues),
            "error_count": sum(1 for i in issues if i["severity"] == "error"),
            "warning_count": sum(1 for i in issues if i["severity"] == "warning")
        }

    def migrate_legacy_config(self) -> Dict[str, Any]:
        """
        レガシー設定を新しい形式に移行
        
        Returns:
            Dict[str, Any]: 移行結果情報
        """
        try:
            results = {
                'migrated_paths': [],
                'failed_paths': [],
                'created_dirs': []
            }
            
            # レガシーパス設定ファイルの検索
            legacy_paths = [
                os.path.join(os.path.expanduser("~"), ".projectsuite_paths.txt"),
                os.path.join(self._app_base_path, "paths.config"),
                os.path.join(os.path.expanduser("~"), "Documents", "ProjectManager", "config.txt")
            ]
            
            for path in legacy_paths:
                if os.path.exists(path):
                    try:
                        # レガシー設定ファイルの読み込み
                        with open(path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#'):
                                    try:
                                        key, value = [x.strip() for x in line.split('=', 1)]
                                        # キーの標準化（例: project_dir → PROJECTS_DIR）
                                        normalized_key = self._normalize_legacy_key(key)
                                        if normalized_key:
                                            self.register_path(normalized_key, value)
                                            results['migrated_paths'].append(f"{key} → {normalized_key}: {value}")
                                    except ValueError:
                                        results['failed_paths'].append(f"Invalid format: {line}")
                        
                        # バックアップを作成して名前変更
                        backup_path = f"{path}.bak"
                        if os.path.exists(backup_path):
                            os.remove(backup_path)
                        os.rename(path, backup_path)
                        
                    except Exception as e:
                        self.logger.error(f"レガシー設定ファイル移行エラー {path}: {e}")
                        results['failed_paths'].append(f"{path}: {str(e)}")
            
            # 必須ディレクトリの作成
            essential_dirs = [
                "USER_DATA_DIR", "LOGS_DIR", "DATA_DIR", "PROJECTS_DIR", 
                "CPL_DIR", "CPL_CONFIG_DIR", "CPL_TEMP_DIR"
            ]
            
            for key in essential_dirs:
                if self.ensure_directory(key):
                    results['created_dirs'].append(key)
            
            return results
            
        except Exception as e:
            self.logger.error(f"設定移行エラー: {e}")
            return {
                'error': str(e),
                'migrated_paths': [],
                'failed_paths': [str(e)],
                'created_dirs': []
            }

    def _normalize_legacy_key(self, key: str) -> Optional[str]:
        """
        レガシーキーを新しい形式に変換
        
        Args:
            key: レガシーキー
            
        Returns:
            Optional[str]: 新しいキー。対応するものがなければNone
        """
        # レガシーキーと新キーのマッピング
        key_map = {
            'project_dir': 'PROJECTS_DIR',
            'output_dir': 'PROJECTS_DIR',
            'template_dir': 'TEMPLATES_DIR',
            'master_dir': 'MASTER_DIR',
            'database_path': 'DB_PATH',
            'log_dir': 'LOGS_DIR',
            'data_dir': 'DATA_DIR',
            'export_dir': 'EXPORTS_DIR',
            'temp_dir': 'TEMP_DIR'
        }
        
        # 大文字小文字を無視して検索
        lower_key = key.lower()
        for old_key, new_key in key_map.items():
            if lower_key == old_key.lower():
                return new_key
        
        return None
    
    def auto_repair(self, issues: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List]:
        """
        診断結果に基づく自動修復
        
        Args:
            issues: 診断結果の問題リスト（Noneの場合は自動診断）
            
        Returns:
            Dict[str, List]: 修復結果
        """
        repaired = []
        failed = []
        
        # 問題リストが指定されていない場合は診断を実行
        if issues is None:
            diagnosis = self.diagnose()
            issues = diagnosis["issues"]
        
        for issue in issues:
            if issue.get("fixable", False):
                if issue["type"] == "missing_dir":
                    try:
                        path = Path(issue["path"])
                        path.mkdir(parents=True, exist_ok=True)
                        repaired.append({
                            "key": issue["key"],
                            "path": issue["path"],
                            "action": "created_directory"
                        })
                    except Exception as e:
                        failed.append({
                            "key": issue["key"],
                            "path": issue["path"],
                            "reason": f"ディレクトリ作成失敗: {e}"
                        })
                
                elif issue["type"] == "db_parent_missing":
                    try:
                        path = Path(issue["path"])
                        path.mkdir(parents=True, exist_ok=True)
                        repaired.append({
                            "key": issue["key"],
                            "path": issue["path"],
                            "action": "created_db_parent"
                        })
                    except Exception as e:
                        failed.append({
                            "key": issue["key"],
                            "path": issue["path"],
                            "reason": f"DBパス親ディレクトリ作成失敗: {e}"
                        })
                
                elif issue["type"] == "projects_dir_missing":
                    try:
                        path = Path(issue["path"])
                        path.mkdir(parents=True, exist_ok=True)
                        repaired.append({
                            "key": issue["key"],
                            "path": issue["path"],
                            "action": "created_projects_dir"
                        })
                    except Exception as e:
                        failed.append({
                            "key": issue["key"],
                            "path": issue["path"],
                            "reason": f"プロジェクトディレクトリ作成失敗: {e}"
                        })
        
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
    
    def export_config(self, path: Optional[str] = None) -> bool:
        """
        設定を外部ファイルに保存
        
        Args:
            path: 保存先パス（Noneの場合はデフォルト）
            
        Returns:
            bool: 保存成功時True
        """
        try:
            # 保存先パスの決定
            if path is None:
                user_docs = self.get_path("USER_DATA_DIR")
                if not user_docs:
                    user_docs = os.path.join(os.path.expanduser("~"), "Documents", "ProjectSuite")
                path = os.path.join(user_docs, "path_settings.json")
            
            # 保存するデータの準備
            export_data = {
                "paths": self._paths,
                "timestamp": datetime.now().isoformat(),
                "app_version": "1.0.0"
            }
            
            # 保存
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            return True
            
        except Exception as e:
            self.logger.error(f"設定エクスポートエラー: {e}")
            return False
    
    def import_config(self, path: str) -> bool:
        """
        設定を外部ファイルから読み込み
        
        Args:
            path: 読み込むファイルパス
            
        Returns:
            bool: 読み込み成功時True
        """
        try:
            # ファイルの読み込み
            with open(path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # パスの更新
            if 'paths' in import_data and isinstance(import_data['paths'], dict):
                for key, value in import_data['paths'].items():
                    self.register_path(key, value)
                
            return True
            
        except Exception as e:
            self.logger.error(f"設定インポートエラー: {e}")
            return False
    
    def create_report(self, format: str = "text") -> str:
        """
        パス設定レポートを生成
        
        Args:
            format: レポート形式 ("text", "html", "json")
            
        Returns:
            str: レポート内容
        """
        try:
            # 診断の実行
            diagnosis = self.diagnose()
            
            # パス情報の収集
            paths_info = []
            for key, path in sorted(self._paths.items()):
                path_obj = Path(path) if path else None
                exists = path_obj and path_obj.exists() if path else False
                is_dir = path_obj and path_obj.is_dir() if path else False
                
                paths_info.append({
                    "key": key,
                    "path": path,
                    "exists": exists,
                    "is_directory": is_dir,
                    "is_user_path": key in self._user_paths
                })
            
            # テキスト形式
            if format == "text":
                report = ["PathRegistry レポート", "=" * 30, ""]
                
                # パス情報
                report.append("登録済みパス:")
                for info in paths_info:
                    status = "✓" if info["exists"] else "✗"
                    report.append(f"{status} {info['key']}: {info['path']}")
                
                # 問題
                if diagnosis["issues"]:
                    report.append("\n検出された問題:")
                    for issue in diagnosis["issues"]:
                        report.append(f"- {issue['type']}: {issue.get('key', '')}")
                        report.append(f"  {issue['solution']}")
                else:
                    report.append("\n問題は見つかりませんでした。")
                
                return "\n".join(report)
                
            # HTML形式
            elif format == "html":
                html = [
                    "<!DOCTYPE html>",
                    "<html>",
                    "<head>",
                    "<title>PathRegistry レポート</title>",
                    "<style>",
                    "body { font-family: Arial, sans-serif; margin: 20px; }",
                    "h1 { color: #333; }",
                    "table { border-collapse: collapse; width: 100%; }",
                    "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
                    "th { background-color: #f2f2f2; }",
                    "tr:nth-child(even) { background-color: #f9f9f9; }",
                    ".error { color: red; }",
                    ".warning { color: orange; }",
                    ".ok { color: green; }",
                    "</style>",
                    "</head>",
                    "<body>",
                    "<h1>PathRegistry レポート</h1>",
                    "<h2>登録済みパス</h2>",
                    "<table>",
                    "<tr><th>キー</th><th>パス</th><th>状態</th></tr>"
                ]
                
                # パス情報
                for info in paths_info:
                    status_class = "ok" if info["exists"] else "error"
                    status_text = "存在" if info["exists"] else "未検出"
                    html.append(f"<tr><td>{info['key']}</td><td>{info['path']}</td>"
                              f"<td class='{status_class}'>{status_text}</td></tr>")
                
                html.append("</table>")
                
                # 問題
                if diagnosis["issues"]:
                    html.append("<h2>検出された問題</h2><ul>")
                    for issue in diagnosis["issues"]:
                        severity_class = "error" if issue["severity"] == "error" else "warning"
                        html.append(f"<li class='{severity_class}'><strong>{issue['type']}: {issue.get('key', '')}</strong><br>")
                        html.append(f"{issue['solution']}</li>")
                    html.append("</ul>")
                else:
                    html.append("<h2>問題は見つかりませんでした</h2>")
                
                html.extend(["</body>", "</html>"])
                return "\n".join(html)
                
            # JSON形式
            elif format == "json":
                report_data = {
                    "timestamp": datetime.now().isoformat(),
                    "paths": paths_info,
                    "diagnosis": diagnosis
                }
                return json.dumps(report_data, indent=2, ensure_ascii=False)
                
            else:
                return f"未対応のレポート形式: {format}"
                
        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            return f"レポート生成中にエラーが発生しました: {e}"
    
    def find_data_source(self) -> Optional[Path]:
        """
        データソースディレクトリを検索
        
        Returns:
            Optional[Path]: 検出されたデータソースパス
        """
        # 検索場所のリスト（優先順位順）
        potential_paths = [
            # アプリケーションのデータディレクトリ
            Path(self._app_base_path) / "data",
            
            # ProjectManagerのデータディレクトリ（複数の可能性）
            Path(self._app_base_path) / "ProjectManager" / "data",
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
                    self.logger.info(f"データソースディレクトリを発見: {path}")
                    return path
        
        # 見つからない場合
        self.logger.warning("データソースディレクトリが見つかりませんでした")
        return None


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