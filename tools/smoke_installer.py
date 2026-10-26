"""Install and uninstall in an isolated directory; never touch the real app."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import uuid
import winreg

ROOT=Path(__file__).resolve().parents[1]
APP_KEY=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{6F1D4BC1-5435-4A86-B8F2-2D91D7003F4C}_is1'

def registered():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,APP_KEY,0,winreg.KEY_READ|winreg.KEY_WOW64_64KEY) as key:
            return winreg.QueryValueEx(key,'Publisher')[0]
    except FileNotFoundError:return None

def main():
    if registered() is not None:
        raise SystemExit('A real installer registration exists; refusing to replace it for testing.')
    version=json.loads((ROOT/'releases.json').read_text('utf-8'))['releases'][0]['version']
    target=(ROOT/'build'/('installer-smoke-'+uuid.uuid4().hex)).resolve()
    assert target.is_relative_to((ROOT/'build').resolve()) and not target.exists()
    setup=ROOT/'dist'/f'DownloadNow-Setup-{version}-Windows-x64.exe'
    options=dict(creationflags=subprocess.CREATE_NO_WINDOW,env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'})
    args=[str(setup),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/NOICONS','/TASKS=',f'/DIR={target}',f'/LOG={ROOT/"build/installer-smoke.log"}']
    subprocess.run(args,check=True,timeout=120,**options)
    process=None
    try:
        assert registered()=='XOmongoose'
        exe=target/'DownloadNow.exe'
        assert exe.is_file() and not (target/'data').exists()
        assert (target/'extension/chromium/manifest.json').is_file()
        assert json.loads((target/'extension/chromium/manifest.json').read_text('utf-8'))['version']==version
        subprocess.run([str(exe),'--self-test-tls'],check=True,timeout=30,**options)
        profile=target/'data';profile.mkdir()
        marker=profile/'keep-this-download.txt';marker.write_text('Preserve downloads on uninstall',encoding='utf-8')
        (profile/'preferences.json').write_text(json.dumps({'auto_check_updates':False,'auto_install_updates':False,'update_confirmation_version':1}))
        # The test instance has its own port and data; the real app is untouched.
        import socket
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        process=subprocess.Popen([str(exe),'--setup-browser','--no-browser','--port',str(port)],**options)
        for _ in range(100):
            try:
                token=(profile/'bridge-token.txt').read_text().strip()
                headers={'Authorization':'Bearer '+token}
                info=json.load(opener.open(urllib.request.Request(base+'/api/info',headers=headers),timeout=3))
                if info['version']==version:break
            except (OSError,ValueError):time.sleep(.2)
        else:raise AssertionError('Installed app did not start')
        for _ in range(5):
            try:
                page=opener.open(base+'/').read().decode('utf-8')
                jobs=json.load(opener.open(urllib.request.Request(base+'/api/jobs',headers=headers)))
                break
            except OSError:time.sleep(.2)
        else:raise AssertionError('Cannot read installed app')
        assert 'Tác giả: <strong>XOmongoose</strong></span>' in page
        assert jobs==[], 'Installer must not contain the developer download history'
        setup=json.load(opener.open(urllib.request.Request(base+'/api/extension/setup',headers=headers)))
        assert Path(setup['folder'])==(target/'extension/chromium').resolve()
        assert setup['requires_confirmation'] and setup['distribution']=='unpacked'
        blocked=subprocess.run(args,timeout=45,**options)
        assert blocked.returncode!=0, 'Reinstallation must refuse to replace the running app'
        print('Install verified: clean queue, publisher, extensions, TLS, app startup and running-app guard.',flush=True)
    finally:
        if process:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,**options)
        uninstaller=target/'unins000.exe'
        if uninstaller.exists():
            subprocess.run([str(uninstaller),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'],check=True,timeout=60,**options)
    assert not (target/'DownloadNow.exe').exists()
    assert registered() is None
    assert marker.read_text('utf-8')=='Preserve downloads on uninstall'
    print('Uninstall verified: app removed, download data preserved. Test folder: '+str(target),flush=True)

if __name__=='__main__':main()
