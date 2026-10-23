"""Local UI + authenticated extension bridge. Run: python app.py"""
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import ssl
import sys
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from engine import Manager
from save_dialogs import SavePrompts
from preferences import Preferences
from updater import UpdateService, update_source, apply_update
from extension_status import ExtensionStatus

BASE = Path(__file__).resolve().parent
APP_HOME = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else BASE


class LocalHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False
    allow_reuse_port = False

    def server_bind(self):
        if sys.platform=='win32':
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()


def version():
    return json.loads((BASE / 'releases.json').read_text('utf-8'))['releases'][0]['version']


def open_download_folder(manager, ident):
    path = manager.completed_path(ident)
    # Open only the containing folder, never execute a downloaded file.
    if sys.platform == 'win32':
        os.startfile(str(path.parent))
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', '-R', str(path)])
    else:
        subprocess.Popen(['xdg-open', str(path.parent)])
    return str(path)


def open_download_file(manager, ident):
    path = manager.completed_path(ident)
    if sys.platform == 'win32':
        os.startfile(str(path))
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', str(path)])
    else:
        subprocess.Popen(['xdg-open', str(path)])
    return str(path)


def lock_data(directory):
    """Hold an OS lock so two app processes never write the same queue."""
    directory.mkdir(parents=True, exist_ok=True)
    handle = (directory / 'instance.lock').open('a+b')
    try:
        if handle.seek(0, 2) == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if sys.platform == 'win32':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise
    return handle


