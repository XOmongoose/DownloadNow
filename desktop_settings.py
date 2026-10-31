"""Per-user Windows startup and browser UI background lifetime."""
import os
from pathlib import Path
import subprocess
import sys

RUN_KEY=r'Software\Microsoft\Windows\CurrentVersion\Run'
VALUE='DownloadNow'

def startup_enabled():
    if os.name!='nt':return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,RUN_KEY) as key:
            return bool(winreg.QueryValueEx(key,VALUE)[0])
    except FileNotFoundError:return False

def set_startup(enabled,root):
    if os.name!='nt':raise ValueError('Khởi động cùng Windows chỉ khả dụng trên Windows.')
    import winreg
    executable=Path(sys.executable).resolve()
    if enabled and not getattr(sys,'frozen',False):raise ValueError('Hãy dùng bản EXE đã cài để bật khởi động cùng Windows.')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,RUN_KEY) as key:
        if enabled:
            command=subprocess.list2cmdline([str(executable),'--startup','--data',str(Path(root).resolve())])
            winreg.SetValueEx(key,VALUE,0,winreg.REG_SZ,command)
        else:
            try:winreg.DeleteValue(key,VALUE)
            except FileNotFoundError:pass

def should_stop_background(enabled,last_seen,now):
    return not enabled and last_seen is not None and now-last_seen>120
