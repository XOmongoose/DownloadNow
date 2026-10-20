# Download Now

Ứng dụng quản lý tải HTTP/HTTPS chạy cục bộ, giao diện tiếng Việt. Không cần thư viện Python bên ngoài.

## Phiên bản và nâng cấp giao diện

Phiên bản hiện tại: **1.9.1**. Nhấn nút phiên bản ở thanh bên để xem lịch sử thay đổi. Tiện ích cũng hiển thị phiên bản trong popup.

Mỗi lần nâng cấp, thêm mục mới lên đầu `releases.json`, tăng `major.minor.patch` phù hợp rồi chạy `python tools/sync_release.py`. Lệnh đồng bộ phiên bản, lịch sử trong giao diện và hai gói tiện ích từ cùng một nguồn. Sau đó tải lại giao diện; với tiện ích đã cài cần nhấn Reload ở trang quản lý tiện ích.

## Bản Windows portable (không cần cài Python)

Giải nén `DownloadNow-1.9.1-Windows-x64.zip` vào thư mục có quyền ghi, chạy `DownloadNow.exe`. Giao diện tự mở trong trình duyệt mặc định. Giữ cửa sổ chương trình mở để tải và thực hiện lịch; nhấn Ctrl+C để thoát. Đây là bản EXE portable x64 chưa ký số, không phải bộ cài MSI.

Tệp tải nằm tại `data/files` cạnh EXE; dữ liệu không lưu vào thư mục giải nén tạm của chương trình. Khi nâng cấp, tắt bản cũ, thay EXE/tiện ích rồi giữ nguyên `data`. Đóng bản chạy mã nguồn trước khi mở EXE vì cả hai mặc định dùng cổng 8765. Để chuyển hàng đợi từ bản mã nguồn, tắt cả hai bản rồi sao chép toàn bộ thư mục `data` sang cạnh EXE. Không chạy hai bản cùng ghi vào một thư mục dữ liệu.

Lệnh bổ sung: `DownloadNow.exe --version`, `DownloadNow.exe --no-browser`, `DownloadNow.exe --port 8766`, `DownloadNow.exe --data D:\Downloads\DownloadNow`. Tiện ích mặc định vẫn kết nối cổng 8765.

Tự build trên Windows x64 bằng Python 3.12: tạo venv `.venv-build`, cài `requirements-build.txt`, chạy `.venv-build/Scripts/python.exe tools/build_windows.py`. Script tạo EXE, ZIP, thông tin phiên bản Windows và SHA-256 trong `dist`; không đưa dữ liệu cá nhân, token hay môi trường build vào gói. Nếu gói cùng phiên bản đã tồn tại, script từ chối ghi đè.

## Chạy trên Windows

1. Cài Python 3.11 trở lên.
2. Nhấp đúp `start.bat`, hoặc chạy `python app.py` trong thư mục này.
3. Mở **http://127.0.0.1:8765** trong trình duyệt. Giữ cửa sổ ứng dụng đang chạy.

Tệp hoàn tất nằm trong `data/files`. Các phần đang tải nằm trong `data/parts`; hàng đợi nằm trong `data/state.json`. Không xóa thư mục `data` nếu muốn tiếp tục tải. Dùng Ctrl+C để thoát gọn. Có thể chọn vị trí lưu bằng `python app.py --data D:\Downloads\DownloadNow` (giao diện mặc định vẫn hiển thị đường dẫn tương đối `data/files`). Đổi cổng bằng `--port`; tiện ích hiện dùng cổng 8765 cố định.

## Các chức năng

