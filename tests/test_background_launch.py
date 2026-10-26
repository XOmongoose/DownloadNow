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

    def test_second_launch_checks_local_listener_before_opening_existing_ui(self):
        with patch('app.socket.create_connection') as connection,patch('app.webbrowser.open') as browser:
            self.assertTrue(app.open_running_app(self.root,8765))
            browser.assert_called_once_with('http://127.0.0.1:8765')
            connection.assert_called_once_with(('127.0.0.1',8765),timeout=2)

    def test_profile_without_existing_token_is_not_opened(self):
        (self.root/'bridge-token.txt').unlink()
        with patch('app.socket.create_connection') as connection,patch('app.webbrowser.open') as browser:
            self.assertFalse(app.open_running_app(self.root,8765))
            browser.assert_not_called()
            connection.assert_not_called()

    def test_transient_connection_reset_is_retried(self):
        with patch('app.socket.create_connection',side_effect=[ConnectionResetError('Transient reset'),MagicMock()]) as connection,patch('app.webbrowser.open') as browser,patch('app.time.sleep'):
            self.assertTrue(app.open_running_app(self.root,8765))
            self.assertEqual(connection.call_count,2)
            browser.assert_called_once()

    def test_no_browser_flag_does_not_open_existing_ui(self):
        with patch('app.socket.create_connection'),patch('app.webbrowser.open') as browser:
            self.assertTrue(app.open_running_app(self.root,8765,True))
            browser.assert_not_called()

    def test_setup_flag_opens_setup_on_existing_listener(self):
        with patch('app.socket.create_connection'),patch('app.webbrowser.open') as browser:
            self.assertTrue(app.open_running_app(self.root,8765,False,True))
        browser.assert_called_once_with('http://127.0.0.1:8765/?extensions=1')

    def test_occupied_port_is_skipped_without_closing_its_owner(self):
        import errno
        expected=MagicMock()
        with patch('app.make_server',side_effect=[OSError(errno.EADDRINUSE,'occupied'),expected]) as factory:
            self.assertIs(app.make_available_server(MagicMock(),8765),expected)
        self.assertEqual([call.args[1] for call in factory.call_args_list],[8765,8766])

    def test_other_socket_errors_are_not_hidden(self):
        import errno
        with patch('app.make_server',side_effect=OSError(errno.EMFILE,'too many files')) as factory:
            with self.assertRaises(OSError):app.make_available_server(MagicMock())
        factory.assert_called_once()

    def test_busy_candidate_range_falls_back_to_os_assigned_port(self):
        import errno
        expected=MagicMock()
        with patch('app.make_server',side_effect=[*[OSError(errno.EADDRINUSE,'busy') for _ in range(10)],expected]) as factory:
            self.assertIs(app.make_available_server(MagicMock()),expected)
        self.assertEqual([call.args[1] for call in factory.call_args_list],[*range(8765,8775),0])

    def test_saved_port_is_used_to_reopen_running_app(self):
        (self.root/'bridge-endpoint.json').write_text(json.dumps({'port':8771}))
        with patch('app.socket.create_connection') as connection,patch('app.webbrowser.open') as browser:
            self.assertTrue(app.open_running_app(self.root,8765))
            connection.assert_called_once_with(('127.0.0.1',8771),timeout=2)
            browser.assert_called_once_with('http://127.0.0.1:8771')

    def test_frozen_tls_check_requires_certificate_and_hostname_verification(self):
        context=MagicMock(verify_mode=app.ssl.CERT_REQUIRED,check_hostname=True)
        with patch('app.sys.argv',['app','--self-test-tls']),patch('app.ssl.create_default_context',return_value=context):
            self.assertEqual(app.main(),0)

    def test_frozen_tls_check_fails_for_missing_resource(self):
        with patch('app.sys.argv',['app','--self-test-tls']),patch('app.ssl.create_default_context',side_effect=FileNotFoundError('CA policy missing')):
            self.assertEqual(app.main(),1)

    def test_frozen_tls_check_rejects_disabled_verification(self):
        context=MagicMock(verify_mode=app.ssl.CERT_NONE,check_hostname=False)
        with patch('app.sys.argv',['app','--self-test-tls']),patch('app.ssl.create_default_context',return_value=context):
            self.assertEqual(app.main(),1)
