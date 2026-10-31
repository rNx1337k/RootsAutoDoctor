; Instalador do Roots Auto Doctor (Inno Setup 6). Criado pelo build_release.bat.
; Leva tudo o que o programa precisa (Python, Qt, runtime do Visual C++, pontes): o PC da oficina não precisa de
; instalar mais nada nem de internet.
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
; Driver FTDI opcional: só entra se o build_release.bat o encontrar em installer\drivers\ftdi
#define FtdiDriver FileExists(AddBackslash(SourcePath) + "drivers\ftdi\ftdibus.inf")

[Setup]
AppId={{6B1E2C3A-9F44-4C1B-A7D2-5E0C8B9A7F10}
AppName=Roots Auto Doctor
AppVersion={#AppVersion}
AppVerName=Roots Auto Doctor {#AppVersion}
AppPublisher=Roots
VersionInfoVersion={#AppVersion}
VersionInfoProductName=Roots Auto Doctor
DefaultDirName={autopf}\Roots Auto Doctor
DefaultGroupName=Roots Auto Doctor
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\RootsAutoDoctor.exe
UninstallDisplayName=Roots Auto Doctor
OutputDir=..\dist
OutputBaseFilename=Setup_RootsAutoDoctor_{#AppVersion}
SetupIconFile=..\rad\assets\icon.ico
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
; Só Windows 10/11 de 64 bits: noutros sistemas o instalador explica porquê, em vez de instalar um programa
; que não abriria.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
PrivilegesRequiredOverridesAllowed=dialog
; Fecha o programa se estiver aberto durante uma actualização.
CloseApplications=yes
SetupLogging=yes

[Languages]
Name: "pt"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
pt.DriverStatus=A preparar o Windows para os cabos de diagnóstico...
en.DriverStatus=Preparing Windows for the diagnostic cables...
pt.UninstallLink=Desinstalar Roots Auto Doctor
en.UninstallLink=Uninstall Roots Auto Doctor

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\build\main.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#if FtdiDriver
; Driver oficial dos cabos com chip FTDI (ver drivers\LEIA-ME.txt). Fica guardado no Windows para que um cabo
; novo seja reconhecido mesmo sem internet; os cabos que já funcionam não são alterados.
Source: "drivers\ftdi\*"; DestDir: "{app}\drivers\ftdi"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{group}\Roots Auto Doctor"; Filename: "{app}\RootsAutoDoctor.exe"
Name: "{group}\{cm:UninstallLink}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Roots Auto Doctor"; Filename: "{app}\RootsAutoDoctor.exe"; Tasks: desktopicon

[Run]
#if FtdiDriver
; /add-driver sem /install: o driver entra no "armazém de drivers" do Windows e só é usado por cabos que ainda
; não têm driver. Precisa de administrador (instalação para todos os utilizadores).
Filename: "{sys}\pnputil.exe"; Parameters: "/add-driver ""{app}\drivers\ftdi\*.inf"" /subdirs"; Flags: runhidden waituntilterminated; StatusMsg: "{cm:DriverStatus}"; Check: IsAdminInstallMode
#endif
Filename: "{app}\RootsAutoDoctor.exe"; Description: "{cm:LaunchProgram,Roots Auto Doctor}"; Flags: nowait postinstall skipifsilent
