"""
ProjectSuiteビルドスクリプト
PyInstallerを使用してパッケージングを自動化する
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
import datetime
import traceback

def create_directories():
    """必要なディレクトリを作成"""
    directories = [
        'build',
        'dist',
        'dist/ProjectManager/data/projects',
        'dist/ProjectManager/data/exports',
        'dist/ProjectManager/logs',
        'installer',
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"ディレクトリを作成: {directory}")

def build_application():
    """アプリケーションのビルド"""
    print("PyInstallerでビルドを開始...")
    
    # .specファイルがない場合は、新しく作成する
    if not Path('ProjectSuite.spec').exists():
        print("ProjectSuite.specファイルが見つかりません。新しく作成します...")
        create_spec_file()
    
    # ビルド実行
    try:
        result = subprocess.run(
            ['pyinstaller', 'ProjectSuite.spec'],
            check=True,
            capture_output=True,
            text=True
        )
        print("ビルド完了")
    except subprocess.CalledProcessError as e:
        print(f"ビルドに失敗しました。エラー内容:")
        print(e.stderr)
        sys.exit(1)

def create_spec_file():
    """基本的なspec設定ファイルを作成"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

import os
block_cipher = None

# データファイルの定義 - シンプルなタプル形式 (ソース, ターゲット)
datas = [
    ('defaults.txt', '.'),
    ('PathRegistry.py', '.'),
]

# initialdata は組み込まない - インストーラーで別途コピーする

# プロジェクトマネージャーのソースファイルがある場合
if os.path.exists('ProjectManager/src'):
    datas.append(('ProjectManager/src', 'ProjectManager/src'))

# テンプレートファイルがある場合
if os.path.exists('ProjectManager/data/templates'):
    datas.append(('ProjectManager/data/templates', 'ProjectManager/data/templates'))

# 必要な隠れた依存関係
hidden_imports = [
    'pandas',
    'win32com',
    'openpyxl',
    'xlrd',
    'portalocker',
    'customtkinter',
    'PIL',
    'docx',
    'ProjectManager',
    'CreateProjectList',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProjectSuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico' if os.path.exists('resources/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ProjectSuite',
)
"""
    
    with open('ProjectSuite.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("ProjectSuite.specファイルを作成しました")

def copy_additional_files():
    """追加ファイルのコピー"""
    print("追加ファイルをコピーしています...")
    
    # README、ライセンスなどのコピー
    if Path('README.md').exists():
        shutil.copy('README.md', 'dist/')
    
    # 初期データフォルダ構造の作成
    data_dirs = [
        'dist/ProjectManager/data/projects',
        'dist/ProjectManager/data/exports',
        'dist/ProjectManager/logs',
    ]
    
    for data_dir in data_dirs:
        if not Path(data_dir).exists():
            Path(data_dir).mkdir(parents=True, exist_ok=True)
            print(f"データディレクトリを作成: {data_dir}")
    
    # 空のファイルの作成（必要に応じて）
    empty_files = [
        'dist/ProjectManager/logs/app.log',
    ]
    
    for empty_file in empty_files:
        if not Path(empty_file).exists():
            Path(empty_file).touch()
            print(f"空のファイルを作成: {empty_file}")
    
    # initialdata フォルダをインストーラーディレクトリにコピー
    if Path('initialdata').exists():
        installer_dir = Path('installer')
        installer_dir.mkdir(parents=True, exist_ok=True)
        
        target_dir = installer_dir / 'initialdata'
        if target_dir.exists():
            shutil.rmtree(target_dir)
        
        shutil.copytree('initialdata', target_dir)
        print(f"初期データフォルダをインストーラーディレクトリにコピー: {target_dir}")
    else:
        print("警告: initialdata フォルダが見つかりません。初期データなしでビルドされます。")
    
    print("追加ファイルのコピー完了")

def create_empty_db():
    """空のデータベースファイルを作成"""
    db_path = Path('dist/ProjectManager/data/projects.db')
    
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True)
    
    if not db_path.exists():
        # 空のファイルを作成
        db_path.touch()
        print(f"空のデータベースファイルを作成: {db_path}")

def find_exe_file():
    """実行ファイルを検索する"""
    # 可能性のあるパスを確認
    candidates = [
        Path('dist/ProjectSuite.exe'),
        Path('dist/ProjectSuite/ProjectSuite.exe')
    ]
    
    # distディレクトリ内を再帰的に検索
    if Path('dist').exists():
        for path in Path('dist').glob('**/ProjectSuite.exe'):
            if path not in candidates:
                candidates.append(path)
    
    # 存在確認
    for path in candidates:
        if path.exists():
            return path
    
    return None

def generate_installer_script():
    """InnoSetupのインストーラースクリプトを生成"""
    print("インストーラースクリプトを生成...")
    
    # まず実際のEXEファイルの場所を確認
    exe_path = find_exe_file()
    
    if not exe_path:
        print("警告: 実行ファイル(ProjectSuite.exe)が見つかりません。")
        print("インストーラースクリプトの生成をスキップします。")
        return False
    
    print(f"実行ファイルを検出: {exe_path}")
    
    # 親ディレクトリのパスを取得（ソースディレクトリ）
    source_dir = exe_path.parent
    
    # 実行ファイルとソースディレクトリの相対パス
    rel_exe_path = str(exe_path).replace("\\", "\\\\")
    rel_source_dir = str(source_dir).replace("\\", "\\\\")
    
    version = datetime.datetime.now().strftime("%Y.%m.%d")
    
    iss_content = f"""[Setup]
