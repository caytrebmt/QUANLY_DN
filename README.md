# 🏢 ERPmini - Hệ thống ERP quản lý kho

## Tính năng chính
- ✅ Quản lý **hàng hóa** (CRUD, import/export Excel)
- ✅ Quản lý **nhà cung cấp** & **khách hàng** (import/export Excel)
- ✅ **Phiếu nhập kho** với VAT đầu vào (in PDF)
- ✅ **Phiếu xuất kho** với VAT đầu ra (in PDF)
- ✅ **Tồn kho real-time** (giá vốn bình quân gia quyền)
- ✅ **Lịch sử biến động** tồn kho
- ✅ **Công nợ** phải thu / phải trả + thanh toán
- ✅ **Sổ VAT** đầu vào / đầu ra (bảng kê theo tháng)
- ✅ **Kế toán**: nhật ký chung, hệ thống tài khoản, cân đối số phát sinh
- ✅ **Menu & Thông báo** định nghĩa bằng bảng DB (dễ mở rộng)
- ✅ Export **Excel** & **PDF** (pandas, reportlab)
- ✅ Import Excel cho hàng hóa, KH, NCC

## Cài đặt trên Windows + VSCode

### 1. Yêu cầu hệ thống
- Python 3.10+
- PostgreSQL 14+
- VSCode

### 2. Cài đặt PostgreSQL
```sql
-- Mở pgAdmin hoặc psql, chạy:
CREATE DATABASE erpmini;
CREATE USER erp_user WITH PASSWORD 'erp_password';
GRANT ALL PRIVILEGES ON DATABASE erpmini TO erp_user;
```

### 3. Clone / Copy project
```
erpmini/
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   └── templates/
├── config/
├── run.py
├── init_db.py
├── requirements.txt
└── .env
```

### 4. Tạo môi trường ảo
```bash
# Windows VSCode Terminal
python -m venv venv
venv\Scripts\activate

# Cài thư viện
pip install -r requirements.txt
```

### 5. Cấu hình .env
```bash
# Copy file mẫu
copy .env.example .env

# Chỉnh sửa .env:
DATABASE_URL=postgresql://erp_user:erp_password@localhost:5432/erpmini
SECRET_KEY=your-very-secret-key-2026
COMPANY_NAME=Tên công ty của bạn
COMPANY_ADDRESS=Địa chỉ công ty
COMPANY_TAX_CODE=Mã số thuế
```

### 6. Khởi tạo database
```bash
python init_db.py
```
Kết quả:
```
✅ Tạo bảng thành công!
✅ 14 cấu hình
✅ 26 menu items
✅ 14 mẫu thông báo
✅ admin (admin123)
✅ 3 kho
✅ 28 tài khoản kế toán
✅ 10 hàng hóa
✅ 4 nhà cung cấp
✅ 5 khách hàng
```

### 7. Chạy ứng dụng
```bash
python run.py
```
Mở trình duyệt: **http://localhost:5000**

### 8. Đăng nhập
| Username | Password | Vai trò |
|----------|----------|---------|
| admin    | admin123 | Quản trị |
| ketoan   | ketoan123| Kế toán  |

---

## Cấu trúc thư mục
```
app/
├── models/
│   ├── system.py      # Menu, Notification, User, SystemConfig
│   ├── master.py      # Product, Supplier, Customer, Warehouse, AccountChart
│   └── transaction.py # StockIn/Out, Inventory, JournalEntry, Debt, VAT
├── routes/
│   ├── auth.py        # Đăng nhập/xuất
│   ├── dashboard.py   # Trang tổng quan
│   ├── products.py    # Hàng hóa
│   ├── suppliers.py   # Nhà cung cấp
│   ├── customers.py   # Khách hàng
│   ├── warehouses.py  # Kho hàng
│   ├── stock_in.py    # Phiếu nhập kho
│   ├── stock_out.py   # Phiếu xuất kho
│   ├── inventory.py   # Tồn kho & lịch sử
│   ├── accounting.py  # Kế toán, bút toán
│   ├── debt.py        # Công nợ
│   ├── vat.py         # Sổ VAT
│   ├── settings.py    # Cài đặt hệ thống
│   └── api.py         # REST API (JSON)
├── services/
│   ├── inventory_service.py  # Tồn kho real-time (avg cost)
│   └── export_service.py     # Excel & PDF export/import
└── templates/         # HTML Jinja2 templates
```

## Mở rộng hệ thống

### Thêm menu mới
```python
# Vào psql hoặc pgAdmin, thêm vào bảng menus:
INSERT INTO menus (code, name, url, icon, order_no, module, is_active)
VALUES ('NEW_MODULE', 'Module mới', '/new-module/', 'fas fa-star', 10, 'new', true);
```

### Thêm thông báo mới
```python
INSERT INTO notifications (code, name, message_template, noti_type, module, is_active)
VALUES ('NEW_EVENT', 'Sự kiện mới', 'Thông báo: {name} đã xảy ra!', 'info', 'new', true);
```

### Thêm cấu hình mới
```python
INSERT INTO system_configs (key, value, description, group_name)
VALUES ('new_setting', 'default_value', 'Mô tả cài đặt', 'general');
```

## API Endpoints
- `GET /api/products/search?q=keyword` - Tìm hàng hóa
- `GET /api/products/<id>/stock?warehouse_id=X` - Tồn kho theo kho
- `GET /api/customers/search?q=keyword` - Tìm khách hàng
- `GET /api/suppliers/search?q=keyword` - Tìm nhà cung cấp
- `GET /api/dashboard/stats` - Thống kê dashboard

## Công nghệ sử dụng
| Thư viện | Mục đích |
|----------|----------|
| Flask | Web framework |
| SQLAlchemy | ORM PostgreSQL |
| Flask-Login | Xác thực người dùng |
| Pandas | Xử lý dữ liệu Excel |
| ReportLab | Tạo file PDF |
| openpyxl | Đọc/ghi Excel |
| Bootstrap 5 | UI framework |
| Chart.js | Biểu đồ dashboard |
| Select2 | Dropdown tìm kiếm |
