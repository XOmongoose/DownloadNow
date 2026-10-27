"""Build a versioned Windows portable EXE and ZIP, excluding all user data.

Run using the build venv: .venv-build/Scripts/python.exe tools/build_windows.py
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import ssl
import struct
import subprocess
import sys
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]


def make_icon(path):
    """Render our code-native download mark into a PNG-backed Windows icon."""
    size = 256
    segments = [(128, 62, 128, 156), (92, 124, 128, 160), (128, 160, 164, 124),
                (70, 170, 70, 195), (70, 195, 186, 195), (186, 170, 186, 195)]
    def distance(x, y, line):
        ax, ay, bx, by = line
        t = max(0, min(1, ((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2)))
        return math.hypot(x-ax-t*(bx-ax), y-ay-t*(by-ay))
    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            edge = math.hypot(max(24-x, 0, x-231), max(24-y, 0, y-231))
            alpha = round(255 * min(1, max(0, 24.5-edge)))
            d = min(distance(x, y, line) for line in segments)
            blend = min(1, max(0, 9.5-d))
            rgb = [round(a*(1-blend)+b*blend) for a, b in zip((241,175,0),(48,38,0))]
            rows.extend((*rgb, alpha))
    def chunk(kind, body):
        return struct.pack('!I',len(body))+kind+body+struct.pack('!I',zlib.crc32(kind+body)&0xffffffff)
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b'')
    path.write_bytes(struct.pack('<3H',0,1,1)+struct.pack('<4B2H2I',0,0,0,0,1,32,len(png),22)+png)


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build this package on Windows.')
    from build_media_runtime import build
    media_runtime=build()
    subprocess.run([sys.executable, str(ROOT/'tools/sync_release.py')], check=True, cwd=ROOT)
    release = json.loads((ROOT/'releases.json').read_text('utf-8'))['releases'][0]
    version = release['version']
    name = f'DownloadNow-{version}-Windows-x64'
    dist = ROOT/'dist'
    work = ROOT/'build'
    dist.mkdir(exist_ok=True)
    work.mkdir(exist_ok=True)
    package = dist/name
    # Refuse to mix artifacts with an existing release or silently overwrite it.
    if package.exists() or (dist/(name+'.zip')).exists():
        raise SystemExit('Release already exists. Increment releases.json before building again.')
    icon = work/'DownloadNow.ico'
    make_icon(icon)
    version_tuple = tuple(map(int,version.split('.'))) + (0,)
    info = work/'version-info.txt'
    info.write_text(f'''VSVersionInfo(ffi=FixedFileInfo(filevers={version_tuple!r}, prodvers={version_tuple!r}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('CompanyName', 'XOmongoose'), StringStruct('FileDescription', 'Download Now Download Manager'), StringStruct('FileVersion', '{version}'), StringStruct('InternalName', 'DownloadNow'), StringStruct('OriginalFilename', 'DownloadNow.exe'), StringStruct('ProductName', 'Download Now'), StringStruct('ProductVersion', '{version}')])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])''', encoding='utf-8')
    ssl_data=[]
    # Keep optional CA policy resources beside the frozen ssl module.
    ssl_policy=Path(ssl.__file__).with_name('codex-rejected-cas.pem')
    if ssl_policy.is_file():ssl_data=['--add-data',f'{ssl_policy}:.']
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed', '--noupx',
                    '--name', 'DownloadNow', '--icon', str(icon), '--version-file', str(info),
                    '--add-data', f'{ROOT / "web"}:web', '--add-data', f'{ROOT / "releases.json"}:.',
                    '--add-data', f'{icon}:.',
                    '--add-data', f'{media_runtime}:media-runtime',
                    '--distpath', str(work/'exe'), '--workpath', str(work/'pyinstaller'),
                    '--specpath', str(work), *ssl_data, str(ROOT/'app.py')], check=True, cwd=ROOT)
    package.mkdir()
    shutil.copy2(work/'exe/DownloadNow.exe',package/'DownloadNow.exe')
    shutil.copytree(ROOT/'extension',package/'extension', ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    # Only this stable folder is replaced by the application updater.
    (package/'extension/chromium/managed.json').write_text(json.dumps({'managed':True,'version':version}),encoding='utf-8')
    shutil.copy2(ROOT/'releases.json',package/'releases.json')
    shutil.copy2(ROOT/'README.md',package/'README.md')
    with (package/'README.md').open('a',encoding='utf-8') as notices:
        notices.write('\n\n## Bundled media tool notices and licenses\n')
        for license_file in sorted(media_runtime.glob('*.txt')):
            notices.write('\n### '+license_file.name+'\n\n'+license_file.read_text('utf-8')+'\n')
    (package/'HUONG-DAN.txt').write_text(f'''DOWNLOAD NOW v{version} — WINDOWS x64 PORTABLE

1. Giai nen toan bo ZIP vao thu muc co quyen ghi (vi du Documents).
2. Chay DownloadNow.exe. Khong can cai Python.
3. Giao dien tu mo tai http://127.0.0.1:8765.
4. Ung dung chay nen, khong hien CMD. Dong tab trinh duyet khong dung tai.
5. Mo lai DownloadNow.exe de quay lai giao dien dang chay.

Du lieu va hang doi: thu muc data canh DownloadNow.exe.
Tep hoan tat: data/files. Khong xoa data neu muon tiep tuc tai.
Nang cap: bam Cap nhat trong ung dung, dong y de tai/kiem tra/cai ban moi.
Co the sao chep data tu ban chay ma nguon sau khi da tat ca hai ban.

Ung dung tu chon cong trong neu cong uu tien dang duoc su dung.
Cong uu tien: DownloadNow.exe --port 8766. Tien ich tu tim hoac ghep noi qua trang ung dung.
Khong tu mo trinh duyet: DownloadNow.exe --no-browser.
Xem phien ban: DownloadNow.exe --version.

Tien ich: nap extension/chromium tren Chrome/Edge/Opera, hoac
extension/firefox/manifest.json de thu tren Firefox. Xem README.md.
Safari can dong goi rieng tren macOS.

Ban EXE chua ky so. Day la ban portable thu nghiem, khong phai bo cai MSI.
163 kiem thu loi/cap nhat va 104 kiem thu mo phong tien ich/giao dien da qua; kiem thu HTTP socket va giao dien native chua qua day du.
Khong bao dam tang toc 8 lan. Xem README.md ve gioi han chuc nang.
''', encoding='utf-8-sig')
    (package/'HUONG-DAN.txt').write_text((package/'HUONG-DAN.txt').read_text('utf-8-sig')+'\n\n'+'''DOWNLOAD NOW - TAC GIA: XOmongoose

CAI TREN MAY KHAC (Windows 10/11 x64)
1. Chep DownloadNow-Setup-VERSION-Windows-x64.exe sang may can cai.
2. Mo bo cai, chon thu muc va bam Install. Khong can Python hay Node.js.
3. Mo Download Now tu Desktop hoac Start menu.
4. Giu lua chon Set up browser extensions after installation trong bo cai.
   Mo lai tu Start menu > Download Now > Set up browser extensions.
   Chon Chrome/Edge/Opera, sao chep duong dan thu muc da chuan bi,
   bat Developer mode va chon Load unpacked de xac nhan lan dau.
   Firefox can ban da ky Mozilla hoac che do thu nghiem.
5. Tien ich mo trang Download Now de tu ghep noi; ung dung kiem tra dong bo.
   Chua co ban cua hang: khong tu cai ngam hoac ep chinh sach trinh duyet.

Mac dinh cai rieng cho tai khoan Windows hien tai trong LocalAppData/Programs/DownloadNow.
Du lieu, tuy chon va tep tai nam trong data canh DownloadNow.exe.
Goi cai moi khong mang lich su, tep hay ma ghep noi tu may tao bo cai.
Goi cap nhat ZIP van hoat dong qua nut Cap nhat trong ung dung.
Go cai dat qua Windows Settings > Apps; thu muc data va tep tai duoc giu lai.
Neu cai lai cung thu muc, tam dung va dong Download Now truoc khi cai.
Bo cai chua duoc ky so. Chi lay goi tu XOmongoose/DownloadNow tren GitHub.
'''.replace('VERSION',version),encoding='utf-8-sig')
    entries = sorted(p for p in package.rglob('*') if p.is_file())
    sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(package).as_posix()}\n' for p in entries)
    (package/'SHA256SUMS.txt').write_text(sums,encoding='utf-8')
    archive = dist/(name+'.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(package.rglob('*')):
            if p.is_file():
                z.write(p,p.relative_to(dist))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (dist/(name+'.zip.sha256')).write_text(digest+'  '+archive.name+'\n',encoding='utf-8')
    template={'version':version,'url':'https://your-domain.example/releases/'+archive.name,
              'sha256':digest,'notes':release['title']}
    (dist/(name+'.update.example.json')).write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Package: {archive}\nSHA256: {digest}')


if __name__ == '__main__':
    main()
