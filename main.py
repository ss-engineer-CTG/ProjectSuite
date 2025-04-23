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
from typing import Optional, Dict, Any, List
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

def find_installer_and_copy_initialdata() -> bool:
    """
    インストーラーファイルを検索し、隣接するinitialdataフォルダから必要なファイルをコピー
    
    Returns:
        bool: コピーに成功したらTrue
    """
    try:
        print("インストーラーとinitialdataの検索を開始...")
        
        # 検索対象のディレクトリ
        search_paths = [
            Path.home() / "Downloads",
            Path.home() / "Desktop",
            Path(os.getenv("TEMP", "")),
            Path.home() / "Documents",
            Path.home() / "Downloads" / "installer",
            Path.cwd(),
            Path.cwd() / "installer",
        ]
        
        # インストーラーファイルのパターン
        installer_pattern = "ProjectSuite_Setup_*.exe"
        
        # インストーラーファイルを検索
        installer_found = False
        initialdata_copied = False
        copy_errors = []
        
        for path in search_paths:
            if not path.exists():
                continue
                
            print(f"ディレクトリを検索中: {path}")
            
            # ディレクトリとすべてのサブディレクトリを検索
            for file in path.glob(f"**/{installer_pattern}"):
                installer_found = True
                print(f"インストーラーが見つかりました: {file}")
                
                # インストーラーの親ディレクトリにinitialdataがあるか確認
                initialdata_path = file.parent / "initialdata"
                if initialdata_path.exists() and initialdata_path.is_dir():
                    print(f"initialdataフォルダが見つかりました: {initialdata_path}")
                    
                    # ユーザードキュメントのProjectSuiteディレクトリ
                    target_dir = Path.home() / "Documents" / "ProjectSuite"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # ProjectManager/dataディレクトリ
                    pm_data_dir = target_dir / "ProjectManager" / "data"
                    pm_data_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 各サブディレクトリを作成
                    subdirs = ["exports", "master", "projects", "templates"]
                    for subdir in subdirs:
                        subdir_path = pm_data_dir / subdir
                        subdir_path.mkdir(parents=True, exist_ok=True)
                    
                    # ログディレクトリを作成
                    log_dir = target_dir / "logs"
                    log_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 一時ファイル用ディレクトリ
                    temp_dir = target_dir / "temp"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    
                    # バックアップディレクトリ
                    backup_dir = target_dir / "backup"
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 1. データベースファイルのコピー
                    try:
                        src_db = initialdata_path / "projects.db"
                        if src_db.exists():
                            dst_db = pm_data_dir / "projects.db"
                            try:
                                shutil.copy2(src_db, dst_db)
                                print(f"データベースファイルをコピーしました: {dst_db}")
                            except PermissionError:
                                print(f"データベースコピー権限エラー: {dst_db}へのアクセスが拒否されました")
                                copy_errors.append(f"DB: {dst_db}")
                            except Exception as db_err:
                                print(f"データベースコピーエラー: {db_err}")
                                copy_errors.append(f"DB: {str(db_err)}")
                    except Exception as db_ex:
                        print(f"データベース処理エラー: {db_ex}")
                        copy_errors.append(f"DB処理: {str(db_ex)}")
                    
                    # 2. 各サブディレクトリのファイルをコピー
                    for subdir in subdirs:
                        try:
                            src_subdir = initialdata_path / subdir
                            if src_subdir.exists() and src_subdir.is_dir():
                                dst_subdir = pm_data_dir / subdir
                                
                                # ファイルを個別にコピー
                                file_copied = 0
                                for src_file in src_subdir.glob("**/*"):
                                    if src_file.is_file():
                                        try:
                                            # 相対パスを維持
                                            rel_path = src_file.relative_to(src_subdir)
                                            dst_file = dst_subdir / rel_path
                                            
                                            # 親ディレクトリを作成
                                            dst_file.parent.mkdir(parents=True, exist_ok=True)
                                            
                                            # ファイルが存在しない場合のみコピー
                                            if not dst_file.exists():
                                                shutil.copy2(src_file, dst_file)
                                                file_copied += 1
                                        except PermissionError:
                                            print(f"ファイルコピー権限エラー: {dst_file}")
                                            copy_errors.append(f"{subdir}/{rel_path}")
                                        except Exception as file_err:
                                            print(f"ファイルコピーエラー: {file_err}")
                                            copy_errors.append(f"{subdir}/{rel_path}: {str(file_err)}")
                                
                                print(f"  {subdir}ディレクトリから{file_copied}ファイルをコピーしました")
                        except Exception as dir_err:
                            print(f"  {subdir}ディレクトリ処理エラー: {dir_err}")
                            copy_errors.append(f"{subdir}: {str(dir_err)}")
                    
                    # 3. 初期化完了マークの作成
                    try:
                        init_flag = target_dir / ".init_complete"
                        with open(init_flag, 'w') as f:
                            f.write(datetime.now().isoformat())
                        print("初期化完了マークを作成しました")
                    except Exception as flag_err:
                        print(f"初期化マーク作成エラー: {flag_err}")
                        copy_errors.append(f"初期化マーク: {str(flag_err)}")
                    
                    # 4. コピー結果の確認
                    if copy_errors:
                        print(f"一部のファイルコピーに失敗しました ({len(copy_errors)}件):")
                        for err in copy_errors[:5]:  # 最初の5件のみ表示
                            print(f"  - {err}")
                        if len(copy_errors) > 5:
                            print(f"  ... 他 {len(copy_errors) - 5} 件")
                            
                        # エラーがあっても成功したファイルはあるのでTrueを返す
                        initialdata_copied = True
                    else:
                        initialdata_copied = True
                        print("すべてのファイルが正常にコピーされました")
                    
                    return initialdata_copied
        
        # 結果のログ出力
        if installer_found and not initialdata_copied:
            print("インストーラーは見つかりましたが、initialdataフォルダが見つかりませんでした")
        elif not installer_found:
            print("インストーラーファイルが見つかりませんでした")
        
        return initialdata_copied
        
    except Exception as e:
        print(f"initialdataコピーエラー: {e}")
        traceback.print_exc()
        return False

