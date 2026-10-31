"""Installer shutdown helper; targets only the selected installation's EXE."""
import ctypes
from ctypes import wintypes
import json
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

def request_shutdown(root):
    folder=Path(root)/'data'
    port=json.loads((folder/'bridge-endpoint.json').read_text('utf-8'))['port']
    if type(port) is not int or not 1024<=port<=65535:raise ValueError('Cổng không hợp lệ.')
    token=(folder/'bridge-token.txt').read_text('utf-8').strip()
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f'http://127.0.0.1:{port}/api/discovery',timeout=5) as response:
        info=json.load(response)
        if info.get('application')!='DownloadNow' or info.get('protocol')!=1 or info.get('port')!=port:raise ValueError('Cổng không phải Download Now.')
    request=urllib.request.Request(f'http://127.0.0.1:{port}/api/app/exit',data=b'{"confirm":true}',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with opener.open(request,timeout=5) as response:
        if response.status!=200:raise ValueError('Ứng dụng chưa hỗ trợ thoát an toàn.')

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
