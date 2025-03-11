"""
ProjectManagerSuite ビルドスクリプト - 最適化版
- PyInstallerによる実行ファイル生成
- Inno Setupによるインストーラー作成
- 冗長な処理の削除と効率化
"""

import os
import sys
import subprocess
import shutil
import argparse
import json
import logging
from pathlib import Path

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("builder")

# ルートディレクトリの設定（常に絶対パスを使用）
ROOT_DIR = Path(__file__).parent.absolute()

# 重要なディレクトリパスの初期設定
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
INSTALLER_DIR = ROOT_DIR / "installer"

def load_config():
    """設定ファイルの読み込み"""
    config_path = ROOT_DIR / "build_config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info(f"設定ファイルを読み込みました: {config_path}")
            return config
    except Exception as e:
        logger.error(f"設定ファイル読み込みエラー: {e}")
        # デフォルト設定を返す
        return {
            "app_info": {
                "name": "ProjectManagerSuite",
                "version": "1.0.0"
            },
            "build": {
                "output_dir": "dist",
                "build_dir": "build",
                "clean_build": True,
                "create_installer": True
            }
        }

def verify_required_files():
    """必要なファイルが存在するか確認"""
    logger.info("必要なファイルを確認中...")
    
    required_files = [
        ROOT_DIR / "main.py",
        ROOT_DIR / "defaults.txt",
        ROOT_DIR / "ProjectManagerSuite.spec"
    ]
    
    required_dirs = [
        ROOT_DIR / "ProjectManager",
        ROOT_DIR / "CreateProjectList",
        ROOT_DIR / "ProjectDashBoard"
    ]
    
    all_exist = True
    
    # ファイルの確認
    for file_path in required_files:
        if not file_path.is_file():
            logger.error(f"必要なファイルが見つかりません: {file_path}")
            all_exist = False
    
    # ディレクトリの確認
    for dir_path in required_dirs:
        if not dir_path.is_dir():
            logger.error(f"必要なディレクトリが見つかりません: {dir_path}")
            all_exist = False
    
    return all_exist

def clean_build_dirs():
    """ビルドディレクトリのクリーンアップ"""
    logger.info("ビルドディレクトリをクリーンアップ中...")
    
    # ディレクトリの削除
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                logger.info(f"- {dir_path} を削除しました")
            except Exception as e:
                logger.error(f"- {dir_path} の削除に失敗: {e}")
    
    # インストーラーディレクトリの作成
    INSTALLER_DIR.mkdir(exist_ok=True, parents=True)
    logger.info(f"- {INSTALLER_DIR} を作成しました")

def create_dashboard_launcher():
    """ダッシュボード起動用バッチファイルの作成"""
    batch_file = ROOT_DIR / "dashboard_launcher.bat"
    
    try:
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write('REM Dashboard launcher script\n')
            f.write('SET PYTHONPATH=%~dp0\n')
            f.write('"%~dp0ProjectManagerSuite.exe" ProjectDashBoard\n')
        logger.info(f"ダッシュボード起動バッチファイルを作成: {batch_file}")
        return batch_file
    except Exception as e:
        logger.error(f"バッチファイル作成エラー: {e}")
        return None

def run_pyinstaller(config):
    """PyInstallerでビルドを実行 - 最適化版"""
    logger.info("PyInstallerでビルドを実行中...")
    
    # バッチファイルの作成は .spec ファイルに移動
    # ここでは明示的に作成しない
    
    # specファイルのパス
    spec_file = ROOT_DIR / "ProjectManagerSuite.spec"
    
    if not spec_file.exists():
        logger.error(f"エラー: specファイルが見つかりません: {spec_file}")
        return False
    
    # コマンドライン構築
    cmd = [
        sys.executable, 
        "-m", 
        "PyInstaller", 
        str(spec_file), 
        "--noconfirm", 
        "--clean"
    ]
    
    # UPXの使用設定
    if config["build"].get("use_upx", True):
        cmd.append("--upx-dir=upx")
    
    logger.info(f"実行コマンド: {' '.join(cmd)}")
    logger.info(f"実行ディレクトリ: {ROOT_DIR}")
    
    try:
        # ビルド実行
        result = subprocess.run(
            cmd, 
            check=True, 
            cwd=str(ROOT_DIR),
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        
        # 出力のログ出力
        for line in result.stdout.splitlines():
            if "[WARNING]" in line:
                logger.warning(line)
            else:
                logger.debug(line)
        
        logger.info("PyInstallerによるビルドが完了しました")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"PyInstallerのビルドに失敗しました")
        logger.error(f"終了コード: {e.returncode}")
        logger.error(f"標準出力:\n{e.stdout}")
        logger.error(f"標準エラー出力:\n{e.stderr}")
        return False

