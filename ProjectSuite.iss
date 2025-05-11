[Setup]
AppName=ProjectSuite
AppVersion=2025.05.10
DefaultDirName={pf}\ProjectSuite
DefaultGroupName=ProjectSuite
OutputDir=installer
OutputBaseFilename=ProjectSuite_Setup_2025_05_10
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
; アプリケーションファイル
Source: "dist\\ProjectSuite.exe"; DestDir: "{app}"; Flags: ignoreversion

; initialdataコピー処理はPythonコードで実行するため削除

[Dirs]
; フォルダの作成とユーザーへの完全な権限付与
Name: "{userappdata}\..\Documents\ProjectSuite"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\ProjectManager"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\ProjectManager\data"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\ProjectManager\data\projects"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\ProjectManager\data\exports"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\ProjectManager\data\master"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\ProjectManager\data\templates"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\logs"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\temp"; Permissions: users-full
Name: "{userappdata}\..\Documents\ProjectSuite\backup"; Permissions: users-full

[Icons]
Name: "{group}\ProjectSuite"; Filename: "{app}\ProjectSuite.exe"
Name: "{commondesktop}\ProjectSuite"; Filename: "{app}\ProjectSuite.exe"

[Run]
; インストール完了後にinitialdata処理を実行
Filename: "{app}\ProjectSuite.exe"; Parameters: "init-data"; Description: "初期データ設定"; Flags: runasoriginaluser nowait postinstall

; 通常のアプリ起動
Filename: "{app}\ProjectSuite.exe"; Description: "Launch ProjectSuite"; Flags: nowait postinstall skipifsilent runasoriginaluser