def try_copy_critical_files() -> bool:
    """
    重要なファイルを手動で確実にコピー
    
    Returns:
        bool: 重要なファイルのコピーに成功したらTrue
    """
    try:
        # 検索パス
        search_paths = [
            Path.home() / "Downloads" / "installer" / "initialdata",
            Path.home() / "Documents" / "ProjectSuite" / "initialdata",
            Path.cwd() / "installer" / "initialdata",
            Path("installer") / "initialdata",
        ]
        
        # ターゲットパス
        target_dir = Path.home() / "Documents" / "ProjectSuite"
        pm_data_dir = target_dir / "ProjectManager" / "data"
        
        # 重要なファイルリスト (ソース相対パス, 宛先絶対パス)
        critical_files = [
            ("projects.db", pm_data_dir / "projects.db"),
            ("master/factory_info.csv", pm_data_dir / "master" / "factory_info.csv"),
            ("exports/dashboard.csv", pm_data_dir / "exports" / "dashboard.csv"),
            ("exports/projects.csv", pm_data_dir / "exports" / "projects.csv")
        ]
        
        # ディレクトリの事前作成
        pm_data_dir.mkdir(parents=True, exist_ok=True)
        (pm_data_dir / "master").mkdir(parents=True, exist_ok=True)
        (pm_data_dir / "exports").mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        
        for src_rel_path, dst_path in critical_files:
            for search_path in search_paths:
                src_path = search_path / src_rel_path
                if src_path.exists() and src_path.is_file():
                    try:
                        # 親ディレクトリ確保
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # ファイルコピー
                        shutil.copy2(src_path, dst_path)
                        print(f"重要ファイルをコピーしました: {src_path} -> {dst_path}")
                        success_count += 1
                        break  # このファイルのコピーに成功したら次のファイルへ
                    except Exception as e:
                        print(f"ファイルコピーエラー ({src_path}): {e}")
        
        return success_count > 0
        
    except Exception as e:
        print(f"重要ファイルコピーエラー: {e}")
        return False

