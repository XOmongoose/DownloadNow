"""Optional HTTPS update feed, verified portable packages and idle-only install."""
import hashlib
import ctypes
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
import uuid
import zipfile

LIMIT = 512 * 1024 * 1024


def version_tuple(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):
        raise ValueError('Phiên bản phải có dạng 1.6.0.')
    return tuple(map(int,value.split('.')))


def https_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Nguồn cập nhật và gói tải phải dùng URL HTTPS không chứa mật khẩu.')
    return value


def github_repository(value):
    """Accept owner/repo, a repository page, or the GitHub latest-release API."""
    if not isinstance(value,str):raise ValueError('Nguồn cập nhật không hợp lệ.')
    if '://' not in value:
        parts=value.strip('/').split('/')
    else:
        https_url(value)
        url=urllib.parse.urlsplit(value)
        if url.hostname not in ('github.com','www.github.com','api.github.com'):return None
        if url.query or url.fragment:raise ValueError('Dùng địa chỉ gốc của kho GitHub, không kèm tham số.')
        parts=url.path.strip('/').split('/')
        if url.hostname=='api.github.com':
            if len(parts)!=5 or parts[0]!='repos' or parts[3:]!=['releases','latest']:
                raise ValueError('Dùng URL kho GitHub hoặc API releases/latest.')
            parts=parts[1:3]
        else:
            if parts[2:] not in ([],['releases'],['releases','latest']):
                raise ValueError('Dùng địa chỉ kho dạng https://github.com/chủ-kho/tên-kho.')
            parts=parts[:2]
    if len(parts)!=2:raise ValueError('Kho GitHub phải có dạng tài-khoản/tên-kho.')
    owner,repo=parts
    if repo.endswith('.git'):repo=repo[:-4]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}',owner) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',repo) or repo in ('.','..'):
        raise ValueError('Tên tài khoản hoặc tên kho GitHub không hợp lệ.')
    return owner+'/'+repo


def update_source(value):
    value=value.strip()
    if not value:return ''
    repo=github_repository(value)
    return 'https://github.com/'+repo if repo else https_url(value)


def github_release_info(repository):
    request=urllib.request.Request('https://api.github.com/repos/'+repository+'/releases/latest',
        headers={'Accept':'application/vnd.github+json','User-Agent':'DownloadNow-Updater'})
    try:
        with urllib.request.urlopen(request,timeout=15) as response:
            https_url(response.geturl())
            body=response.read(2*1024*1024+1)
    except urllib.error.HTTPError as error:
        code=error.code
        error.close()
        if code==404:raise ValueError('Chưa đọc được Releases. Kho phải công khai và có Release ổn định đã phát hành.') from error
        if code in (403,429):raise ValueError('GitHub giới hạn lượt truy cập hoặc không cấp quyền. Hãy kiểm tra lại sau.') from error
        raise
    if len(body)>2*1024*1024:raise ValueError('Thông tin GitHub Release quá lớn.')
    release=json.loads(body)
    if release.get('draft') or release.get('prerelease'):
        raise ValueError('Chỉ cập nhật từ GitHub Release ổn định đã phát hành.')
    tag=release.get('tag_name','')
    version=tag[1:] if tag.startswith(('v','V')) else tag
    version_tuple(version)
    filename=f'DownloadNow-{version}-Windows-x64.zip'
    assets=release.get('assets',[])
    matches=[asset for asset in assets if asset.get('name')==filename and asset.get('state','uploaded')=='uploaded']
    if len(matches)!=1:raise ValueError('Release chưa có đúng gói '+filename)
    def asset_url(asset):
        value=https_url(asset['browser_download_url'])
        parsed=urllib.parse.urlsplit(value)
        parts=urllib.parse.unquote(parsed.path).strip('/').split('/')
        if parsed.hostname!='github.com' or len(parts)!=6 or '/'.join(parts[:2]).casefold()!=repository.casefold() or parts[2:4]!=['releases','download'] or parts[4]!=tag or parts[5]!=asset['name']:
            raise ValueError('Tệp phát hành không thuộc đúng kho hoặc tag GitHub.')
        return value
    asset=matches[0]
    url=asset_url(asset)
    digest=asset.get('digest') or ''
    if re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest):
        checksum=digest.split(':',1)[1]
    else:
        candidates=[item for item in assets if item.get('name')==filename+'.sha256']
        if len(candidates)!=1:raise ValueError('Release thiếu SHA-256. Tải kèm tệp .zip.sha256 khi phát hành.')
        with urllib.request.urlopen(asset_url(candidates[0]),timeout=15) as response:
            https_url(response.geturl())
            raw=response.read(4097)
        if len(raw)>4096:raise ValueError('Tệp checksum quá lớn.')
        words=raw.decode('utf-8-sig').strip().split()
        if not words or not re.fullmatch('[a-fA-F0-9]{64}',words[0]) or len(words)>2 or (len(words)==2 and words[1].lstrip('*')!=filename):
            raise ValueError('Tệp checksum không khớp tên gói cập nhật.')
        checksum=words[0]
    return {'version':version,'url':url,'sha256':checksum.lower(),
            'notes':str(release.get('body') or release.get('name') or '')[:4000]}


