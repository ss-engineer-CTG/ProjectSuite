[Setup]
AppName=ProjectSuite
AppVersion=2025.04.05
DefaultDirName={pf}\ProjectSuite
DefaultGroupName=ProjectSuite
OutputDir=installer
OutputBaseFilename=ProjectSuite_Setup_2025_04_05
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\\ProjectSuite\\ProjectSuite.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\\ProjectSuite\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}\ProjectManager\data\projects"; Permissions: users-modify
Name: "{app}\ProjectManager\data\exports"; Permissions: users-modify
Name: "{app}\ProjectManager\logs"; Permissions: users-modify

[Icons]
Name: "{group}\ProjectSuite"; Filename: "{app}\ProjectSuite.exe"
Name: "{commondesktop}\ProjectSuite"; Filename: "{app}\ProjectSuite.exe"

[Run]
Filename: "{app}\ProjectSuite.exe"; Description: "Launch ProjectSuite"; Flags: nowait postinstall skipifsilent
