; ProjectManagerSuite インストーラースクリプト - 最適化版
; Inno Setup を使用してインストーラーを作成

; 基本アプリケーション情報
; これらの値はビルドスクリプトから渡されます
#define MyAppName "ProjectManagerSuite"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Your Company"
#define MyAppURL "http://www.example.com/"
#define MyAppExeName "ProjectManagerSuite.exe"
#define MyAppDescription "プロジェクト管理統合アプリケーション"

; セットアップに関する情報
#define SourceDir "dist\ProjectManagerSuite"
#define OutputDir "installer"
#define OutputBaseFilename "ProjectManagerSuite_Setup"

; アイコンファイルの定義 - ビルドパラメータでオーバーライド可能
#ifndef SetupIconFile
#define SetupIconFile ""
#endif

; アプリケーションID (GUIDは固有値)
#define MyAppId "{{CF2C9156-2A0B-4594-B173-ED4B6C0C038D}}"

[Setup]
; セットアップの基本設定
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppCopyright=Copyright (C) {#MyAppPublisher}
AppComments={#MyAppDescription}

; インストールディレクトリの設定
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; 出力設定
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}

; アイコンの設定 - 指定されていれば使用
#if SetupIconFile != ""
SetupIconFile={#SetupIconFile}
#endif
UninstallDisplayIcon={app}\{#MyAppExeName}

; 圧縮設定
Compression=lzma
SolidCompression=yes

; UI設定
WizardStyle=modern
WizardResizable=yes
WizardSizePercent=120

; その他の設定
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
AllowNoIcons=yes
ShowLanguageDialog=auto

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

; カスタムメッセージの定義
[CustomMessages]
english.CreateStartMenuIcon=Create Start Menu Icon
japanese.CreateStartMenuIcon=スタートメニューにアイコンを作成する

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "startmenuicon"; Description: "{cm:CreateStartMenuIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "起動時に自動的に起動する"; GroupDescription: "スタートアップ"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; データディレクトリの作成（存在しなくても作成）
[Dirs]
Name: "{app}\data"
Name: "{app}\logs"

[Icons]
; メインアプリケーション
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

; ダッシュボード起動用
Name: "{group}\ダッシュボード"; Filename: "{app}\dashboard_launcher.bat"; Comment: "ダッシュボードを起動します"

; アンインストーラー
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; デスクトップアイコン
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{commondesktop}\{#MyAppName} ダッシュボード"; Filename: "{app}\dashboard_launcher.bat"; Tasks: desktopicon

; クイック起動
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

; 自動起動
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 一時ファイルやログファイルの削除
Type: filesandordirs; Name: "{app}\logs\*"
Type: filesandordirs; Name: "{app}\data\temp\*"

[Code]
// アンインストール時に全てのファイルを削除するか確認するダイアログを表示
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DeleteDataDir: Boolean;
begin
  if CurUninstallStep = usUninstall then
  begin
    DeleteDataDir := MsgBox('データディレクトリも削除しますか？' + #13#10 +
                            '「はい」を選択するとすべてのデータが削除されます。' + #13#10 +
                            '「いいえ」を選択するとデータは保持されます。', mbConfirmation, MB_YESNO) = IDYES;
    if DeleteDataDir then
    begin
      // 削除するディレクトリを指定
      DelTree(ExpandConstant('{app}\data'), True, True, True);
    end;
  end;
end;

// ディレクトリの存在確認（オプションファイルのための関数）
function DirExists(const DirName: string): Boolean;
begin
  Result := DirExists(DirName);
end;