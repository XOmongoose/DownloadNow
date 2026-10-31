import sys
import unittest
from unittest.mock import MagicMock,patch
from pathlib import Path
import desktop_settings

class DesktopSettingsTests(unittest.TestCase):
    def test_background_waits_for_last_tab_and_never_stops_before_first_ui(self):
        check=desktop_settings.should_stop_background
        self.assertFalse(check(False,None,999))
        self.assertFalse(check(False,100,220))
        self.assertTrue(check(False,100,221))
        self.assertFalse(check(True,100,999))

    def test_startup_command_is_quoted_and_per_user(self):
        reg=MagicMock();key=reg.CreateKey.return_value.__enter__.return_value
        with patch.dict(sys.modules,{'winreg':reg}),patch.object(desktop_settings.sys,'frozen',True,create=True),patch.object(desktop_settings.os,'name','nt'):
            desktop_settings.set_startup(True,Path('C:/Download Now/data'))
        args=reg.SetValueEx.call_args.args
        self.assertIs(args[0],key)
        self.assertEqual(args[1],'DownloadNow')
        self.assertIn('--startup',args[4]);self.assertIn('--data',args[4])
        reg.CreateKey.assert_called_once_with(reg.HKEY_CURRENT_USER,desktop_settings.RUN_KEY)

    def test_disable_removes_only_named_value(self):
        reg=MagicMock();key=reg.CreateKey.return_value.__enter__.return_value
        with patch.dict(sys.modules,{'winreg':reg}),patch.object(desktop_settings.os,'name','nt'):
            desktop_settings.set_startup(False,'.')
        reg.DeleteValue.assert_called_once_with(key,'DownloadNow');reg.SetValueEx.assert_not_called()

    def test_source_mode_does_not_register_python_as_startup(self):
        reg=MagicMock()
        with patch.dict(sys.modules,{'winreg':reg}),patch.object(desktop_settings.sys,'frozen',False,create=True),patch.object(desktop_settings.os,'name','nt'):
            with self.assertRaises(ValueError):desktop_settings.set_startup(True,'.')
        reg.CreateKey.assert_not_called()