- **Tải song song:** tối đa 8 kết nối HTTP cho mỗi tệp, tối đa 2 tệp cùng lúc. Máy chủ phải hỗ trợ Range; worker nhận phần tiếp theo ngay khi hoàn thành phần hiện tại, phân phối công việc theo tốc độ thực tế. Đây là cơ chế phân đoạn theo hàng đợi; chưa có thuật toán chia lại một phần đang tải như IDM. Không thể bảo đảm tốc độ gấp 8: máy chủ, đường truyền, ổ đĩa và giới hạn dịch vụ quyết định tốc độ.
- **Khôi phục:** các phần được ghi ra đĩa; sau khi mở lại ứng dụng, những lượt tải đang chạy tự trở lại hàng đợi. Dùng ETag mạnh hoặc Last-Modified cùng kích thước để xác nhận tệp trước khi nối. Khi không có dấu nhận dạng đáng tin cậy, tệp đổi hoặc máy chủ không hỗ trợ Range, ứng dụng tải lại từ đầu để bảo toàn dữ liệu. Kiểm tra Content-Range và kích thước trước khi ghép; không ghi đè tệp đã có.
- **Thử lại:** tự kết nối lại với khoảng chờ tăng dần (tối đa 6 lần mỗi phần). Sau khi hết số lần thử, trạng thái “Cần kiểm tra” hiển thị nguyên nhân; nhấn tiếp tục để thử lại. Không tự sửa tệp nguồn bị hỏng nếu máy chủ không cung cấp checksum.
- **Lịch tải:** chọn thời điểm bắt đầu và tạm dừng cho từng tệp. Lịch lưu trên đĩa, dùng múi giờ của máy/trình duyệt và chạy khi ứng dụng đang mở. Nếu đã qua giờ dừng khi khởi động, tệp chuyển sang tạm dừng. Tiếp tục thủ công xóa lịch cũ. Không đánh thức máy ngủ, bật/tắt máy hoặc tự khởi động cùng Windows.
- **Giao diện:** tiến độ, tốc độ, ước tính thời gian, tìm kiếm, lọc theo trạng thái, tạm dừng/tiếp tục, tạo lịch, mã ghép nối tiện ích.

## Tiện ích trình duyệt

Gói độc lập: `dist/DownloadNow-Browser-Extensions-1.9.1.zip`. Giải nén, mở `BAT-DAU.html` hoặc `BAT-DAU.txt`, làm theo hướng dẫn trong `huong-dan` cho từng trình duyệt. Bộ này có thư mục nạp trực tiếp cho Chrome/Edge/Opera/Firefox, ZIP riêng với manifest ở gốc, cùng XPI Firefox **chưa ký**. Chrome/Edge/Opera dùng Load unpacked; Firefox nạp tạm qua about:debugging. Firefox cần ký Mozilla để cài lâu dài; Safari chưa có gói cài và cần macOS/Xcode. Chưa cài kiểm chứng trong từng trình duyệt. Không có khóa, token cá nhân hay dữ liệu tải trong các gói.

Tái tạo sau khi tăng phiên bản trong `releases.json`: `python tools/build_extensions.py`. Script đồng bộ phiên bản rồi tạo các gói và SHA-256; từ chối ghi đè gói đã có.

Chrome, Edge, Opera dùng thư mục `extension/chromium`:

1. Mở `chrome://extensions`, `edge://extensions` hoặc `opera://extensions`.
2. Bật chế độ nhà phát triển → Load unpacked / Tải tiện ích đã giải nén → chọn thư mục.
3. Trong giao diện ứng dụng chọn **Tiện ích trình duyệt**, sao chép mã kết nối.
4. Mở popup tiện ích, dán mã rồi nhấn **Lưu kết nối**.
5. Nhấn chuột phải lên liên kết/video/âm thanh → **Tải bằng Download Now**, hoặc bật tự động chuyển lượt tải. Tự bắt chỉ hủy lượt tải của trình duyệt sau khi ứng dụng đã nhận liên kết; khi bridge lỗi, lượt tải của trình duyệt tiếp tục. Nếu trình duyệt đã hoàn tất trước khi hủy, có thể còn một bản tải của trình duyệt.

Firefox: mở `about:debugging#/runtime/this-firefox` → Load Temporary Add-on → chọn `extension/firefox/manifest.json`. Bản cài tạm mất khi thoát Firefox; phát hành lâu dài cần ký tiện ích bằng Mozilla. Khi sửa các tệp dùng chung, chạy `python tools/sync_extension.py` để cập nhật bản Firefox.

Safari: mã tiện ích là WebExtension nhưng **chưa có gói Safari được ký**. Cần macOS + Xcode để chuyển đổi bằng `xcrun safari-web-extension-converter extension/chromium`, cấu hình quyền localhost và kiểm tra API downloads trên Safari đích; chức năng tự bắt tải có thể cần điều chỉnh hoặc chỉ dùng menu gửi liên kết. Không thể biên dịch/kiểm chứng Safari trên Windows. Các gói Chrome/Firefox cũng cần kiểm thử trong trình duyệt đích trước khi phát hành lên store.

Chỉ hỗ trợ URL HTTP(S) trực tiếp, bao gồm tệp video/âm thanh trực tiếp. Không dò luồng media trong trang, không tải `blob:`, DRM, ghép HLS/DASH, đăng nhập/cookie trình duyệt hay link hết hạn. Có thể đổi tên tệp trong hộp thoại thêm tải. Chỉ tải nội dung bạn có quyền tải.

