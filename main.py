"""
ProjectManagerSuiteのメインエントリーポイント
ProjectManagerを中心に他のアプリケーション(CreateProjectList)を統合管理
"""

import os
import sys
import logging
import traceback
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from tkinter import messagebox
from datetime import datetime

# PathRegistry をインポート
from PathRegistry import PathRegistry, get_path, ensure_dir
# データ移行用のユーティリティをインポート
from data_migrator import DataMigrator

# アプリケーションのルートディレクトリを特定
if getattr(sys, 'frozen', False):
    # PyInstallerで実行ファイル化した場合
    APP_ROOT = Path(sys._MEIPASS)
    
    # アプリケーションディレクトリをPYTHONPATHに追加
    if str(APP_ROOT) not in sys.path:
        sys.path.insert(0, str(APP_ROOT))
else:
    # 開発環境での実行
    APP_ROOT = Path(__file__).parent

# 適切な形式でインポート
try:
    # ユーティリティのインポート
    try:
        from utils.path_utils import get_app_root, ensure_directory
        from utils.dependency_checker import check_python_version
    except ImportError:
        # utils モジュールが使えない場合のフォールバック
        def get_app_root():
            return APP_ROOT
            
        def ensure_directory(path):
            path.mkdir(parents=True, exist_ok=True)
            return path
            
        def check_python_version(min_version=(3, 8, 0)):
            return sys.version_info[:3] >= min_version
    
    # パッケージからのインポートを試みる
    from ProjectManager.src.core.config import Config
    from ProjectManager.src.core.database import DatabaseManager
    from ProjectManager.src.ui.dashboard import DashboardGUI
    from ProjectManager.src.services.task_loader import TaskLoader
except ImportError:
    # 相対パスからのインポートを試みる
    sys.path.insert(0, str(APP_ROOT))
    from ProjectManager.src.core.config import Config
    from ProjectManager.src.core.database import DatabaseManager
    from ProjectManager.src.ui.dashboard import DashboardGUI
    from ProjectManager.src.services.task_loader import TaskLoader

def initialize_sample_data():
    """サンプルデータをユーザーデータディレクトリに直接配置"""
    try:
        print("サンプルデータの初期化を開始します...")
        
        # ターゲットディレクトリ
        target_dir = Path.home() / "Documents" / "ProjectSuite"
        target_data_dir = target_dir / "ProjectManager" / "data"
        print(f"Debug: ターゲットディレクトリ: {target_dir}")
        print(f"Debug: ターゲットデータディレクトリ: {target_data_dir}")
        
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_data_dir.mkdir(parents=True, exist_ok=True)
            print(f"Debug: ターゲットディレクトリを作成しました")
        except Exception as e:
            print(f"Warning: ターゲットディレクトリの作成に失敗しました: {e}")
        
        # 必要なディレクトリを作成
        logs_dir = target_dir / "logs"
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
            print(f"Debug: ログディレクトリを作成しました: {logs_dir}")
        except Exception as e:
            print(f"Warning: ログディレクトリの作成に失敗しました: {e}")
        
        for subdir in ["temp", "backup"]:
            try:
                (target_dir / subdir).mkdir(parents=True, exist_ok=True)
                print(f"Debug: サブディレクトリを作成しました: {target_dir / subdir}")
            except Exception as e:
                print(f"Warning: サブディレクトリ {subdir} の作成に失敗しました: {e}")
        
        # ユーザードキュメントフォルダ内のinitialdataを探す
        source_data = target_dir / "initialdata"
        print(f"Debug: 初期ソースデータディレクトリパス: {source_data}")
        print(f"Debug: ソースディレクトリ存在チェック: {source_data.exists()}")
        
        # initialdata が見つからない場合の代替パス
        if not source_data.exists():
            print(f"Warning: {source_data} が見つかりません。代替パスを検索します。")
            
            # 可能性のある候補パス
            candidate_paths = [
                Path(sys.executable).parent / "initialdata",  # 実行ファイルと同じフォルダ
                Path(sys._MEIPASS).parent / "initialdata" if getattr(sys, 'frozen', False) else None,  # PyInstaller環境
                Path('C:/Users/') / os.getlogin() / 'Downloads' / 'installer' / 'initialdata',  # ダウンロードフォルダ
                Path('C:/Program Files (x86)/ProjectSuite/initialdata'),  # インストール先フォルダ
                APP_ROOT / "initialdata"  # アプリケーションルートディレクトリ
            ]
            
            for path in candidate_paths:
                if path and path.exists():
                    print(f"Debug: 代替データソースを発見: {path}")
                    source_data = path
                    break
        
        # 初期データ生成
        print("初期データを生成しています...")
        
        # サブディレクトリの作成
        for subdir in ["exports", "master", "projects", "templates"]:
            target_subdir = target_data_dir / subdir
            try:
                target_subdir.mkdir(parents=True, exist_ok=True)
                print(f"Debug: データサブディレクトリを作成しました: {target_subdir}")
            except Exception as e:
                print(f"Warning: データサブディレクトリ {subdir} の作成に失敗しました: {e}")
                continue
            
            # initialdataフォルダからコピー(存在する場合)
            if source_data.exists():
                src_subdir = source_data / subdir
                if src_subdir.exists():
                    print(f"Debug: ソースサブディレクトリが存在します: {src_subdir}")
                    for src_file in src_subdir.glob("**/*"):
                        if src_file.is_file():
                            try:
                                rel_path = src_file.relative_to(src_subdir)
                                dst_file = target_subdir / rel_path
                                dst_file.parent.mkdir(parents=True, exist_ok=True)
                                if not dst_file.exists():  # 既存ファイルを上書きしない
                                    print(f"Debug: ファイルをコピーします: {src_file} -> {dst_file}")
                                    shutil.copy2(src_file, dst_file)
                                    print(f"  コピー: {rel_path}")
                                else:
                                    print(f"Debug: ファイルは既に存在します: {dst_file}")
                            except Exception as file_err:
                                print(f"Warning: ファイルコピーエラー: {src_file} -> {file_err}")
        
        # 必要最小限のファイル作成
        create_minimal_sample_files(target_data_dir)
        
        # initialdata自体はもう不要なので、処理が完了したら削除
        if source_data.exists():
            try:
                shutil.rmtree(source_data)
                print("一時データディレクトリを削除しました")
            except Exception as e:
                print(f"Warning: 一時データディレクトリの削除に失敗しました: {e}")
            
        # 初期化完了マークを作成
        init_flag = target_dir / ".init_complete"
        try:
            with open(init_flag, 'w') as f:
                f.write(datetime.now().isoformat())
            print(f"Debug: 初期化完了マークを作成しました: {init_flag}")
        except Exception as e:
            print(f"Warning: 初期化完了マークの作成に失敗しました: {e}")
        
        print("初期データの配置が完了しました")
        return True
        
    except Exception as e:
        print(f"初期データ配置エラー: {e}")
        traceback.print_exc()
        return False

