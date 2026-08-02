# 📘 THÔNG TIN CHI TIẾT DỰ ÁN & HƯỚNG DẪN KẾT NỐI DỮ LIỆU (ONLINE & LOCALHOST)

---

## 🚀 1. TỔNG QUAN DỰ ÁN (PROJECT OVERVIEW)

**Tên dự án:** ERP ACC & WebShop E-Commerce System  
**Phiên bản:** v4.2 SaaS Cloud Enterprise Edition  
**Mục tiêu:** Hệ thống quản trị tổng thể doanh nghiệp (SaaS ERP) kết hợp Cửa hàng trực tuyến (E-Commerce WebShop), hỗ trợ đa ngôn ngữ (Tiếng Việt & Tiếng Anh), đồng bộ kho bãi, đơn hàng, danh mục sản phẩm, hóa đơn VAT và sổ cái kế toán realtime.

---

## 🛠️ 2. KIẾN TRÚC & CÔNG NGHỆ (TECH STACK)

* **Frontend:** React 19 + TypeScript + Vite 6 + Tailwind CSS v4 + Lucide Icons + Motion
* **Backend:** Node.js Express + TSX (Dev Server) / ESBuild (Production CJS Bundle)
* **Database Driver:** `pg` (PostgreSQL Connection Pool) hỗ trợ Auto-Migration từ `schema.sql`
* **Xác thực & Bảo mật:** JWT Authentication (Bearer Token), phân quyền Admin / User
* **Đa ngôn ngữ:** `LanguageContext` (Chuyển đổi VI 🇻🇳 / EN 🇺🇸 realtime)
* **Dữ liệu Đa ngữ cảnh:** Các bảng lưu trữ cấu trúc song ngữ: `name_vi`, `name_en`, `description_vi`, `description_en`

---

## 🌐 3. MÔI TRƯỜNG KẾT NỐI DỮ LIỆU (ONLINE & LOCALHOST)

Dự án hỗ trợ chuyển đổi linh hoạt giữa môi trường **Localhost** (chạy test máy cục bộ) và môi trường **Online** (khi đưa lên máy chủ Cloud / Production).

### 3.1 Cấu hình Môi trường Localhost (Chạy thử & Kiểm thử)

Để chạy thử trên máy tính của bạn (Localhost) trước khi deploy online:

1. **Chuẩn bị PostgreSQL tại Localhost:**
   * Cài đặt PostgreSQL (version 14+) hoặc dùng Docker:
     ```bash
     docker run --name erpacc-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=erpacc_db -p 5432:5432 -d postgres:15
     ```

2. **Cấu hình File `.env` tại Localhost:**
   Tạo file `.env` (hoặc sao chép từ `.env.example`) tại thư mục `/webshop`:
   ```env
   # Cách 1: Sử dụng URL đơn (Khuyên dùng)
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/erpacc_db

   # Cách 2: Hoặc khai báo từng thông số riêng lẻ
   PGHOST=localhost
   PGPORT=5432
   PGUSER=postgres
   PGPASSWORD=postgres
   PGDATABASE=erpacc_db

   NODE_ENV=development
   PORT=3000
   VITE_API_BASE_URL=/api
   ```

---

### 3.2 Cấu hình Môi trường Online (Production / Staging)

Khi triển khai lên máy chủ thật (Cloud SQL, Supabase, Neon DB, Render PostgreSQL, VPS):

1. **Khởi tạo chuỗi DATABASE_URL Online:**
   Ví dụ kết nối tới Cloud DB với SSL mã hóa an toàn:
   ```env
   DATABASE_URL=postgresql://db_user:secret_password@your-cloud-db-host.com:5432/erpacc_prod?sslmode=require
   NODE_ENV=production
   PORT=3000
   ```

2. **Cơ chế Tự động hóa của Hệ thống:**
   * Trong `src/db/index.ts`, hệ thống tự động nhận diện `DATABASE_URL` online và áp dụng kết nối mã hóa SSL (`rejectUnauthorized: false`).
   * Nếu có kết nối PostgreSQL thật, hệ thống tự động kiểm tra và cập nhật `schema.sql` (Auto Migration).
   * Nếu không có kết nối cơ sở dữ liệu thật, hệ thống sẽ tự động bật chế độ dự phòng thông minh (Fallback In-memory Data) giúp ứng dụng vẫn phản hồi mượt mà không bị treo.

---

## 🗄️ 4. CẤU TRÚC DỮ LIỆU CHI TIẾT (`schema.sql`)

Dữ liệu được chuẩn hóa song ngữ cho dữ liệu thật:

| Bảng (Table) | Trường dữ liệu Tiếng Việt | Trường dữ liệu Tiếng Anh | Mục đích |
|---|---|---|---|
| `categories` | `name_vi`, `description_vi` | `name_en`, `description_en` | Danh mục sản phẩm song ngữ |
| `brands` | `name_vi`, `description_vi` | `name_en`, `description_en` | Thương hiệu sản phẩm song ngữ |
| `units` | `name_vi` | `name_en` | Đơn vị tính (Cái/Pcs, Tệp/Pack, Hộp/Box) |
| `products` | `name_vi`, `description_vi` | `name_en`, `description_en` | Thông tin chi tiết mặt hàng & tồn kho |
| `v_products_detail` | `category_name_vi`, `uom_name_vi` | `category_name_en`, `uom_name_en` | View truy vấn danh mục & đơn vị tính nhanh |

---

## ⚡ 5. QUY TRÌNH CHẠY & KIỂM THỬ DỰ ÁN (COMMANDS)

```bash
# 1. Chạy chế độ Development (Full-stack Express + Vite HMR)
npm run dev

# 2. Kiểm tra lỗi Syntax & Typescript Compiler
npm run lint

# 3. Đóng gói cho Production
npm run build

# 4. Khởi chạy Production Server
npm run start
```
