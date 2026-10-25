import unittest
import concurrent.futures
import threading
from unittest.mock import patch
import download_window
from download_window import format_download_size

class DownloadSizeDisplayTests(unittest.TestCase):
    def test_repeated_dialogs_share_one_owner_thread(self):
        owners=[]
        def choose(name,*args):
            owners.append(threading.get_ident())
            return name
        with patch('download_window._download_details',side_effect=choose):
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                results=list(pool.map(lambda name:download_window.download_details(name,'.','https://example.com/file'),['one','two','three']))
        self.assertEqual(results,['one','two','three'])
        self.assertEqual(len(set(owners)),1)
        self.assertNotEqual(owners[0],threading.get_ident())

    def test_dialog_failure_does_not_block_the_next_link(self):
        with patch('download_window._download_details',side_effect=[ValueError('dialog error'),'next-file']):
            with self.assertRaisesRegex(ValueError,'dialog error'):
                download_window.download_details('one','.','https://example.com/one')
            self.assertEqual(download_window.download_details('two','.','https://example.com/two'),'next-file')

    def test_exact_size_and_empty_file(self):
        self.assertEqual(format_download_size({'bytes':681868631}), 'Dung lượng tệp: 650,3 MB (681.868.631 byte)')
        self.assertEqual(format_download_size({'bytes':0}), 'Dung lượng tệp: 0 B')

    def test_missing_or_invalid_metadata_is_unknown(self):
        for info in (None,{}, {'bytes':-1},{'bytes':True}):
            self.assertEqual(format_download_size(info),'Dung lượng tệp: Chưa xác định')

    def test_estimate_is_explicit(self):
        self.assertEqual(format_download_size({'bytes':1048576,'estimated':True}),'Dung lượng tệp: Khoảng 1,0 MB (ước tính)')
