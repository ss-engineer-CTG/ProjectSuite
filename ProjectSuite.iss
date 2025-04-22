[Setup]
AppName=ProjectSuite
AppVersion=2025.04.23
DefaultDirName={pf}\ProjectSuite
DefaultGroupName=ProjectSuite
OutputDir=installer
OutputBaseFilename=ProjectSuite_Setup_2025_04_23
Compression=lzma
SolidCompression=yes

[Files]
; アプリケーションファイル
Source: "dist\\ProjectSuite\\ProjectSuite.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\\ProjectSuite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; サンプルデータをユーザードキュメントフォルダにコピー
Source: "initialdata\*"; DestDir: "{userappdata}\..\Documents\ProjectSuite\initialdata"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\ProjectManager\data\projects"; Permissions: users-modify
Name: "{app}\ProjectManager\data\exports"; Permissions: users-modify
Name: "{app}\ProjectManager\logs"; Permissions: users-modify
Name: "{userappdata}\..\Documents\ProjectSuite"; Permissions: users-modify

[Icons]
Name: "{group}\ProjectSuite"; Filename: "{app}\ProjectSuite.exe"
Name: "{commondesktop}\ProjectSuite"; Filename: "{app}\ProjectSuite.exe"

[Run]
; インストール完了後にinitialdata処理を実行
Filename: "{app}\ProjectSuite.exe"; Parameters: "init-data"; Description: "初期データ設定"; Flags: runhidden nowait postinstall

; 通常のアプリ起動
Filename: "{app}\ProjectSuite.exe"; Description: "Launch ProjectSuite"; Flags: nowait postinstall skipifsilent
