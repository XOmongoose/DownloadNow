"""Public Google Drive files and bounded large-file confirmation handling."""
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit,parse_qs,urlencode,urljoin
from urllib.request import Request

HOSTS={'drive.google.com','drive.usercontent.google.com','docs.google.com'}
def file_id(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password:return None
    if '/folders/' in p.path:raise ValueError('Đây là thư mục Google Drive. Hãy mở tệp bên trong và dùng liên kết của tệp cần tải.')
    match=re.fullmatch(r'/file/d/([A-Za-z0-9_-]+)(?:/.*)?',p.path)
    ident=match[1] if match else parse_qs(p.query).get('id',[''])[0] if p.path in ('/uc','/download','/open') else ''
    return ident if re.fullmatch(r'[A-Za-z0-9_-]{8,200}',ident) else None

def download_url(url):
    ident=file_id(url)
    if not ident:return None
    query=parse_qs(urlsplit(url).query)
    fields={'id':ident,'export':'download'}
    for key in ('confirm','uuid','resourcekey'):
        if key in query and len(query[key][0])<=500:fields[key]=query[key][0]
    return 'https://drive.usercontent.google.com/download?'+urlencode(fields)

class DownloadForm(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.forms=[];self.current=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='form':
            self.current={'action':attrs.get('action',''),'method':attrs.get('method','get').lower(),'fields':{}}
            self.forms.append(self.current)
        elif tag=='input' and self.current is not None and attrs.get('type','').lower()=='hidden':
            key,value=attrs.get('name',''),attrs.get('value','')
            if key in ('id','export','confirm','uuid','resourcekey') and len(value)<=500:self.current['fields'][key]=value
    def handle_endtag(self,tag):
        if tag=='form':self.current=None

def confirmation_url(html,page,ident):
    parser=DownloadForm();parser.feed(html)
    for form in parser.forms:
        action=urljoin(page,form['action']);p=urlsplit(action)
        if form['method']!='get' or p.scheme!='https' or p.hostname not in ('drive.google.com','drive.usercontent.google.com') or p.username or p.password or p.path not in ('/download','/uc'):continue
        fields=form['fields']
        if fields.get('id')!=ident or not fields.get('confirm'):continue
        fields={**fields,'id':ident,'export':'download'}
        return 'https://'+p.hostname+p.path+'?'+urlencode(fields)
    raise ValueError('Google Drive chưa cung cấp tệp tải công khai. Link có thể cần quyền truy cập, đăng nhập hoặc đã vượt hạn mức tải.')

def open_download(opener,url,headers=None,cache=None,timeout=15):
    ident=file_id(url)
    if not ident:raise ValueError('Liên kết tệp Google Drive không hợp lệ.')
    current=(cache or {}).get(ident) or download_url(url)
    for attempt in range(3):
        response=opener.open(Request(current,headers={'User-Agent':'DownloadNow/1.0','Accept-Encoding':'identity',**(headers or {})}),timeout=timeout)
        mime=response.headers.get('Content-Type','').split(';',1)[0].lower()
        if mime not in ('text/html','application/xhtml+xml') or 'attachment' in response.headers.get('Content-Disposition','').lower():
            if cache is not None:cache[ident]=current
            return response
        try:
            body=response.read(1048577)
            if len(body)>1048576:raise ValueError('Trang xác nhận Google Drive quá lớn; chưa nhận được dữ liệu tệp.')
            current=confirmation_url(body.decode('utf-8','replace'),response.geturl(),ident)
        finally:response.close()
    raise ValueError('Google Drive vẫn trả trang xác nhận thay vì tệp. Hãy mở lại tệp và thử lại.')