def verify_build_result(config):
    """ビルド結果の検証"""
    logger.info("ビルド結果を検証中...")
    
    app_name = config["app_info"]["name"]
    
    # 実行ファイルの検証
    exe_path = DIST_DIR / app_name / f"{app_name}.exe"
    if not exe_path.exists():
        logger.error(f"実行ファイルが見つかりません: {exe_path}")
        return False
    
    # ダッシュボード起動スクリプトの検証
    batch_path = DIST_DIR / app_name / "dashboard_launcher.bat"
    if not batch_path.exists():
        logger.warning(f"ダッシュボード起動スクリプトが見つかりません: {batch_path}")
    
    # データディレクトリの作成（存在しない場合のみ）
    data_dir = DIST_DIR / app_name / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        logger.warning(f"データディレクトリを作成しました: {data_dir}")
    
    logger.info("ビルド結果の検証が完了しました")
    return True

def create_installer(config):
    """Inno Setupを使用してインストーラーを作成 - 最適化版"""
    logger.info("Inno Setupでインストーラーを作成中...")
    
    # Inno Setupコンパイラの検索
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe"
    ]
    
    iscc_path = None
    for path in iscc_paths:
        if os.path.exists(path):
            iscc_path = path
            break
    
    if not iscc_path:
        logger.error("Inno Setup Compilerが見つかりません")
        return False
    
    # インストーラースクリプトの取得
    installer_script = ROOT_DIR / "installer.iss"
    if not installer_script.exists():
        logger.error(f"インストーラースクリプトが見つかりません: {installer_script}")
        return False
    
    # アプリ名とバージョンを設定ファイルから取得
    app_name = config["app_info"]["name"]
    app_version = config["app_info"]["version"]
    app_publisher = config["app_info"].get("publisher", "Your Company")
    
    # 追加設定
    output_base_filename = config["installer"].get("file_name", f"{app_name}_Setup")
    
    # アイコンの存在確認
    icon_path = ROOT_DIR / "assets" / "icon.ico"
    icon_param = []
    if icon_path.exists():
        icon_param = [f"/DSetupIconFile={icon_path}"]
    else:
        logger.warning(f"アイコンファイルが見つからないため、デフォルトアイコンを使用します: {icon_path}")
    
    # Inno Setupに渡すパラメータを準備
    cmd = [
        iscc_path, 
        f"/DMyAppName={app_name}", 
        f"/DMyAppVersion={app_version}", 
        f"/DMyAppPublisher={app_publisher}",
        f"/DOutputBaseFilename={output_base_filename}",
        f"/DOutputDir={INSTALLER_DIR}"
    ] + icon_param + [
        str(installer_script)
    ]
    
    try:
        # コンソール文字コード設定（Windows環境の場合）
        if os.name == 'nt':
            subprocess.run("chcp 65001", shell=True, check=False)
        
        # Inno Setupの実行
        result = subprocess.run(
            cmd, 
            check=True, 
            cwd=str(ROOT_DIR), 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        
        logger.info("インストーラーの作成に成功しました")
        
        # 出力パスの検証
        installer_file = INSTALLER_DIR / f"{output_base_filename}.exe"
        if installer_file.exists():
            logger.info(f"インストーラーファイル: {installer_file}")
            return True
        else:
            logger.warning(f"インストーラーファイルが見つかりません: {installer_file}")
            return False
            
    except subprocess.CalledProcessError as e:
        logger.error(f"インストーラービルドに失敗しました")
        logger.error(f"終了コード: {e.returncode}")
        logger.error(f"標準出力:\n{e.stdout}")
        logger.error(f"標準エラー出力:\n{e.stderr}")
        return False

def create_portable_archive(config):
    """ポータブル版のZIPアーカイブを作成"""
    logger.info("ポータブル版アーカイブを作成中...")
    
    app_name = config["app_info"]["name"]
    app_version = config["app_info"]["version"]
    
    # ディストディレクトリのパス
    dist_app_dir = DIST_DIR / app_name
    
    if not dist_app_dir.exists():
        logger.error(f"ディストディレクトリが存在しません: {dist_app_dir}")
        return False
    
    # アーカイブファイル名
    archive_name = f"{app_name}_v{app_version}_Portable"
    archive_path = INSTALLER_DIR / f"{archive_name}.zip"
    
    try:
        # ZIP圧縮
        shutil.make_archive(
            str(INSTALLER_DIR / archive_name),  # ベース名（拡張子なし）
            'zip',                              # フォーマット
            root_dir=DIST_DIR,                  # アーカイブするディレクトリ
            base_dir=app_name                   # アーカイブに含めるサブディレクトリ
        )
        
        logger.info(f"ポータブル版アーカイブを作成: {archive_path}")
        return True
        
    except Exception as e:
        logger.error(f"ポータブル版アーカイブの作成に失敗: {e}")
        return False

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="ProjectManagerSuiteビルドスクリプト")
    parser.add_argument('--no-clean', action='store_true', help='ビルド前にビルドディレクトリをクリーンアップしない')
    parser.add_argument('--no-installer', action='store_true', help='インストーラーを作成しない')
    parser.add_argument('--portable', action='store_true', help='ポータブル版ZIPアーカイブを作成する')
    parser.add_argument('--verbose', action='store_true', help='詳細なログ出力')
    args = parser.parse_args()
    
    # 詳細ログの設定
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        # ハンドラーのレベルも変更
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
            
    logger.info(f"===== ProjectManagerSuite ビルド開始 =====")
    logger.info(f"作業ディレクトリ: {ROOT_DIR}")
    
    # 設定の読み込み
    config = load_config()
    app_name = config["app_info"]["name"]
    
    # 必要なファイルの検証
    if not verify_required_files():
        logger.error("必要なファイルが揃っていません。ビルドを中止します。")
        return 1
    
    # ビルドディレクトリのクリーンアップ
    if not args.no_clean and config["build"].get("clean_build", True):
        clean_build_dirs()
    
    # PyInstallerによるビルド
    if not run_pyinstaller(config):
        return 1
    
    # ビルド結果の検証
    if not verify_build_result(config):
        logger.warning("ビルド結果に問題があります。続行します。")
    
    # インストーラーの作成
    installer_created = False
    if not args.no_installer and config["build"].get("create_installer", True):
        installer_created = create_installer(config)
        if not installer_created:
            logger.warning("インストーラーの作成に失敗しました。続行します。")
    
    # ポータブル版アーカイブの作成
    portable_created = False
    if args.portable or config["build"].get("create_portable", False):
        portable_created = create_portable_archive(config)
        if not portable_created:
            logger.warning("ポータブル版アーカイブの作成に失敗しました。")
    
    logger.info("\n===== ビルドプロセスが完了しました =====")
    
    # 成功時のパス情報表示
    exe_path = DIST_DIR / app_name / f"{app_name}.exe"
    installer_path = INSTALLER_DIR / f"{app_name}_Setup.exe"
    portable_path = INSTALLER_DIR / f"{app_name}_v{config['app_info']['version']}_Portable.zip"
    
    if exe_path.exists():
        logger.info(f"実行ファイル: {exe_path}")
    if installer_path.exists() and installer_created:
        logger.info(f"インストーラー: {installer_path}")
    if portable_path.exists() and portable_created:
        logger.info(f"ポータブル版: {portable_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())