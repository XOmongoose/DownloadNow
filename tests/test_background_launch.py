import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock,patch
import app


class BackgroundLaunchTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[1]/'data/test-runs'
        base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base)
        assert Path(self.temp.name).resolve().is_relative_to(base.resolve())
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'bridge-token.txt').write_text('local-test-token')

    def test_windowed_streams_write_utf8_log(self):
        with patch('app.sys.stdout',None),patch('app.sys.stderr',None):
            app.background_streams(self.root)
            stream=app.sys.stdout
            self.assertIs(stream,app.sys.stderr)
            stream.write('Ứng dụng chạy nền\n')
        stream.close()
        self.assertIn('Ứng dụng chạy nền',(self.root/'application.log').read_text('utf-8'))

    def test_existing_console_streams_are_unchanged(self):
        out,err=io.StringIO(),io.StringIO()
        with patch('app.sys.stdout',out),patch('app.sys.stderr',err):
            app.background_streams(self.root)
            self.assertIs(app.sys.stdout,out)
            self.assertIs(app.sys.stderr,err)
        self.assertFalse((self.root/'application.log').exists())

    def test_second_launch_authenticates_before_opening_existing_ui(self):
        opener=MagicMock()
        opener.open.return_value.__enter__.return_value=io.BytesIO(json.dumps({'features':['capture-preflight']}).encode())
        with patch('app.urllib.request.build_opener',return_value=opener),patch('app.webbrowser.open') as browser:
            self.assertTrue(app.open_running_app(self.root,8765))
            browser.assert_called_once_with('http://127.0.0.1:8765')
        request=opener.open.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'),'Bearer local-test-token')

    def test_unrelated_server_is_not_opened(self):
        opener=MagicMock()
        opener.open.return_value.__enter__.return_value=io.BytesIO(b'{"features":[]}')
        with patch('app.urllib.request.build_opener',return_value=opener),patch('app.webbrowser.open') as browser:
            self.assertFalse(app.open_running_app(self.root,8765))
            browser.assert_not_called()

    def test_no_browser_flag_does_not_open_existing_ui(self):
        opener=MagicMock()
        opener.open.return_value.__enter__.return_value=io.BytesIO(b'{"features":["capture-preflight"]}')
        with patch('app.urllib.request.build_opener',return_value=opener),patch('app.webbrowser.open') as browser:
            self.assertTrue(app.open_running_app(self.root,8765,True))
            browser.assert_not_called()
