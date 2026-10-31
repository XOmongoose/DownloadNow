"""Installer shutdown helper; targets only the selected installation's EXE."""
import ctypes
from ctypes import wintypes
import json
import hmac
import hashlib
import secrets
from pathlib import Path
import time
import urllib.request

class Entry(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),('heap',ctypes.c_size_t),('module',wintypes.DWORD),('threads',wintypes.DWORD),('parent',wintypes.DWORD),('priority',wintypes.LONG),('flags',wintypes.DWORD),('name',wintypes.WCHAR*260)]

def process_ids(root):
    expected=str((Path(root).resolve()/'DownloadNow.exe')).casefold()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD)]
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    snapshot=kernel.CreateToolhelp32Snapshot(2,0)
    if snapshot==wintypes.HANDLE(-1).value:raise OSError('Không đọc được danh sách tiến trình.')
    result=[]
    try:
        item=Entry();item.size=ctypes.sizeof(item)
        more=kernel.Process32FirstW(snapshot,ctypes.byref(item))
        while more:
            if item.name.casefold()=='downloadnow.exe':
                handle=kernel.OpenProcess(0x1000,False,item.pid)
                if handle:
                    try:
                        size=wintypes.DWORD(32768);value=ctypes.create_unicode_buffer(size.value)
                        if kernel.QueryFullProcessImageNameW(handle,0,value,ctypes.byref(size)) and str(Path(value.value).resolve()).casefold()==expected:result.append(item.pid)
                    finally:kernel.CloseHandle(handle)
            more=kernel.Process32NextW(snapshot,ctypes.byref(item))
    finally:kernel.CloseHandle(snapshot)
    return result

def exit_signature(token,at,nonce):
    return hmac.new(token.encode(),f'exit:{at}:{nonce}'.encode(),hashlib.sha256).hexdigest()

def valid_exit_request(value,token,started,now):
    try:
        at=value['at'];nonce=value['nonce']
        return type(at) in (float,int) and started<=at<=now+5 and now-at<120 and isinstance(nonce,str) and len(nonce)==32 and hmac.compare_digest(value['signature'],exit_signature(token,at,nonce))
    except (KeyError,TypeError,ValueError):return False

def request_shutdown(root):
    folder=Path(root)/'data'
    token=(folder/'bridge-token.txt').read_text('utf-8').strip()
    at=time.time();nonce=secrets.token_hex(16)
    value={'at':at,'nonce':nonce,'signature':exit_signature(token,at,nonce)}
    request=folder/'shutdown-request.json';temporary=request.with_suffix('.tmp')
    temporary.write_text(json.dumps(value),encoding='utf-8');temporary.replace(request)

def prepare(root,force=False,timeout=45):
    root=Path(root).resolve()
    if not (root/'DownloadNow.exe').is_file():return 0
    if not process_ids(root):return 0
    if not force:
        try:request_shutdown(root)
        except (OSError,ValueError,KeyError):return 2
    else:
        # Only called after a separate installer confirmation for older versions.
        kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        for pid in process_ids(root):
            handle=kernel.OpenProcess(1,False,pid)
            if handle:
                try:kernel.TerminateProcess(handle,0)
                finally:kernel.CloseHandle(handle)
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if not process_ids(root):return 0
        time.sleep(.3)
    return 2