def initialize_sample_data():
    """サンプルデータをユーザーデータディレクトリに直接配置"""
    try:
        print("サンプルデータの初期化を開始します...")
        
        # 1. まず新しいアプローチでinitialdataのコピーを試みる
        if find_installer_and_copy_initialdata():
            print("インストーラーからinitialdataをコピーしました")
        else:
            print("インストーラーからのコピーに失敗しました。代替手段を試行...")
            
            # 2. 重要ファイルの直接コピーを試みる
            if try_copy_critical_files():
                print("重要なファイルのコピーに成功しました")
            else:
                print("重要ファイルのコピーにも失敗しました。最小構成で初期化します...")
        
        # ターゲットディレクトリ
        target_dir = Path.home() / "Documents" / "ProjectSuite"
        target_data_dir = target_dir / "ProjectManager" / "data"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_data_dir.mkdir(parents=True, exist_ok=True)
        
        # CreateProjectList用のディレクトリも作成
        cpl_dir = target_dir / "CreateProjectList"
        cpl_dir.mkdir(parents=True, exist_ok=True)
        (cpl_dir / "config").mkdir(parents=True, exist_ok=True)
        (cpl_dir / "temp").mkdir(parents=True, exist_ok=True)
        (cpl_dir / "templates").mkdir(parents=True, exist_ok=True)
        (cpl_dir / "cache").mkdir(parents=True, exist_ok=True)
        
        # 必要なディレクトリを作成
        logs_dir = target_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        for subdir in ["temp", "backup"]:
            (target_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # ユーザードキュメントフォルダ内のinitialdataを探す
        source_data = target_dir / "initialdata"
        
        # initialdataが見つかった場合は各サブディレクトリにコピー
        if source_data.exists() and source_data.is_dir():
            print("initialdataフォルダが見つかりました。ファイルをコピーします...")
            
            # サブディレクトリの作成とコピー
            for subdir in ["exports", "master", "projects", "templates"]:
                target_subdir = target_data_dir / subdir
                target_subdir.mkdir(parents=True, exist_ok=True)
                
                src_subdir = source_data / subdir
                if src_subdir.exists():
                    for src_file in src_subdir.glob("**/*"):
                        if src_file.is_file():
                            try:
                                rel_path = src_file.relative_to(src_subdir)
                                dst_file = target_subdir / rel_path
                                dst_file.parent.mkdir(parents=True, exist_ok=True)
                                if not dst_file.exists():  # 既存ファイルを上書きしない
                                    shutil.copy2(src_file, dst_file)
                                    print(f"  コピー: {rel_path}")
                            except Exception as e:
                                print(f"  ファイルコピーエラー ({src_file.name}): {e}")
            
            # CreateProjectList用のデータもコピー
            src_cpl_dir = source_data / "CreateProjectList"
            if src_cpl_dir.exists():
                for src_file in src_cpl_dir.glob("**/*"):
                    if src_file.is_file():
                        try:
                            rel_path = src_file.relative_to(src_cpl_dir)
                            dst_file = cpl_dir / rel_path
                            dst_file.parent.mkdir(parents=True, exist_ok=True)
                            if not dst_file.exists():  # 既存ファイルを上書きしない
                                shutil.copy2(src_file, dst_file)
                                print(f"  CPLファイルコピー: {rel_path}")
                        except Exception as e:
                            print(f"  CPLファイルコピーエラー ({src_file.name}): {e}")
            
            # initialdataは処理完了後に削除しない（削除時の権限エラー回避）
            print("initialdataフォルダの処理が完了しました（フォルダは維持されます）")
        else:
            print("initialdataフォルダが見つかりません。最小限のサンプルファイルを作成します。")
        
        # 必要最小限のファイル作成
        create_minimal_sample_files(target_data_dir)
        
        # CreateProjectList用の設定ファイルを作成
        create_cpl_config_file(cpl_dir)
        
        # 初期化完了マークを作成
        try:
            init_flag = target_dir / ".init_complete"
            with open(init_flag, 'w') as f:
                f.write(datetime.now().isoformat())
            print("初期化完了マークを作成しました")
        except Exception as e:
            print(f"初期化マーク作成エラー: {e}")
        
        print("初期データの配置が完了しました")
        return True
        
    except Exception as e:
        print(f"初期データ配置エラー: {e}")
        traceback.print_exc()
        return False

def create_cpl_config_file(cpl_dir: Path) -> None:
    """
    CreateProjectList用の設定ファイルを作成
    
    Args:
        cpl_dir: CreateProjectListディレクトリパス
    """
    config_file = cpl_dir / "config" / "config.json"
    
    # 既に存在する場合は何もしない
    if config_file.exists():
        return
    
    try:
        # ユーザーフォルダのパスを取得
        user_dir = Path.home() / "Documents" / "ProjectSuite"
        
        # 基本的な設定を作成
        config = {
            "db_path": str(user_dir / "ProjectManager" / "data" / "projects.db"),
            "last_input_folder": str(user_dir / "ProjectManager" / "data" / "templates"),
            "last_output_folder": str(user_dir / "ProjectManager" / "data" / "projects"),
            "replacement_rules": [
                {"search": "#案件名#", "replace": "project_name"},
                {"search": "#作成日#", "replace": "start_date"},
                {"search": "#工場#", "replace": "factory"},
                {"search": "#工程#", "replace": "process"},
                {"search": "#ライン#", "replace": "line"},
                {"search": "#作成者#", "replace": "manager"},
                {"search": "#確認者#", "replace": "reviewer"},
                {"search": "#承認者#", "replace": "approver"},
                {"search": "#事業部#", "replace": "division"}
            ],
            "last_update": datetime.now().isoformat(),
            "temp_dir": str(user_dir / "CreateProjectList" / "temp")
        }
        
        # JSONとして保存
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"CreateProjectList設定ファイルを作成: {config_file}")
        
    except Exception as e:
        print(f"CreateProjectList設定ファイル作成エラー: {e}")

