import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
import zipfile

from engine import Manager
from preferences import Preferences, remembered_directory
from save_dialogs import SavePrompts
from updater import UpdateService, apply_update, https_url, github_repository, github_release_info, update_source


class SettingsUpdateTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]/'data'/'test-runs'
        root.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root)
        self.manager=Manager(self.temp.name)
        self.manager.shutdown.set()
        self.manager.scheduler.join()
        self.preferences=Preferences(self.manager.root)
        self.home=self.manager.root/'application'
        self.home.mkdir()
        self.updates=UpdateService(self.manager,self.preferences,'1.0.0',self.home,Path(__file__).resolve().parents[1])

    def tearDown(self):
        self.manager.close()
        self.temp.cleanup()

    def wait_prompt(self,prompts,ticket):
        end=time.monotonic()+3
        while time.monotonic()<end:
            result=prompts.get(ticket)
            if result['state']!='pending':return result
            time.sleep(.01)
        self.fail('Prompt timed out')

    def package(self,version='2.0.0',tamper=False,extra=None):
        root=f'DownloadNow-{version}-Windows-x64/'
        data={'DownloadNow.exe':b'MZ-new-executable','releases.json':json.dumps({'releases':[{'version':version,'title':'Test update'}]}).encode(),'README.md':b'new readme'}
        sums=''.join(hashlib.sha256(value).hexdigest()+'  '+key+'\n' for key,value in data.items())
        if tamper:data['DownloadNow.exe']=b'MZ-altered-executable'
        archive=self.manager.root/(version+('-bad' if tamper else '')+'.zip')
        with zipfile.ZipFile(archive,'w') as z:
            for key,value in data.items():z.writestr(root+key,value)
            z.writestr(root+'SHA256SUMS.txt',sums)
            if extra:z.writestr(extra,b'unsafe')
        return archive

    def test_remembered_folder_survives_restart(self):
        folder=self.manager.root/'chosen'
        folder.mkdir()
        chooser=lambda *_:{'path':folder/'file.zip','remember':True}
        prompts=SavePrompts(self.manager,chooser,self.preferences)
        result=self.wait_prompt(prompts,prompts.start({'url':'https://example.com/file.zip'}))
        self.assertEqual(result['state'],'accepted')
        reloaded=Preferences(self.manager.root)
        self.assertEqual(remembered_directory(reloaded,self.manager.output),folder)

    def test_unchecking_remember_restores_default_next_time(self):
        folder=self.manager.root/'chosen'
        folder.mkdir()
        self.preferences.set(last_save_dir=str(folder),remember_save_dir=True)
        prompts=SavePrompts(self.manager,lambda *_:{'path':folder/'file.zip','remember':False},self.preferences)
        result=self.wait_prompt(prompts,prompts.start({'url':'https://example.com/file.zip'}))
        self.assertEqual(result['state'],'accepted')
        self.assertFalse(self.preferences.get()['remember_save_dir'])
        self.assertEqual(remembered_directory(self.preferences,self.manager.output),self.manager.output)

    def test_cancel_does_not_change_saved_preference(self):
        before=self.preferences.get()
        prompts=SavePrompts(self.manager,lambda *_:None,self.preferences)
        self.wait_prompt(prompts,prompts.start({'url':'https://example.com/file.zip'}))
        self.assertEqual(self.preferences.get(),before)

    def test_missing_remembered_folder_falls_back(self):
        self.preferences.set(last_save_dir=str(self.manager.root/'missing'))
        self.assertEqual(remembered_directory(self.preferences,self.manager.output),self.manager.output)

    def test_idm_dialog_prefers_original_link_name(self):
        selected={'path':self.manager.output/'original.zip','remember':True}
        with patch('download_window.download_details',return_value=selected) as dialog,patch.object(self.manager,'capture',return_value='download-id'):
            prompts=SavePrompts(self.manager,preferences=self.preferences)
            result=self.wait_prompt(prompts,prompts.start({'url':'https://example.com/original.zip','name':'renamed (1).zip','request_id':'download-001'},automatic=True))
        self.assertEqual(result['state'],'accepted')
        self.assertEqual(dialog.call_args.args[0],'original.zip')

    def test_no_feed_is_unconfigured_not_up_to_date(self):
        self.updates._check()
        self.assertEqual(self.updates.snapshot()['state'],'unconfigured')

    def test_automatic_update_downloads_available_release(self):
        self.preferences.set(update_feed='https://github.com/XOmongoose/DownloadNow',auto_install_updates=True)
        self.updates._set(state='available')
        with patch.object(self.updates,'download') as download:
            self.updates._auto_tick(None)
        download.assert_called_once()

    def test_one_click_update_downloads_without_web_polling(self):
        info={'version':'2.0.0','url':'https://example.com/update.zip','sha256':'a'*64}
        def check():
            self.updates.available=info
            self.updates._set(state='available')
        with patch.object(self.updates,'_start',side_effect=lambda state,operation:operation()),patch.object(self.updates,'_check',side_effect=check),patch.object(self.updates,'_download') as download:
            self.updates.run_update()
        download.assert_called_once_with(info)
        self.assertTrue(self.updates.install_requested)

    def test_one_click_up_to_date_does_not_download(self):
        with patch.object(self.updates,'_start',side_effect=lambda state,operation:operation()),patch.object(self.updates,'_check',side_effect=lambda:self.updates._set(state='up_to_date')),patch.object(self.updates,'_download') as download:
            self.updates.run_update()
        download.assert_not_called()
        self.assertFalse(self.updates.install_requested)

    def test_explicit_update_finishes_even_when_automatic_install_is_disabled(self):
        self.preferences.set(update_feed='https://github.com/XOmongoose/DownloadNow',auto_install_updates=False)
        self.updates.install_requested=True
        self.updates._set(state='ready')
        prompts=SavePrompts(self.manager,lambda *_:None)
        with patch('updater.sys.frozen',True,create=True),patch('updater.sys.platform','win32'),patch.object(self.updates,'install') as install:
            self.updates._auto_tick(prompts)
        install.assert_called_once_with(prompts)

    def test_automatic_update_waits_for_queue_and_pending_dialog(self):
        self.preferences.set(update_feed='https://github.com/XOmongoose/DownloadNow',auto_install_updates=True)
        self.updates._set(state='ready')
        prompts=SavePrompts(self.manager,lambda *_:None)
        with patch('updater.sys.frozen',True,create=True),patch('updater.sys.platform','win32'),patch.object(self.updates,'install') as install:
            self.manager.jobs['queued']={'status':'queued'}
            self.updates._auto_tick(prompts)
            install.assert_not_called()
            self.manager.jobs.clear()
            prompts.items['waiting']={'state':'pending'}
            self.updates._auto_tick(prompts)
            install.assert_not_called()
            prompts.items.clear()
            self.updates._auto_tick(prompts)
            install.assert_called_once_with(prompts)

    def test_automatic_update_can_be_disabled(self):
        self.preferences.set(update_feed='https://github.com/XOmongoose/DownloadNow',auto_install_updates=False)
        self.updates._set(state='available')
        with patch.object(self.updates,'download') as download,patch.object(self.updates,'check') as check:
            self.updates._auto_tick(None)
        download.assert_not_called()
        check.assert_not_called()

    def test_automatic_check_does_not_discard_ready_package(self):
        self.preferences.set(update_feed='https://github.com/XOmongoose/DownloadNow',auto_check_updates=True)
        self.updates._set(state='ready')
        with patch.object(self.updates,'check') as check:
            self.updates._auto_tick(None)
        check.assert_not_called()

    def test_automatic_check_throttles_failed_checks(self):
        self.preferences.set(update_feed='https://github.com/XOmongoose/DownloadNow',auto_check_updates=True)
        with patch.object(self.updates,'check') as check:
            self.updates._auto_tick(None)
            self.updates._auto_tick(None)
        check.assert_called_once()

    def test_drive_name_resolved_before_dialog_and_saved_unchanged(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.headers={'Content-Disposition': "attachment; filename=report.pdf; filename*=UTF-8''B%C3%A1o%20c%C3%A1o.pdf"}
        names=[]
        def chooser(name,directory):
            names.append(name)
            return directory/name
        with patch.object(self.manager,'_request',return_value=response) as request:
            prompts=SavePrompts(self.manager,chooser,self.preferences)
            result=self.wait_prompt(prompts,prompts.start({'url':'https://drive.usercontent.google.com/download?id=123&export=download'}))
        self.assertEqual(result['state'],'accepted')
        self.assertEqual(names,['Báo cáo.pdf'])
        self.assertEqual(self.manager.jobs[result['id']]['name'],'Báo cáo.pdf')
        self.assertEqual(request.call_args.args[1],{'Range':'bytes=0-0'})

    def test_drive_browser_filename_does_not_need_another_request(self):
        with patch.object(self.manager,'_request') as request:
            name=self.manager.resolve_download_name('https://drive.usercontent.google.com/download?id=123','Video gốc.mp4',True)
        self.assertEqual(name,'Video gốc.mp4')
        request.assert_not_called()

    def test_generic_browser_filename_is_replaced_by_server_name(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.headers={'Content-Disposition':'attachment; filename="archive.zip"'}
        with patch.object(self.manager,'_request',return_value=response):
            self.assertEqual(self.manager.resolve_download_name('https://example.com/download','download',True),'archive.zip')

    def test_redirect_filename_is_used_without_disposition(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.headers={}
        response.geturl.return_value='https://cdn.example.com/My%20File.zip?token=secret'
        with patch.object(self.manager,'_request',return_value=response):
            self.assertEqual(self.manager.resolve_download_name('https://example.com/download'),'My File.zip')

    def test_unknown_endpoint_name_is_not_silently_saved_as_download(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.headers={}
        response.geturl.return_value='https://example.com/download'
        with patch.object(self.manager,'_request',return_value=response),self.assertRaises(ValueError):
            self.manager.resolve_download_name('https://example.com/download')

    def test_explicit_user_filename_is_kept(self):
        with patch.object(self.manager,'_request') as request:
            self.assertEqual(self.manager.resolve_download_name('https://example.com/download','Tên riêng.zip'),'Tên riêng.zip')
        request.assert_not_called()

    def test_update_feed_requires_https_and_checksum(self):
        with self.assertRaises(ValueError):https_url('http://example.com/updates.json')
        self.preferences.set(update_feed='https://example.com/updates.json')
        response=MagicMock()
        response.__enter__.return_value=response
        response.geturl.return_value='https://example.com/updates.json'
        response.read.return_value=json.dumps({'version':'2.0.0','url':'https://example.com/update.zip','sha256':'bad'}).encode()
        with patch('updater.urllib.request.urlopen',return_value=response),self.assertRaises(ValueError):self.updates._check()

    def test_valid_feed_reports_new_version(self):
        self.preferences.set(update_feed='https://example.com/updates.json')
        response=MagicMock()
        response.__enter__.return_value=response
        response.geturl.return_value='https://example.com/updates.json'
        response.read.return_value=json.dumps({'version':'2.0.0','url':'https://example.com/update.zip','sha256':'a'*64}).encode()
        with patch('updater.urllib.request.urlopen',return_value=response):self.updates._check()
        self.assertEqual(self.updates.snapshot()['state'],'available')

    def test_valid_local_package_is_staged_without_user_data(self):
        self.updates._prepare(self.package())
        self.assertEqual(self.updates.snapshot()['state'],'ready')
        self.assertEqual((self.updates.staged/'DownloadNow.exe').read_bytes(),b'MZ-new-executable')
        self.assertFalse((self.updates.staged/'data').exists())

    def test_tampered_package_is_rejected(self):
        with self.assertRaises(ValueError):self.updates._prepare(self.package(tamper=True))
        self.assertIsNone(self.updates.staged)

    def test_unsafe_zip_paths_are_rejected(self):
        with self.assertRaises(ValueError):self.updates._prepare(self.package(extra='../../outside.exe'))
        self.assertIsNone(self.updates.staged)

    def test_older_or_wrong_version_is_rejected(self):
        with self.assertRaises(ValueError):self.updates._prepare(self.package('1.0.0'))
        with self.assertRaises(ValueError):self.updates._prepare(self.package(),expected='3.0.0')

    def test_update_install_refuses_active_downloads(self):
        self.updates._prepare(self.package())
        prompts=SavePrompts(self.manager,chooser=lambda *_:None)
        with patch('updater.sys.frozen',True,create=True),patch('updater.sys.platform','win32'),patch.object(self.manager,'running',{'active':None}),patch('updater.subprocess.Popen') as launch:
            with self.assertRaises(ValueError):self.updates.install(prompts)
            launch.assert_not_called()

    def test_install_notifies_server_to_exit_for_automatic_updates(self):
        self.updates._prepare(self.package())
        self.updates.on_install=MagicMock()
        prompts=SavePrompts(self.manager,chooser=lambda *_:None)
        with patch('updater.sys.frozen',True,create=True),patch('updater.sys.platform','win32'),patch('updater.shutil.copy2'),patch('updater.subprocess.Popen') as launch:
            self.updates.install(prompts)
        self.assertEqual(launch.call_args.kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'],'1')
        self.assertIn('--update-data',launch.call_args.args[0])
        self.updates.on_install.assert_called_once()
        self.assertEqual(self.updates.snapshot()['state'],'installing')

    def test_helper_backs_up_and_keeps_data(self):
        self.updates._prepare(self.package())
        (self.home/'DownloadNow.exe').write_bytes(b'old-executable')
        (self.home/'data').mkdir()
        (self.home/'data'/'preferences.json').write_text('keep')
        kernel=MagicMock()
        kernel.OpenProcess.return_value=0
        backup=self.manager.root/'backup'
        with patch('updater.ctypes.WinDLL',return_value=kernel),patch('updater.sys.platform','win32'),patch('updater.subprocess.Popen') as launch:
            result=apply_update(self.updates.staged,self.home,backup,123456,port=8876,data=self.manager.root)
        self.assertEqual(result,0)
        self.assertEqual((backup/'DownloadNow.exe').read_bytes(),b'old-executable')
        self.assertEqual((self.home/'data'/'preferences.json').read_text(),'keep')
        launch.assert_called_once()
        self.assertEqual(launch.call_args.kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'],'1')
        self.assertEqual(launch.call_args.args[0][1:],['--port','8876','--data',str(self.manager.root)])

    def test_helper_rolls_back_if_copy_fails(self):
        self.updates._prepare(self.package())
        (self.home/'DownloadNow.exe').write_bytes(b'old-executable')
        kernel=MagicMock()
        kernel.OpenProcess.return_value=0
        import os
        original_replace=os.replace
        def replace(source,target):
            if Path(target).name=='README.md':raise OSError('simulated copy error')
            return original_replace(source,target)
        with patch('updater.ctypes.WinDLL',return_value=kernel),patch('updater.sys.platform','win32'),patch('updater.os.replace',side_effect=replace),patch('updater.subprocess.Popen') as launch:
            result=apply_update(self.updates.staged,self.home,self.manager.root/'backup',123456)
        self.assertEqual(result,1)
        self.assertEqual((self.home/'DownloadNow.exe').read_bytes(),b'old-executable')
        self.assertFalse((self.home/'releases.json').exists())
        launch.assert_not_called()

    def github_release(self,digest=True):
        name='DownloadNow-2.0.0-Windows-x64.zip'
        asset={'name':name,'browser_download_url':'https://github.com/example/DownloadNow/releases/download/v2.0.0/'+name}
        if digest:asset['digest']='sha256:'+'a'*64
        return {'tag_name':'v2.0.0','draft':False,'prerelease':False,'body':'New release','assets':[asset]}

    def github_response(self,body,url='https://api.github.com/repos/example/DownloadNow/releases/latest'):
        response=MagicMock()
        response.__enter__.return_value=response
        response.geturl.return_value=url
        response.read.return_value=json.dumps(body).encode() if isinstance(body,dict) else body
        return response

    def test_github_repository_formats(self):
        for source in ('example/DownloadNow','https://github.com/example/DownloadNow','https://github.com/example/DownloadNow.git','https://github.com/example/DownloadNow/releases/latest','https://api.github.com/repos/example/DownloadNow/releases/latest'):
            self.assertEqual(github_repository(source),'example/DownloadNow')
            self.assertEqual(update_source(source),'https://github.com/example/DownloadNow')
        self.assertIsNone(github_repository('https://example.com/feed.json'))

    def test_github_release_uses_asset_digest(self):
        with patch('updater.urllib.request.urlopen',return_value=self.github_response(self.github_release())) as network:
            info=github_release_info('example/DownloadNow')
        self.assertEqual(info['version'],'2.0.0')
        self.assertEqual(info['sha256'],'a'*64)
        self.assertEqual(network.call_args.args[0].full_url,'https://api.github.com/repos/example/DownloadNow/releases/latest')

    def test_github_release_checksum_sidecar(self):
        release=self.github_release(digest=False)
        checksum={'name':release['assets'][0]['name']+'.sha256','browser_download_url':release['assets'][0]['browser_download_url']+'.sha256'}
        release['assets'].append(checksum)
        sidecar=('b'*64+'  '+release['assets'][0]['name']+'\n').encode()
        with patch('updater.urllib.request.urlopen',side_effect=[self.github_response(release),self.github_response(sidecar,checksum['browser_download_url'])]):
            info=github_release_info('example/DownloadNow')
        self.assertEqual(info['sha256'],'b'*64)

    def test_github_release_requires_windows_asset(self):
        release=self.github_release()
        release['assets'][0]['name']='source-code.zip'
        with patch('updater.urllib.request.urlopen',return_value=self.github_response(release)),self.assertRaises(ValueError):
            github_release_info('example/DownloadNow')

    def test_github_release_rejects_prerelease(self):
        release=self.github_release()
        release['prerelease']=True
        with patch('updater.urllib.request.urlopen',return_value=self.github_response(release)),self.assertRaises(ValueError):
            github_release_info('example/DownloadNow')

    def test_github_release_rejects_foreign_asset(self):
        release=self.github_release()
        release['assets'][0]['browser_download_url']=release['assets'][0]['browser_download_url'].replace('/example/','/another-owner/')
        with patch('updater.urllib.request.urlopen',return_value=self.github_response(release)),self.assertRaises(ValueError):
            github_release_info('example/DownloadNow')

    def test_github_release_missing_checksum_is_not_accepted(self):
        with patch('updater.urllib.request.urlopen',return_value=self.github_response(self.github_release(digest=False))),self.assertRaises(ValueError):
            github_release_info('example/DownloadNow')

    def test_default_repository_does_not_overwrite_saved_source(self):
        first=Preferences(self.manager.root,default_feed='https://github.com/example/DownloadNow')
        self.assertEqual(first.get()['update_feed'],'https://github.com/example/DownloadNow')
        self.assertTrue(first.get()['auto_check_updates'])
        first.set(update_feed='https://github.com/other/DownloadNow',auto_check_updates=False)
        restored=Preferences(self.manager.root,default_feed='https://github.com/example/DownloadNow')
        self.assertEqual(restored.get()['update_feed'],'https://github.com/other/DownloadNow')
        self.assertFalse(restored.get()['auto_check_updates'])

    def test_github_404_explains_public_release_requirement(self):
        error=urllib.error.HTTPError('https://api.github.com/example',404,'Not Found',{},None)
        with patch('updater.urllib.request.urlopen',side_effect=error),self.assertRaisesRegex(ValueError,'công khai'):
            github_release_info('example/DownloadNow')


if __name__=='__main__':unittest.main()