## Dữ liệu và an toàn

Server chỉ lắng nghe `127.0.0.1`. API yêu cầu token riêng tại `data/bridge-token.txt`; chỉ chia sẻ token với tiện ích tin cậy. Không đưa thư mục data vào Git: có thể chứa URL có chữ ký hoặc dữ liệu riêng. Xóa token khi ứng dụng đã tắt để tạo mã mới ở lần mở sau, rồi ghép nối lại tiện ích. Giao diện chặn nhúng iframe và kiểm tra Host để chống DNS rebinding. Không mở API này ra Internet.

## Kiểm thử

`python -m unittest discover -s tests -v`

Bộ mặc định gồm 81 kiểm thử lõi/cập nhật với HTTP transport mô phỏng trong bộ nhớ: đối chiếu byte Range, mất kết nối, tạm dừng/khởi động lại, thay đổi ETag, không hỗ trợ Range, lịch tải và tên tệp an toàn. Trạng thái và phần tải vẫn ghi xuống đĩa thật. Các kiểm thử này đã qua trên Python 3.14, bao gồm tên tệp và kiểm tra mở đúng thư mục mà không thực thi tệp tải.

Kiểm thử tích hợp qua socket thật: `python -m unittest discover -s tests -p integration_downloads.py -v`. Bộ này bổ sung kiểm tra xác thực API và Host. Trong môi trường xây dựng Windows hiện tại, một số ca bị reset/timeout socket kể cả trên loopback; bộ tích hợp **chưa qua toàn bộ**. Chưa kiểm chứng giao diện trực tiếp hoặc cài tiện ích trong từng trình duyệt. Cần chạy bộ tích hợp và kiểm thử trình duyệt trong môi trường triển khai trước khi xem đây là bản phát hành ổn định.

## Vị trí tệp và tên tệp (v1.3.0)

Tệp hoàn tất có nút **Thư mục** để mở thư mục chứa tệp trên máy chạy ứng dụng,
và nút cạnh bên để xem/sao chép đường dẫn đầy đủ. Đường dẫn cũng hiển thị dưới
tên tệp; cuối danh sách hiển thị thư mục tải thực tế, kể cả khi dùng `--data`.
Nếu tệp đã bị chuyển hoặc xóa, ứng dụng báo lỗi khi mở thư mục.

Để trống ô tên để giữ tên từ link: giải mã tên Unicode và khoảng trắng trong đường dẫn,
hỗ trợ tham số `filename`, `file_name`, `download_filename`. Các endpoint tải chung
như `download.php` lấy tên máy chủ trong Content-Disposition, bao gồm filename* UTF-8.
Tên đặt thủ công được ưu tiên. Chỉ thay ký tự không hợp lệ trên Windows; nếu trùng
thêm (1), (2)… để tránh ghi đè. Hàng đợi cũ giữ nguyên tên đã lưu.

## Bắt tải tự động (v1.4.0)

Cần nâng cấp cả ứng dụng và tiện ích lên v1.4.0. Mở popup tiện ích, lưu mã kết nối,
bật **Tự bắt lượt tải của trình duyệt**. Bật thêm **Bắt link tệp ngay khi bấm**,
cấp quyền truy cập HTTP/HTTPS khi trình duyệt hỏi rồi tải lại các trang đang mở.
Quyền đọc link trên trang chỉ được yêu cầu khi bạn chủ động bật tùy chọn này.
Tiện ích không chuyển cookie hay quét lịch sử duyệt web.

Bộ bắt click nhận các link đuôi tệp phổ biến, thuộc tính download và tham số tên tệp.
Lượt tải không nhận ra từ click (ví dụ nút JavaScript tạo lượt tải) vẫn dùng lớp
bắt downloads.onCreated: tạm dừng bản trình duyệt, gửi link sang ứng dụng; chỉ hủy
bản gốc sau khi nhận xác nhận. Ứng dụng kiểm tra truy cập URL trước khi nhận.
Nếu không kết nối được hoặc link trả về trang đăng nhập, thử tiếp tục lượt tải bằng
trình duyệt. Nếu resume không được hỗ trợ, tiện ích báo để bạn tiếp tục thủ công.
Popup có nút kiểm tra kết nối và trạng thái tự bắt để chẩn đoán cấu hình.

