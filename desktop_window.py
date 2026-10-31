"""Standalone Windows WebView2 window. The downloader stays in its own process."""
from pathlib import Path
import json
import os
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

TITLE='Download Now'

def local_url(value):
    u=urlsplit(value)
    if u.scheme!='http' or u.hostname!='127.0.0.1' or u.username or u.password or not u.port or not 1024<=u.port<=65535 or u.path not in ('','/') or u.query not in ('','extensions=1','update=1') or u.fragment:
        raise ValueError('Địa chỉ cửa sổ ứng dụng không hợp lệ.')
    return value

def launch(url,root):
    local_url(url)
    command=[sys.executable]
    if not getattr(sys,'frozen',False):command.append(str(Path(__file__).with_name('app.py')))
    command+=['--desktop-url',url,'--data',str(Path(root).resolve())]
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    return subprocess.Popen(command,**options)

def run(url,root):
    local_url(url)
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    import msvcrt
    lock=(root/'desktop-window.lock').open('a+b')
    lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
    request=root/'desktop-open.json'
    try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        lock.close()
        temp=request.with_suffix('.tmp');temp.write_text(json.dumps({'url':url,'at':time.time_ns()}),'utf-8');temp.replace(request)
        return 0
    stopped=threading.Event()
    try:
        import webview
        window=webview.create_window(TITLE,url,width=1320,height=900,min_size=(900,650),text_select=True)
        window.events.closed+=lambda:stopped.set()
        last=request.stat().st_mtime_ns if request.exists() else 0
        def reopen():
            nonlocal last
            while not stopped.wait(.5):
                try:
                    stamp=request.stat().st_mtime_ns
                    if stamp==last:continue
                    last=stamp;target=local_url(json.loads(request.read_text('utf-8'))['url'])
                    if urlsplit(target).netloc!=urlsplit(url).netloc:continue
                    if urlsplit(target).query:window.load_url(target)
                    window.show();window.restore()
                except (OSError,ValueError,KeyError):continue
        threading.Thread(target=reopen,daemon=True).start()
        webview.start(gui='edgechromium',debug=False,private_mode=False,storage_path=str(root/'webview-profile'))
        return 0
    finally:
        stopped.set();lock.close()
