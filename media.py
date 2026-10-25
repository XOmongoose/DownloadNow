"""Public video page downloads through the bundled, pinned yt-dlp runtime."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from urllib.parse import urlsplit


def is_video_page(url):
    p=urlsplit(url)
    host=(p.hostname or '').lower().removeprefix('www.').removeprefix('m.')
    if p.scheme not in ('http','https') or p.username or p.password:return False
    if host=='youtu.be':return bool(p.path.strip('/'))
    if host=='youtube.com':return p.path.startswith(('/shorts/','/watch','/live/'))
    if host=='instagram.com':return p.path.startswith(('/reel/','/reels/','/p/'))
    if host in ('facebook.com','web.facebook.com'):return p.path.startswith(('/reel/','/reels/','/watch','/share/r/','/stories/','/video.php','/video/video.php','/story.php','/permalink.php')) or '/videos/' in p.path or '/posts/' in p.path
    return False


def runtime_directory():
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))
    directory=base/'media-runtime' if getattr(sys,'frozen',False) else base/'build'/'media-runtime'
    if not all((directory/name).is_file() for name in ('yt-dlp.exe','ffmpeg.exe','deno.exe')):
        raise ValueError('Thiếu bộ xử lý video. Dùng gói Windows đầy đủ hoặc chạy tools/build_media_runtime.py.')
    return directory


def command(url):
    if not is_video_page(url):raise ValueError('Liên kết trang video không được hỗ trợ.')
    directory=runtime_directory()
    return [str(directory/'yt-dlp.exe'),'--ignore-config','--no-playlist','--no-warnings',
            '--no-colors','--socket-timeout','20','--retries','3','--fragment-retries','3',
            '--js-runtimes','deno:'+str(directory/'deno.exe'),'--ffmpeg-location',str(directory/'ffmpeg.exe'),
            '--format','bv*[vcodec^=avc1][height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*[height<=1080]+ba/b',
            '--merge-output-format','mp4','--remux-video','mp4']


def process_options():
    return dict(encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
                env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'})


def video_info(url):
    result=subprocess.run(command(url)+['--skip-download','--dump-single-json','--',url],
                          capture_output=True,timeout=100,**process_options())
    if result.returncode:raise ValueError(video_error(result.stderr,url))
    info=json.loads(result.stdout)
    if info.get('_type') in ('playlist','multi_video'):raise ValueError('Hãy dùng liên kết của một video cụ thể.')
    return info


def video_name(url):
    info=video_info(url)
    return str(info.get('title') or info.get('id') or 'Video')[:150]+'.mp4'


def media_size(info):
    size=info.get('filesize')
    if isinstance(size,int) and not isinstance(size,bool) and size>=0:
        return {'bytes':size,'estimated':False}
    parts=info.get('requested_formats') or info.get('requested_downloads')
    if isinstance(parts,list) and parts:
        sizes=[media_size(part) for part in parts if isinstance(part,dict)]
        if len(sizes)==len(parts) and all(value is not None for value in sizes):
            # Muxed output includes container overhead, so combined streams are an estimate.
            return {'bytes':sum(value['bytes'] for value in sizes),'estimated':True}
    size=info.get('filesize_approx')
    if isinstance(size,(int,float)) and not isinstance(size,bool) and size>=0:
        return {'bytes':int(size),'estimated':True}
    return None


def video_size(url):
    return media_size(video_info(url))


def video_error(message,url=''):
    if '/stories/' in url and ('login.php' in message or 'Unsupported URL' in message):
        return 'Tin Facebook này cần mở trong trình duyệt đã đăng nhập. Bật Bắt link tệp, tải lại Facebook, mở đúng Tin và dùng nút Tải video / Tin. Nếu chưa lấy được nguồn phát, ứng dụng sẽ không tải trang đăng nhập thay video.'
    detail=next((line for line in reversed(message.splitlines()) if 'ERROR:' in line),message[-800:])
    return 'Không tải được video. Video phải truy cập công khai; nền tảng có thể yêu cầu đăng nhập hoặc giới hạn truy cập. '+detail[:650]


class VideoStopped(Exception):pass


def stop_process(process):
    if process.poll() is not None:return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,**process_options())
    else:process.terminate()
    try:process.wait(timeout=8)
    except subprocess.TimeoutExpired:process.kill();process.wait()


def download_video(url,folder,stop,progress):
    """Keep fragments isolated per job; pause kills only this process tree."""
    folder=Path(folder)
    fields=('downloaded_bytes','total_bytes','total_bytes_estimate','speed','filename','status')
    template='download:DN_PROGRESS {'+','.join('"'+key+'":%(progress.'+key+')j' for key in fields)+'}'
    args=command(url)+['--newline','--progress','--output-na-placeholder','null','--progress-template',template,'--continue',
                      '--no-overwrites','--output',str(folder/'video.%(ext)s'),'--',url]
    process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**process_options())
    lines=queue.Queue(maxsize=256)
    def read():
        try:
            for line in process.stdout:
                # Bounded queue. On stop, allow the reader to finish without blocking.
                while not stop.is_set():
                    try:lines.put(line,timeout=.2);break
                    except queue.Full:continue
        finally:process.stdout.close()
    reader=threading.Thread(target=read,daemon=True);reader.start()
    errors=[]
    try:
        while reader.is_alive() or not lines.empty() or process.poll() is None:
            if stop.is_set():raise VideoStopped()
            try:line=lines.get(timeout=.2)
            except queue.Empty:continue
            if line.startswith('DN_PROGRESS '):
                try:
                    data=json.loads(line[len('DN_PROGRESS '):])
                    progress(data)
                except (ValueError,TypeError):pass
            elif 'ERROR:' in line:errors=(errors+[line])[-8:]
        if process.wait()!=0:raise ValueError(video_error(''.join(errors),url))
        target=folder/'video.mp4'
        if not target.is_file() or not target.stat().st_size:raise ValueError('Bộ xử lý chưa tạo được tệp MP4 hoàn chỉnh.')
        return target
    finally:
        stop_process(process)
        reader.join(timeout=3)
