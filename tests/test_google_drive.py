import io
import unittest
from unittest.mock import MagicMock
import google_drive as drive

IDENT='1ixJtCrMHSY1POtNF2Xhx7bNwq7dyW-xU'
URL='https://drive.google.com/file/d/'+IDENT+'/view'
FORM='<form id="download-form" action="https://drive.usercontent.google.com/download" method="get"><input type="hidden" name="id" value="'+IDENT+'"><input type="hidden" name="export" value="download"><input type="hidden" name="confirm" value="t"><input type="hidden" name="uuid" value="public-confirmation"></form>'
class Response(io.BytesIO):
    status=200
    def __init__(self,body,mime='text/html'):
        super().__init__(body);self.headers={'Content-Type':mime}
    def geturl(self):return 'https://drive.usercontent.google.com/download?id='+IDENT

class GoogleDriveTests(unittest.TestCase):
    def test_view_link_becomes_file_download(self):
        self.assertEqual(drive.file_id(URL),IDENT)
        self.assertIn('export=download',drive.download_url(URL))

    def test_folder_link_is_explicitly_rejected(self):
        with self.assertRaisesRegex(ValueError,'thư mục'):drive.file_id('https://drive.google.com/drive/folders/folder123')

    def test_foreign_hosts_and_embedded_credentials_are_not_drive_links(self):
        for value in ['https://drive.google.com.evil.test/uc?id='+IDENT,'https://u:p@drive.google.com/uc?id='+IDENT]:self.assertIsNone(drive.file_id(value))

    def test_public_confirmation_fields_are_kept_but_browser_signature_is_not(self):
        url=drive.download_url('https://drive.usercontent.google.com/download?id='+IDENT+'&at=private-token&authuser=0&resourcekey=shared-key')
        self.assertNotIn('private-token',url);self.assertIn('resourcekey=shared-key',url)

    def test_matching_confirmation_form_is_followed(self):
        url=drive.confirmation_url(FORM,URL,IDENT)
        self.assertIn('confirm=t',url);self.assertIn('uuid=public-confirmation',url)

    def test_confirmation_never_changes_file_or_leaves_google(self):
        for html in [FORM.replace(IDENT,'other-file-id'),FORM.replace('https://drive.usercontent.google.com/download','https://evil.test/download')]:
            with self.assertRaises(ValueError):drive.confirmation_url(html,URL,IDENT)

    def test_large_file_warning_is_closed_and_range_preserved_for_binary_request(self):
        html=Response(FORM.encode());binary=Response(b'Rar!\x1a\x07\x00','application/octet-stream')
        opener=MagicMock();opener.open.side_effect=[html,binary];cache={}
        result=drive.open_download(opener,URL,{'Range':'bytes=0-31'},cache)
        self.assertTrue(html.closed);self.assertIs(result,binary);self.assertTrue(result.read().startswith(b'Rar!'))
        request=opener.open.call_args.args[0];self.assertEqual(request.get_header('Range'),'bytes=0-31');self.assertIn('confirm=t',request.full_url);self.assertIn(IDENT,cache)

    def test_login_or_quota_page_is_not_saved_as_an_archive(self):
        response=Response(b'<html>Sign in or quota exceeded</html>');opener=MagicMock();opener.open.return_value=response
        with self.assertRaisesRegex(ValueError,'quyền truy cập'):drive.open_download(opener,URL)
        self.assertTrue(response.closed)

    def test_confirmation_loop_is_bounded(self):
        opener=MagicMock();opener.open.side_effect=[Response(FORM.encode()) for _ in range(3)]
        with self.assertRaisesRegex(ValueError,'vẫn trả trang'):drive.open_download(opener,URL)
        self.assertEqual(opener.open.call_count,3)
