# Phát hành và cập nhật tự động

Kho chính thức: https://github.com/XOmongoose/DownloadNow

Quy trình `.github/workflows/release.yml` chạy trên Windows khi đẩy thẻ `vX.Y.Z`.
Nó kiểm tra phiên bản với `releases.json`, chạy kiểm thử, đóng gói EXE và tiện ích,
tải ZIP và SHA-256 lên một Release nháp, rồi công khai sau khi tải đủ tài sản.
Workflow dùng `GITHUB_TOKEN` của GitHub Actions, không cần lưu PAT trong mã nguồn.
Nếu phát hành lỗi, kiểm tra tab Actions và Release nháp trước khi thử lại.
Không ghi đè tài sản của phiên bản đã phát hành.

Lần đầu cần đăng nhập GitHub, đưa mã nguồn lên kho và cho phép Actions chạy.
Không đưa thư mục `data`, `.tools`, `.venv-build`, `build`, `dist` lên Git.
Nếu kho đã có mã, hợp nhất lịch sử trước; không force push.

Mỗi lần nâng cấp:

1. Thêm phiên bản mới ở đầu `releases.json`.
2. Chạy `python tools/sync_release.py`, kiểm thử và commit mã.
3. Đẩy commit lên nhánh phát triển, rồi tạo và đẩy thẻ trùng phiên bản:

```powershell
git tag v1.7.0
git push origin HEAD
git push origin v1.7.0
```

Ứng dụng Windows EXE kiểm tra Release ổn định mỗi ngày khi đang chạy.
Trong **Cập nhật & tùy chọn**, bật kiểm tra tự động và tự tải/cài.
Ứng dụng tải ZIP, kiểm tra SHA-256 và nội dung gói, chờ không còn hàng đợi
hoặc hộp thoại tải, rồi sao lưu, cài và tự mở lại. Dữ liệu được giữ lại.
Bản mã nguồn chỉ chuẩn bị gói; tiện ích vẫn cần cập nhật ở trang quản lý
tiện ích của trình duyệt. Tự cập nhật tiện ích lâu dài cần phát hành qua
các cửa hàng trình duyệt.
