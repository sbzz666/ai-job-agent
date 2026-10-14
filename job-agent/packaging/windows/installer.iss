#define AppName "AI Job Assistant"
#define AppVersion "0.1.0"
#define AppExe "AIJobAssistant.exe"

[Setup]
AppId={{5E37A6C5-610B-42B7-A4BA-DCDAC305BA5D}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\AI Job Assistant
DefaultGroupName={#AppName}
OutputDir=..\..\release
OutputBaseFilename=AI-Job-Assistant-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "..\..\dist\AIJobAssistant\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标："

[Run]
Filename: "{app}\{#AppExe}"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent
