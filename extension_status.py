"""Short-lived local acknowledgements from connected browser extensions."""
import re
import threading
import time


class ExtensionStatus:
    def __init__(self,version):
        self.version=version
        self.clients={}
        self.lock=threading.RLock()

    def report(self,data):
        if set(data)!={'id','version','managed','browser'}:raise ValueError('Thông tin tiện ích không hợp lệ.')
        if not isinstance(data['id'],str) or not re.fullmatch(r'[A-Za-z0-9_@.{}-]{1,160}',data['id']):raise ValueError('ID tiện ích không hợp lệ.')
        if not isinstance(data['version'],str) or not re.fullmatch(r'\d+\.\d+\.\d+',data['version']):raise ValueError('Phiên bản tiện ích không hợp lệ.')
        if not isinstance(data['managed'],bool) or data['browser'] not in ('Chrome','Edge','Opera','Firefox'):raise ValueError('Trình duyệt không hợp lệ.')
        with self.lock:
            self.clients[data['browser']+':'+data['id']]={**data,'seen':time.monotonic()}
        return self.snapshot()

    def snapshot(self):
        with self.lock:
            now=time.monotonic()
            self.clients={k:v for k,v in self.clients.items() if now-v['seen']<120}
            clients=[{k:v for k,v in client.items() if k not in ('id','seen')} for client in self.clients.values()]
            synced=bool(clients) and all(c['version']==self.version and c['managed'] for c in clients)
            return {'version':self.version,'clients':clients,'state':'synced' if synced else 'waiting' if clients else 'unconfirmed'}
