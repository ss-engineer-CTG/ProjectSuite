"""
シンプルなビルドスクリプト for ProjectManagerSuite
PyInstallerによる実行ファイル生成とInno Setupによるインストーラー作成
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse
import json
import logging

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("builder")

# ルートディレクトリの設定 - 絶対パスを使用
ROOT_DIR = Path(__file__).parent.absolute()
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
INSTALLER_DIR = ROOT_DIR / "installer"

def load_config():
    """設定ファイルの読み込み"""
    config_path = ROOT_DIR / "build_config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"設定ファイル読み込みエラー: {e}")
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
        ROOT_DIR / "launcher.py",
        ROOT_DIR / "defaults.txt",
        ROOT_DIR / "ProjectManagerSuite.spec"
    ]
    
    required_dirs = [
        ROOT_DIR / "ProjectManager",
        ROOT_DIR / "CreateProjectList",
        ROOT_DIR / "ProjectDashBoard"
    ]
    
    all_exist = True
    
    for file_path in required_files:
        if not file_path.is_file():
            logger.error(f"必要なファイルが見つかりません: {file_path}")
            all_exist = False
    
    for dir_path in required_dirs:
        if not dir_path.is_dir():
            logger.error(f"必要なディレクトリが見つかりません: {dir_path}")
            all_exist = False
    
    return all_exist

def clean_build_dirs():
    """ビルドディレクトリのクリーンアップ"""
    logger.info("ビルドディレクトリをクリーンアップ中...")
    
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            logger.info(f"- {dir_path} を削除しました")
    
    # インストーラーディレクトリの作成
    INSTALLER_DIR.mkdir(exist_ok=True)

def run_pyinstaller():
    """PyInstallerを実行"""
    logger.info("PyInstallerでビルドを実行中...")
    
    # 絶対パスでspecファイルを指定
    spec_file = ROOT_DIR / "ProjectManagerSuite.spec"
    
    if not spec_file.exists():
        logger.error(f"エラー: specファイルが見つかりません: {spec_file}")
        return False
    
    # コマンドラインを構築（すべて絶対パスで）
    cmd = [
        sys.executable, 
        "-m", 
        "PyInstaller", 
        str(spec_file), 
        "--noconfirm", 
        "--clean"
    ]
    
    logger.info(f"実行コマンド: {' '.join(cmd)}")
    logger.info(f"実行ディレクトリ: {ROOT_DIR}")
    
    try:
        # 作業ディレクトリを明示的に設定
        result = subprocess.run(cmd, check=True, cwd=str(ROOT_DIR), capture_output=True, text=True)
        logger.info("PyInstallerによるビルド完了")
        logger.debug(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"PyInstallerのビルドに失敗しました")
        logger.error(f"終了コード: {e.returncode}")
        logger.error(f"標準出力:\n{e.stdout}")
        logger.error(f"標準エラー出力:\n{e.stderr}")
        return False

def create_installer(config):
    """Inno Setupを使用してインストーラーを作成"""
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
    
    # インストーラースクリプトの取得 - 絶対パスを使用
    installer_script = ROOT_DIR / "installer.iss"
    if not installer_script.exists():
        logger.error(f"インストーラースクリプトが見つかりません: {installer_script}")
        return False
    
    # アプリ名とバージョンを設定ファイルから取得
    app_name = config["app_info"]["name"]
    app_version = config["app_info"]["version"]
    
    cmd = [
        iscc_path, 
        f"/DMyAppName={app_name}", 
        f"/DMyAppVersion={app_version}", 
        str(installer_script)
    ]
    
    try:
        # 作業ディレクトリを明示的に設定
        result = subprocess.run(cmd, check=True, cwd=str(ROOT_DIR), capture_output=True, text=True)
        logger.info("インストーラーの作成完了")
        logger.debug(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"インストーラービルドに失敗しました")
        logger.error(f"終了コード: {e.returncode}")
        logger.error(f"標準出力:\n{e.stdout}")
        logger.error(f"標準エラー出力:\n{e.stderr}")
        return False

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(description="ProjectManagerSuiteビルドスクリプト")
    parser.add_argument('--no-clean', action='store_true', help='ビルド前にビルドディレクトリをクリーンアップしない')
    parser.add_argument('--no-installer', action='store_true', help='インストーラーを作成しない')
    parser.add_argument('--verbose', action='store_true', help='詳細なログ出力')
    args = parser.parse_args()
    
    # 詳細ログの設定
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
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
    if not run_pyinstaller():
        return 1
    
    # インストーラーの作成
    if not args.no_installer and config["build"].get("create_installer", True):
        if not create_installer(config):
            return 1
    
    logger.info("\n===== ビルドプロセスが完了しました =====")
    
    # 成功時のパス情報表示
    exe_path = DIST_DIR / app_name / f"{app_name}.exe"
    installer_path = INSTALLER_DIR / f"{app_name}_Setup.exe"
    
    if exe_path.exists():
        logger.info(f"実行ファイル: {exe_path}")
    if installer_path.exists() and not args.no_installer:
        logger.info(f"インストーラー: {installer_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())