def make_server(manager, port=8765):
    repository = json.loads((BASE/'releases.json').read_text('utf-8')).get('update_repository','')
    preferences = Preferences(manager.root,default_feed='https://github.com/'+repository if repository else '')
    prompts = SavePrompts(manager,preferences=preferences)
    updates = UpdateService(manager,preferences,version(),APP_HOME,BASE)
    extensions = ExtensionStatus(version())
    token_file = manager.root / 'bridge-token.txt'
    if not token_file.exists():
        token_file.write_text(secrets.token_urlsafe(32), encoding='utf-8')
    token = token_file.read_text('utf-8').strip()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def allowed_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def cors(self):
            origin = self.headers.get('Origin', '')
            if origin.startswith(('chrome-extension://', 'moz-extension://', 'safari-web-extension://')):
                self.send_header('Access-Control-Allow-Origin', origin)
                self.send_header('Vary', 'Origin')

        def reply(self, value, status=200):
            data = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.cors()
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self):
            if not self.allowed_host():
                return self.reply({'error': 'Invalid Host'}, 403)
            self.send_response(204)
            self.cors()
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
            self.end_headers()

        def do_GET(self):
            if not self.allowed_host():
                return self.reply({'error': 'Invalid Host'}, 403)
            path = urlsplit(self.path).path
            if path.startswith('/api/'):
                if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                    return self.reply({'error': 'Unauthorized'}, 401)
                if path == '/api/jobs':
                    return self.reply(manager.snapshot())
                if path == '/api/info':
                    return self.reply({'version': version(), 'features': ['capture-preflight','save-dialog','remember-folder','updates']})
                if path == '/api/settings':
                    return self.reply({key:value for key,value in preferences.get().items() if key!='last_update_check'})
                if path == '/api/update/status':
                    return self.reply({**updates.snapshot(),'extension_sync':extensions.snapshot()})
                if path == '/api/extension/status':
                    return self.reply(extensions.snapshot())
                if path.startswith('/api/prompts/'):
                    try:
                        return self.reply(prompts.get(path.rsplit('/',1)[-1]))
                    except KeyError:
                        return self.reply({'error':'Hộp thoại đã hết hạn. Hãy thử tải lại.'},404)
                if path == '/api/storage':
                    return self.reply({'directory': str(manager.output)})
                return self.reply({'error': 'Not found'}, 404)
            if path == '/':
                data = (BASE / 'web' / 'index.html').read_text('utf-8').replace('__TOKEN__', token).encode('utf-8')
                mime = 'text/html; charset=utf-8'
            elif path in ('/app.js', '/style.css'):
                data = (BASE / 'web' / path[1:]).read_bytes()
                mime = 'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8'
            else:
                return self.reply({'error': 'Not found'}, 404)
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if not self.allowed_host():
                return self.reply({'error': 'Invalid Host'}, 403)
            if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                return self.reply({'error': 'Mã kết nối không hợp lệ.'}, 401)
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 16384:
                    return self.reply({'error': 'Yêu cầu quá lớn hoặc rỗng.'}, 400)
                data = json.loads(self.rfile.read(length))
                path = urlsplit(self.path).path
                if updates.snapshot()['state']=='installing':
                    return self.reply({'error':'Đang cập nhật. Vui lòng chờ ứng dụng mở lại.'},409)
                if path == '/api/settings':
                    if set(data)-{'remember_save_dir','last_save_dir','update_feed','auto_check_updates','auto_install_updates'}:
                        raise ValueError('Tùy chọn không hợp lệ.')
                    for key in ('remember_save_dir','auto_check_updates','auto_install_updates'):
                        if key in data and not isinstance(data[key],bool):raise ValueError('Tùy chọn bật/tắt không hợp lệ.')
                    for key in ('last_save_dir','update_feed'):
                        if key in data and not isinstance(data[key],str):raise ValueError('Đường dẫn hoặc nguồn cập nhật không hợp lệ.')
                    if data.get('last_save_dir') and (not Path(data['last_save_dir']).is_absolute() or not Path(data['last_save_dir']).is_dir()):
                        raise ValueError('Thư mục ghi nhớ không tồn tại.')
                    if 'update_feed' in data:data['update_feed']=update_source(data['update_feed'])
                    if data.get('remember_save_dir') is False:data['last_save_dir']=''
                    preferences.set(**data)
                    return self.reply({'ok':True})
                if path == '/api/update/check':
                    updates.check()
                    return self.reply({'ok':True},202)
                if path == '/api/extension/heartbeat':
                    return self.reply(extensions.report(data))
                if path == '/api/update/run':
                    updates.run_update()
                    return self.reply({'ok':True},202)
                if path == '/api/update/accept':
                    if set(data)!={'version'} or not isinstance(data['version'],str):raise ValueError('Phiên bản không hợp lệ.')
                    updates.accept(data['version'])
                    return self.reply({'ok':True},202)
                if path == '/api/extension/open-folder':
                    folder=APP_HOME/'extension'/'chromium'
                    if not (folder/'manifest.json').is_file():raise ValueError('Không tìm thấy tiện ích kèm ứng dụng. Hãy giải nén đầy đủ gói ứng dụng.')
                    if sys.platform!='win32':raise ValueError('Mở thư mục tự động chỉ hỗ trợ Windows.')
                    os.startfile(str(folder))
                    return self.reply({'path':str(folder)})
                if path == '/api/update/download':
                    updates.download()
                    return self.reply({'ok':True},202)
                if path == '/api/update/import':
                    updates.import_local()
                    return self.reply({'ok':True},202)
                if path == '/api/update/install':
                    updates.install(prompts)
                    return self.reply({'ok':True},202)
                if path in ('/api/jobs','/api/capture') and data.pop('ask_save',False):
                    return self.reply({'prompt_id':prompts.start(data,automatic=path=='/api/capture')},202)
                if path == '/api/jobs':
                    ident = manager.add(**data)
                    return self.reply({'id': ident}, 201)
                if path == '/api/capture':
                    ident = manager.capture(**data)
                    return self.reply({'id': ident}, 201)
                if path == '/api/action':
                    manager.action(data['id'], data['action'])
                    return self.reply({'ok': True})
                if path == '/api/redownload':
                    if set(data)!={'id'}:raise ValueError('Tham số tải lại không hợp lệ.')
                    return self.reply({'id':manager.redownload(data['id'])},201)
                if path == '/api/history/clear':
                    if set(data)-{'id','ids','delete_files'}:raise ValueError('Tham số xóa lịch sử không hợp lệ.')
                    return self.reply({'removed':manager.clear_history(data.get('id'),data.get('ids'),data.get('delete_files',False))})
                if path == '/api/open-folder':
                    return self.reply({'path': open_download_folder(manager, data['id'])})
                if path == '/api/open-file':
                    return self.reply({'path': open_download_file(manager, data['id'])})
                return self.reply({'error': 'Not found'}, 404)
            except (ValueError, TypeError, KeyError) as ex:
                return self.reply({'error': str(ex)}, 400)
            except Exception:
                return self.reply({'error': 'Không thể lưu dữ liệu. Kiểm tra quyền ghi và dung lượng đĩa.'}, 500)

    server = LocalHTTPServer(('127.0.0.1', port), Handler)
    server.updates = updates
    server.prompts = prompts
    updates.restart_port = server.server_port
    updates.on_install = lambda: threading.Timer(.7,server.shutdown).start()
    return server


