import json
from pathlib import Path
import tempfile
import threading
import sys
import unittest
from unittest.mock import patch

from engine import Manager
from media import is_video_page, VideoStopped, download_video


class MediaTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'data/test-runs';root.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root)
        self.manager=Manager(self.temp.name);self.manager.shutdown.set();self.manager.scheduler.join()
        self.url='https://www.facebook.com/reel/2193421561521675'

    def tearDown(self):self.manager.close();self.temp.cleanup()

    def job(self):
        ident=self.manager.add(self.url,name='Video thử.mp4')
        return self.manager.jobs[ident]

    def fake_download(self,url,folder,stop,progress):
        progress({'filename':'video','downloaded_bytes':8,'total_bytes':8,'speed':4})
        target=folder/'video.mp4';target.write_bytes(b'test-mp4');return target

    def test_only_supported_video_hosts_and_paths(self):
        for url in [self.url,'https://www.youtube.com/shorts/abc','https://youtu.be/abc','https://www.instagram.com/reel/abc/']:
            self.assertTrue(is_video_page(url))
        for url in ['https://youtube.com.evil.example/shorts/abc','https://www.youtube.com/','https://user:pass@youtube.com/shorts/x','file:///reel/x','https://example.com/video.mp4']:
            self.assertFalse(is_video_page(url))

    def test_page_name_is_resolved_before_save_dialog(self):
        with patch('engine.video_name',return_value='Video gốc.mp4'):
            self.assertEqual(self.manager.resolve_download_name(self.url,automatic=True),'Video gốc.mp4')

    def test_video_publishes_only_finished_output(self):
        job=self.job()
        with patch('engine.download_video',side_effect=self.fake_download):self.manager._run(job,threading.Event())
        self.assertEqual(job['status'],'completed')
        self.assertEqual((self.manager.output/job['name']).read_bytes(),b'test-mp4')
        self.assertFalse((self.manager.parts/job['id']).exists())

    def test_pause_preserves_partial_media_for_resume(self):
        job=self.job()
        def pause(url,folder,stop,progress):
            (folder/'video.f137.mp4.part').write_bytes(b'partial');raise VideoStopped()
        with patch('engine.download_video',side_effect=pause):self.manager._run(job,threading.Event())
        self.assertEqual(job['status'],'paused')
        self.assertTrue((self.manager.parts/job['id']/'video.f137.mp4.part').exists())
        self.manager.action(job['id'],'resume');self.assertEqual(job['status'],'queued')

    def test_cancel_cleans_all_stream_fragments_but_keeps_other_files(self):
        job=self.job();folder=self.manager.parts/job['id'];folder.mkdir()
        for name in ['video.f137.mp4.part','video.f140.m4a','video.mp4.ytdl']:(folder/name).write_bytes(b'partial')
        other=self.manager.output/'keep.txt';other.write_text('keep')
        self.manager.action(job['id'],'cancel')
        self.assertEqual(job['status'],'cancelled');self.assertFalse(folder.exists());self.assertTrue(other.exists())

    def test_does_not_overwrite_existing_destination(self):
        job=self.job();target=self.manager.output/job['name'];target.write_bytes(b'original')
        with patch('engine.download_video',side_effect=self.fake_download):self.manager._run(job,threading.Event())
        self.assertEqual(job['status'],'error');self.assertEqual(target.read_bytes(),b'original')

    def test_video_errors_are_not_marked_complete(self):
        job=self.job()
        with patch('engine.download_video',side_effect=ValueError('Video unavailable')):self.manager._run(job,threading.Event())
        self.assertEqual(job['status'],'error');self.assertFalse((self.manager.output/job['name']).exists())

    def test_missing_progress_fields_do_not_break_video_download(self):
        job=self.job()
        def download(url,folder,stop,progress):
            progress({'downloaded_bytes':5,'total_bytes':'NA','speed':'NA'})
            target=folder/'video.mp4';target.write_bytes(b'video');return target
        with patch('engine.download_video',side_effect=download):self.manager._run(job,threading.Event())
        self.assertEqual(job['status'],'completed')

    def test_redownload_keeps_original_page_for_fresh_stream_resolution(self):
        job=self.job()
        with patch('engine.download_video',side_effect=self.fake_download):self.manager._run(job,threading.Event())
        fresh=self.manager.jobs[self.manager.redownload(job['id'])]
        self.assertEqual(fresh['url'],self.url);self.assertNotEqual(fresh['name'],job['name'])

    def test_subprocess_progress_and_final_output_are_received(self):
        folder=self.manager.parts/'pipeline';folder.mkdir()
        script="import json;from pathlib import Path;print('DN_PROGRESS '+json.dumps({'downloaded_bytes':8,'total_bytes':None,'speed':4}),flush=True);Path("+repr(str(folder/'video.mp4'))+").write_bytes(b'test-mp4')"
        updates=[]
        with patch('media.command',return_value=[sys.executable,'-u','-c',script]):
            result=download_video(self.url,folder,threading.Event(),updates.append)
        self.assertEqual(result.read_bytes(),b'test-mp4');self.assertEqual(updates[0]['downloaded_bytes'],8)


if __name__=='__main__':unittest.main()
