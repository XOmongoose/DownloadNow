from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import install_shutdown

class InstallShutdownTests(unittest.TestCase):
    def setUp(self):
        base=Path(__file__).resolve().parents[1]/'data/test-runs';base.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=base);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'DownloadNow.exe').write_bytes(b'fixture')

    def test_not_running_does_not_send_shutdown(self):
        with patch('install_shutdown.process_ids',return_value=[]),patch('install_shutdown.request_shutdown') as request:
            self.assertEqual(install_shutdown.prepare(self.root),0);request.assert_not_called()

    def test_graceful_exit_waits_for_installed_processes(self):
        with patch('install_shutdown.process_ids',side_effect=[[1],[]]),patch('install_shutdown.request_shutdown') as request:
            self.assertEqual(install_shutdown.prepare(self.root),0);request.assert_called_once_with(self.root)

    def test_old_version_requires_separate_force_confirmation(self):
        with patch('install_shutdown.process_ids',return_value=[1]),patch('install_shutdown.request_shutdown',side_effect=OSError('404')),patch('install_shutdown.ctypes.WinDLL') as native:
            self.assertEqual(install_shutdown.prepare(self.root),2);native.assert_not_called()

    def test_real_process_filter_excludes_current_test_interpreter(self):
        self.assertEqual(install_shutdown.process_ids(self.root),[])
