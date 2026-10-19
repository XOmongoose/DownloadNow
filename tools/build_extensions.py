"""Package browser-specific unpacked builds, store ZIPs and unsigned Firefox XPI."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def archive(folder, output, prefix=''):
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                z.write(path, prefix + path.relative_to(folder).as_posix())


def readable_guides(folder):
    """Include formats Windows can open without a Markdown application."""
    for source in sorted(folder.rglob('*.md')):
        content = source.read_text('utf-8')
        source.with_suffix('.txt').write_text(content.replace('.md', '.txt').replace('`', ''), encoding='utf-8-sig')
        if source.parent == folder:
            navigation = '<nav>' + ''.join(f'<a href="huong-dan/{browser}.html">{browser.title()}</a>' for browser in ('chrome', 'edge', 'opera', 'firefox', 'safari')) + '</nav>'
        else:
            navigation = '<nav><a href="../BAT-DAU.html">← Tất cả trình duyệt</a></nav>'
        title = content.splitlines()[0].lstrip('# ')
        page = f'''<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>body{{margin:0;background:#faf9f5;color:#302600;font:16px/1.8 'Segoe UI',Arial,sans-serif}}main{{max-width:900px;margin:36px auto;padding:28px;background:white;border:1px solid #eee3c4;border-top:5px solid #F1AF00;border-radius:12px}}h1{{font-size:25px;line-height:1.4}}nav{{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}}a{{color:#795800;background:#fff5d6;padding:6px 14px;border-radius:6px}}pre{{font:inherit;white-space:pre-wrap;overflow-wrap:anywhere}}@media(max-width:650px){{main{{margin:12px;padding:18px}}}}</style></head><body><main><h1>{html.escape(title)}</h1>{navigation}<pre>{html.escape(content.replace('.md', '.html').replace('`', ''))}</pre></main></body></html>'''
        source.with_suffix('.html').write_text(page, encoding='utf-8')


def main():
    subprocess.run([sys.executable, str(ROOT/'tools/sync_release.py')], check=True, cwd=ROOT)
    version = json.loads((ROOT/'releases.json').read_text('utf-8'))['releases'][0]['version']
    name = f'DownloadNow-Browser-Extensions-{version}'
    out = ROOT/'dist'/name
    if out.exists() or (ROOT/'dist'/(name+'.zip')).exists():
        raise SystemExit('Package already exists. Use a new release version.')
    out.mkdir(parents=True)
    guides = out/'huong-dan'
    guides.mkdir()
    shared = f'''# Download Now Bridge v{version}

Tiện ích này kết nối với Download Now trên chính máy của bạn, cổng 8765.
Bắt tự động yêu cầu ứng dụng Windows portable v1.6.0 trở lên. Cần nâng cấp cả EXE và tiện ích.

## Ghép nối sau khi cài

1. Chạy DownloadNow.exe, mở http://127.0.0.1:8765.
2. Mở trang ứng dụng trong trình duyệt đã cài tiện ích mới; tiện ích tự ghép nối.
3. Nếu cần nối lại, nhấn **Tự kết nối / Mở trang ứng dụng** trong popup. Mã kết nối chỉ dùng dự phòng.
4. Dán liên kết trực tiếp rồi nhấn **Gửi tải xuống**, hoặc dùng menu chuột phải.
5. Bật **Tự bắt lượt tải của trình duyệt**. Tùy chọn này lưu ngay khi đổi.
6. Bật **Bắt link tệp ngay khi bấm**, cấp quyền truy cập HTTP/HTTPS khi trình duyệt hỏi.
7. Tải lại trang có link tải, sau đó bấm link tệp, chọn nơi lưu trong hộp thoại Windows rồi nhấn Save/Lưu.
8. Dùng **Kiểm tra kết nối** trong popup để kiểm tra mã và phiên bản ứng dụng.

Bắt trực tiếp nhận link có đuôi tệp phổ biến hoặc thuộc tính download/tham số filename.
Các lượt tải khác dùng sự kiện downloads của trình duyệt làm lớp dự phòng.
Trình duyệt được tạm dừng trong khi ứng dụng kiểm tra link. Chỉ hủy lượt tải gốc
sau khi ứng dụng đã nhận. Khi lỗi, tiện ích thử tiếp tục lượt tải trình duyệt;
nếu trình duyệt không cho resume, mở danh sách tải của trình duyệt để thao tác.
Một số tệp rất nhỏ có thể hoàn tất trước khi tiện ích kịp can thiệp.

Khi tải thủ công hoặc tự bắt link, ứng dụng v1.6.0 mở cửa sổ Thông tin tải xuống kiểu IDM.
Chọn thư mục bằng Duyệt…, giữ tên từ link và nhấn Bắt đầu tải; nhấn Hủy để bỏ lượt tải.
Bật Ghi nhớ thư mục này để lần sau dùng lại vị trí đã chọn, kể cả sau khi mở lại ứng dụng.
Hộp thoại nằm trên máy đang chạy Download Now, không phải bộ chọn thư mục của trang web.

Chỉ hỗ trợ tệp/video/âm thanh HTTP(S) trực tiếp; không dò luồng trong trang,
không hỗ trợ blob/DRM/ghép HLS hoặc DASH, không chuyển cookie đăng nhập.
Để ứng dụng đang chạy khi dùng tiện ích. Không chia sẻ mã kết nối.

## Quyền truy cập

- storage: lưu mã kết nối và lựa chọn bắt tải trên máy.
- contextMenus: thêm mục gửi liên kết trong menu chuột phải.
- downloads: chuyển lượt tải sang ứng dụng khi bạn bật tùy chọn này.
- http://127.0.0.1:8765/*: gửi URL tải đến ứng dụng cục bộ.
- scripting: đăng ký bộ bắt click sau khi bật tùy chọn.
- HTTP/HTTPS (tùy chọn, hỏi khi bật bắt link): đọc liên kết người dùng bấm trên trang.
Không quét lịch sử duyệt web, không đọc hoặc chuyển cookie. Link cần đăng nhập sẽ
được giữ lại cho trình duyệt nếu ứng dụng không truy cập được.

Không có dịch vụ phân tích hoặc máy chủ thu thập từ xa trong tiện ích.
Máy chủ chứa tệp vẫn nhận yêu cầu tải do ứng dụng thực hiện.
Các gói chưa được ký/phát hành trên cửa hàng và chưa được kiểm thử cài trong
từng trình duyệt. Đã kiểm tra cú pháp JavaScript, manifest, tài nguyên và ZIP.

## Nâng cấp và gỡ

Giải nén bản mới vào vị trí cố định rồi tải lại tiện ích trong trang quản lý.
Không xóa thư mục tiện ích sau khi nạp bản giải nén.
Muốn gỡ: mở trang quản lý tiện ích, chọn Download Now Bridge → Xóa/Remove.
Việc gỡ tiện ích không xóa tệp đã tải hoặc hàng đợi trong ứng dụng.
'''
    browser_pages = {'chrome':'chrome://extensions', 'edge':'edge://extensions', 'opera':'opera://extensions'}
    produced = []
    for browser, page in browser_pages.items():
        folder = out/browser
        shutil.copytree(ROOT/'extension/chromium', folder)
        data = json.loads((folder/'manifest.json').read_text('utf-8'))
        assert data['version'] == version
        filename = f'DownloadNow-{browser.title()}-{version}.zip'
        archive(folder, out/filename)
        produced.append(filename)
        (guides/(browser+'.md')).write_text(f'''# Cài cho {browser.title()}

1. Giải nén `{filename}` vào một thư mục cố định.
   Nếu dùng bộ đầy đủ, dùng ngay thư mục `{browser}` bên cạnh `huong-dan`.
2. Mở `{page}` trên {browser.title()}.
3. Bật **Developer mode / Chế độ nhà phát triển**.
4. Nhấn **Load unpacked / Tải tiện ích đã giải nén**.
5. Chọn thư mục có tệp `manifest.json` (không chọn tệp ZIP).
6. Ghim tiện ích lên thanh công cụ, rồi làm theo hướng dẫn ghép nối.

Bản ZIP này cũng có cấu trúc để nộp lên cửa hàng tương ứng; chưa được nộp hoặc duyệt.
Không có bộ cài CRX một lần nhấp. Chrome trên Windows hạn chế cài ngoài cửa hàng;
bản giải nén là cách cài cho phát triển/cá nhân.

Nguồn: https://developer.chrome.com/docs/extensions/how-to/distribute

'''+shared, encoding='utf-8')
    firefox = out/'firefox'
    shutil.copytree(ROOT/'extension/firefox', firefox)
    firefox_zip = f'DownloadNow-Firefox-{version}-unsigned.zip'
    firefox_xpi = f'DownloadNow-Firefox-{version}-unsigned.xpi'
    archive(firefox, out/firefox_zip)
    shutil.copyfile(out/firefox_zip, out/firefox_xpi)
    produced.extend([firefox_zip, firefox_xpi])
    (guides/'firefox.md').write_text(f'''# Cài thử trên Firefox

Gói `{firefox_xpi}` chưa có chữ ký Mozilla. Đây không phải bản cài lâu dài
cho Firefox thông thường. Không đổi thiết lập bảo mật để bỏ kiểm tra chữ ký.

1. Giải nén `{firefox_zip}` hoặc dùng thư mục `firefox` trong bộ đầy đủ.
2. Mở `about:debugging#/runtime/this-firefox`.
3. Nhấn **Load Temporary Add-on / Tải tiện ích tạm thời**.
4. Chọn `manifest.json` trong thư mục vừa giải nén.
5. Ghép nối với ứng dụng theo hướng dẫn dưới đây.

Tiện ích tạm thời sẽ bị gỡ khi đóng Firefox; cần nạp lại ở lần mở sau.
Muốn cài lâu dài: chủ sở hữu đăng nhập addons.mozilla.org, chọn phân phối
unlisted/self-distributed, nộp ZIP để Mozilla kiểm tra/ký rồi tải XPI đã ký.
Sau đó người dùng cài XPI đã ký qua about:addons → bánh răng → Install Add-on From File.
Chưa nộp hay sử dụng tài khoản Mozilla nào trong quy trình đóng gói này.

Nguồn: https://extensionworkshop.com/documentation/publish/self-distribution/
https://extensionworkshop.com/documentation/publish/package-your-extension/

'''+shared, encoding='utf-8')
    (guides/'safari.md').write_text('''# Safari — chưa có gói cài

Không có Xcode/macOS trong môi trường đóng gói Windows nên chưa tạo gói Safari.
Không thể cài ZIP Chromium hoặc XPI Firefox trực tiếp vào Safari.

Dùng mã nguồn thư mục chrome làm đầu vào cho công cụ Safari Web Extension
packager/converter của Xcode trên macOS. Tên công cụ phụ thuộc phiên bản Xcode;
xem tài liệu Apple bên dưới. Sau đó cấu hình app/extension target, quyền localhost,
kiểm tra API downloads/contextMenus và ký bằng tài khoản Apple phù hợp.
Chức năng tự bắt tải có thể cần điều chỉnh theo API Safari; mã nguồn hiện tại
chưa được xác nhận chạy trên Safari. Cần chạy bộ máy Download Now trên cùng máy Mac;
EXE Windows trong bản portable không chạy trực tiếp trên macOS.

Nguồn: https://developer.apple.com/documentation/safariservices/packaging-a-web-extension-for-safari
https://developer.apple.com/safari/extensions/
''', encoding='utf-8')
    (out/'BAT-DAU.md').write_text(f'''# Download Now — Bộ tiện ích v{version}

- Chrome: đọc `huong-dan/chrome.md`, nạp thư mục `chrome`.
- Edge: đọc `huong-dan/edge.md`, nạp thư mục `edge`.
- Opera: đọc `huong-dan/opera.md`, nạp thư mục `opera`.
- Firefox: đọc `huong-dan/firefox.md`, nạp tạm thư mục `firefox`; XPI hiện chưa ký.
- Safari: chưa có gói cài; đọc `huong-dan/safari.md` về yêu cầu macOS/Xcode.

Các ZIP riêng có manifest.json ở gốc để giải nén/nộp store. Cài xong mở trang ứng dụng cục bộ để tự ghép nối, không cần sao chép mã.
Mã kết nối thủ công chỉ dùng dự phòng. Đã kèm hướng dẫn từng bước.
Gói không chứa EXE ứng dụng, token, hàng đợi hoặc dữ liệu cá nhân.
''', encoding='utf-8')
    readable_guides(out)
    sums = ''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out).as_posix()}\n'
                   for p in sorted(out.rglob('*')) if p.is_file())
    (out/'SHA256SUMS.txt').write_text(sums,encoding='utf-8')
    bundle = out.parent/(name+'.zip')
    archive(out,bundle,prefix=name+'/')
    digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
    Path(str(bundle)+'.sha256').write_text(digest+'  '+bundle.name+'\n',encoding='utf-8')
    print(f'Bundle: {bundle}\nBrowser packages: '+', '.join(produced))


if __name__ == '__main__':
    main()
