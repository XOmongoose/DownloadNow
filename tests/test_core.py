"""Deterministic downloader checks with an in-memory HTTP transport.

The real HTTP suite is in integration_downloads.py and remains independently runnable.
"""
import io
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch, MagicMock

from engine import Manager, safe_name, valid_url, link_name, response_name
import integration_downloads as fixtures

Source, PAYLOAD = fixtures.Source, fixtures.PAYLOAD


class Response(io.BytesIO):
    def __init__(self, data, headers, status, slow, drop):
        super().__init__(data)
        self.headers = headers
        self.status = status
        self.slow = slow
        self.drop = drop

    def read(self, size=-1):
        if self.drop and self.tell() >= 65536:
            raise ConnectionResetError('Simulated network interruption')
        if self.slow and len(self.getbuffer()) > 1:
            time.sleep(.025)
        return super().read(size)


transport_lock = threading.Lock()


def request(manager, job, headers=None):
    headers = headers or {}
    with transport_lock:
        data = Source.payload
        ranged = not job['url'].endswith('/plain') and 'Range' in headers
        start, end = 0, len(data)-1
        if ranged:
            start, end = map(int, headers['Range'][6:].split('-'))
            Source.ranges_seen.append((start, end))
        info = {'Content-Length': str(end-start+1), 'ETag': Source.etag}
        if ranged:
            info['Content-Range'] = f'bytes {start}-{end}/{len(data)}'
        drop = Source.drop_once and end-start > 1
        if drop:
            Source.drop_once = False
        return Response(data[start:end+1], info, 206 if ranged else 200, Source.slow, drop)