def create_minimal_sample_files(target_dir):
    """最小限必要なサンプルファイルを作成する"""
    # データベースファイル
    db_path = target_dir / "projects.db"
    if not db_path.exists():
        try:
            # 空のSQLiteデータベースファイルを作成
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.close()
            print(f"  空のデータベースを作成: {db_path}")
        except Exception as e:
            print(f"  データベース作成エラー: {e}")
    
    # マスターデータ
    master_dir = target_dir / "master"
    master_dir.mkdir(parents=True, exist_ok=True)
    factory_info = master_dir / "factory_info.csv"
    if not factory_info.exists():
        try:
            # 基本的なマスターデータを作成
            with open(factory_info, 'w', encoding='utf-8') as f:
                f.write("division_code,division_name,factory_code,factory_name,process_code,process_name,line_code,line_name\n")
                f.write("D001,開発事業部,F001,第一工場,P001,組立工程,L001,組立ライン1\n")
                f.write("D001,開発事業部,F001,第一工場,P001,組立工程,L002,組立ライン2\n")
                f.write("D001,開発事業部,F002,第二工場,P002,検査工程,L003,検査ライン1\n")
            print(f"  サンプルマスターデータを作成: {factory_info}")
        except Exception as e:
            print(f"  マスターデータ作成エラー: {e}")
    
    # エクスポートファイル
    exports_dir = target_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    dashboard_file = exports_dir / "dashboard.csv"
    projects_file = exports_dir / "projects.csv"
    
    if not dashboard_file.exists():
        try:
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write("project_id,project_name,manager,division,factory,process,line,status,created_at\n")
            print(f"  空のダッシュボードファイルを作成: {dashboard_file}")
        except Exception as e:
            print(f"  ダッシュボードファイル作成エラー: {e}")
            
    if not projects_file.exists():
        try:
            with open(projects_file, 'w', encoding='utf-8') as f:
                f.write("project_id,project_name,start_date,manager,reviewer,approver,division,factory,process,line,status,project_path,ganttchart_path,created_at,updated_at\n")
            print(f"  空のプロジェクトファイルを作成: {projects_file}")
        except Exception as e:
            print(f"  プロジェクトファイル作成エラー: {e}")
    
    # テンプレートファイル
    templates_dir = target_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir = templates_dir / "999. metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    
    template_file = metadata_dir / "工程表作成補助アプリ_#案件名#.csv"
    if not template_file.exists():
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write("task_name,task_start_date,task_finish_date,task_status,task_milestone,task_assignee,task_work_hours\n")
                f.write("サンプルタスク,2025-04-01,2025-04-30,未着手,計画,担当者名,8\n")
            print(f"  基本テンプレートファイルを作成: {template_file}")
        except Exception as e:
            print(f"  テンプレートファイル作成エラー: {e}")