Không cam kết bắt mọi nguồn như IDM: video DRM/HLS/DASH, URL blob, tải bằng POST,
link một lần, cookie/phiên đăng nhập và các trang hạn chế tiện ích có thể không
chuyển được. Tệp nhỏ có thể hoàn tất trước khi bắt kịp. Chế độ bắt link khi bấm
không đổi hành vi Ctrl/Alt/Shift-click; lớp bắt lượt tải vẫn hoạt động nếu bật.

Kiểm thử mô phỏng tiện ích: `node --test tests/extension.test.cjs` (8 ca đã qua:
thứ tự pause/gửi/cancel, resume khi lỗi, tắt/chưa ghép nối, chống gửi trùng,
click trực tiếp, bỏ qua điều hướng thường và khôi phục hành vi gốc khi lỗi).
Kiểm thử lõi có thêm 4 ca xác nhận URL, chặn trang đăng nhập và idempotency.
Đây là kiểm thử mô phỏng API trình duyệt; chưa thay thế việc cài và thử trên
Chrome/Edge/Opera/Firefox thật. Kiểm thử socket thật vẫn có giới hạn đã ghi ở trên.

## Chọn nơi lưu khi bấm tải (v1.5.0)

Nâng cấp cả EXE và tiện ích lên v1.5.0. Khi bấm **Chọn nơi lưu & tải** trong
ứng dụng hoặc bấm tải qua tiện ích, hộp thoại **Lưu thành…** của Windows xuất hiện.
Chọn thư mục và tên tệp rồi nhấn **Lưu**; nhấn **Hủy** để không tạo lượt tải.
Hộp thoại mở trên máy đang chạy Download Now. Mỗi tệp có thư mục lưu riêng,
được giữ qua tạm dừng/khởi động lại. Tệp cũ vẫn nằm ở vị trí đã lưu trước đó.
Nếu trùng tên, thêm số thứ tự để tránh ghi đè.

Luồng chọn dùng vé bất đồng bộ để chờ người dùng, không giữ một yêu cầu HTTP
chờ hộp thoại. Chỉ mở lần lượt một hộp thoại; tối đa 10 lượt chờ chọn.
Tệp tạm ghép được đặt ở thư mục đích để xuất bản qua ổ đĩa khác; các phần tải
vẫn nằm trong data/parts. Khi mất điện lúc ghép có thể còn tệp .downloadnow-*.tmp
ở thư mục đích; tiếp tục tải sẽ ghép lại tệp tạm tương ứng.

Hộp thoại hiện hỗ trợ Windows qua GetSaveFileNameW, chưa kiểm chứng giao diện
native bằng thao tác thực tế. 23 ca lõi và 11 ca tiện ích mô phỏng đã qua,
bao gồm chọn/hủy, chờ trước khi tạo lượt tải, chống mở trùng và lưu đúng thư mục.

## Cửa sổ tải và ghi nhớ nơi lưu (v1.6.0)

Cửa sổ **Thông tin tải xuống** kiểu IDM hiển thị địa chỉ link, tên tệp, ô thư mục,
nút **Duyệt…**, ô **Ghi nhớ thư mục này cho lần tải sau** và nút **Bắt đầu tải**.
Chọn thư mục không làm đổi tên tệp. Khi link có tên tệp rõ ràng, tiện ích dùng
lại tên đó thay vì hậu tố trùng tên do trình duyệt thêm trước khi chuyển tải.
Tùy chọn được lưu trong `data/preferences.json`. Bỏ ghi nhớ sẽ dùng lại thư mục
mặc định ở lần sau. Nếu thư mục đã nhớ bị xóa, tự quay về thư mục mặc định.

## Cập nhật ứng dụng (v1.6.0)

Nhấn **Cập nhật** ở góc trên để cấu hình nguồn HTTPS, bật kiểm tra hằng ngày,
kiểm tra thủ công hoặc chọn ZIP trên máy. Hiện **chưa có máy chủ cập nhật mặc định**.
Không báo đã mới nhất khi nguồn chưa cấu hình hoặc không truy cập được.

Nguồn là tệp JSON có `version` (major.minor.patch), `url` HTTPS tới ZIP Windows,
`sha256` đầy đủ của ZIP và `notes` tùy chọn. Script build tạo mẫu
`dist/DownloadNow-<version>-Windows-x64.update.example.json`; thay URL mẫu bằng
địa chỉ thật sau khi tải ZIP lên máy chủ của bạn, rồi lưu JSON trên HTTPS.
Nhập địa chỉ JSON trong hộp thoại Cập nhật. Không dùng URL mẫu làm nguồn thật.

