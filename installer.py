"""
PyInstallerを使ってデスクトップアプリケーションをビルド
"""

import subprocess
import os
import sys
import shutil
from pathlib import Path

# アイコンファイルのパス設定
ICON_PATH = "resources/icon.ico"

# ビルド設定
APP_NAME = "ProjectSuite"
APP_VERSION = "1.0.0"
AUTHOR = "Your Company"

def create_executable():
    """実行可能ファイルを作成"""
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--windowed",  # GUIアプリケーション
        "--onedir",    # ディレクトリ構造で出力
        "--add-data", "ProjectManager/data;data",  # データディレクトリの含め方
        "--add-data", "ProjectManager/defaults.txt;.",  # 設定ファイル
        "--icon", ICON_PATH,
        "ProjectManager/src/main.py"  # メインスクリプト
    ]
    
    # Windowsのみの設定
    if os.name == 'nt':
        cmd.extend([
            "--add-binary", "venv/Lib/site-packages/pywin32_system32/pythoncom39.dll;.",
            "--add-binary", "venv/Lib/site-packages/pywin32_system32/pywintypes39.dll;."
        ])
    
    subprocess.run(cmd, check=True)

def package_additional_modules():
    """追加モジュールをパッケージ化"""
    # CreateProjectList
    subprocess.run([
        "pyinstaller",
        "--name", "CreateProjectList",
        "--windowed",
        "--onedir",
        "CreateProjectList/run.py"
    ], check=True)
    
    # ProjectDashBoard
    subprocess.run([
        "pyinstaller",
        "--name", "ProjectDashBoard",
        "--windowed",
        "--onedir",
        "ProjectDashBoard/app.py"
    ], check=True)

def create_installer():
    """インストーラーの作成"""
    if os.name == 'nt':
        # Windows: Inno Setup 使用
        iss_content = f"""
        #define MyAppName "{APP_NAME}"
        #define MyAppVersion "{APP_VERSION}"
        #define MyAppPublisher "{AUTHOR}"
        #define MyAppURL "https://example.com"
        #define MyAppExeName "{APP_NAME}.exe"

        [Setup]
        AppId={{{{{APP_NAME}}}}
        AppName={{#MyAppName}}
        AppVersion={{#MyAppVersion}}
        AppPublisher={{#MyAppPublisher}}
        AppPublisherURL={{#MyAppURL}}
        AppSupportURL={{#MyAppURL}}
        AppUpdatesURL={{#MyAppURL}}
        DefaultDirName={{autopf}}\\{{#MyAppName}}
        DefaultGroupName={{#MyAppName}}
        DisableProgramGroupPage=yes
        OutputBaseFilename={APP_NAME}-{APP_VERSION}-setup
        Compression=lzma
        SolidCompression=yes
        WizardStyle=modern

        [Languages]
        Name: "japanese"; MessagesFile: "compiler:Languages\\Japanese.isl"

        [Tasks]
        Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

        [Files]
        Source: "dist\\{APP_NAME}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs
        Source: "dist\\CreateProjectList\\*"; DestDir: "{{app}}\\CreateProjectList"; Flags: ignoreversion recursesubdirs createallsubdirs
        Source: "dist\\ProjectDashBoard\\*"; DestDir: "{{app}}\\ProjectDashBoard"; Flags: ignoreversion recursesubdirs createallsubdirs

        [Icons]
        Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
        Name: "{{commondesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

        [Run]
        Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
        """
        
        # Inno Setup スクリプトの保存
        iss_path = "installer.iss"
        with open(iss_path, "w") as f:
            f.write(iss_content)
        
        # Inno Setup コンパイラの実行
        subprocess.run(["iscc", iss_path], check=True)
    else:
        # Mac または Linux: シンプルな zip または tar.gz
        archive_name = f"{APP_NAME}-{APP_VERSION}"
        dist_dir = Path("dist")
        
        if os.name == 'posix':  # Mac または Linux
            if sys.platform == 'darwin':  # Mac
                # Mac用DMGの作成
                subprocess.run([
                    "hdiutil", "create",
                    f"{archive_name}.dmg",
                    "-srcfolder", f"{dist_dir}/{APP_NAME}",
                    "-srcfolder", f"{dist_dir}/CreateProjectList",
                    "-srcfolder", f"{dist_dir}/ProjectDashBoard",
                    "-volname", APP_NAME
                ], check=True)
            else:  # Linux
                # tar.gz の作成
                subprocess.run([
                    "tar", "-czf",
                    f"{archive_name}.tar.gz",
                    "-C", "dist",
                    APP_NAME,
                    "CreateProjectList",
                    "ProjectDashBoard"
                ], check=True)

if __name__ == "__main__":
    # 実行可能ファイルの作成
    create_executable()
    
    # 追加モジュールのパッケージ化
    package_additional_modules()
    
    # インストーラーの作成
    create_installer()
    
    print(f"{APP_NAME} v{APP_VERSION} のインストーラーが作成されました。")