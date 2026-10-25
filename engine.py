"""Persistent, bounded parallel HTTP downloader. Python standard library only."""
from __future__ import annotations

import concurrent.futures
from email.message import Message
from email.header import decode_header, make_header
from email.utils import collapse_rfc2231_value
import filecmp
import http.client
import json
import os
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from media import is_video_page, video_name, video_size, download_video, VideoStopped
import google_drive
import http.cookiejar
from datetime import datetime

CHUNK = 4 * 1024 * 1024
BLOCK = 1024 * 1024
MAX_ACTIVE_DOWNLOADS = 4


def valid_url(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Chỉ hỗ trợ URL HTTP/HTTPS không chứa mật khẩu.')
    return url


def safe_name(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value).strip(' .')[:180]
    if not value or value.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
        return 'download_' + value
    return value


def link_name(url):
    """Decode URL filenames without treating a '+' in a path as a space."""
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qs(parsed.query)
    for key in ('response-content-disposition','rscd'):
        if query.get(key):
            candidate=response_name({'Content-Disposition':query[key][0]})
            if candidate:return candidate
    for key in ('filename', 'file_name', 'download_filename'):
        if query.get(key, [''])[0]:
            return query[key][0]
    leaf = urllib.parse.unquote(parsed.path.rsplit('/', 1)[-1])
    if not Path(leaf).suffix:
        for key in ('name', 'file', 'download'):
            candidate = query.get(key, [''])[0]
            if candidate and Path(candidate).suffix:
                return candidate
    return leaf or 'download.bin'


def response_name(headers):
    message = Message()
    message['Content-Disposition'] = headers.get('Content-Disposition', '')
    # Prefer RFC 5987 Unicode filename* over the ASCII fallback filename.
    parameters = message.get_params(header='Content-Disposition') or []
    extended = next((value for key, value in parameters if key == 'filename' and isinstance(value, tuple)), None)
    name = collapse_rfc2231_value(extended) if extended else message.get_filename()
    return str(make_header(decode_header(name))) if name else None


def generic_name(name):
    return (not name or name.lower() in {'download', 'download.bin', 'file', 'get', 'view'}
            or not Path(name).suffix
            or Path(name).suffix.lower() in {'.php', '.aspx', '.ashx', '.jsp'})


class Paused(Exception):
    pass


class Changed(Exception):
    pass


class Manager:
    def resolve_download_size(self,url):
        """Read metadata only; a partial response's Content-Length is not file size."""
        valid_url(url)
        if is_video_page(url):return video_size(url)
        with self._request({'url':url},{'Range':'bytes=0-0'}) as response:
            mime=response.headers.get('Content-Type','').split(';',1)[0].lower()
            disposition=response.headers.get('Content-Disposition','').lower()
            if mime in ('text/html','application/xhtml+xml') and 'attachment' not in disposition:return None
            if response.status==206:
                match=re.fullmatch(r'bytes 0-0/(\d+)',response.headers.get('Content-Range',''))
                return {'bytes':int(match[1]),'estimated':False} if match else None
            length=response.headers.get('Content-Length','')
            if response.status==200 and re.fullmatch(r'\d+',length):
                return {'bytes':int(length),'estimated':False}
        return None

    def resolve_download_name(self, url, supplied='', automatic=False):
        """Resolve endpoint URLs before a Save dialog makes its name explicit."""
        if is_video_page(url):
            return safe_name(supplied if supplied and not automatic else video_name(url))
        original = link_name(url)
        if supplied and not automatic:
            return safe_name(supplied)
        if not generic_name(original):
            return safe_name(original)
        if supplied and not generic_name(supplied):
            return safe_name(supplied)
        with self._request({'url': url}, {'Range': 'bytes=0-0'}) as response:
            name = response_name(response.headers)
            if not name:
                redirected = response.geturl()
                name = link_name(redirected) if isinstance(redirected, str) else ''
            if generic_name(name):
                raise ValueError('Máy chủ chưa cung cấp tên tệp. Hãy nhập tên tệp khi thêm link hoặc tải bằng trình duyệt.')
            return safe_name(name)

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.output = self.root / 'files'
        self.output.mkdir(exist_ok=True)
        self.parts = self.root / 'parts'
        self.parts.mkdir(exist_ok=True)
        self.lock = threading.RLock()
        self.jobs = {}
        self.running = {}
        self.samples = {}
        self.http = threading.local()
        self.shutdown = threading.Event()
        state = self.root / 'state.json'
        if state.exists():
            # Fail visibly on corruption: never silently discard a user's queue.
            self.jobs = json.loads(state.read_text('utf-8'))
            for j in self.jobs.values():
                if j.get('cancel_requested'):
                    self._discard_partial(j)
                    j.update(status='cancelled', done=0, ranges=[])
                if j['status'] in ('downloading', 'probing', 'pausing'):
                    j['status'] = 'queued'
        self.scheduler = threading.Thread(target=self._schedule, daemon=True)
        self.scheduler.start()

    def save(self):
        with self.lock:
            temp = self.root / 'state.tmp'
            with temp.open('w', encoding='utf-8') as f:
                json.dump(self.jobs, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp, self.root / 'state.json')

    def add(self, url, name='', connections=8, start_at=None, stop_at=None, capture_id=None, save_dir=None):
        valid_url(url)
        connections = int(connections)
        if not 1 <= connections <= 8:
            raise ValueError('Số kết nối phải từ 1 đến 8.')
        start_at = self._date(start_at)
        stop_at = self._date(stop_at)
        if start_at and stop_at and stop_at <= start_at:
            raise ValueError('Thời gian dừng phải sau thời gian bắt đầu.')
        custom_name = bool(name)
        name = safe_name(name or link_name(url))
        if is_video_page(url) and not name.lower().endswith('.mp4'):name=safe_name(name+'.mp4')
        destination = Path(save_dir).expanduser() if save_dir else self.output
        if not destination.is_absolute() or not destination.is_dir():
            raise ValueError('Thư mục lưu phải là đường dẫn tuyệt đối và đang tồn tại.')
        destination = destination.resolve()
        with self.lock:
            if capture_id:
                existing = self._capture_existing(capture_id, url)
                if existing:
                    return existing
            name = self._unique_name(name, directory=destination)
            ident = uuid.uuid4().hex
            self.jobs[ident] = dict(id=ident, url=url, name=name, connections=connections,
                                   start_at=start_at, stop_at=stop_at, status='queued',
                                   total=None, done=0, ranges=[], etag=None, modified=None,
                                   ranged=False, error='', created=time.time(), custom_name=custom_name,
                                   name_resolved=False, capture_id=capture_id, save_dir=str(destination))
            self.save()
        return ident

    def _capture_existing(self, request_id, url):
        if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9-]{8,80}', request_id):
            raise ValueError('Mã chuyển tải không hợp lệ.')
        for job in self.jobs.values():
            if job.get('capture_id') == request_id:
                if job['url'] != url:
                    raise ValueError('Mã chuyển tải đã dùng cho liên kết khác.')
                return job['id']
        return None

    def capture(self, url, name='', request_id=None, save_dir=None):
        """Check public access before accepting a browser download handoff."""
        valid_url(url)
        if not request_id:
            raise ValueError('Thiếu mã chuyển tải.')
        with self.lock:
            existing = self._capture_existing(request_id, url)
            if existing:
                return existing
        # Supported video pages are HTML by design. Their media extractor,
        # rather than the direct-file preflight, validates and downloads them.
        if is_video_page(url):
            return self.add(url, name=name, capture_id=request_id, save_dir=save_dir)
        try:
            req = urllib.request.Request(url, headers={'Range': 'bytes=0-0',
                'Accept-Encoding': 'identity', 'User-Agent': 'DownloadNow/1.0'})
            response_context=self._request({'url':url},{'Range':'bytes=0-0'}) if google_drive.file_id(url) else urllib.request.urlopen(req,timeout=8)
            with response_context as response:
                valid_url(response.geturl())
                if response.status not in (200, 206):
                    raise ValueError('Máy chủ không chấp nhận chuyển tải.')
                mime = response.headers.get('Content-Type', '').split(';', 1)[0].lower()
                disposition = response.headers.get('Content-Disposition', '').lower()
                if mime in ('text/html', 'application/xhtml+xml') and 'attachment' not in disposition:
                    raise ValueError('Link trả về trang web hoặc yêu cầu đăng nhập. Tiếp tục bằng trình duyệt.')
                if response.status == 206:
                    response.read(1)
        except (OSError, urllib.error.URLError, http.client.HTTPException) as ex:
            if isinstance(ex, urllib.error.HTTPError):
                ex.close()
            raise ValueError('Không truy cập được link. Trình duyệt sẽ tiếp tục tải; link có thể cần đăng nhập.') from ex
        return self.add(url, name=name, capture_id=request_id, save_dir=save_dir)

    def failed_capture(self,url,name,request_id,save_dir,error):
        # Hold the scheduler lock through creation and error persistence so no
        # worker can publish HTML while a rejected browser handoff is recorded.
        with self.lock:
            existing=self._capture_existing(request_id,url)
            if existing:return existing
            ident=self.add(url,name=name,capture_id=request_id,save_dir=save_dir)
            self.jobs[ident].update(status='error',error=str(error))
            self.save()
            return ident

    def output_for(self, job):
        return Path(job.get('save_dir') or self.output).resolve()

    def _unique_name(self, name, exclude=None, directory=None):
        directory = directory or self.output
        occupied = {j['name'].casefold() for j in self.jobs.values()
                    if j['id'] != exclude and self.output_for(j) == directory}
        base = Path(name)
        count = 1
        while name.casefold() in occupied or (directory / name).exists():
            name = f'{base.stem} ({count}){base.suffix}'
            count += 1
        return name

    def completed_path(self, ident):
        with self.lock:
            job = self.jobs[ident]
            if job['status'] != 'completed':
                raise ValueError('Tệp chưa tải hoàn tất.')
            directory = self.output_for(job)
            path = (directory / job['name']).resolve()
            if path.parent != directory:
                raise ValueError('Đường dẫn tệp không hợp lệ.')
            if not path.is_file():
                raise ValueError('Không tìm thấy tệp. Có thể tệp đã bị di chuyển hoặc xóa.')
            return path

    @staticmethod
    def _date(value):
        if not value:
            return None
        if isinstance(value, (float, int)):
            result = float(value)
        else:
            result = datetime.fromisoformat(value).timestamp()
        if not __import__('math').isfinite(result):
            raise ValueError('Thời gian không hợp lệ.')
        return result

    def action(self, ident, action):
        with self.lock:
            j = self.jobs[ident]
            if j['status'] in ('cancelled','cancelling'):
                if action=='cancel':return
                raise ValueError('Lượt tải đã hủy. Hãy thêm liên kết để tải lại.')
            if action == 'pause':
                if ident in self.running:
                    j['status'] = 'pausing'
                    self.running[ident][0].set()
                elif j['status'] != 'completed':
                    j['status'] = 'paused'
            elif action == 'resume':
                if ident in self.running:
                    raise ValueError('Đang dừng kết nối. Vui lòng thử lại sau.')
                if j['status'] == 'completed':
                    return
                j.update(status='queued', error='', start_at=None, stop_at=None)
            elif action == 'cancel':
                if j['status']=='completed':
                    raise ValueError('Tệp đã hoàn tất. Bạn có thể xóa lịch sử tải.')
                j['cancel_requested']=True
                if ident in self.running:
                    j['status']='cancelling'
                    self.running[ident][0].set()
                else:
                    self._discard_partial(j)
                    j.update(status='cancelled', done=0, ranges=[], error='')
            else:
                raise ValueError('Thao tác không hợp lệ.')
            self.save()

    def redownload(self,ident):
        """Create a fresh job; preserve the previous record and completed file."""
        with self.lock:
            original=self.jobs[ident]
            # A completed file is already published and closed. Its old worker
            # may still be cleaning its own part directory; the new ID is safe.
            if original['status'] not in ('completed','cancelled'):
                raise ValueError('Dùng Tiếp tục cho lượt chưa hoàn tất. Tải lại dùng cho lượt đã hoàn tất hoặc đã hủy.')
            return self.add(original['url'],name=original['name'],connections=original['connections'],save_dir=str(self.output_for(original)))

    def _discard_partial(self,j):
        folder=self.parts/j['id']
        if is_video_page(j['url']):
            for item in folder.glob('*'):
                if item.is_file():item.unlink()
        for part in folder.glob('*.part'):
            part.unlink(missing_ok=True)
        (folder/'assembled.tmp').unlink(missing_ok=True)
        if folder.exists():folder.rmdir()
        (self.output_for(j)/f'.downloadnow-{j["id"]}.tmp').unlink(missing_ok=True)

    def clear_history(self,ident=None,ids=None,delete_files=False):
        """Remove selected terminal records, optionally their exact completed files."""
        if not isinstance(delete_files,bool):raise ValueError('Tùy chọn xóa tệp không hợp lệ.')
        if ident is not None and ids is not None:raise ValueError('Chỉ chọn một danh sách lịch sử.')
        if ids is not None and (not isinstance(ids,list) or not ids or any(not isinstance(key,str) for key in ids)):
            raise ValueError('Danh sách lịch sử không hợp lệ.')
        requested=set(ids) if ids is not None else ({ident} if ident is not None else None)
        with self.lock:
            if requested is not None and any(key not in self.jobs for key in requested):
                raise ValueError('Không tìm thấy lượt tải.')
            eligible=[key for key,j in self.jobs.items() if j['status'] in ('completed','cancelled') and key not in self.running and (requested is None or key in requested)]
            if requested is not None and set(eligible)!=requested:
                raise ValueError('Chỉ xóa lịch sử lượt tải đã hoàn tất hoặc đã hủy.')
            removed,failed=0,[]
            for key in eligible:
                job=self.jobs[key]
                if delete_files and job['status']=='completed':
                    try:
                        directory=self.output_for(job)
                        path=directory/job['name']
                        if path.resolve().parent!=directory or path.is_dir():
                            raise ValueError('Đường dẫn tệp không hợp lệ.')
                        path.unlink(missing_ok=True)
                    except (OSError,ValueError):
                        failed.append(job['name'])
                        continue
                del self.jobs[key]
                self.samples.pop(key,None)
                removed+=1
            self.save()
            if failed:
                raise ValueError(f'Đã xóa {removed} mục. Không xóa được {len(failed)} tệp; các mục này vẫn được giữ trong lịch sử. Tệp có thể đang mở hoặc không có quyền xóa.')
            return removed

    def _schedule(self):
        while not self.shutdown.wait(.3):
            with self.lock:
                now = time.time()
                for ident, (event, _) in list(self.running.items()):
                    j = self.jobs[ident]
                    if not j.get('cancel_requested') and j['stop_at'] and now >= j['stop_at']:
                        j['status'] = 'pausing'
                        event.set()
                # Keep a bounded file queue; each file retains its own workers.
                for j in self.jobs.values():
                    if len(self.running) >= MAX_ACTIVE_DOWNLOADS:
                        break
                    if j['status'] != 'queued' or j['id'] in self.running:
                        continue
                    if j['stop_at'] and now >= j['stop_at']:
                        j['status'] = 'paused'
                        self.save()
                        continue
                    if j['start_at'] and j['start_at'] > now:
                        continue
                    event = threading.Event()
                    thread = threading.Thread(target=self._run, args=(j, event), daemon=True)
                    self.running[j['id']] = (event, thread)
                    j['status'] = 'probing'
                    thread.start()

    def _request(self, j, headers=None):
        if google_drive.file_id(j['url']):
            if not hasattr(self.http,'drive_opener'):
                self.http.drive_opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                self.http.drive_urls={}
            return google_drive.open_download(self.http.drive_opener,j['url'],headers,self.http.drive_urls)
        if not hasattr(self.http, 'opener'):
            self.http.opener = urllib.request.build_opener()
            self.http.local_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        opener = self.http.local_opener if urllib.parse.urlsplit(j['url']).hostname in ('127.0.0.1', 'localhost', '::1') else self.http.opener
        return opener.open(urllib.request.Request(j['url'], headers={
            'User-Agent': 'DownloadNow/1.0', 'Accept-Encoding': 'identity', **(headers or {})}), timeout=15)

    def _probe(self, j, stop):
        for attempt in range(5):
            if stop.is_set():
                raise Paused()
            try:
                with self._request(j, {'Range': 'bytes=0-0'}) as r:
                    match = re.fullmatch(r'bytes 0-0/(\d+)', r.headers.get('Content-Range', ''))
                    ranged = r.status == 206 and match is not None
                    total = int(match[1]) if ranged else (int(r.headers['Content-Length']) if r.headers.get('Content-Length') else None)
                    etag = r.headers.get('ETag')
                    modified = r.headers.get('Last-Modified')
                    if ranged:
                        r.read(1)
                    return total, ranged, etag, modified, response_name(r.headers)
            except (OSError, urllib.error.URLError, http.client.HTTPException) as ex:
                if os.environ.get('DOWNLOAD_NOW_DEBUG'):
                    print('request retry', repr(ex), flush=True)
                if isinstance(ex, urllib.error.HTTPError) and ex.code not in (408, 429, 500, 502, 503, 504):
                    raise
                if attempt == 4:
                    raise
                if stop.wait(min(2 ** attempt, 16)):
                    raise Paused()

    def _run(self, j, stop):
        if is_video_page(j['url']):
            return self._run_video(j,stop)
        folder = self.parts / j['id']
        folder.mkdir(exist_ok=True)
        try:
            total, ranged, etag, modified, suggested_name = self._probe(j, stop)
            if stop.is_set():raise Paused()
            with self.lock:
                # Resolve the final server filename once, before publishing a file.
                # Old queues keep their existing names during upgrades.
                if not j.get('name_resolved', True):
                    guessed = link_name(j['url'])
                    generic_link = Path(guessed).suffix.lower() in ('', '.php', '.aspx', '.ashx', '.jsp') or guessed == 'download.bin'
                    if suggested_name and generic_link and not j.get('custom_name', True):
                        j['name'] = self._unique_name(safe_name(suggested_name), exclude=j['id'], directory=self.output_for(j))
                    j['name_resolved'] = True
                    self.save()
            # Only reuse bytes when a strong validator proves entity identity.
            validator_ok = bool(etag and not etag.startswith('W/') and etag == j['etag']) or bool(not etag and modified and modified == j['modified'])
            reuse = ranged and j['ranged'] and total == j['total'] and validator_ok
            if not reuse:
                for part in folder.glob('*.part'):
                    part.unlink()
                j['ranges'] = []
            if not j['ranges']:
                if ranged and total:
                    # Workers claim pending segments dynamically as they finish.
                    size = max(256 * 1024, min(CHUNK, (total + j['connections'] - 1) // j['connections']))
                    j['ranges'] = [[start, min(start + size, total) - 1] for start in range(0, total, size)]
                else:
                    j['ranges'] = [[0, total - 1 if total is not None else None]]
            with self.lock:
                j.update(total=total, ranged=ranged, etag=etag, modified=modified, status='downloading', error='')
                self.samples[j['id']] = (time.monotonic(), self._done(j))
                self.save()
            with concurrent.futures.ThreadPoolExecutor(max_workers=j['connections'] if ranged else 1) as pool:
                futures = [pool.submit(self._segment, j, i, bounds, folder, stop) for i, bounds in enumerate(j['ranges'])]
                try:
                    for f in concurrent.futures.as_completed(futures):
                        f.result()
                except BaseException:
                    stop.set()
                    raise
            if stop.is_set():
                raise Paused()
            target = self.output_for(j) / j['name']
            # Assemble privately, then publish a complete file atomically without
            # overwriting a user file. A crash during assembly is safe to retry.
            # Stage on the destination volume so publishing also works to D:/USB.
            assembled = target.parent / f'.downloadnow-{j["id"]}.tmp'
            with assembled.open('wb') as out:
                for i in range(len(j['ranges'])):
                    with (folder / f'{i}.part').open('rb') as source:
                        while data := source.read(1024 * 1024):
                            out.write(data)
                out.flush()
                os.fsync(out.fileno())
            with self.lock:
                if stop.is_set():raise Paused()
                try:
                    if os.name == 'nt':
                        os.rename(assembled, target)
                    else:
                        os.link(assembled, target)
                except FileExistsError:
                    if not filecmp.cmp(assembled, target, shallow=False):
                        raise ValueError('Tệp đích đã tồn tại với nội dung khác. Hãy đổi tên lượt tải mới.')
                assembled.unlink(missing_ok=True)
                j.update(status='completed', done=target.stat().st_size)
                self.save()
            for part in folder.glob('*.part'):
                part.unlink()
            (folder / 'assembled.tmp').unlink(missing_ok=True)
            folder.rmdir()
        except Paused:
            with self.lock:
                j['status'] = 'paused'
        except Exception as ex:
            with self.lock:
                j.update(status='error', error=str(ex))
        finally:
            with self.lock:
                if j.get('cancel_requested') and j['status']!='completed':
                    try:
                        self._discard_partial(j)
                        j.update(status='cancelled',done=0,ranges=[],error='')
                    except OSError as ex:
                        j.update(status='error',error='Không dọn được tệp tải dở: '+str(ex))
                self.running.pop(j['id'], None)
                self.save()

    def _run_video(self,j,stop):
        folder=self.parts/j['id'];folder.mkdir(exist_ok=True)
        sizes={}
        try:
            if not j.get('custom_name') and not j.get('name_resolved'):
                name=safe_name(video_name(j['url']))
                with self.lock:
                    j.update(name=self._unique_name(name,exclude=j['id'],directory=self.output_for(j)),name_resolved=True)
            if stop.is_set():raise VideoStopped()
            with self.lock:j.update(status='downloading',error='',media_speed=0);self.save()
            def progress(data):
                def number(value):
                    try:return max(0,float(value or 0))
                    except (ValueError,TypeError):return 0
                key=str(data.get('filename','video'))
                done=int(number(data.get('downloaded_bytes')))
                total=number(data.get('total_bytes')) or number(data.get('total_bytes_estimate'))
                sizes[key]=(done,max(done,int(total)) if total else None)
                with self.lock:
                    j.update(done=sum(x[0] for x in sizes.values()),total=sum(x[1] for x in sizes.values()) if all(x[1] is not None for x in sizes.values()) else None,
                             media_speed=number(data.get('speed')),media_tick=time.monotonic())
            source=download_video(j['url'],folder,stop,progress)
            target=self.output_for(j)/j['name']
            assembled=target.parent/f'.downloadnow-{j["id"]}.tmp'
            with source.open('rb') as src,assembled.open('wb') as out:
                while block:=src.read(1024*1024):
                    if stop.is_set():raise VideoStopped()
                    out.write(block)
                out.flush();os.fsync(out.fileno())
            with self.lock:
                if stop.is_set():raise VideoStopped()
                try:
                    if os.name=='nt':os.rename(assembled,target)
                    else:os.link(assembled,target)
                except FileExistsError:
                    if not filecmp.cmp(assembled,target,shallow=False):raise ValueError('Tệp đích đã tồn tại. Hãy đổi tên để giữ nguyên tệp cũ.')
                assembled.unlink(missing_ok=True)
                j.update(status='completed',done=target.stat().st_size,total=target.stat().st_size,media_speed=0)
                self.save()
            self._discard_partial(j)
        except VideoStopped:
            with self.lock:j.update(status='paused',media_speed=0)
        except Exception as ex:
            with self.lock:j.update(status='error',error=str(ex),media_speed=0)
        finally:
            with self.lock:
                if j.get('cancel_requested') and j['status']!='completed':
                    try:self._discard_partial(j);j.update(status='cancelled',done=0,total=None,error='')
                    except OSError as ex:j.update(status='error',error='Không dọn được video tải dở: '+str(ex))
                self.running.pop(j['id'],None);self.save()

    def _segment(self, j, index, bounds, folder, stop):
        path = folder / f'{index}.part'
        start, end = bounds
        expected = end - start + 1 if end is not None else None
        for attempt in range(6):
            if stop.is_set():
                raise Paused()
            have = path.stat().st_size if path.exists() else 0
            if expected is not None and have == expected and j['ranged']:
                return
            if expected is not None and have > expected:
                path.unlink()
                have = 0
            headers = {}
            if j['ranged']:
                headers['Range'] = f'bytes={start + have}-{end}'
                validator = j['etag'] if j['etag'] and not j['etag'].startswith('W/') else j['modified']
                if validator:
                    headers['If-Range'] = validator
            else:
                have = 0
            try:
                with self._request(j, headers) as r:
                    if j['ranged']:
                        wanted = f"bytes {start + have}-{end}/{j['total']}"
                        if r.status != 206 or r.headers.get('Content-Range') != wanted:
                            raise Changed('Máy chủ đã thay đổi tệp hoặc không còn hỗ trợ Range. Hãy tiếp tục để kiểm tra lại.')
                    read=getattr(r,'read1',r.read)
                    with path.open('ab' if j['ranged'] else 'wb',buffering=BLOCK) as f:
                        last_flush=time.monotonic()
                        while True:
                            if stop.is_set():
                                raise Paused()
                            # read1 returns available network bytes promptly, keeping
                            # pause/cancel responsive even on slow connections.
                            data = read(BLOCK)
                            if not data:
                                break
                            if expected is not None and have + len(data) > expected:
                                raise Changed('Máy chủ trả về dữ liệu vượt kích thước dự kiến.')
                            f.write(data)
                            have += len(data)
                            now=time.monotonic()
                            if now-last_flush>=.25:
                                f.flush()
                                last_flush=now
                        f.flush()
                        os.fsync(f.fileno())
                    if expected is not None and have != expected:
                        raise OSError('Kết nối kết thúc trước khi đủ dữ liệu.')
                    return
            except (Paused, Changed):
                raise
            except (OSError, urllib.error.URLError, http.client.HTTPException) as ex:
                if os.environ.get('DOWNLOAD_NOW_DEBUG'):
                    print('segment retry', index, have, repr(ex), flush=True)
                if isinstance(ex, urllib.error.HTTPError) and ex.code not in (408, 429, 500, 502, 503, 504):
                    raise
                if attempt == 5:
                    raise
                if stop.wait(min(2 ** attempt, 16)):
                    raise Paused()

    def _done(self, j):
        if is_video_page(j['url']):return j['done']
        if j['status'] == 'completed':
            return j['done']
        total = 0
        for p in (self.parts / j['id']).glob('*.part'):
            try:
                total += p.stat().st_size
            except FileNotFoundError:
                pass
        return total

    def snapshot(self):
        with self.lock:
            result = []
            for j in self.jobs.values():
                done = self._done(j)
                now = time.monotonic()
                prev_t, prev_d = self.samples.get(j['id'], (now, done))
                speed = max(0, (done - prev_d) / max(now - prev_t, .001)) if j['status'] == 'downloading' else 0
                if is_video_page(j['url']):speed=j.get('media_speed',0) if j['status']=='downloading' and now-j.get('media_tick',0)<3 else 0
                self.samples[j['id']] = (now, done)
                result.append({**j, 'done': done, 'speed': speed, 'ranges': len(j['ranges']),
                               'file_path': str(self.output_for(j) / j['name']) if j['status'] == 'completed' else None})
            return result

    def close(self):
        self.shutdown.set()
        self.scheduler.join()
        with self.lock:
            active = list(self.running.values())
            for event, _ in active:
                event.set()
        for _, thread in active:
            thread.join()
