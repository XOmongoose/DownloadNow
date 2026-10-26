# Cài Download Now trên máy khác

Tác giả: **XOmongoose**.

1. Tải `DownloadNow-Setup-1.14.3-Windows-x64.exe` từ GitHub Releases của `XOmongoose/DownloadNow` và chép sang máy đích.
2. Chạy bộ cài trên Windows 10/11 x64, chọn thư mục và bấm **Install**.
3. Mở **Download Now** từ Desktop hoặc Start menu. Máy đích không cần Python hay Node.js.
4. Với Chrome, Edge hoặc Opera, mở **Download Now → Browser extensions** trong Start menu và nạp thư mục `chromium` bằng chức năng tải tiện ích đã giải nén của trình duyệt. Firefox cần gói được Mozilla ký hoặc chế độ thử nghiệm.
5. Mở giao diện ứng dụng để tiện ích ghép nối. Bộ cài không tự cấp quyền hay cài ngầm tiện ích trình duyệt.

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