def setup_logging() -> None:
    """
    ログ設定を初期化する
    
    ログファイルとコンソールの両方に出力を設定
    """
    try:
        # ユーザードキュメントフォルダ内にログディレクトリを作成
        user_log_dir = Path.home() / "Documents" / "ProjectSuite" / "logs"
        user_log_dir.mkdir(parents=True, exist_ok=True)
        user_log_file = user_log_dir / "app.log"
        
        # ログハンドラーの設定
        handlers = []
        
        # ファイルハンドラー（権限エラーに対応）
        try:
            file_handler = logging.FileHandler(user_log_file, encoding='utf-8')
            handlers.append(file_handler)
        except PermissionError:
            print(f"Warning: ログファイルの作成権限がありません: {user_log_file}")
        except Exception as e:
            print(f"Warning: ログファイルハンドラーの作成に失敗: {e}")
        
        # コンソールハンドラー（常に追加）
        handlers.append(logging.StreamHandler(sys.stdout))
        
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
            # 毎回起動時に権限エラーなしの再コピー処理を行う
            try_copy_critical_files()
            logging.info("既存のユーザーデータディレクトリを使用します。")
        
        # 診断を実行して問題を検出
        diagnosis = registry.diagnose()
        if diagnosis['issues']:
            logging.warning(f"{len(diagnosis['issues'])}件のパス問題を検出しました")
            # 自動修復を試行
            repair_result = registry.auto_repair(diagnosis['issues'])
            logging.info(f"自動修復: {len(repair_result['repaired'])}件成功, {len(repair_result['failed'])}件失敗")
        
        # ディレクトリの作成（基本ディレクトリ）
        ensure_dir("LOGS_DIR")
        ensure_dir("DATA_DIR")
        ensure_dir("EXPORTS_DIR")
        ensure_dir("TEMPLATES_DIR")
        ensure_dir("PROJECTS_DIR")
        ensure_dir("MASTER_DIR")
        ensure_dir("TEMP_DIR")
        ensure_dir("BACKUP_DIR")
        
        # CreateProjectList用のディレクトリも作成
        ensure_dir("CPL_DIR")
        ensure_dir("CPL_CONFIG_DIR")
        ensure_dir("CPL_TEMP_DIR")
        ensure_dir("CPL_TEMPLATES_DIR")
        ensure_dir("CPL_CACHE_DIR")
        
        # CreateProjectList設定ファイルの移行処理
        migrate_cpl_files()
                
        # defaults.txtの確認
        defaults_path = APP_ROOT / "defaults.txt"
        if not defaults_path.exists():
            # ProjectManagerからコピー
            source = APP_ROOT / "ProjectManager" / "defaults.txt"
            if source.exists():
                try:
                    shutil.copy(source, defaults_path)
                    print(f"デフォルト設定ファイルをコピー: {source} -> {defaults_path}")
                except Exception as e:
                    print(f"デフォルト設定ファイルコピーエラー: {e}")
            else:
                # デフォルト内容で新規作成
                try:
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
                except Exception as e:
                    print(f"デフォルト設定ファイル作成エラー: {e}")
        
        # Pythonバージョンの確認
        if not check_python_version():
            print("警告: Python 3.8.0以上を推奨します")
            
    except Exception as e:
        print(f"環境設定エラー: {e}")
        raise

def migrate_cpl_files():
    """CreateProjectList のファイルをユーザードキュメントに移行"""
    try:
        # PathRegistryを取得
        registry = PathRegistry.get_instance()
        
        # ソースパス（インストールディレクトリ内）
        if getattr(sys, 'frozen', False):
            source_dir = Path(sys._MEIPASS) / "CreateProjectList"
        else:
            source_dir = APP_ROOT / "CreateProjectList"
        
        # 宛先パス（ユーザードキュメント内）
        target_dir = Path.home() / "Documents" / "ProjectSuite" / "CreateProjectList"
        
        # 移行対象ファイル
        files_to_migrate = [
            {"src": "config/config.json", "dst": "config/config.json"},
            {"src": "defaults.txt", "dst": "defaults.txt"}
        ]
        
        # ファイルの移行
        for file_info in files_to_migrate:
            src_path = source_dir / file_info["src"]
            dst_path = target_dir / file_info["dst"]
            
            # ソースファイルが存在し、宛先が存在しない場合
            if src_path.exists() and not dst_path.exists():
                try:
                    # 親ディレクトリの作成
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # ファイルのコピー
                    shutil.copy2(src_path, dst_path)
                    logging.info(f"ファイルを移行: {src_path} -> {dst_path}")
                except Exception as e:
                    logging.error(f"ファイル移行エラー {src_path}: {e}")
        
        # CPL設定ファイルが存在しない場合は新規作成
        config_file = target_dir / "config" / "config.json"
        if not config_file.exists():
            create_cpl_config_file(target_dir)
            
        logging.info("CreateProjectListファイルの移行が完了しました")
        
    except Exception as e:
        logging.error(f"CreateProjectList移行エラー: {e}")

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
        try:
            Config.validate_environment()
        except Exception as e:
            logging.warning(f"環境検証エラー: {e}")
            print(f"警告: 環境検証に失敗しましたが、処理は続行します: {e}")
        
        # データベースマネージャーの初期化とマイグレーション
        db_path = get_path("DB_PATH", Config.DB_PATH)
        
        # データベースファイルの存在確認
        db_file = Path(db_path)
        if not db_file.exists():
            # データベースファイルが存在しない場合は作成を試みる
            try:
                db_file.parent.mkdir(parents=True, exist_ok=True)
                import sqlite3
                conn = sqlite3.connect(str(db_file))
                conn.close()
                logging.info(f"データベースファイルを新規作成しました: {db_file}")
            except Exception as db_err:
                logging.warning(f"データベースファイル作成エラー: {db_err}")
        
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
    
    # 通常起動時も一度コピーを試みる
    try_copy_critical_files()
    
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