**Cập nhật ngay** tải và xác minh rồi cài nếu là bản EXE Windows đang rảnh.
Tự kiểm tra hằng ngày chỉ thông báo có phiên bản mới; việc cài do bạn bấm nút.
Có thể chọn ZIP trên máy, kiểm tra xong rồi nhấn **Cài đặt & mở lại**.
Bản mã nguồn chỉ chuẩn bị gói, không tự sửa mã nguồn.

Cài đặt bị chặn khi có lượt tải đang chạy, hàng đợi chưa tạm dừng hoặc hộp thoại
chọn tải đang mở. Helper là bản sao EXE hiện tại: chờ app thoát, sao lưu tệp ứng dụng,
thay bằng gói đã kiểm tra rồi mở lại. Không dùng PowerShell và không đổi chính sách
thực thi của Windows. Không thay/xóa `data`, tệp tải, token hay tùy chọn; các bản sao
lưu và nhật ký nằm trong `data/updates`. Khi thay tệp lỗi, thử khôi phục từ sao lưu.
Tiện ích được chép vào thư mục extension của ứng dụng; trình duyệt vẫn cần Reload
hoặc nạp lại đúng thư mục nếu bạn dùng một bản tiện ích giải nén ở nơi khác.

Gói được kiểm tra SHA-256, danh sách tệp, phiên bản và đường dẫn trước khi giải nén;
chặn đường dẫn ra ngoài thư mục ứng dụng. EXE chưa ký số, nên chỉ dùng nguồn cập nhật
và gói ZIP bạn tin cậy. SHA-256 kiểm tra toàn vẹn, không thay thế chữ ký nhà phát hành.
38 kiểm thử lõi/cập nhật và 11 ca tiện ích mô phỏng đã qua; chưa kiểm chứng toàn bộ
cửa sổ Tk, mạng thật hoặc chu trình EXE tự thay bản thân trên máy người dùng.

## Nguồn GitHub Releases (v1.6.1)

Trong **Cập nhật**, nhập URL kho GitHub công khai hoặc dạng `owner/repo` rồi lưu.
Không cần lưu API key cho kho công khai. GitHub private chưa hỗ trợ đăng nhập/token.
Ứng dụng gọi API `/repos/owner/repo/releases/latest`, chỉ nhận Release ổn định.
Tag phải có dạng `v1.6.1` hoặc `1.6.1`, trùng phiên bản bên trong gói.

Mỗi lần phát hành, tạo Release trên kho thực tế của bạn, tải lên hai tệp từ dist:
`DownloadNow-<version>-Windows-x64.zip` và `DownloadNow-<version>-Windows-x64.zip.sha256`.
Tên tệp phải giữ nguyên. Không dùng Source code ZIP tự động của GitHub để cập nhật.
SHA-256 ưu tiên trường digest của GitHub; nếu chưa có thì đọc tệp .sha256 kèm gói.
Không nhận gói sai kho/tag, thiếu checksum hoặc bản prerelease/draft.

Chưa gắn kho mặc định vì chưa có địa chỉ GitHub thực tế được xác nhận. Chưa tạo kho,
đẩy mã, tạo Release hoặc tải tài sản nào lên GitHub trong bước phát triển này.
45 ca lõi/cập nhật và 11 ca mô phỏng tiện ích đã qua, gồm 7 ca GitHub mới.
Nguồn chính thức: https://docs.github.com/en/rest/releases/releases
https://docs.github.com/en/rest/releases/assets

## Kho phát hành đã chọn (v1.6.2)

Kho mặc định cho bản cài mới: https://github.com/XOmongoose/DownloadNow.
Trong lần kiểm tra ngày 19/10/2026, API GitHub trả 404 cho kho và Release mới nhất,
và tài khoản XOmongoose chưa hiển thị kho công khai. Chưa tải mã hay tài sản lên GitHub.
Cần tạo/công khai kho DownloadNow rồi tạo Release và tải lên ZIP + .zip.sha256.
Cấu hình nguồn cũ đã lưu của người dùng vẫn được giữ khi nâng cấp.

## Sửa tên tệp trong v1.6.3

