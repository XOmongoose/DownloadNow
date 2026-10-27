# Cài Download Now trên máy khác

Tác giả: **XOmongoose**.

1. Tải `DownloadNow-Setup-1.15.7-Windows-x64.exe` từ GitHub Releases của `XOmongoose/DownloadNow` và chép sang máy đích.
2. Chạy bộ cài trên Windows 10/11 x64, chọn thư mục và bấm **Install**.
3. Mở **Download Now** từ Desktop hoặc Start menu. Máy đích không cần Python hay Node.js.
4. Giữ lựa chọn **Set up browser extensions after installation** trong bộ cài. Khi mở ứng dụng sau cài đặt, cửa sổ thiết lập tiện ích sẽ xuất hiện; có thể mở lại bằng **Start menu → Download Now → Set up browser extensions**.
5. Chọn Chrome, Edge hoặc Opera. Ứng dụng mở trang quản lý tiện ích và trang ghép nối, hiển thị đúng thư mục với nút sao chép. Bật chế độ dành cho nhà phát triển, chọn **Load unpacked / Tải tiện ích đã giải nén** và chọn thư mục đó một lần. Firefox cần gói được Mozilla ký hoặc chế độ thử nghiệm.
6. Tiện ích mở trang ứng dụng để tự ghép nối; cửa sổ thiết lập tự kiểm tra kết nối và phiên bản. Cập nhật qua GitHub sẽ thay cả ứng dụng và tiện ích trong thư mục quản lý.

Hiện tiện ích chưa phát hành trên cửa hàng. Chrome trên Windows yêu cầu bản phát hành qua Chrome Web Store để phân phối theo luồng cài thông thường; bộ cài này chuẩn bị và hướng dẫn thiết lập, không thể cài ngầm hoặc tự xác nhận thay người dùng. Xem [quy định phân phối chính thức của Chrome](https://developer.chrome.com/docs/extensions/how-to/distribute).

Bộ cài mặc định dùng `%LOCALAPPDATA%\Programs\DownloadNow` cho tài khoản hiện tại. Tệp tải, lịch sử và cấu hình nằm trong thư mục `data` cạnh EXE. Gói phát hành không chứa dữ liệu hoặc mã kết nối của người đóng gói.

Cập nhật qua nút **Cập nhật** vẫn dùng gói ZIP có kiểm tra SHA-256. Để cài lại cùng thư mục, hãy tạm dừng các lượt tải và đóng tiến trình Download Now trước. Bộ cài sẽ từ chối thay bản đang chạy trong thư mục đích.

Gỡ cài đặt qua **Windows Settings → Apps → Download Now**. Thư mục `data` và tệp tải được giữ lại.

Bộ cài chưa ký số. Tệp `.exe.sha256` đi kèm dùng để kiểm tra toàn vẹn gói tải. Chỉ lấy gói từ kho phát hành của tác giả.

## Tạo bộ cài

Trên Windows, chạy lần lượt:

```powershell
python tools/build_windows.py
./tools/bootstrap_inno.ps1
python tools/build_installer.py
python tools/smoke_installer.py
```

Compiler Inno Setup 6.7.3 được tải từ kho chính thức và kiểm tra SHA-256 cùng chữ ký nhà phát hành. Bước smoke test cài vào thư mục kiểm thử riêng, kiểm tra ứng dụng và gỡ lại; không thay bản ứng dụng thực tế. GitHub Actions chạy các bước này trước khi phát hành.