def choose_update_zip():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost',True)
    try:
        return filedialog.askopenfilename(parent=root,title='Chọn gói cập nhật Download Now',filetypes=[('Gói Download Now','*.zip')]) or None
    finally:
        root.destroy()


class UpdateService:
    def __init__(self,manager,preferences,current,app_home,resources):
        self.manager,self.preferences = manager,preferences
        self.current,self.app_home,self.resources = current,Path(app_home).resolve(),Path(resources)
        self.work = manager.root/'updates'
        self.lock = threading.RLock()
        self.state = {'state':'idle','current_version':current}
        self.available = None
        self.staged = None
        self.stop = threading.Event()
        self.on_install = None
        self.install_requested = False
        self.restart_port = 8765

    def snapshot(self):
        with self.lock:
            result = dict(self.state)
            if not self.preferences.get()['update_feed'] and result['state']=='idle':
                result['state']='unconfigured'
            result['can_install']=bool(getattr(sys,'frozen',False) and sys.platform=='win32')
            result['install_requested']=self.install_requested
            return result

    def _set(self,**values):
        with self.lock:
            self.state.update(values)

    def _start(self,state,operation):
        with self.lock:
            if self.state['state'] in ('checking','downloading','importing','installing'):
                raise ValueError('Đang xử lý cập nhật. Vui lòng chờ.')
            self.state={'state':state,'current_version':self.current}
        def run():
            try:operation()
            except Exception as error:self._set(state='error',error=str(error))
        threading.Thread(target=run,daemon=True).start()

    def check(self):
        self.install_requested=False
        self._start('checking',self._check)

    def accept(self,version):
        """Download exactly the release the user has just approved."""
        with self.lock:
            if not self.available or self.state['state'] not in ('available','ready') or self.available['version']!=version:
                raise ValueError('Phiên bản đã thay đổi. Hãy kiểm tra cập nhật lại.')
            info=dict(self.available)
            if self.state['state']=='ready':
                self.install_requested=True
                return
            def run():
                self._download(info)
                self.install_requested=True
            self._start('downloading',run)

    def run_update(self):
        """User requested pipeline survives closing the web dialog."""
        def run():
            self._check()
            if self.snapshot()['state']=='available':
                self._set(state='downloading')
                self._download(dict(self.available))
                self.install_requested=True
        self._start('checking',run)

    def _check(self):
        feed = self.preferences.get()['update_feed']
        if not feed:
            self._set(state='unconfigured')
            return
        repository=github_repository(feed)
        if repository:
            info=github_release_info(repository)
        else:
            with urllib.request.urlopen(https_url(feed),timeout=15) as response:
                https_url(response.geturl())
                data = response.read(65537)
            if len(data)>65536:
                raise ValueError('Thông tin cập nhật quá lớn.')
            info = json.loads(data)
        version_tuple(info['version'])
        https_url(info['url'])
        if not re.fullmatch(r'[a-fA-F0-9]{64}',info.get('sha256','')):
            raise ValueError('Nguồn cập nhật thiếu mã SHA-256 hợp lệ.')
        self.preferences.set(last_update_check=time.time())
        with self.lock:
            self.available=info
            self.staged=None
        newer = version_tuple(info['version'])>version_tuple(self.current)
        self._set(state='available' if newer else 'up_to_date',version=info['version'],notes=str(info.get('notes',''))[:4000])

    def download(self):
        if not self.available or version_tuple(self.available['version'])<=version_tuple(self.current):
            raise ValueError('Hãy kiểm tra phiên bản trước khi tải cập nhật.')
        info = dict(self.available)
        self._start('downloading',lambda:self._download(info))

    def _download(self,info):
        self.work.mkdir(exist_ok=True)
        archive = self.work/(uuid.uuid4().hex+'.zip')
        digest,total = hashlib.sha256(),0
        with urllib.request.urlopen(https_url(info['url']),timeout=20) as response, archive.open('xb') as output:
            https_url(response.geturl())
            while block:=response.read(1024*1024):
                total+=len(block)
                if total>LIMIT:raise ValueError('Gói cập nhật vượt giới hạn 512 MB.')
                digest.update(block)
                output.write(block)
                self._set(bytes=total)
            output.flush()
            os.fsync(output.fileno())
        if digest.hexdigest().lower()!=info['sha256'].lower():
            raise ValueError('SHA-256 không khớp. Gói cập nhật không được cài.')
        self._prepare(archive,info['version'])

    def import_local(self,chooser=choose_update_zip):
        def run():
            selected = chooser()
            if not selected:
                self._set(state='idle')
                return
            self._prepare(Path(selected))
        self._start('importing',run)

    def _prepare(self,archive,expected=None):
        if Path(archive).stat().st_size>LIMIT:
            raise ValueError('Gói cập nhật vượt giới hạn 512 MB.')
        with zipfile.ZipFile(archive) as package:
            files = [item for item in package.infolist() if not item.is_dir()]
            if len(files)>1000 or sum(item.file_size for item in files)>LIMIT:
                raise ValueError('Gói cập nhật có quá nhiều dữ liệu.')
            names,seen = {},set()
            for item in files:
                path = PurePosixPath(item.filename)
                if ('\\' in item.filename or path.is_absolute() or len(path.parts)<2 or
                    any(part in ('.','..') or ':' in part or part.endswith((' ','.')) for part in path.parts) or
                    stat.S_ISLNK(item.external_attr>>16)):
                    raise ValueError('Gói cập nhật chứa đường dẫn không an toàn.')
                key = item.filename.casefold()
                if key in seen:raise ValueError('Gói cập nhật chứa tệp trùng tên.')
                seen.add(key)
                names[item.filename]=item
            roots={PurePosixPath(name).parts[0] for name in names}
            if len(roots)!=1:raise ValueError('Gói cập nhật phải có một thư mục gốc.')
            prefix=roots.pop()+'/'
            release=json.loads(package.read(prefix+'releases.json'))['releases'][0]
            new_version=release['version']
            version_tuple(new_version)
            if expected and expected!=new_version:raise ValueError('Phiên bản trong gói không khớp nguồn cập nhật.')
            if version_tuple(new_version)<=version_tuple(self.current):raise ValueError('Gói này không mới hơn phiên bản đang chạy.')
            if prefix!=f'DownloadNow-{new_version}-Windows-x64/':raise ValueError('Sai loại gói cập nhật Windows x64.')
            sums={}
            for line in package.read(prefix+'SHA256SUMS.txt').decode('utf-8').splitlines():
                checksum,name=line.split('  ',1)
                if not re.fullmatch('[a-fA-F0-9]{64}',checksum) or name in sums:
                    raise ValueError('Danh sách SHA-256 không hợp lệ.')
                sums[name]=checksum.lower()
            required={name[len(prefix):] for name in names}-{ 'SHA256SUMS.txt' }
            if set(sums)!=required or 'DownloadNow.exe' not in required:
                raise ValueError('Gói thiếu tệp hoặc kiểm tra toàn vẹn không đầy đủ.')
            for browser in ('chromium','firefox'):
                manifest='extension/'+browser+'/manifest.json'
                if manifest not in required or json.loads(package.read(prefix+manifest)).get('version')!=new_version:
                    raise ValueError('Gói phải chứa ứng dụng và các tiện ích cùng phiên bản.')
            marker='extension/chromium/managed.json'
            if marker not in required or json.loads(package.read(prefix+marker))!={'managed':True,'version':new_version}:
                raise ValueError('Gói thiếu cấu hình đồng bộ tiện ích.')
            top={'DownloadNow.exe','README.md','HUONG-DAN.txt','releases.json','SHA256SUMS.txt'}
            for name in required:
                path=PurePosixPath(name)
                extension=(len(path.parts)>=3 and path.parts[0]=='extension' and path.parts[1] in ('chromium','firefox') and path.suffix in ('.js','.json','.html','.css','.png','.ico','.svg','.txt','.md'))
                if name not in top and not extension:raise ValueError('Gói chứa tệp ngoài ứng dụng hoặc dữ liệu người dùng.')
                if hashlib.sha256(package.read(prefix+name)).hexdigest()!=sums[name]:
                    raise ValueError('Tệp trong gói bị hỏng: '+name)
            if package.read(prefix+'DownloadNow.exe')[:2]!=b'MZ':raise ValueError('Tệp EXE không hợp lệ.')
            self.work.mkdir(exist_ok=True)
            destination=self.work/('staged-'+uuid.uuid4().hex)
            destination.mkdir()
            for full in names:
                target=destination/PurePosixPath(full[len(prefix):])
                target.parent.mkdir(parents=True,exist_ok=True)
                with package.open(full) as source,target.open('xb') as output:
                    while block:=source.read(1024*1024):output.write(block)
        self.staged=destination
        self._set(state='ready',version=new_version,notes=release.get('title',''))

    def install(self,prompts):
        if not getattr(sys,'frozen',False) or sys.platform!='win32':
            raise ValueError('Cài tự động chỉ dùng trong bản EXE Windows. Bản mã nguồn có thể chuẩn bị gói để dùng riêng.')
        with self.manager.lock,prompts.lock,self.lock:
            if self.manager.running or any(j['status']=='queued' for j in self.manager.jobs.values()) or any(p['state']=='pending' for p in prompts.items.values()):
                raise ValueError('Hãy tạm dừng hàng đợi và đóng hộp thoại tải trước khi cập nhật.')
            if self.state['state']!='ready' or not self.staged:
                raise ValueError('Chưa có gói cập nhật đã xác minh.')
            for item in self.staged.rglob('*'):
                if item.is_file() and not (self.app_home/item.relative_to(self.staged)).resolve().is_relative_to(self.app_home):
                    raise ValueError('Đích cập nhật đi ra ngoài thư mục ứng dụng.')
            helper=self.work/'DownloadNowUpdater.exe'
            shutil.copy2(sys.executable,helper)
            backup=self.work/('backup-'+uuid.uuid4().hex)
            subprocess.Popen([str(helper),'--apply-update','--update-parent',str(os.getpid()),
                '--update-source',str(self.staged),'--update-destination',str(self.app_home),
                '--update-backup',str(backup),'--update-port',str(self.restart_port),
                '--update-data',str(self.manager.root)],creationflags=subprocess.CREATE_NO_WINDOW,
                env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'})
            self.state['state']='installing'
            self.manager.shutdown.set()
            if self.on_install is not None:
                self.on_install()

    def _auto_tick(self,prompts):
        values=self.preferences.get()
        state=self.snapshot()['state']
        if (self.install_requested or values.get('auto_install_updates')) and values['update_feed']:
            if state=='available':
                self.download()
                return
            if state=='ready' and prompts is not None and getattr(sys,'frozen',False) and sys.platform=='win32':
                with self.manager.lock,prompts.lock:
                    busy=bool(self.manager.running or any(j['status']=='queued' for j in self.manager.jobs.values()) or any(p['state']=='pending' for p in prompts.items.values()))
                if not busy:
                    self.install(prompts)
                return
        # Never discard a verified package while waiting for an idle queue.
        if state in ('available','ready','checking','downloading','importing','installing'):
            return
        if values['auto_check_updates'] and values['update_feed'] and time.time()-values['last_update_check']>86400:
            self.preferences.set(last_update_check=time.time())
            self.check()

    def start_auto_check(self,prompts=None):
        def run():
            while not self.stop.wait(5):
                try:self._auto_tick(prompts)
                except Exception as error:self._set(state='error',error=str(error))
        threading.Thread(target=run,daemon=True).start()


def apply_update(source,destination,backup,parent_id,port=8765,data=None):
    """Private helper mode: wait, back up, replace only application files, restart."""
    source,destination,backup = Path(source).resolve(),Path(destination).resolve(),Path(backup).resolve()
    log=source.parent/'update.log'
    copied=[]
    created=set()
    try:
        if sys.platform!='win32':raise ValueError('Windows update helper required.')
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
        kernel.OpenProcess.restype=ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        process=kernel.OpenProcess(0x00100000,False,parent_id)
        if process:
            try:
                if kernel.WaitForSingleObject(process,120000)!=0:raise ValueError('Ứng dụng cũ chưa thoát.')
            finally:kernel.CloseHandle(process)
        sums={}
        for line in (source/'SHA256SUMS.txt').read_text('utf-8').splitlines():
            digest,name=line.split('  ',1)
            relative=PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name or relative.parts[0]=='data':
                raise ValueError('Unsafe staged path.')
            if name not in ('DownloadNow.exe','README.md','HUONG-DAN.txt','releases.json') and not (len(relative.parts)>=3 and relative.parts[0]=='extension' and relative.parts[1] in ('chromium','firefox')):
                raise ValueError('Unexpected staged file.')
            if not (source/name).resolve().is_relative_to(source) or not (destination/name).resolve().is_relative_to(destination):
                raise ValueError('Unsafe update destination.')
            if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('Staged checksum mismatch.')
            sums[name]=digest
        if 'DownloadNow.exe' not in sums:raise ValueError('Missing executable.')
        for name in [*sums,'SHA256SUMS.txt']:
            original=destination/name
            if original.is_file():
                saved=backup/name
                saved.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(original,saved)
            else:created.add(name)
        for name in [*sums,'SHA256SUMS.txt']:
            target=destination/name
            target.parent.mkdir(parents=True,exist_ok=True)
            temp=target.with_name(target.name+'.updating')
            shutil.copy2(source/name,temp)
            for attempt in range(60):
                try:
                    os.replace(temp,target)
                    break
                except PermissionError:
                    if attempt==59:raise
                    time.sleep(1)
            copied.append(name)
        log.write_text('Update installed successfully.\n',encoding='utf-8')
        arguments=[str(destination/'DownloadNow.exe'),'--port',str(port)]
        if data is not None:arguments+=['--data',str(data)]
        subprocess.Popen(arguments,cwd=destination,creationflags=subprocess.CREATE_NO_WINDOW,
                         env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'})
        return 0
    except Exception as error:
        for name in copied:
            saved=backup/name
            if saved.is_file():
                try:shutil.copy2(saved,destination/name)
                except OSError:pass
            elif name in created:
                try:(destination/name).unlink(missing_ok=True)
                except OSError:pass
        log.write_text('Update failed; originals restored where possible: '+str(error),encoding='utf-8')
        return 1
