# 📦 ERP-VIET — Hướng Dẫn Cài Đặt & Triển Khai

## Yêu Cầu Hệ Thống

| Thành phần | Yêu cầu |
|------------|----------|
| **Hệ điều hành** | Windows 10/11 (64-bit) |
| **RAM** | Tối thiểu 4 GB |
| **Ổ cứng** | ~500 MB cho ERP + ~200 MB cho PostgreSQL |
| **PostgreSQL** | Phiên bản 13 trở lên |
| **Trình duyệt** | Chrome, Edge, Firefox (phiên bản mới) |

---

## Bước 1: Cài Đặt PostgreSQL

> [!IMPORTANT]
> Nếu máy đã có PostgreSQL đang chạy, bỏ qua bước này.

1. Tải PostgreSQL tại: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Chạy installer, ghi nhớ **password** bạn đặt cho user `postgres`
3. Giữ port mặc định **5432**
4. Hoàn tất cài đặt, đảm bảo PostgreSQL **service đang chạy**

Kiểm tra nhanh: mở Command Prompt, gõ:
```
psql -U postgres -c "SELECT version();"
```

---

## Bước 2: Chạy ERP-VIET

1. **Giải nén** thư mục `ERP-VIET` vào ổ đĩa (ví dụ: `D:\ERP-VIET\`)
2. **Double-click** file `ERP-VIET.exe`
3. Cửa sổ **Cấu hình kết nối** sẽ hiện ra:

| Trường | Giá trị mặc định | Ghi chú |
|--------|------------------|---------|
| Host | `localhost` | Hoặc IP máy chủ DB |
| Port | `5432` | Port PostgreSQL |
| Database | `erpmini` | Sẽ tự tạo nếu chưa có |
| Username | `postgres` | User PostgreSQL |
| Password | *(nhập)* | Password bạn đặt khi cài PG |
| Port ứng dụng | `5000` | Đổi nếu port bị trùng |

4. Nhấn **"Kiểm tra kết nối"** để test
5. Nhấn **"Lưu và khởi động"**
6. Hệ thống sẽ:
   - Tự tạo database (nếu chưa có)
   - Tự tạo bảng và dữ liệu mẫu
   - Mở trình duyệt tại `http://localhost:5000`

---

## Bước 3: Đăng Nhập

| Vai trò | Username | Password |
|---------|----------|----------|
| **Admin** | `admin` | `admin123` |
| **Kế toán** | `ketoan` | `ketoan123` |

> [!WARNING]
> Đổi mật khẩu ngay sau lần đăng nhập đầu tiên!
> Vào **Cài đặt → Quản lý Users** để đổi.

---

## Truy Cập Từ Máy Khác (Mạng LAN)

Các máy khác trong cùng mạng LAN có thể truy cập ERP qua:

```
http://<IP-máy-chạy-ERP>:5000
```

Ví dụ: `http://192.168.1.100:5000`

> [!TIP]
> IP máy chạy ERP được hiển thị trong icon tray (góc phải taskbar).
> Click phải icon ERP → xem thông tin.

---

## Quản Lý & Bảo Trì

### Thay đổi cấu hình DB
- Click phải **icon ERP** trên khay hệ thống → **"Cấu hình dữ liệu"**

### Xem log lỗi
- File `launcher.log` nằm cùng thư mục với `ERP-VIET.exe`

### Thoát ứng dụng
- Click phải **icon ERP** trên khay hệ thống → **"Thoát"**

---

## Xử Lý Sự Cố

| Vấn đề | Giải pháp |
|--------|-----------|
| Không kết nối được DB | Kiểm tra PostgreSQL đang chạy (`services.msc` → tìm `postgresql`) |
| Port 5000 bị chiếm | Đổi port trong cửa sổ cấu hình |
| Trang web không load | Kiểm tra `launcher.log` để xem lỗi |
| Quên mật khẩu admin | Liên hệ người quản trị để reset trong DB |

---

## Cấu Trúc Thư Mục

```
ERP-VIET/
├── ERP-VIET.exe          ← Chạy file này
├── .env                  ← Cấu hình (tự tạo lần đầu)
├── launcher.log          ← Log lỗi
├── HUONG_DAN_CAI_DAT.txt ← Hướng dẫn
├── icon.ico              ← Icon ứng dụng
├── splash.png            ← Splash screen
└── _internal/            ← Thư viện (không chỉnh sửa)
```