class CoreTests(fixtures.DownloadTests):
    @classmethod
    def setUpClass(cls):
        cls.url = 'http://fixture.invalid'
        cls.patcher = patch.object(Manager, '_request', request)
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def setUp(self):
        Source.etag = '"v1"'
        Source.payload = PAYLOAD
        Source.ranges_seen = []
        Source.drop_once = False
        Source.slow = False
        root = Path(__file__).resolve().parents[1] / 'data' / 'test-runs'
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.manager = Manager(self.temp.name)

    def test_api_auth_host_and_add(self):
        # Actual HTTP authorization is exercised by the integration suite.
        for url in ('file:///etc/passwd', 'ftp://example.com/file', 'http://user:pass@example.com'):
            with self.assertRaises(ValueError):
                valid_url(url)
        self.assertNotIn('/', safe_name('../name?.zip'))
        self.assertTrue(safe_name('CON').startswith('download_'))
        with self.assertRaises(ValueError):
            self.manager.add(self.url, connections=9)

    def test_cancel_paused_removes_partial_and_cannot_resume(self):
        ident=self.pause_partial()
        self.assertTrue((self.manager.parts/ident).exists())
        self.manager.action(ident,'cancel')
        self.assertEqual(self.manager.jobs[ident]['status'],'cancelled')
        self.assertFalse((self.manager.parts/ident).exists())
        with self.assertRaises(ValueError):self.manager.action(ident,'resume')

    def test_cancel_running_waits_for_workers_and_removes_partial(self):
        Source.slow=True
        ident=self.manager.add(self.url+'/cancel.zip')
        end=time.monotonic()+5
        while time.monotonic()<end:
            if self.manager.jobs[ident]['status']=='downloading' and self.manager._done(self.manager.jobs[ident])>0:break
            time.sleep(.01)
        else:self.fail('Download never started')
        self.manager.action(ident,'cancel')
        self.assertEqual(self.wait(ident,statuses=('cancelled',))['status'],'cancelled')
        self.assertFalse((self.manager.parts/ident).exists())
        self.assertFalse((self.manager.output/'cancel.zip').exists())

    def test_restart_finishes_pending_cancellation(self):
        ident=self.pause_partial()
        self.manager.close()
        self.manager.jobs[ident].update(status='cancelling',cancel_requested=True)
        self.manager.save()
        self.manager=Manager(self.temp.name)
        self.assertEqual(self.manager.jobs[ident]['status'],'cancelled')
        self.assertFalse((self.manager.parts/ident).exists())

    def test_clear_history_keeps_downloaded_file_and_resumable_jobs(self):
        completed=self.manager.add(self.url+'/keep.zip')
        self.verify(completed)
        paused=self.pause_partial()
        cancelled=self.manager.add(self.url+'/cancelled.zip',start_at=time.time()+3600)
        self.manager.action(cancelled,'cancel')
        self.assertEqual(self.manager.clear_history(),2)
        self.assertEqual(set(self.manager.jobs),{paused})
        self.assertEqual((self.manager.output/'keep.zip').read_bytes(),PAYLOAD)
        self.assertTrue((self.manager.parts/paused).exists())
        self.manager.close()
        self.manager=Manager(self.temp.name)
        self.assertEqual(set(self.manager.jobs),{paused})

    def test_clear_one_history_record_only(self):
        first=self.manager.add(self.url+'/first.zip',start_at=time.time()+3600)
        second=self.manager.add(self.url+'/second.zip',start_at=time.time()+3600)
        self.manager.action(first,'cancel')
        self.manager.action(second,'cancel')
        self.assertEqual(self.manager.clear_history(first),1)
        self.assertIn(second,self.manager.jobs)

    def test_history_cannot_remove_resumable_download(self):
        ident=self.manager.add(self.url+'/waiting.zip',start_at=time.time()+3600)
        with self.assertRaises(ValueError):self.manager.clear_history(ident)
        self.assertIn(ident,self.manager.jobs)

    def test_restart_recovers_running_job_automatically(self):
        ident = self.pause_partial()
        self.manager.close()
        self.manager.jobs[ident]['status'] = 'downloading'
        self.manager.save()
        Source.slow = False
        self.manager = Manager(self.temp.name)
        self.verify(ident)

    def test_names_from_url_and_query(self):
        self.assertEqual(link_name('https://example.com/B%C3%A1o%20c%C3%A1o+2026.pdf?token=123'), 'Báo cáo+2026.pdf')
        self.assertEqual(link_name('https://example.com/download?filename=Bao+cao.zip'), 'Bao cao.zip')
        self.assertEqual(link_name('https://example.com/get?file=music.mp3'), 'music.mp3')
        self.assertEqual(link_name('https://example.com/'), 'download.bin')
        self.assertEqual(response_name({'Content-Disposition': "attachment; filename*=UTF-8''B%C3%A1o%20c%C3%A1o.pdf"}), 'Báo cáo.pdf')

    def test_server_name_only_for_generic_link(self):
        def named_request(manager, job, headers=None):
            response = request(manager, job, headers)
            response.headers['Content-Disposition'] = "attachment; filename*=UTF-8''B%C3%A1o%20c%C3%A1o.pdf"
            return response
        with patch.object(Manager, '_request', named_request):
            generic = self.manager.add(self.url+'/download.php')
            self.verify(generic)
            self.assertEqual(self.manager.jobs[generic]['name'], 'Báo cáo.pdf')
            explicit = self.manager.add(self.url+'/original.zip')
            self.verify(explicit)
            self.assertEqual(self.manager.jobs[explicit]['name'], 'original.zip')
            custom = self.manager.add(self.url+'/download', name='my-file.zip')
            self.verify(custom)
            self.assertEqual(self.manager.jobs[custom]['name'], 'my-file.zip')

    def test_completed_path_and_missing_file(self):
        ident = self.manager.add(self.url+'/file.zip')
        with self.assertRaises(ValueError):
            self.manager.completed_path(ident)
        self.verify(ident)
        path = self.manager.completed_path(ident)
        self.assertEqual(path, self.manager.output/'file.zip')
        snapshot = next(j for j in self.manager.snapshot() if j['id'] == ident)
        self.assertEqual(snapshot['file_path'], str(path))
        path.rename(self.manager.output/'moved.zip')
        with self.assertRaisesRegex(ValueError, 'Không tìm thấy'):
            self.manager.completed_path(ident)
        self.manager.jobs[ident]['name'] = '../outside.txt'
        with self.assertRaisesRegex(ValueError, 'không hợp lệ'):
            self.manager.completed_path(ident)

    def test_open_folder_does_not_execute_file(self):
        import app
        ident = self.manager.add(self.url+'/file.exe')
        self.verify(ident)
        with patch('app.sys.platform', 'win32'), patch('app.os.startfile', create=True) as launch:
            app.open_download_folder(self.manager, ident)
            launch.assert_called_once_with(str(self.manager.output))

    def capture_response(self, mime='application/zip', disposition=''):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 206
        response.headers = {'Content-Type':mime, 'Content-Disposition':disposition}
        response.geturl.return_value = self.url+'/file.zip'
        response.read.return_value = b'x'
        return response

    def test_capture_verifies_then_deduplicates(self):
        with patch('engine.urllib.request.urlopen', return_value=self.capture_response()) as network:
            first = self.manager.capture(self.url+'/file.zip', request_id='capture-0001')
            second = self.manager.capture(self.url+'/file.zip', request_id='capture-0001')
            self.assertEqual(first, second)
            network.assert_called_once()
            self.assertEqual(len(self.manager.jobs), 1)
            with self.assertRaises(ValueError):
                self.manager.capture(self.url+'/other.zip', request_id='capture-0001')
        self.verify(first)

    def test_capture_login_page_stays_in_browser(self):
        with patch('engine.urllib.request.urlopen', return_value=self.capture_response('text/html')):
            with self.assertRaisesRegex(ValueError, 'đăng nhập'):
                self.manager.capture(self.url+'/private', request_id='capture-0002')
        self.assertEqual(self.manager.jobs, {})

    def test_capture_network_failure_does_not_enqueue(self):
        with patch('engine.urllib.request.urlopen', side_effect=OSError('Network unavailable')):
            with self.assertRaisesRegex(ValueError, 'Trình duyệt'):
                self.manager.capture(self.url+'/file.zip', request_id='capture-0003')
        self.assertEqual(self.manager.jobs, {})

    def test_capture_explicit_html_attachment(self):
        with patch('engine.urllib.request.urlopen', return_value=self.capture_response('text/html', 'attachment; filename="page.html"')):
            ident = self.manager.capture(self.url+'/page.html', request_id='capture-0004')
        self.verify(ident)

    def test_selected_directory_is_used_and_persisted(self):
        chosen = Path(self.temp.name)/'chosen'
        chosen.mkdir()
        ident = self.manager.add(self.url+'/file.zip',save_dir=str(chosen))
        self.assertEqual(self.wait(ident)['status'],'completed')
        self.assertEqual((chosen/'file.zip').read_bytes(),PAYLOAD)
        self.assertFalse((self.manager.output/'file.zip').exists())
        self.assertEqual(self.manager.completed_path(ident), chosen/'file.zip')
        self.manager.close()
        self.manager = Manager(self.temp.name)
        self.assertEqual(self.manager.completed_path(ident), chosen/'file.zip')

    def test_same_filename_allowed_in_different_directories(self):
        chosen = Path(self.temp.name)/'chosen'
        chosen.mkdir()
        first = self.manager.add(self.url+'/file.zip')
        second = self.manager.add(self.url+'/file.zip',save_dir=str(chosen))
        self.verify(first)
        self.assertEqual(self.wait(second)['status'],'completed')
        self.assertEqual(self.manager.jobs[second]['name'],'file.zip')
        with self.assertRaises(ValueError):
            self.manager.add(self.url+'/file.zip',save_dir='relative-folder')

    def wait_prompt(self, prompts, ident):
        deadline = time.monotonic()+4
        while time.monotonic()<deadline:
            state = prompts.get(ident)
            if state['state']!='pending':
                return state
            time.sleep(.01)
        self.fail('Save prompt did not finish')

    def test_save_prompt_enqueues_only_after_selection(self):
        from save_dialogs import SavePrompts
        chosen = Path(self.temp.name)/'chosen'
        chosen.mkdir()
        entered, release = threading.Event(), threading.Event()
        def chooser(name,directory):
            entered.set()
            release.wait(3)
            return chosen/'renamed.zip'
        prompts = SavePrompts(self.manager,chooser=chooser)
        ticket = prompts.start({'url':self.url+'/file.zip'})
        self.assertTrue(entered.wait(1))
        self.assertEqual(prompts.get(ticket)['state'],'pending')
        self.assertEqual(self.manager.jobs,{})
        release.set()
        result = self.wait_prompt(prompts,ticket)
        self.assertEqual(result['state'],'accepted')
        self.assertEqual(self.wait(result['id'])['status'],'completed')
        self.assertEqual((chosen/'renamed.zip').read_bytes(),PAYLOAD)

    def test_save_prompt_cancel_creates_no_job(self):
        from save_dialogs import SavePrompts
        prompts = SavePrompts(self.manager,chooser=lambda *_:None)
        ticket = prompts.start({'url':self.url+'/file.zip'})
        self.assertEqual(self.wait_prompt(prompts,ticket)['state'],'cancelled')
        self.assertEqual(self.manager.jobs,{})

    def test_automatic_save_prompt_is_deduplicated(self):
        from save_dialogs import SavePrompts
        prompts = SavePrompts(self.manager,chooser=lambda *_:self.manager.output/'selected.zip')
        with patch('engine.urllib.request.urlopen', return_value=self.capture_response()):
            data = {'url':self.url+'/file.zip','request_id':'save-prompt-001'}
            ticket = prompts.start(data,automatic=True)
            self.assertEqual(prompts.start(data,automatic=True),ticket)
            result = self.wait_prompt(prompts,ticket)
        self.assertEqual(result['state'],'accepted')
        self.assertEqual(len(self.manager.jobs),1)
        self.verify(result['id'])
