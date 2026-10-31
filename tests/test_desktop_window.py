import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import desktop_window

class DesktopWindowTests(unittest.TestCase):
    def test_native_window_rejects_remote_and_credential_urls(self):
        for url in ['https://example.com/','http://localhost:8765/','http://127.0.0.1:8765.evil.test/','http://user:pass@127.0.0.1:8765/','http://127.0.0.1:8765/api/jobs','http://127.0.0.1:8765/?unknown=1']:
            with self.subTest(url=url),self.assertRaises(ValueError):desktop_window.local_url(url)

    def test_allowed_routes_stay_on_loopback(self):
        for route in ['','/?extensions=1','/?update=1']:
            url='http://127.0.0.1:8771'+route
            self.assertEqual(desktop_window.local_url(url),url)

    def test_frozen_launch_opens_same_executable_in_native_ui_mode(self):
        with patch.object(sys,'frozen',True,create=True),patch('desktop_window.subprocess.Popen') as process:
            desktop_window.launch('http://127.0.0.1:8765',Path('.'))
        args=process.call_args.args[0]
        self.assertEqual(args[0],sys.executable)
        self.assertEqual(args[1:3],['--desktop-url','http://127.0.0.1:8765'])
        self.assertIn('--data',args)

    def test_second_frozen_launch_uses_native_window_not_browser(self):
        import app,tempfile
        base=Path(__file__).resolve().parents[1]/'data/test-runs';base.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as folder:
            root=Path(folder);(root/'bridge-token.txt').write_text('test-token')
            with patch.object(sys,'frozen',True,create=True),patch('app.socket.create_connection'),patch('app.desktop_window.launch') as window,patch('app.webbrowser.open') as browser:
                self.assertTrue(app.open_running_app(root,8772))
                window.assert_called_once_with('http://127.0.0.1:8772',root)
                browser.assert_not_called()
