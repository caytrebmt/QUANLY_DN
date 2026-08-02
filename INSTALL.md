### 1. Yêu cầu hệ thống

| Phần mềm   | Phiên bản | Tải về                               |
| ---------- | --------- | ------------------------------------ |
| Python     | 3.9+      | https://www.python.org/downloads/    |
| PostgreSQL | 13+       | https://www.postgresql.org/download/ |
| VSCode     | Bất kỳ    | https://code.visualstudio.com/       |

### 2. Tạo Database PostgreSQL

Mở **pgAdmin 4** hoặc **psql** và chạy:

```sql
CREATE DATABASE erpmini
    ENCODING 'UTF8'
    LC_COLLATE 'en-US'
    LC_CTYPE 'en-US';
```

### 3. Mở Terminal trong VSCode

Mở thư mục dự án trong VSCode → Terminal → New Terminal

### 4. Tạo Virtual Environment

```cmd
:: Windows
python -m venv venv
venv\Scripts\activate

:: Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 5. Cài thư viện

```cmd
pip install -r requirements.txt
```

### 6. Cấu hình .env

Tạo file `.env` từ `.env.example`:

```cmd
copy .env.example .env
```

Mở `.env` và chỉnh sửa:

```env
DATABASE_URL=postgresql://postgres:YourPassword@localhost:5432/erpmini
COMPANY_NAME=Tên công ty
COMPANY_TAX_CODE=0123456789
```

### 7. Khởi tạo Database

```cmd
python init_db.py
```

Output mẫu:

```
✅ Tạo bảng thành công!
✅ 14 cấu hình
✅ 26 menu items
✅ admin (admin123)
✅ 10 hàng hóa mẫu
```

### 8. Chạy ứng dụng

```cmd
python run.py
```

Mở trình duyệt: **http://localhost:5000**

---

## 🔑 Tài khoản mặc định

| Username | Mật khẩu    | Vai trò       |
| -------- | ----------- | ------------- |
| `admin`  | `admin123`  | Quản trị viên |
| `ketoan` | `ketoan123` | Kế toán viên  |

> ⚠️ **Bắt buộc đổi mật khẩu sau lần đăng nhập đầu tiên!**

---

## 🚀 Khởi động ứng dụng hàng ngày

### Windows — Double-click

```
start_erpmini.bat
```

### VSCode — F5

Mở project trong VSCode → nhấn **F5** để chạy ở chế độ debug

### Terminal

```cmd
venv\Scripts\activate
python run.py
```

---

## 🛠️ Cấu hình VSCode (tùy chọn)

Cài các extensions sau để làm việc hiệu quả hơn:

```
- Python (Microsoft)
- Pylance
- Flask Snippets
- Jinja
- PostgreSQL (cweijan)
- GitLens
```

Mở **Extensions** (Ctrl+Shift+X) và tìm tên từng extension để cài.

---

## ❗ Xử lý lỗi thường gặp

### Lỗi: `psycopg2 installation failed`

```cmd
pip install psycopg2-binary
```

### Lỗi: `ModuleNotFoundError: No module named 'flask'`

```cmd
venv\Scripts\activate
pip install -r requirements.txt
```

### Lỗi: `could not connect to server`

1. Kiểm tra PostgreSQL đang chạy:
   - Windows: Tìm **Services** → PostgreSQL service → Start
2. Kiểm tra mật khẩu trong `.env`
3. Kiểm tra tên database đã tạo chưa

### Lỗi: `Address already in use` (port 5000)

Chỉnh port trong `.env`:

```env
PORT=5001
```

Hoặc tắt app khác đang dùng port 5000.

### Lỗi: `UnicodeDecodeError`

Đảm bảo file `.env` được lưu với encoding UTF-8.

---

## 📊 Sơ đồ luồng nghiệp vụ

```
Nhập tồn đầu kỳ (opening_stock)
        ↓
Nhập hàng (StockIn) ←── Nhà cung cấp (Supplier)
        ↓                        ↓
  Tồn kho (Inventory)    Công nợ phải trả (Debt)
        ↓                        ↓
Xuất hàng (StockOut) ←── Khách hàng (Customer)
        ↓                        ↓
  Cập nhật tồn kho        Công nợ phải thu (Debt)
        ↓
Sổ nhập xuất tồn (Reports)
Sổ VAT đầu vào/đầu ra (VAT)
Nhật ký kế toán (Journal)
```

---

## 📞 Hỗ trợ

Nếu gặp vấn đề trong quá trình cài đặt:

1. Chụp màn hình lỗi
2. Ghi lại phiên bản Python: `python --version`
3. Ghi lại phiên bản PostgreSQL: `psql --version`
4. Xem file log (nếu có) trong thư mục dự án
