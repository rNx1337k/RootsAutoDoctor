; Instalador do Roots Auto Doctor (Inno Setup 6). Criado pelo build_release.bat.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{6B1E2C3A-9F44-4C1B-A7D2-5E0C8B9A7F10}
AppName=Roots Auto Doctor
AppVersion={#AppVersion}
AppPublisher=Roots
DefaultDirName={autopf}\Roots Auto Doctor
DefaultGroupName=Roots Auto Doctor
UninstallDisplayIcon={app}\RootsAutoDoctor.exe
OutputDir=..\dist
OutputBaseFilename=Setup_RootsAutoDoctor_{#AppVersion}
SetupIconFile=..\rad\assets\icon.ico
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\main.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Roots Auto Doctor"; Filename: "{app}\RootsAutoDoctor.exe"
Name: "{group}\Desinstalar Roots Auto Doctor"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Roots Auto Doctor"; Filename: "{app}\RootsAutoDoctor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RootsAutoDoctor.exe"; Description: "{cm:LaunchProgram,Roots Auto Doctor}"; Flags: nowait postinstall skipifsilent
