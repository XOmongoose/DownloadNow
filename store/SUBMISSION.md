# Hồ sơ nộp tiện ích Download Now Bridge

Chưa đăng cửa hàng, chưa ký Mozilla. Các ZIP là gói để nộp xét duyệt, không phải
liên kết cài tự động. Chủ kho cần tạo tài khoản nhà phát triển, hoàn tất thông tin
pháp lý/liên hệ và chấp nhận điều khoản của từng cửa hàng.

## Gói nộp

- Chrome Web Store: DownloadNow-Chrome-VERSION.zip.
- Microsoft Edge Add-ons: DownloadNow-Edge-VERSION.zip.
- Firefox Add-ons: DownloadNow-Firefox-VERSION-unsigned.zip, chọn phân phối trên AMO.
- Không nộp bộ ZIP tổng hợp chứa nhiều trình duyệt.
- Không thêm update_url tự lưu trữ vào gói cửa hàng. Cửa hàng quản lý cập nhật.

## Nội dung trang niêm yết

Tên: Download Now Bridge

Mô tả ngắn: Gửi liên kết tải sang Download Now trên máy, tự ghép nối và hỗ trợ tiếp tục tải.

Mô tả dài: Tiện ích kết nối trình duyệt với ứng dụng Download Now trên Windows.
Cài ứng dụng rồi mở http://127.0.0.1:8765 trong trình duyệt có tiện ích để tự ghép nối.
Bạn có thể gửi link từ menu chuột phải, chuyển lượt tải trình duyệt hoặc bật bắt link
khi bấm. Ứng dụng hiển thị hộp thoại chọn nơi lưu, hỗ trợ nhiều kết nối khi máy chủ
cho phép, dừng, tiếp tục, hủy và quản lý lịch sử. Hỗ trợ gửi trang Shorts/Reels công khai đến bộ xử lý video trong ứng dụng. Không hỗ trợ DRM hoặc tự truyền phiên đăng nhập. Cần ứng dụng đang chạy trên cùng máy.

Mục đích duy nhất: chuyển lượt tải người dùng chọn sang ứng dụng tải cục bộ.

Chính sách công khai: https://github.com/XOmongoose/DownloadNow/blob/main/store/PRIVACY.md
Trang hỗ trợ: https://github.com/XOmongoose/DownloadNow/issues
Mã nguồn: https://github.com/XOmongoose/DownloadNow

## Giải thích quyền cho nhà xét duyệt

- activeTab: chỉ đọc URL trang hiện tại khi người dùng mở tiện ích và chọn Tải video trang hiện tại.
- storage: lưu token ghép nối và tùy chọn trên máy, không đồng bộ lên máy chủ.
- downloads: đọc trạng thái và tạm dừng/chuyển lượt tải khi người dùng bật bắt tải; chờ xác định tên và hủy lượt trình duyệt sau khi ứng dụng nhận. Chế độ riêng báo lỗi thay vì tự tải bằng trình duyệt.
- contextMenus: thêm lệnh gửi link, video, audio đến ứng dụng.
- scripting: đăng ký mã bắt click tĩnh sau khi người dùng bật và cấp quyền.
- alarms: kiểm tra bản tiện ích mới khoảng mỗi 6 giờ khi trình duyệt hoạt động.
- api.github.com: chỉ đọc thông tin Release công khai, không gửi link tải hoặc token.
- localhost/127.0.0.1 cổng 8765: ghép nối và giao tiếp với ứng dụng cục bộ.
- HTTP/HTTPS tùy chọn: nhận link người dùng bấm; chỉ xin quyền khi bật tính năng.
- Không dùng remote code, cookies, history, webRequest hoặc quyền quản trị trình duyệt.

Khai báo dữ liệu cần phản ánh đúng phiên bản và biểu mẫu tại thời điểm nộp:
URL/tên tệp được xử lý và gửi đến ứng dụng cục bộ để thực hiện tải, không gửi cho
nhà phát triển. Không khẳng định tiện ích không truy cập URL hoặc dữ liệu tải.

## Kiểm tra trước khi nộp

1. Cài EXE và gói tiện ích trên hồ sơ trình duyệt thử nghiệm.
2. Mở trang ứng dụng, xác nhận tự ghép nối mà không chép mã.
3. Kiểm tra tải link công khai, hủy chọn lưu, mất kết nối và quyền tùy chọn.
4. Chụp ảnh giao diện thực tế theo kích thước cửa hàng yêu cầu. Chưa kèm ảnh giả lập.
5. Nhà xét duyệt có thể tải EXE Windows từ Releases để kiểm tra. Không cần tài khoản.
6. Nộp ZIP đúng trình duyệt, hoàn tất khai báo và chờ duyệt.
7. Sau khi được cấp trang tiện ích chính thức, ghi URL cửa hàng vào ứng dụng.
8. Những lần sau tăng phiên bản và nộp ZIP mới; người dùng đã cài từ cửa hàng sẽ
   nhận cập nhật qua trình duyệt. GitHub Release không tự xuất bản lên cửa hàng.

Nguồn chính thức:
https://developer.chrome.com/docs/webstore/publish
https://learn.microsoft.com/en-us/microsoft-edge/extensions/publish/publish-extension
https://extensionworkshop.com/documentation/publish/submitting-an-add-on/
