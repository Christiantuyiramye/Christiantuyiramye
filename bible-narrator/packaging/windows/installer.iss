; Inno Setup script for the Windows installer.
; 1) Build the app folder first:  pyinstaller packaging\bible_narrator.spec --noconfirm
; 2) Compile this script with Inno Setup 6 (iscc packaging\windows\installer.iss)
; Output: dist\BibleNarrator-Setup-1.0.0.exe

#define AppName "Bible Narrator"
#define AppVersion "1.0.0"

[Setup]
AppId={{6C9E2F7A-3B1D-4E8A-9C55-0A7D2B1E4F60}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Bible Narrator contributors
DefaultDirName={autopf}\Bible Narrator
DefaultGroupName={#AppName}
OutputDir=..\..\dist
OutputBaseFilename=BibleNarrator-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
LicenseFile=..\..\docs\INSTALLER_NOTICE.txt
UninstallDisplayIcon={app}\BibleNarrator.exe

[Files]
Source: "..\..\dist\BibleNarrator\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\BibleNarrator.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\BibleNarrator.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\BibleNarrator.exe"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent
