"""Small atomic settings store shared by dialogs and the updater."""
import json
import os
from pathlib import Path
import threading


class Preferences:
    def __init__(self, root, default_feed=''):
        self.path = Path(root)/'preferences.json'
        self.lock = threading.RLock()
        self.values = {'remember_save_dir':True, 'last_save_dir':'',
                       'update_feed':default_feed, 'auto_check_updates':bool(default_feed),
                       'auto_install_updates':False, 'last_update_check':0}
        if self.path.exists():
            self.values.update(json.loads(self.path.read_text('utf-8')))
        # New update flow always asks before downloading, including old installs.
        if self.values.get('update_confirmation_version')!=1:
            if self.path.exists():self.set(auto_install_updates=False,update_confirmation_version=1)
            else:self.values.update(auto_install_updates=False,update_confirmation_version=1)

    def get(self):
        with self.lock:
            return dict(self.values)

    def set(self, **values):
        with self.lock:
            self.values.update(values)
            temp = self.path.with_suffix('.tmp')
            with temp.open('w',encoding='utf-8') as file:
                json.dump(self.values,file,ensure_ascii=False,indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temp,self.path)


def remembered_directory(preferences, fallback):
    values = preferences.get()
    path = Path(values.get('last_save_dir') or fallback)
    if values['remember_save_dir'] and path.is_absolute() and path.is_dir():
        return path
    return Path(fallback)