AppName=ProjectSuite
AppVersion={version}
DefaultDirName={{pf}}\\ProjectSuite
DefaultGroupName=ProjectSuite
OutputDir=installer
OutputBaseFilename=ProjectSuite_Setup_{version.replace('.', '_')}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
; アプリケーションファイル
Source: "{rel_exe_path}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{rel_source_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

; initialdataコピー処理はPythonコードで実行するため削除

[Dirs]
; フォルダの作成とユーザーへの完全な権限付与
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\ProjectManager"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\ProjectManager\\data"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\ProjectManager\\data\\projects"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\ProjectManager\\data\\exports"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\ProjectManager\\data\\master"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\ProjectManager\\data\\templates"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\logs"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\temp"; Permissions: users-full
Name: "{{userappdata}}\\..\\Documents\\ProjectSuite\\backup"; Permissions: users-full

[Icons]
Name: "{{group}}\\ProjectSuite"; Filename: "{{app}}\\ProjectSuite.exe"
Name: "{{commondesktop}}\\ProjectSuite"; Filename: "{{app}}\\ProjectSuite.exe"

[Run]
; インストール完了後にinitialdata処理を実行
Filename: "{{app}}\\ProjectSuite.exe"; Parameters: "init-data"; Description: "初期データ設定"; Flags: runasoriginaluser nowait postinstall

; 通常のアプリ起動
Filename: "{{app}}\\ProjectSuite.exe"; Description: "Launch ProjectSuite"; Flags: nowait postinstall skipifsilent runasoriginaluser
"""
    
    with open("ProjectSuite.iss", "w", encoding="utf-8") as f:
        f.write(iss_content)
    
    print("インストーラースクリプトを生成しました: ProjectSuite.iss")
    return True

def compile_installer():
    """InnoSetupでインストーラーをコンパイル"""
    print("インストーラーのコンパイルを試行中...")
    
    # インストーラースクリプトが存在するか確認
    if not Path("ProjectSuite.iss").exists():
        print("インストーラースクリプトが見つかりません。インストーラーのコンパイルをスキップします。")
        return
    
    # InnoSetupのコンパイラが利用可能か確認
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]
    
    iscc_path = None
    for path in inno_paths:
        if Path(path).exists():
            iscc_path = path
            break
    
    if iscc_path:
        print(f"InnoSetupコンパイラを発見: {iscc_path}")
        try:
            result = subprocess.run(
                [iscc_path, "ProjectSuite.iss"],
                check=True,
                capture_output=True,
                text=True
            )
            
            print(result.stdout)
            print("インストーラーのコンパイルに成功しました")
        except subprocess.CalledProcessError as e:
            print(f"インストーラーのコンパイル中にエラー:")
            print(e.stdout)
            print(e.stderr)
        except Exception as e:
            print(f"インストーラーのコンパイル中にエラー: {e}")
    else:
        print("InnoSetupコンパイラが見つかりません。インストーラーのコンパイルをスキップします。")
        print("手動でコンパイルするには、InnoSetupをインストールし、ProjectSuite.issファイルをコンパイルしてください。")

def main():
    """メインビルド処理"""
    start_time = datetime.datetime.now()
    print(f"ビルドプロセスを開始... [{start_time.strftime('%Y-%m-%d %H:%M:%S')}]")
    
    try:
        # 古いビルドファイルのクリーンアップ
        if Path('dist').exists():
            shutil.rmtree('dist')
            print("古いdistフォルダを削除しました")
        
        if Path('build').exists():
            shutil.rmtree('build')
            print("古いbuildフォルダを削除しました")
        
        # 必要なディレクトリの作成
        create_directories()
        
        # アプリケーションのビルド
        build_application()
        
        # 追加ファイルのコピー
        copy_additional_files()
        
        # 空のDB作成
        create_empty_db()
        
        # インストーラースクリプトの生成
        script_generated = generate_installer_script()
        
        # インストーラーのコンパイル（スクリプト生成に成功した場合のみ）
        if script_generated:
            compile_installer()
        
        # 完了メッセージの表示
        print("\nビルドファイルの構造:")
        exe_path = find_exe_file()
        if exe_path:
            print(f"実行ファイル: {exe_path}")
            print(f"実行するには: {exe_path} をダブルクリックするか、コマンドラインから実行してください")
        else:
            print("実行ファイルが見つかりません。ビルドに問題があります。")
        
        end_time = datetime.datetime.now()
        duration = end_time - start_time
        print(f"\nビルドプロセスが完了しました [{end_time.strftime('%Y-%m-%d %H:%M:%S')}]")
        print(f"所要時間: {duration}")
    
    except Exception as e:
        print(f"ビルドプロセス中にエラーが発生しました: {e}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()