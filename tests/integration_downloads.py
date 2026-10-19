import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from app import make_server
from engine import Manager

PAYLOAD = bytes(range(256)) * 12288


class Source(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'
    etag = '"v1"'
    payload = PAYLOAD
    ranges_seen = []
    drop_once = False
    slow = False

    def log_message(self, *_):
        pass

    def do_GET(self):
        data = type(self).payload
        ranged = self.path != '/plain' and self.headers.get('Range')
        start, end = 0, len(data) - 1
        if ranged:
            start, end = map(int, self.headers['Range'][6:].split('-'))
            end = min(end, len(data)-1)
            type(self).ranges_seen.append((start,end))
        self.send_response(206 if ranged else 200)
        self.send_header('Content-Length', str(end-start+1))
        self.send_header('ETag', type(self).etag)
        self.send_header('Connection', 'close')
        self.close_connection = True
        if ranged:
            self.send_header('Content-Range', f'bytes {start}-{end}/{len(data)}')
        self.end_headers()
        try:
            if type(self).drop_once and end-start>1:
                type(self).drop_once=False
                self.wfile.write(data[start:start+65536])
                self.wfile.flush()
                self.close_connection=True
                self.connection.shutdown(socket.SHUT_RDWR)
                return
            if not type(self).slow:
                self.wfile.write(data[start:end+1])
            else:
                for i in range(start,end+1,16384):
                    self.wfile.write(data[i:min(i+16384,end+1)])
                    if end-start>1:
                        time.sleep(.006)
            self.wfile.flush()
        except (OSError, ConnectionError):
            pass


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=ThreadingHTTPServer(('127.0.0.1',0),Source)
        cls.source.request_queue_size = 32
        cls.thread=threading.Thread(target=cls.source.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.source.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.source.shutdown()
        cls.source.server_close()

    def setUp(self):
        Source.etag='"v1"';Source.payload=PAYLOAD;Source.ranges_seen=[];Source.drop_once=False;Source.slow=False
        self.temp=tempfile.TemporaryDirectory()
        self.manager=Manager(self.temp.name)

    def tearDown(self):
        self.manager.close()
        self.temp.cleanup()

    def wait(self, ident, statuses=('completed','error'), timeout=15):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            with self.manager.lock:
                j=self.manager.jobs[ident].copy()
                if j['status'] in statuses and (j['status'] not in ('paused','error') or ident not in self.manager.running):
                    return j
            time.sleep(.02)
        self.fail(f'Timeout: {self.manager.jobs[ident]}, parts={[(p.name,p.stat().st_size) for p in (self.manager.parts/ident).glob("*.part")]}, requests={Source.ranges_seen}')

    def verify(self, ident, payload=PAYLOAD):
        j=self.wait(ident)
        self.assertEqual(j['status'],'completed',j.get('error'))
        self.assertEqual((self.manager.output/j['name']).read_bytes(),payload)

    def test_parallel_exact_bytes(self):
        ident=self.manager.add(self.url+'/file',connections=8)
        self.verify(ident)
        self.assertGreater(len(Source.ranges_seen),2)

    def test_disconnect_retries_from_saved_offset(self):
        Source.drop_once=True
        ident=self.manager.add(self.url+'/file',connections=1)
        self.verify(ident)
        self.assertIn((65536,len(PAYLOAD)-1),Source.ranges_seen)

    def pause_partial(self):
        Source.slow=True
        ident=self.manager.add(self.url+'/file',connections=1)
        end=time.monotonic()+8
        while time.monotonic()<end:
            if self.manager._done(self.manager.jobs[ident])>=65536:
                break
            time.sleep(.01)
        self.manager.action(ident,'pause')
        self.wait(ident,('paused',))
        self.assertGreater(self.manager._done(self.manager.jobs[ident]),0)
        return ident

    def test_resume_after_restart(self):
        ident=self.pause_partial()
        done=self.manager._done(self.manager.jobs[ident])
        self.manager.close()
        self.manager=Manager(self.temp.name)
        Source.slow=False;Source.ranges_seen=[]
        self.manager.action(ident,'resume')
        self.verify(ident)
        self.assertIn((done,len(PAYLOAD)-1),Source.ranges_seen)

    def test_changed_etag_discards_old_bytes(self):
        ident=self.pause_partial()
        Source.slow=False;Source.etag='"v2"';Source.payload=b'Z'*len(PAYLOAD);Source.ranges_seen=[]
        self.manager.action(ident,'resume')
        self.verify(ident,Source.payload)
        self.assertIn((0,len(PAYLOAD)-1),Source.ranges_seen)

    def test_plain_server(self):
        ident=self.manager.add(self.url+'/plain')
        self.verify(ident)
        self.assertFalse(self.manager.jobs[ident]['ranged'])

    def test_scheduled_start_and_expired_stop(self):
        ident=self.manager.add(self.url+'/file',start_at=time.time()+1)
        time.sleep(.4)
        self.assertEqual(self.manager.jobs[ident]['status'],'queued')
        self.verify(ident)
        expired=self.manager.add(self.url+'/file',stop_at=time.time()-.1)
        self.wait(expired,('paused',))
        self.assertEqual(self.manager._done(self.manager.jobs[expired]),0)

    def test_stop_during_download(self):
        Source.slow=True
        ident=self.manager.add(self.url+'/file',connections=1,stop_at=time.time()+.6)
        self.wait(ident,('paused',))
        self.assertLess(self.manager._done(self.manager.jobs[ident]),len(PAYLOAD))

    def test_api_auth_host_and_add(self):
        server=make_server(self.manager,0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with self.assertRaises(HTTPError) as e:
                urlopen(base+'/api/jobs')
            self.assertEqual(e.exception.code,401)
            e.exception.close()
            token=(Path(self.temp.name)/'bridge-token.txt').read_text()
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'}
            req=Request(base+'/api/jobs',data=json.dumps({'url':self.url+'/file','start_at':time.time()+60}).encode(),headers=headers)
            with urlopen(req) as r:
                self.assertEqual(r.status,201)
            with urlopen(Request(base+'/api/jobs',headers=headers)) as r:
                self.assertEqual(len(json.load(r)),1)
            with self.assertRaises(HTTPError) as e:
                urlopen(Request(base+'/',headers={'Host':'attacker.example'}))
            self.assertEqual(e.exception.code,403)
            e.exception.close()
            with urlopen(base+'/') as r:
                self.assertIn('Download Now',r.read().decode())
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_no_overwrite_and_safe_filename(self):
        (self.manager.output/'file.bin').write_bytes(b'keep')
        ident=self.manager.add(self.url+'/file',name='file.bin')
        self.verify(ident)
        self.assertEqual((self.manager.output/'file.bin').read_bytes(),b'keep')
        self.assertEqual(self.manager.jobs[ident]['name'],'file (1).bin')


if __name__=='__main__':
    unittest.main()
