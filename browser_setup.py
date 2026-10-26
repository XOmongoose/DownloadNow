"""User-initiated browser setup; no profile edits or forced-install policies."""
import os
from pathlib import Path
import subprocess
import sys

BROWSERS={'chrome':('Chrome','chrome.exe','chrome://extensions/'),
          'edge':('Edge','msedge.exe','edge://extensions/'),
          'opera':('Opera','opera.exe','opera://extensions/')}

def browser_path(browser):
    if browser not in BROWSERS:raise ValueError('Trình duyệt không hợp lệ.')
    if sys.platform!='win32':return None
    import winreg
    executable=BROWSERS[browser][1]
    for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY,winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive,rf'Software\Microsoft\Windows\CurrentVersion\App Paths\{executable}',0,winreg.KEY_READ|view) as key:
                    value=winreg.QueryValueEx(key,'')[0]
                    if not isinstance(value,str):continue
                    candidate=Path(value.strip('"'))
                    if candidate.is_absolute() and candidate.is_file():return candidate
            except OSError:pass
    suffixes={'chrome':('Google/Chrome/Application/chrome.exe',),
              'edge':('Microsoft/Edge/Application/msedge.exe',),
              'opera':('Programs/Opera/launcher.exe','Opera/launcher.exe')}
    for location in ('LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)'):
        if not os.environ.get(location):continue
        for suffix in suffixes[browser]:
            candidate=Path(os.environ[location])/suffix
            if candidate.is_file():return candidate
    return None

def setup_info(home):
    return {'folder':str((Path(home)/'extension/chromium').resolve()),
            'requires_confirmation':True,'distribution':'unpacked',
            'browsers':[{'id':key,'name':value[0],'installed':browser_path(key) is not None} for key,value in BROWSERS.items()]}

def open_setup(browser,home,application_url):
    executable=browser_path(browser)
    if executable is None:raise ValueError('Chưa tìm thấy trình duyệt này trên máy.')
    folder=(Path(home)/'extension/chromium').resolve()
    if not (folder/'manifest.json').is_file():raise ValueError('Bộ cài thiếu thư mục tiện ích.')
    try:subprocess.Popen([str(executable),application_url+'/?extensions=1',BROWSERS[browser][2]])
    except OSError as error:raise ValueError('Không mở được trình duyệt. Hãy mở trình duyệt và trang quản lý tiện ích theo hướng dẫn.') from error
    return {'folder':str(folder),'requires_confirmation':True,'browser':BROWSERS[browser][0]}
