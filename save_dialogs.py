"""Native Windows Save As dialogs with asynchronous, authenticated API tickets."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import threading
import time
import uuid

from engine import safe_name, valid_url
from preferences import Preferences, remembered_directory


class OPENFILENAMEW(ctypes.Structure):
    _fields_ = [
        ('lStructSize',wintypes.DWORD),('hwndOwner',wintypes.HWND),('hInstance',wintypes.HINSTANCE),
        ('lpstrFilter',wintypes.LPCWSTR),('lpstrCustomFilter',wintypes.LPWSTR),('nMaxCustFilter',wintypes.DWORD),
        ('nFilterIndex',wintypes.DWORD),('lpstrFile',wintypes.LPWSTR),('nMaxFile',wintypes.DWORD),
        ('lpstrFileTitle',wintypes.LPWSTR),('nMaxFileTitle',wintypes.DWORD),('lpstrInitialDir',wintypes.LPCWSTR),
        ('lpstrTitle',wintypes.LPCWSTR),('Flags',wintypes.DWORD),('nFileOffset',wintypes.WORD),
        ('nFileExtension',wintypes.WORD),('lpstrDefExt',wintypes.LPCWSTR),('lCustData',ctypes.c_ssize_t),
        ('lpfnHook',ctypes.c_void_p),('lpTemplateName',wintypes.LPCWSTR),('pvReserved',ctypes.c_void_p),
        ('dwReserved',wintypes.DWORD),('FlagsEx',wintypes.DWORD)]


def choose_save_file(name, directory):
    if sys.platform != 'win32':
        raise ValueError('Hộp thoại Lưu thành hiện hỗ trợ bản Windows.')
    library = ctypes.WinDLL('comdlg32', use_last_error=True)
    library.GetSaveFileNameW.argtypes = [ctypes.POINTER(OPENFILENAMEW)]
    library.GetSaveFileNameW.restype = wintypes.BOOL
    library.CommDlgExtendedError.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(32768)
    buffer.value = safe_name(name)
    dialog = OPENFILENAMEW()
    dialog.lStructSize = ctypes.sizeof(dialog)
    dialog.lpstrFile = ctypes.cast(buffer,wintypes.LPWSTR)
    dialog.nMaxFile = len(buffer)
    dialog.lpstrFilter = 'Tất cả tệp\0*.*\0\0'
    dialog.nFilterIndex = 1
    dialog.lpstrInitialDir = str(directory)
    dialog.lpstrTitle = 'Download Now — Chọn nơi lưu tệp'
    dialog.Flags = 0x00080000 | 0x00000800 | 0x00000008 | 0x02000000
    if library.GetSaveFileNameW(ctypes.byref(dialog)):
        return Path(buffer.value)
    error = library.CommDlgExtendedError()
    if error:
        raise ValueError(f'Không mở được hộp thoại lưu (mã {error}).')
    return None


class SavePrompts:
    def __init__(self, manager, chooser=None, preferences=None):
        self.manager = manager
        self.chooser = chooser
        self.preferences = preferences or Preferences(manager.root)
        self.lock = threading.RLock()
        self.dialog_lock = threading.Lock()
        self.items = {}

    def start(self, data, automatic=False):
        data = dict(data)
        valid_url(data['url'])
        allowed = {'url','name','request_id'} if automatic else {'url','name','connections','start_at','stop_at'}
        if set(data) - allowed:
            raise ValueError('Tham số tải không hợp lệ.')
        key = data.get('request_id')
        with self.lock:
            # Keep old tickets long enough for reconnects without retaining URLs forever.
            now = time.time()
            self.items = {i:p for i,p in self.items.items() if p['state']=='pending' or now-p['created']<3600}
            for ident, prompt in self.items.items():
                if key and prompt.get('key') == key:
                    if prompt['url'] != data['url']:
                        raise ValueError('Mã chọn tệp đã dùng cho link khác.')
                    return ident
            if sum(p['state']=='pending' for p in self.items.values()) >= 10:
                raise ValueError('Đang có nhiều hộp thoại chờ. Hãy chọn hoặc hủy trước.')
            ident = uuid.uuid4().hex
            self.items[ident] = dict(state='pending', created=now, key=key, url=data['url'])
        threading.Thread(target=self._run,args=(ident,data,automatic),daemon=True).start()
        return ident

    def _run(self, ident, data, automatic):
        try:
            with self.dialog_lock:
                directory = remembered_directory(self.preferences,self.manager.output)
                name = self.manager.resolve_download_name(data['url'], data.get('name', ''), automatic)
                if self.chooser is None:
                    from download_window import download_details
                    selected = download_details(name,directory,data['url'],self.preferences.get()['remember_save_dir'])
                else:
                    selected = self.chooser(name,directory)
            remember = self.preferences.get()['remember_save_dir']
            if isinstance(selected,dict):
                remember = selected['remember']
                selected = selected['path']
            if selected is None:
                result = {'state':'cancelled'}
            else:
                selected = Path(selected)
                if not selected.is_absolute() or not selected.parent.is_dir():
                    raise ValueError('Đường dẫn lưu không hợp lệ.')
                data.update(name=selected.name, save_dir=str(selected.parent))
                try:
                    job = self.manager.capture(**data) if automatic else self.manager.add(**data)
                except Exception as error:
                    if not automatic:raise
                    job=self.manager.failed_capture(data['url'],data['name'],data['request_id'],data['save_dir'],error)
                    result={'state':'error','id':job,'error':str(error)}
                    with self.lock:self.items[ident].update(result)
                    return
                self.preferences.set(remember_save_dir=remember,last_save_dir=str(selected.parent) if remember else '')
                result = {'state':'accepted', 'id':job}
        except Exception as error:
            result = {'state':'error', 'error':str(error)}
        with self.lock:
            self.items[ident].update(result)

    def get(self, ident):
        with self.lock:
            item = self.items[ident]
            return {k:v for k,v in item.items() if k in ('state','id','error')}