def background_streams(directory):
    """A windowed PyInstaller executable has no stdout/stderr handles."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    directory.mkdir(parents=True,exist_ok=True)
    output=(directory/'application.log').open('a',encoding='utf-8',buffering=1)
    if sys.stdout is None:sys.stdout=output
    if sys.stderr is None:sys.stderr=output


def open_running_app(directory,port,no_browser=False):
    """After the data lock is held, reopen the local listener without HTTP races."""
    try:
        if not (directory/'bridge-token.txt').is_file():return False
        address=f'http://127.0.0.1:{port}'
        for attempt in range(4):
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=2):pass
                break
            except OSError:
                if attempt==3:raise
                time.sleep(.2)
        if not no_browser:webbrowser.open(address)
        return True
    except (OSError,ValueError):return False


def startup_error(message):
    print(message,file=sys.stderr)
    if sys.platform=='win32' and getattr(sys,'frozen',False) and sys.__stderr__ is None:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,message,'Download Now',0x10)


def main():
    for stream in (sys.stdout,sys.stderr):
        if hasattr(stream,'reconfigure'):stream.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Download Now — local download manager')
    parser.add_argument('--version', action='version', version='Download Now ' + version())
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data', type=Path, default=APP_HOME / 'data')
    parser.add_argument('--no-browser', action='store_true', help='Do not open the browser automatically')
    parser.add_argument('--self-test-tls',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--apply-update',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--update-source',help=argparse.SUPPRESS)
    parser.add_argument('--update-destination',help=argparse.SUPPRESS)
    parser.add_argument('--update-backup',help=argparse.SUPPRESS)
    parser.add_argument('--update-parent',type=int,help=argparse.SUPPRESS)
    parser.add_argument('--update-port',type=int,default=8765,help=argparse.SUPPRESS)
    parser.add_argument('--update-data',type=Path,help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.self_test_tls:
        try:
            context=ssl.create_default_context()
            return 0 if context.verify_mode==ssl.CERT_REQUIRED and context.check_hostname else 1
        except Exception:return 1
    if args.apply_update:
        if not all((args.update_source,args.update_destination,args.update_backup,args.update_parent)):
            return 1
        return apply_update(args.update_source,args.update_destination,args.update_backup,args.update_parent,args.update_port,args.update_data)
    try:
        background_streams(args.data.resolve())
    except OSError:
        startup_error('Không thể ghi nhật ký. Hãy đặt Download Now trong thư mục có quyền ghi.')
        return 1
    try:
        storage_lock = lock_data(args.data.resolve())
    except OSError:
        if open_running_app(args.data.resolve(),args.port,args.no_browser):return 0
        startup_error('Dữ liệu đang được ứng dụng khác sử dụng hoặc không có quyền ghi. Hãy đóng bản đang chạy.')
        return 1
    manager = Manager(args.data)
    try:
        server = make_server(manager, args.port)
    except OSError as ex:
        manager.close()
        storage_lock.close()
        startup_error(f'Không thể mở cổng {args.port}: {ex}. Hãy đóng bản đang chạy hoặc dùng --port khác.')
        return 1
    print(f'Download Now v{version()}: http://127.0.0.1:{server.server_port}')
    print(f'Tệp tải về: {manager.output}')
    print('Ứng dụng chạy nền. Đóng tab trình duyệt không dừng tải hoặc lịch tải.')
    server.updates.start_auto_check(server.prompts)
    if getattr(sys, 'frozen', False) and not args.no_browser:
        threading.Timer(.8, webbrowser.open, args=(f'http://127.0.0.1:{server.server_port}',)).start()
    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        server.serve_forever()
    finally:
        server.updates.stop.set()
        manager.close()
        server.server_close()
        storage_lock.close()


if __name__ == '__main__':
    sys.exit(main())
