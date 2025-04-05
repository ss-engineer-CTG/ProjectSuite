"""
ビルド前の環境チェックスクリプト
必要なパッケージやファイルの存在を確認する
"""

import importlib
import importlib.util
import os
import sys
from pathlib import Path

def check_module(module_name):
    """モジュールがインストールされているか確認"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def check_file(file_path):
    """ファイルが存在するか確認"""
    return Path(file_path).exists()

def check_directory(dir_path):
    """ディレクトリが存在するか確認"""
    path = Path(dir_path)
    return path.exists() and path.is_dir()

def check_pyinstaller():
    """PyInstallerの機能確認"""
    if not check_module('PyInstaller'):
        return False, "PyInstallerがインストールされていません"
    
    try:
        # PyInstallerのバージョンを確認
        import PyInstaller
        version = PyInstaller.__version__
        print(f"PyInstallerバージョン: {version}")
        
        return True, f"PyInstaller {version} が利用可能です"
    except Exception as e:
        return False, f"PyInstallerのバージョン確認中にエラー: {e}"

def main():
    """メインチェック処理"""
    print("ビルド環境チェックを開始...")
    
    # 必要なモジュールのチェック
    required_modules = [
        'pandas',
        'win32com',
        'openpyxl',
        'xlrd',
        'portalocker',
        'customtkinter',
        'docx',
        'PIL',
        'PyInstaller',
    ]
    
    missing_modules = []
    for module in required_modules:
        if not check_module(module):
            missing_modules.append(module)
    
    if missing_modules:
        print("以下のモジュールがインストールされていません:")
        for module in missing_modules:
            print(f"  - {module}")
        print("\n以下のコマンドを実行してインストールしてください:")
        print("pip install " + " ".join(missing_modules))
    else:
        print("必要なモジュールはすべてインストールされています。")
    
    # PyInstallerの詳細チェック
    if 'PyInstaller' not in missing_modules:
        pyinstaller_ok, message = check_pyinstaller()
        print(message)
    
    # 必要なファイルのチェック
    required_files = [
        'main.py',
        'PathRegistry.py',
        'defaults.txt',
        'ProjectManager/src/defaults.txt',
        'CreateProjectList/config/config.json',
    ]
    
    missing_files = []
    for file in required_files:
        if not check_file(file):
            missing_files.append(file)
    
    if missing_files:
        print("\n以下のファイルが見つかりません:")
        for file in missing_files:
            print(f"  - {file}")
    else:
        print("必要なファイルはすべて存在します。")
    
    # 必要なディレクトリのチェック
    required_dirs = [
        'ProjectManager',
        'CreateProjectList',
        'ProjectManager/data/templates',
        'ProjectManager/data/master',
    ]
    
    missing_dirs = []
    for directory in required_dirs:
        if not check_directory(directory):
            missing_dirs.append(directory)
    
    if missing_dirs:
        print("\n以下のディレクトリが見つかりません:")
        for directory in missing_dirs:
            print(f"  - {directory}")
    else:
        print("必要なディレクトリはすべて存在します。")
    
    # specファイルの確認
    spec_file = 'ProjectSuite.spec'
    if check_file(spec_file):
        print(f"{spec_file}ファイルが存在します。")
    else:
        print(f"{spec_file}ファイルが見つかりません。ビルド時に自動生成されます。")
    
    # 総合判定
    if not missing_modules and not missing_files and not missing_dirs:
        print("\n✅ すべてのチェックに合格しました。ビルドを開始できます。")
        print("   python build.py コマンドで実行してください。")
        return 0
    else:
        print("\n❌ いくつかの問題が見つかりました。上記のエラーを修正してから再試行してください。")
        return 1

if __name__ == "__main__":
    sys.exit(main())