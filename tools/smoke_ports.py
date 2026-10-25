"""Frozen integration check: skip an occupied port, persist and reopen correctly."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]

def main():
    version=json.loads((ROOT/'releases.json').read_text('utf-8'))['releases'][0]['version']
    exe=ROOT/'dist'/f'DownloadNow-{version}-Windows-x64/DownloadNow.exe'
    profile=ROOT/'build'/('port-smoke-'+uuid.uuid4().hex)
    profile.mkdir()
    (profile/'preferences.json').write_text(json.dumps({'auto_check_updates':False,'auto_install_updates':False,'update_confirmation_version':1}))
    class OtherApplication(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            self.send_response(200);self.end_headers();self.wfile.write(b'Other application remains available')
    other=ThreadingHTTPServer(('127.0.0.1',0),OtherApplication)
    threading.Thread(target=other.serve_forever,daemon=True).start()
    options=dict(creationflags=subprocess.CREATE_NO_WINDOW,env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'})
    args=[str(exe),'--port',str(other.server_port),'--data',str(profile),'--no-browser']
    process=subprocess.Popen(args,**options)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def read(url,headers=None):
        for attempt in range(6):
            try:return opener.open(urllib.request.Request(url,headers=headers or {}),timeout=3).read()
            except OSError:
                if attempt==5:raise
                time.sleep(.2)
    try:
        for _ in range(100):
            try:
                port=json.loads((profile/'bridge-endpoint.json').read_text('utf-8'))['port']
                token=(profile/'bridge-token.txt').read_text().strip()
                base=f'http://127.0.0.1:{port}'
                info=json.loads(read(base+'/api/discovery'))
                if info['application']=='DownloadNow':break
            except (OSError,ValueError):time.sleep(.2)
        else:raise AssertionError('No free-port endpoint was published')
        assert port!=other.server_port and 1024<=port<=65535
        assert info=={'application':'DownloadNow','protocol':1,'version':version,'port':port}
        assert token not in json.dumps(info)
        assert json.loads(read(base+'/api/jobs',{'Authorization':'Bearer '+token}))==[]
        assert b'Other application' in read(f'http://127.0.0.1:{other.server_port}/')
        subprocess.run(args,check=True,timeout=30,**options)
        assert json.loads((profile/'bridge-endpoint.json').read_text())['port']==port
        assert json.loads(read(base+'/api/discovery'))['port']==port
        print(f'Frozen port check passed: occupied {other.server_port} skipped; actual port {port}; second launch reuses it; other server intact.',flush=True)
    finally:
        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,**options)
        other.shutdown();other.server_close()

if __name__=='__main__':main()
