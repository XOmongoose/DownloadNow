import unittest
from download_window import format_download_size

class DownloadSizeDisplayTests(unittest.TestCase):
    def test_exact_size_and_empty_file(self):
        self.assertEqual(format_download_size({'bytes':681868631}), 'Dung lượng tệp: 650,3 MB (681.868.631 byte)')
        self.assertEqual(format_download_size({'bytes':0}), 'Dung lượng tệp: 0 B')

    def test_missing_or_invalid_metadata_is_unknown(self):
        for info in (None,{}, {'bytes':-1},{'bytes':True}):
            self.assertEqual(format_download_size(info),'Dung lượng tệp: Chưa xác định')

    def test_estimate_is_explicit(self):
        self.assertEqual(format_download_size({'bytes':1048576,'estimated':True}),'Dung lượng tệp: Khoảng 1,0 MB (ước tính)')
