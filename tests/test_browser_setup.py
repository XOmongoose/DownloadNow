import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import browser_setup

class BrowserSetupTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'data/test-runs';root.mkdir(exist_ok=True,parents=True)
        self.temp=tempfile.TemporaryDirectory(dir=root);self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name);self.folder=self.home/'extension/chromium';self.folder.mkdir(parents=True)
        (self.folder/'manifest.json').write_text('{}')

    def test_only_supported_browser_names_are_accepted(self):
        with self.assertRaises(ValueError):browser_setup.browser_path('arbitrary-program.exe')

    def test_missing_browser_does_not_launch_anything(self):
        with patch('browser_setup.browser_path',return_value=None),patch('browser_setup.subprocess.Popen') as launch:
            with self.assertRaises(ValueError):browser_setup.open_setup('chrome',self.home,'http://127.0.0.1:8771')
        launch.assert_not_called()

    def test_missing_extension_package_does_not_launch_browser(self):
        (self.folder/'manifest.json').unlink()
        with patch('browser_setup.browser_path',return_value=Path('C:/Chrome/chrome.exe')),patch('browser_setup.subprocess.Popen') as launch:
            with self.assertRaises(ValueError):browser_setup.open_setup('chrome',self.home,'http://127.0.0.1:8771')
        launch.assert_not_called()

    def test_browser_launch_opens_setup_and_manager_without_shell_or_force_flags(self):
        with patch('browser_setup.browser_path',return_value=Path('C:/Chrome/chrome.exe')),patch('browser_setup.subprocess.Popen') as launch:
            result=browser_setup.open_setup('chrome',self.home,'http://127.0.0.1:8771')
        arguments=launch.call_args.args[0]
        self.assertEqual(arguments[1:],['http://127.0.0.1:8771/?extensions=1','chrome://extensions/'])
        self.assertFalse(launch.call_args.kwargs.get('shell',False))
        self.assertTrue(result['requires_confirmation'])

    def test_setup_reports_prepared_folder_and_installed_browsers_honestly(self):
        with patch('browser_setup.browser_path',side_effect=lambda browser:Path('chrome.exe') if browser=='chrome' else None):
            result=browser_setup.setup_info(self.home)
        self.assertEqual(result['folder'],str(self.folder.resolve()))
        self.assertTrue(result['requires_confirmation'])
        self.assertEqual([b['id'] for b in result['browsers'] if b['installed']],['chrome'])
