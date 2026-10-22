import unittest
from unittest.mock import patch
from extension_status import ExtensionStatus


class ExtensionStatusTests(unittest.TestCase):
    def setUp(self):
        self.status=ExtensionStatus('1.10.2')
        self.report={'id':'test-extension','version':'1.10.2','managed':True,'browser':'Chrome'}

    def test_no_reply_is_not_claimed_synced(self):
        self.assertEqual(self.status.snapshot()['state'],'unconfirmed')

    def test_running_version_must_match_not_only_files(self):
        self.status.report({**self.report,'version':'1.10.1'})
        self.assertEqual(self.status.snapshot()['state'],'waiting')
        self.status.report(self.report)
        self.assertEqual(self.status.snapshot()['state'],'synced')

    def test_unmanaged_copy_is_not_claimed_automatic(self):
        self.assertEqual(self.status.report({**self.report,'managed':False})['state'],'waiting')

    def test_all_connected_browsers_must_acknowledge(self):
        self.status.report(self.report)
        self.status.report({**self.report,'browser':'Edge','version':'1.10.1'})
        self.assertEqual(self.status.snapshot()['state'],'waiting')
        self.status.report({**self.report,'browser':'Edge'})
        self.assertEqual(self.status.snapshot()['state'],'synced')

    def test_stale_replies_expire(self):
        with patch('extension_status.time.monotonic',return_value=10):self.status.report(self.report)
        with patch('extension_status.time.monotonic',return_value=131):self.assertEqual(self.status.snapshot()['state'],'unconfirmed')

    def test_status_does_not_expose_identifiers(self):
        self.status.report(self.report)
        self.assertNotIn('id',self.status.snapshot()['clients'][0])

    def test_invalid_reports_are_rejected(self):
        for report in [{**self.report,'managed':'true'},{**self.report,'version':'arbitrary'},{**self.report,'browser':'unknown'}]:
            with self.assertRaises(ValueError):self.status.report(report)


if __name__=='__main__':unittest.main()
