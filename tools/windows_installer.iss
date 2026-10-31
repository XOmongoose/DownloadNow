#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef PackageDir
  #error PackageDir is required
#endif
#ifndef OutputFolder
  #error OutputFolder is required
#endif
[Setup]
AppId={{6F1D4BC1-5435-4A86-B8F2-2D91D7003F4C}
AppName=Download Now
AppVersion={#AppVersion}
AppPublisher=XOmongoose
AppPublisherURL=https://github.com/XOmongoose/DownloadNow
AppSupportURL=https://github.com/XOmongoose/DownloadNow/issues
AppUpdatesURL=https://github.com/XOmongoose/DownloadNow/releases
DefaultDirName={localappdata}\Programs\DownloadNow
DefaultGroupName=Download Now
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputFolder}
OutputBaseFilename=DownloadNow-Setup-{#AppVersion}-Windows-x64
SetupIconFile={#PackageDir}\..\..\build\DownloadNow.ico
UninstallDisplayIcon={app}\DownloadNow.exe
VersionInfoCompany=XOmongoose
VersionInfoDescription=Download Now Installer
VersionInfoCopyright=Copyright (C) XOmongoose
WizardStyle=modern
Compression=lzma2/fast
SolidCompression=yes
CloseApplications=yes
CloseApplicationsFilter=DownloadNow.exe
UsePreviousAppDir=yes
UsePreviousTasks=yes
RestartApplications=no
Uninstallable=yes
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "browserextensions"; Description: "Set up browser extensions after installation (browser confirmation required)"; GroupDescription: "Browser integration:"

[Files]
Source: "{#PackageDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "data\*,.git\*,__pycache__\*,*.pyc"

[Icons]
Name: "{group}\Download Now"; Filename: "{app}\DownloadNow.exe"; WorkingDir: "{app}"
Name: "{group}\Browser extensions"; Filename: "{app}\extension"
Name: "{group}\Set up browser extensions"; Filename: "{app}\DownloadNow.exe"; Parameters: "--setup-browser"; WorkingDir: "{app}"
Name: "{group}\Installation guide"; Filename: "{app}\HUONG-DAN.txt"
Name: "{autodesktop}\Download Now"; Filename: "{app}\DownloadNow.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\DownloadNow.exe"; Parameters: "{code:StartupParameters}"; Description: "Open Download Now"; Flags: nowait postinstall skipifsilent

[Code]
function StartupParameters(Param: String): String;
begin
  if WizardIsTaskSelected('browserextensions') then Result := '--setup-browser'
  else Result := '';
end;

function CreateFile(lpFileName: String; dwDesiredAccess, dwShareMode, lpSecurityAttributes, dwCreationDisposition, dwFlagsAndAttributes, hTemplateFile: LongWord): LongWord;
  external 'CreateFileW@kernel32.dll stdcall';
function CloseHandle(hObject: LongWord): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

function PrepareToInstall(var NeedsRestart: Boolean): String;
var LockPath: String; LockHandle: LongWord;
begin
  Result := '';
  { Interactive setup uses Restart Manager to ask before closing the old EXE. }
  if not WizardSilent then Exit;
  LockPath := ExpandConstant('{app}\data\instance.lock');
  if FileExists(LockPath) then begin
    LockHandle := CreateFile(LockPath, $80000000, 0, 0, 3, $80, 0);
    if LockHandle = $FFFFFFFF then
      Result := 'Download Now is running in this folder. Pause your downloads and close Download Now before installing.'
    else
      CloseHandle(LockHandle);
  end;
end;

function InitializeSetup(): Boolean;
var ExistingPath, ExistingVersion: String;
begin
  Result := True;
  if RegQueryStringValue(HKCU64, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{6F1D4BC1-5435-4A86-B8F2-2D91D7003F4C}_is1', 'InstallLocation', ExistingPath) then begin
    RegQueryStringValue(HKCU64, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{6F1D4BC1-5435-4A86-B8F2-2D91D7003F4C}_is1', 'DisplayVersion', ExistingVersion);
    if not WizardSilent then
      Result := MsgBox('Đã có Download Now ' + ExistingVersion + '.' + #13#10 +
        'Bộ cài sẽ thay thế phiên bản cũ bằng v{#AppVersion} trong thư mục đã cài.' + #13#10 +
        'Hãy tạm dừng lượt tải. Nếu ứng dụng đang chạy, bước tiếp theo sẽ yêu cầu đóng ứng dụng.' + #13#10 +
        'Lịch sử, cài đặt và tệp đã tải được giữ nguyên. Tiếp tục?', mbConfirmation, MB_YESNO) = IDYES;
  end;
end;