def create_minimal_sample_files(target_dir):
    """最小限必要なサンプルファイルを作成する"""
    # データベースファイル
    db_path = target_dir / "projects.db"
    if not db_path.exists():
        # 空のSQLiteデータベースファイルを作成
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.close()
        print(f"  空のデータベースを作成: {db_path}")
    
    # マスターデータ
    master_dir = target_dir / "master"
    master_dir.mkdir(parents=True, exist_ok=True)
    factory_info = master_dir / "factory_info.csv"
    if not factory_info.exists():
        # 基本的なマスターデータを作成
        with open(factory_info, 'w', encoding='utf-8') as f:
            f.write("division_code,division_name,factory_code,factory_name,process_code,process_name,line_code,line_name\n")
            f.write("D001,開発事業部,F001,第一工場,P001,組立工程,L001,組立ライン1\n")
            f.write("D001,開発事業部,F001,第一工場,P001,組立工程,L002,組立ライン2\n")
            f.write("D001,開発事業部,F002,第二工場,P002,検査工程,L003,検査ライン1\n")
        print(f"  サンプルマスターデータを作成: {factory_info}")
    
    # エクスポートファイル
    exports_dir = target_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    dashboard_file = exports_dir / "dashboard.csv"
    projects_file = exports_dir / "projects.csv"
    if not dashboard_file.exists():
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write("project_id,project_name,manager,division,factory,process,line,status,created_at\n")
        print(f"  空のダッシュボードファイルを作成: {dashboard_file}")
    if not projects_file.exists():
        with open(projects_file, 'w', encoding='utf-8') as f:
            f.write("project_id,project_name,start_date,manager,reviewer,approver,division,factory,process,line,status,project_path,ganttchart_path,created_at,updated_at\n")
        print(f"  空のプロジェクトファイルを作成: {projects_file}")
    
    # テンプレートファイル
    templates_dir = target_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir = templates_dir / "999. metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    with open(metadata_dir / "工程表作成補助アプリ_#案件名#.csv", 'w', encoding='utf-8') as f:
        f.write("task_name,task_start_date,task_finish_date,task_status,task_milestone,task_assignee,task_work_hours\n")
        f.write("サンプルタスク,2025-04-01,2025-04-30,未着手,計画,担当者名,8\n")
    print(f"  基本テンプレートファイルを作成: {metadata_dir}")

def setup_logging() -> None:
    """
    ログ設定を初期化する
    
    ログファイルとコンソールの両方に出力を設定
    """
    try:
        # ユーザードキュメントフォルダ内にログディレクトリを作成
        user_log_dir = Path.home() / "Documents" / "ProjectSuite" / "logs"
        
        # 明示的に例外処理を追加
        try:
            user_log_dir.mkdir(parents=True, exist_ok=True)
            user_log_file = user_log_dir / "app.log"
        except PermissionError as pe:
            print(f"Warning: ログディレクトリの作成に権限がありません: {pe}")
            # フォールバックとして一時ディレクトリを使用
            import tempfile
            user_log_dir = Path(tempfile.gettempdir()) / "ProjectSuite" / "logs"
            user_log_dir.mkdir(parents=True, exist_ok=True)
            user_log_file = user_log_dir / "app.log"
            print(f"Info: 代替ログディレクトリを使用します: {user_log_dir}")
        
        # ログハンドラーの設定
        handlers = [
            logging.FileHandler(user_log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
        
        # ログフォーマットの設定
        formatter = logging.Formatter(Config.LOG_FORMAT)
        for handler in handlers:
            handler.setFormatter(formatter)
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # 既存のハンドラーをクリア
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # 新しいハンドラーを追加
        for handler in handlers:
            root_logger.addHandler(handler)
            
        logging.info("ログ設定を初期化しました")
        
    except Exception as e:
        print(f"ログ設定の初期化に失敗しました: {e}")
        # ログ設定に失敗してもアプリケーションは継続する
        # raise の代わりに標準出力のみに出力
        import traceback
        print(traceback.format_exc())

def setup_environment() -> None:
    """
    アプリケーション環境のセットアップ
    
    - ユーザードキュメントフォルダの確認と作成
    - 設定ファイルの確認
    - データの移行
    - PathRegistryの初期化と診断
    """
    try:
        # PathRegistryの初期化
        registry = PathRegistry.get_instance()
        
        # 基本パスの登録
        registry.register_path("ROOT", str(APP_ROOT))
        
        # ユーザードキュメントのProjectSuiteディレクトリを登録
        user_docs_dir = Path.home() / "Documents" / "ProjectSuite"
        registry.register_path("USER_DATA_DIR", str(user_docs_dir))
        
        # 初回起動かどうかの確認
        is_first_run = registry.check_first_run()
        
        if is_first_run:
            logging.info("初回起動を検出しました。データを移行します。")
            
            # 初期データの配置を実行
            initialize_sample_data()
            
        else:
            logging.info("既存のユーザーデータディレクトリを使用します。")
        
        # 診断を実行して問題を検出
        diagnosis = registry.diagnose()
        if diagnosis['issues']:
            logging.warning(f"{len(diagnosis['issues'])}件のパス問題を検出しました")
            # 自動修復を試行
            repair_result = registry.auto_repair(diagnosis['issues'])
            logging.info(f"自動修復: {len(repair_result['repaired'])}件成功, {len(repair_result['failed'])}件失敗")
        
        # ディレクトリの作成
        ensure_dir("LOGS_DIR")
        ensure_dir("DATA_DIR")
        ensure_dir("EXPORTS_DIR")
        ensure_dir("TEMPLATES_DIR")
        ensure_dir("PROJECTS_DIR")
        ensure_dir("MASTER_DIR")
        ensure_dir("TEMP_DIR")
        ensure_dir("BACKUP_DIR")
                
        # defaults.txtの確認
        defaults_path = APP_ROOT / "defaults.txt"
        if not defaults_path.exists():
            # ProjectManagerからコピー
            source = APP_ROOT / "ProjectManager" / "defaults.txt"
            if source.exists():
                shutil.copy(source, defaults_path)
                print(f"デフォルト設定ファイルをコピー: {source} -> {defaults_path}")
            else:
                # デフォルト内容で新規作成
                with open(defaults_path, "w", encoding="utf-8") as f:
                    f.write("""default_project_name=新規プロジェクト
default_manager=山田太郎
default_reviewer=鈴木一郎
default_approver=佐藤部長
default_division=D001
default_factory=F001
default_process=P001
default_line=L001""")
                print(f"デフォルト設定ファイルを作成: {defaults_path}")
        
        # Pythonバージョンの確認
        if not check_python_version():
            print("警告: Python 3.8.0以上を推奨します")
            
    except Exception as e:
        print(f"環境設定エラー: {e}")
        raise

def initialize_app() -> Optional[DatabaseManager]:
    """
    アプリケーションの初期化処理
    
    Returns:
        Optional[DatabaseManager]: 初期化されたデータベースマネージャー。
                                 エラー時はNone
    """
    try:
        # 環境のセットアップ
        setup_environment()
        
        # アダプターの適用
        try:
            from ProjectManager.config_adapters_pm import adapt_project_manager_config
            adapt_project_manager_config()
            logging.info("ProjectManager設定アダプターを適用しました")
        except Exception as e:
            logging.warning(f"設定アダプター適用エラー: {e}")
        
        # ディレクトリ構造の作成
        Config.setup_directories()
        
        # ログ設定
        setup_logging()
        logging.info("アプリケーションを開始します")
        
        # 環境の検証
        Config.validate_environment()
        
        # データベースマネージャーの初期化とマイグレーション
        db_path = get_path("DB_PATH", Config.DB_PATH)
        db_manager = DatabaseManager(db_path)
        logging.info("データベースマネージャーを初期化しました")
        
        # タスクデータの読み込み
        try:
            task_loader = TaskLoader(db_manager)
            task_loader.load_tasks()
            logging.info("タスクデータを読み込みました")
            
        except Exception as e:
            logging.error(f"データ読み込みエラー: {e}\n{traceback.format_exc()}")
            messagebox.showwarning(
                "警告",
                "データの読み込み中にエラーが発生しました。\n"
                "アプリケーションは起動しますが、データが正しく反映されていない可能性があります。"
            )
        
        return db_manager
        
    except FileNotFoundError as e:
        error_msg = f"必要なファイルが見つかりません: {e}"
        logging.error(error_msg)
        messagebox.showerror("初期化エラー", error_msg)
    except PermissionError as e:
        error_msg = f"アクセス権限がありません: {e}"
        logging.error(error_msg)
        messagebox.showerror("初期化エラー", error_msg)
    except ValueError as e:
        error_msg = f"設定値が不正です: {e}"
        logging.error(error_msg)
        messagebox.showerror("初期化エラー", error_msg)
    except Exception as e:
        error_msg = f"予期せぬエラーが発生しました: {e}"
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        messagebox.showerror("初期化エラー", error_msg)
    
    return None

def run_standalone_app(app_name: str, *args) -> int:
    """
    指定されたアプリケーションをスタンドアロンモードで実行
    
    Args:
        app_name: アプリケーション名
        *args: アプリケーションに渡す引数
        
    Returns:
        int: 終了コード
    """
    # アプリケーション定義
    apps = {
        "CreateProjectList": {
            "module": "CreateProjectList.main.document_processor_main",
            "main_func": "main"
        }
        # "ProjectDashBoard" エントリを削除
    }
    
    try:
        if app_name not in apps:
            print(f"未知のアプリケーション: {app_name}")
            return 1
            
        app_info = apps[app_name]
        
        # モジュールから関数をインポートして実行
        if app_info["module"] and app_info["main_func"]:
            module = __import__(app_info["module"], fromlist=[app_info["main_func"]])
            main_func = getattr(module, app_info["main_func"])
            main_func(*args)
            return 0
        
        # ファイルを直接実行
        elif app_info["module"] and not app_info["main_func"]:
            import subprocess
            
            module_path = app_info["module"].replace(".", os.path.sep) + ".py"
            full_path = APP_ROOT / module_path
            
            # サブプロセスとして実行
            process = subprocess.Popen(
                [sys.executable, str(full_path)] + list(args),
                env=os.environ.copy()
            )
            
            # このプロセスはメインプロセスの終了を待たず独立して実行
            return 0
            
        else:
            print(f"アプリケーション{app_name}の起動方法が定義されていません")
            return 1
            
    except Exception as e:
        print(f"{app_name}実行エラー: {e}\n{traceback.format_exc()}")
        return 1

def main() -> None:
    """
    アプリケーションのメインエントリーポイント
    """
    # コマンドライン引数を解析
    if len(sys.argv) > 1:
        # 特殊コマンド：サンプルデータの初期化
        if sys.argv[1] == "init-data":
            success = initialize_sample_data()
            sys.exit(0 if success else 1)
        else:
            app_name = sys.argv[1]
            app_args = sys.argv[2:]
            sys.exit(run_standalone_app(app_name, *app_args))
    
    # メインアプリケーション（ProjectManager）の起動
    db_manager = None
    try:
        # アプリケーションの初期化
        db_manager = initialize_app()
        if not db_manager:
            return
        
        # GUIの起動
        app = DashboardGUI(db_manager)
        
        try:
            app.run()
        except Exception as e:
            error_msg = f"GUIの実行中にエラーが発生しました: {e}"
            logging.error(f"{error_msg}\n{traceback.format_exc()}")
            messagebox.showerror("エラー", error_msg)
        
    except Exception as e:
        error_msg = f"アプリケーション実行中にエラーが発生しました: {e}"
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        messagebox.showerror("エラー", error_msg)
        
    finally:
        # クリーンアップ処理
        if db_manager:
            logging.info("アプリケーションを終了します")

if __name__ == "__main__":
    main()