Với link dạng Google Drive `/download?id=...`, hộp thoại lấy tên thật từ tiện ích hoặc thông tin `Content-Disposition` của máy chủ trước khi hiển thị. Hỗ trợ `filename*` Unicode và URL chuyển hướng. Tên tự nhập vẫn được giữ. Nếu máy chủ không cung cấp tên, ứng dụng báo lỗi để nhập tên hoặc tiếp tục bằng trình duyệt, thay vì âm thầm lưu thành `download`. Link cần đăng nhập vẫn có thể phải tải bằng trình duyệt. Sáu ca hồi quy tên tệp đã qua với HTTP mô phỏng; chưa kiểm chứng trực tiếp link Google Drive trong ảnh do URL không đầy đủ.

## Điều khiển tải trong v1.8.0

Dừng giữ phần tải dở để Tiếp tục. Hủy dừng kết nối và xóa phần tải dở; thêm lại link nếu muốn tải lại. Xóa lịch sử áp dụng cho các lượt đã hoàn tất hoặc đã hủy, có xác nhận, không xóa tệp đã tải trên máy. Lượt đang tải, đã dừng và bị lỗi vẫn được giữ để tiếp tục. Có thể xóa một mục hoặc toàn bộ lịch sử.

## Xóa đồng loạt trong v1.8.1

Đánh dấu các mục cần xóa hoặc chọn tất cả mục đang hiển thị, sau đó bấm Xóa đã chọn. Xóa tất cả lịch sử áp dụng cho toàn bộ lượt đã hoàn tất và đã hủy. Hộp thoại luôn bỏ chọn Xóa luôn tệp theo mặc định. Nếu bật, tệp hoàn tất được xóa vĩnh viễn; tệp không còn trên máy vẫn có thể bỏ lịch sử, còn tệp không xóa được sẽ giữ mục để thử lại. Không xóa thư mục, tệp ngoài đường dẫn lưu hay các lượt còn tiếp tục được.

## Cập nhật và kết nối trong v1.9.0

Nút Kiểm tra & cập nhật tự động thực hiện toàn bộ chuỗi kiểm tra, tải, xác minh rồi chờ hàng đợi rảnh để cài; đóng hộp thoại không ngắt chuỗi. Bản EXE tự mở lại với cổng và dữ liệu cũ, tách môi trường PyInstaller của tiến trình trước. Bản mã nguồn chỉ chuẩn bị gói, không tự thay mã nguồn.

Tiện ích mới tự ghép nối khi mở trang ứng dụng http://127.0.0.1:8765 hoặc http://localhost:8765 trong cùng trình duyệt. Không công khai token qua API không xác thực. Cần ứng dụng đang chạy; tiện ích chưa tự khởi chạy EXE. Mở trang chỉ có tác dụng sau khi cài hoặc Reload tiện ích v1.9.0.

Tự cập nhật tiện ích lâu dài cần cài từ cửa hàng. Chưa có tài khoản nhà phát triển hay niêm yết được duyệt, nên chưa thể tự cài hoặc tự phát hành lên cửa hàng. Bộ DownloadNow-Store-Submission-1.9.0.zip gồm ZIP riêng cho Chrome/Edge/Firefox, bản mô tả, khai báo quyền và chính sách quyền riêng tư. Xem store/SUBMISSION.md; còn cần tài khoản, ảnh chụp thực tế và xét duyệt. Không chỉnh chính sách doanh nghiệp hoặc sửa hồ sơ trình duyệt để ép cài tiện ích.

## Tải lại và tiện ích tự tìm bản mới (v1.9.1)

Bấm Tải lại ở lượt hoàn tất hoặc đã hủy để tạo một lượt mới từ URL cũ, giữ số kết nối và thư mục. Không ghi đè tệp cũ. Link có token hết hạn vẫn cần lấy URL mới từ trang nguồn.

Popup tiện ích tự lấy thông tin Release công khai trên GitHub, chọn ZIP đúng Chrome/Edge/Opera/Firefox hoặc dùng bộ tổng hợp nếu bản cũ chưa có gói riêng. Có nút Kiểm tra, Tải gói mới, liên kết Release và tùy chọn Tự tải gói mới (mặc định tắt). Kiểm tra nền mỗi 6 giờ khi trình duyệt hoạt động; dữ liệu Release được lưu đệm để tránh giới hạn GitHub. Gói tải nằm trong Downloads/DownloadNow, không bị chuyển lại sang ứng dụng. Gói ZIP vẫn cần giải nén và Reload/cài qua giao diện trình duyệt; chưa có tự cài như bản cửa hàng.
