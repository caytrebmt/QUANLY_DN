-- ============================================================
-- SCHEMAS & DATABASE STRUCTURE FOR ERPACC & WEBSHOP (PostgreSQL)
-- Enterprise Resource Planning + Accounting (TT200) + Inventory Management
-- + Purchasing + Sales & Commercial + Webshop E-Commerce Platform
-- Multilingual Support (VI / EN)
-- ============================================================

-- Drop views in reverse dependency order
DROP VIEW IF EXISTS vw_trial_balance_tt200 CASCADE;
DROP VIEW IF EXISTS vw_vat_tax_filing CASCADE;
DROP VIEW IF EXISTS vw_sales_performance CASCADE;
DROP VIEW IF EXISTS vw_supplier_payable_summary CASCADE;
DROP VIEW IF EXISTS vw_customer_debt_summary CASCADE;
DROP VIEW IF EXISTS vw_product_stock_summary CASCADE;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS web_product_reviews CASCADE;
DROP TABLE IF EXISTS web_order_items CASCADE;
DROP TABLE IF EXISTS web_orders CASCADE;
DROP TABLE IF EXISTS web_cart_items CASCADE;
DROP TABLE IF EXISTS web_carts CASCADE;
DROP TABLE IF EXISTS web_promotions CASCADE;
DROP TABLE IF EXISTS web_customers CASCADE;

DROP TABLE IF EXISTS journal_entry_lines CASCADE;
DROP TABLE IF EXISTS journal_entries CASCADE;
DROP TABLE IF EXISTS receipts_payments CASCADE;
DROP TABLE IF EXISTS invoice_items CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS chart_of_accounts CASCADE;

DROP TABLE IF EXISTS stocktaking_items CASCADE;
DROP TABLE IF EXISTS stocktaking_sessions CASCADE;
DROP TABLE IF EXISTS stock_balances CASCADE;
DROP TABLE IF EXISTS stock_movement_items CASCADE;
DROP TABLE IF EXISTS stock_movements CASCADE;
DROP TABLE IF EXISTS warehouse_locations CASCADE;
DROP TABLE IF EXISTS warehouses CASCADE;

DROP TABLE IF EXISTS purchase_order_items CASCADE;
DROP TABLE IF EXISTS purchase_orders CASCADE;
DROP TABLE IF EXISTS purchase_request_items CASCADE;
DROP TABLE IF EXISTS purchase_requests CASCADE;

DROP TABLE IF EXISTS sales_order_items CASCADE;
DROP TABLE IF EXISTS sales_orders CASCADE;
DROP TABLE IF EXISTS quotation_items CASCADE;
DROP TABLE IF EXISTS quotations CASCADE;

DROP TABLE IF EXISTS suppliers CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS customer_groups CASCADE;

DROP TABLE IF EXISTS product_images CASCADE;
DROP TABLE IF EXISTS product_variants CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS brands CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS uom_conversions CASCADE;
DROP TABLE IF EXISTS uom CASCADE;

DROP TABLE IF EXISTS sys_audit_logs CASCADE;
DROP TABLE IF EXISTS sys_user_roles CASCADE;
DROP TABLE IF EXISTS sys_users CASCADE;
DROP TABLE IF EXISTS sys_role_permissions CASCADE;
DROP TABLE IF EXISTS sys_permissions CASCADE;
DROP TABLE IF EXISTS sys_roles CASCADE;
DROP TABLE IF EXISTS sys_menus CASCADE;
DROP TABLE IF EXISTS sys_translations CASCADE;
DROP TABLE IF EXISTS sys_languages CASCADE;
DROP TABLE IF EXISTS sys_settings CASCADE;

-- Helper Function for Automatic Timestamp Updating
CREATE OR REPLACE FUNCTION fn_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 1. MULTI-LANGUAGE SYSTEM & TRANSLATION DICTIONARY
-- ------------------------------------------------------------
CREATE TABLE sys_languages (
    code VARCHAR(10) PRIMARY KEY, -- 'vi', 'en'
    name VARCHAR(50) NOT NULL,
    flag_icon VARCHAR(50),
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_languages (code, name, flag_icon, is_default, is_active) VALUES
('vi', 'Tiếng Việt', '🇻🇳', TRUE, TRUE),
('en', 'English', '🇬🇧', FALSE, TRUE);

CREATE TABLE sys_translations (
    id SERIAL PRIMARY KEY,
    lang_code VARCHAR(10) NOT NULL REFERENCES sys_languages(code) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL DEFAULT 'common',
    translation_key VARCHAR(150) NOT NULL,
    translation_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_lang_key UNIQUE(lang_code, translation_key)
);

CREATE TRIGGER trg_sys_translations_upd BEFORE UPDATE ON sys_translations FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

-- Seed Dictionary Entries
INSERT INTO sys_translations (lang_code, category, translation_key, translation_value) VALUES
('vi', 'common', 'app_title', 'Hệ Thống ERPACC & Webshop'),
('en', 'common', 'app_title', 'ERPACC & Webshop System'),
('vi', 'common', 'search_placeholder', 'Tìm kiếm dữ liệu...'),
('en', 'common', 'search_placeholder', 'Search data...'),
('vi', 'common', 'actions', 'Thao tác'),
('en', 'common', 'actions', 'Actions'),
('vi', 'common', 'status', 'Trạng thái'),
('en', 'common', 'status', 'Status'),
('vi', 'common', 'save', 'Lưu thay đổi'),
('en', 'common', 'save', 'Save Changes'),
('vi', 'common', 'cancel', 'Hủy bỏ'),
('en', 'common', 'cancel', 'Cancel'),
('vi', 'common', 'delete', 'Xóa'),
('en', 'common', 'delete', 'Delete'),
('vi', 'common', 'edit', 'Chỉnh sửa'),
('en', 'common', 'edit', 'Edit'),
('vi', 'common', 'add_new', 'Thêm mới'),
('en', 'common', 'add_new', 'Add New'),

-- Menu Translations
('vi', 'menu', 'dashboard', 'Tổng quan (Dashboard)'),
('en', 'menu', 'dashboard', 'Dashboard Overview'),
('vi', 'menu', 'quotations', 'Báo giá khách hàng'),
('en', 'menu', 'quotations', 'Customer Quotations'),
('vi', 'menu', 'sales_orders', 'Đơn hàng bán'),
('en', 'menu', 'sales_orders', 'Sales Orders'),
('vi', 'menu', 'web_orders', 'Đơn hàng WebShop'),
('en', 'menu', 'web_orders', 'WebShop Orders'),
('vi', 'menu', 'customers', 'Quản lý Khách hàng'),
('en', 'menu', 'customers', 'Customer Management'),
('vi', 'menu', 'suppliers', 'Nhà cung cấp'),
('en', 'menu', 'suppliers', 'Suppliers'),
('vi', 'menu', 'products', 'Sản phẩm & Hàng hóa'),
('en', 'menu', 'products', 'Products & Items'),
('vi', 'menu', 'categories_uom', 'Danh mục & Đơn vị tính'),
('en', 'menu', 'categories_uom', 'Categories & UOM'),
('vi', 'menu', 'inventory', 'Quản lý kho hàng'),
('en', 'menu', 'inventory', 'Warehouse Inventory'),
('vi', 'menu', 'stock_in', 'Nhập kho (Stock In)'),
('en', 'menu', 'stock_in', 'Stock In Receipt'),
('vi', 'menu', 'stock_out', 'Xuất kho (Stock Out)'),
('en', 'menu', 'stock_out', 'Stock Out Issue'),
('vi', 'menu', 'stocktaking', 'Kiểm kê Kho & Lệch kho'),
('en', 'menu', 'stocktaking', 'Stocktaking & Discrepancies'),
('vi', 'menu', 'finance_invoices', 'Hóa đơn & Thu chi'),
('en', 'menu', 'finance_invoices', 'Invoices & Cashbook'),
('vi', 'menu', 'debt', 'Sổ Công nợ & Thu chi'),
('en', 'menu', 'debt', 'Debts & Cash Flow'),
('vi', 'menu', 'vat', 'Kê Khai Thuế GTGT (VAT)'),
('en', 'menu', 'vat', 'VAT Tax Filings'),
('vi', 'menu', 'accounting', 'Hệ Thống Kế Toán (TT200)'),
('en', 'menu', 'accounting', 'Accounting Ledger (TT200)'),
('vi', 'menu', 'reports', 'Báo cáo & Phân tích'),
('en', 'menu', 'reports', 'Reports & Analytics'),
('vi', 'menu', 'settings', 'Cài đặt Hệ thống'),
('en', 'menu', 'settings', 'System Settings');

-- ------------------------------------------------------------
-- 2. SYSTEM SETTINGS & PARAMETERS
-- ------------------------------------------------------------
CREATE TABLE sys_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_sys_settings_upd BEFORE UPDATE ON sys_settings FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

INSERT INTO sys_settings (setting_key, setting_value, description) VALUES
('company_name_vi', 'CÔNG TY CỔ PHẦN ERP-VIỆT SAAS ENTERPRISE', 'Tên công ty tiếng Việt'),
('company_name_en', 'ERP-VIET SAAS ENTERPRISE JOINT STOCK COMPANY', 'Company name in English'),
('company_tax_code', '0109988776-001', 'Mã số thuế doanh nghiệp'),
('company_address_vi', 'Tòa nhà Keangnam Landmark 72, Đường Phạm Hùng, Cầu Giấy, Hà Nội', 'Địa chỉ đăng ký KD tiếng Việt'),
('company_address_en', 'Keangnam Landmark 72, Pham Hung Street, Cau Giay, Hanoi', 'Registered address in English'),
('company_phone', '024.3998.8888 / 0988.123.456', 'Hotline liên hệ'),
('company_email', 'contact@erp-viet.vn', 'Email công ty'),
('default_language', 'vi', 'Ngôn ngữ mặc định (vi/en)'),
('currency_default', 'VND', 'Đơn vị tiền tệ chính'),
('vat_default_rate', '10', 'Thuế suất VAT mặc định (%)'),
('costing_method', 'Bình quân gia quyền ròng', 'Phương pháp tính giá vốn tồn kho'),
('webshop_sync_enabled', 'true', 'Tự động đồng bộ tồn kho sang Webshop');

-- ------------------------------------------------------------
-- 3. DYNAMIC MENUS & NAVIGATION (MULTILINGUAL)
-- ------------------------------------------------------------
CREATE TABLE sys_menus (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    title_vi VARCHAR(100) NOT NULL,
    title_en VARCHAR(100) NOT NULL,
    path VARCHAR(200) NOT NULL,
    icon VARCHAR(50),
    parent_id INT REFERENCES sys_menus(id) ON DELETE CASCADE,
    sort_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_menus (id, code, title_vi, title_en, path, icon, parent_id, sort_order) VALUES
(1, 'DASHBOARD', 'Tổng quan (Dashboard)', 'Dashboard Overview', '/saas/dashboard', 'LayoutDashboard', NULL, 10),
(2, 'WEB_ORDERS', 'Đơn hàng WebShop', 'WebShop Orders', '/saas/web-orders', 'ShoppingBag', NULL, 15),
(3, 'PRODUCTS', 'Sản phẩm & Hàng hóa', 'Products & Items', '/saas/products', 'Package', NULL, 20),
(4, 'CATEGORIES_UOM', 'Danh mục & Đơn vị tính', 'Categories & UOM', '/saas/categories-units', 'Tags', NULL, 25),
(5, 'CUSTOMERS', 'Khách hàng', 'Customers', '/saas/customers', 'Users', NULL, 30),
(6, 'SUPPLIERS', 'Nhà cung cấp', 'Suppliers', '/saas/suppliers', 'Truck', NULL, 35),
(7, 'WAREHOUSES', 'Địa điểm Kho bãi', 'Warehouse Locations', '/saas/warehouses', 'Warehouse', NULL, 40),
(8, 'STOCK_IN', 'Nhập kho (Stock In)', 'Stock In Receipt', '/saas/stock-in', 'ArrowDownLeft', NULL, 45),
(9, 'STOCK_OUT', 'Xuất kho (Stock Out)', 'Stock Out Issue', '/saas/stock-out', 'ArrowUpRight', NULL, 50),
(10, 'STOCKTAKING', 'Kiểm kê Kho & Lệch kho', 'Stocktaking & Discrepancies', '/saas/stocktaking', 'ClipboardList', NULL, 55),
(11, 'QUOTATIONS', 'Báo giá Commercial', 'Customer Quotations', '/saas/quotations', 'FileText', NULL, 60),
(12, 'INVENTORY', 'Báo cáo Tồn kho', 'Warehouse Inventory', '/saas/inventory', 'Boxes', NULL, 65),
(13, 'DEBT', 'Sổ Công nợ & Thu Chi', 'Debts & Cash Flow', '/saas/debt', 'Receipt', NULL, 70),
(14, 'VAT', 'Kê Khai Thuế GTGT (VAT)', 'VAT Tax Filings', '/saas/vat', 'Percent', NULL, 75),
(15, 'ACCOUNTING', 'Kế toán tổng hợp (TT200)', 'General Ledger (TT200)', '/saas/accounting', 'Calculator', NULL, 80),
(16, 'REPORTS', 'Báo cáo & Phân tích', 'Reports & Analytics', '/saas/reports', 'BarChart3', NULL, 85),
(17, 'SETTINGS', 'Cấu hình hệ thống', 'System Settings', '/saas/settings', 'Settings', NULL, 90);

-- ------------------------------------------------------------
-- 4. ROLES, PERMISSIONS & USERS (RBAC MULTILINGUAL)
-- ------------------------------------------------------------
CREATE TABLE sys_roles (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name_vi VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    description_vi TEXT,
    description_en TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sys_roles (id, code, name_vi, name_en, description_vi, description_en) VALUES
(1, 'ADMIN', 'Quản trị viên', 'System Administrator', 'Toàn quyền cấu hình, xem và chỉnh sửa tất cả dữ liệu', 'Full access to system settings, data, and permissions'),
(2, 'SALES', 'Nhân viên Kinh doanh', 'Sales Representative', 'Tạo báo giá, đơn hàng và quản lý khách hàng', 'Manage quotations, sales orders, and customers'),
(3, 'ACCOUNTANT', 'Kế toán viên', 'Chief Accountant', 'Xử lý hóa đơn, sổ quỹ, thu chi và báo cáo tài chính', 'Manage invoices, cashbook, financial entries and reports'),
(4, 'WAREHOUSE', 'Thủ kho', 'Warehouse Manager', 'Quản lý xuất nhập kho, kiểm kê và điều chuyển', 'Manage stock movements, inventory checks, and transfers'),
(5, 'PURCHASING', 'Nhân viên Mua hàng', 'Purchaser', 'Quản lý yêu cầu và đơn đặt mua hàng NCC', 'Manage purchase requests and orders');

CREATE TABLE sys_permissions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    module VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description_vi TEXT,
    description_en TEXT
);

INSERT INTO sys_permissions (code, module, action, description_vi, description_en) VALUES
('product:view', 'PRODUCT', 'READ', 'Xem danh sách sản phẩm', 'View product list'),
('product:create', 'PRODUCT', 'CREATE', 'Thêm mới sản phẩm', 'Create new product'),
('product:edit', 'PRODUCT', 'UPDATE', 'Sửa sản phẩm', 'Update product details'),
('product:delete', 'PRODUCT', 'DELETE', 'Xóa sản phẩm', 'Delete product'),
('quotation:view', 'QUOTATION', 'READ', 'Xem danh sách báo giá', 'View quotations list'),
('quotation:create', 'QUOTATION', 'CREATE', 'Tạo báo giá mới', 'Create new quotation'),
('order:view', 'ORDER', 'READ', 'Xem đơn hàng bán', 'View sales orders'),
('purchase:view', 'PURCHASE', 'READ', 'Xem đơn mua hàng', 'View purchase orders'),
('finance:view', 'FINANCE', 'READ', 'Xem báo cáo tài chính', 'View financial reports'),
('inventory:manage', 'INVENTORY', 'MANAGE', 'Quản lý xuất nhập kho', 'Manage warehouse inventory');

CREATE TABLE sys_role_permissions (
    role_id INT REFERENCES sys_roles(id) ON DELETE CASCADE,
    permission_id INT REFERENCES sys_permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

INSERT INTO sys_role_permissions (role_id, permission_id)
SELECT 1, id FROM sys_permissions;

CREATE TABLE sys_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    role_id INT REFERENCES sys_roles(id),
    preferred_lang VARCHAR(10) DEFAULT 'vi' REFERENCES sys_languages(code),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_sys_users_upd BEFORE UPDATE ON sys_users FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

INSERT INTO sys_users (id, username, email, password_hash, full_name, phone, role_id, preferred_lang) VALUES
(1, 'admin', 'admin@erpacc.vn', '$2a$10$wT0C2c2E1v6cE8Xg8A3A8uQ4P0O6N9M8L7K6J5H4G3F2E1D0C', 'Nguyễn Quản Trị', '0912345678', 1, 'vi'),
(2, 'sales1', 'sales@erpacc.vn', '$2a$10$wT0C2c2E1v6cE8Xg8A3A8uQ4P0O6N9M8L7K6J5H4G3F2E1D0C', 'John Sales', '0987654321', 2, 'en'),
(3, 'accountant1', 'accountant@erpacc.vn', '$2a$10$wT0C2c2E1v6cE8Xg8A3A8uQ4P0O6N9M8L7K6J5H4G3F2E1D0C', 'Trần Kế Toán', '0911223344', 3, 'vi');

CREATE TABLE sys_user_roles (
    user_id INT REFERENCES sys_users(id) ON DELETE CASCADE,
    role_id INT REFERENCES sys_roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

INSERT INTO sys_user_roles (user_id, role_id) VALUES (1, 1), (2, 2), (3, 3);

CREATE TABLE sys_audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES sys_users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    module VARCHAR(50) NOT NULL,
    record_id VARCHAR(100),
    details TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- 5. MASTER DATA: BRANDS, UOM, CATEGORIES
-- ------------------------------------------------------------
CREATE TABLE uom (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name_vi VARCHAR(50) NOT NULL,
    name_en VARCHAR(50) NOT NULL,
    description_vi TEXT,
    description_en TEXT,
    is_fractional BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO uom (id, code, name_vi, name_en, description_vi, description_en, is_fractional) VALUES
(1, 'CAI', 'Cái', 'Piece', 'Đơn vị tính từng cái', 'Individual piece unit', FALSE),
(2, 'HOP', 'Hộp', 'Box', 'Đơn vị hộp', 'Box packaging unit', FALSE),
(3, 'THUNG', 'Thùng', 'Carton', 'Đơn vị đóng thùng', 'Carton box unit', FALSE),
(4, 'KG', 'Kilogram', 'Kilogram', 'Khối lượng kg', 'Weight unit in kg', TRUE),
(5, 'MET', 'Mét', 'Meter', 'Chiều dài mét', 'Length unit in meters', TRUE),
(6, 'BO', 'Bộ', 'Set', 'Bộ sản phẩm hoàn chỉnh', 'Complete unit set', FALSE);

CREATE TABLE uom_conversions (
    id SERIAL PRIMARY KEY,
    from_uom_id INT REFERENCES uom(id) ON DELETE CASCADE,
    to_uom_id INT REFERENCES uom(id) ON DELETE CASCADE,
    conversion_factor NUMERIC(12, 4) NOT NULL CHECK (conversion_factor > 0),
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO uom_conversions (from_uom_id, to_uom_id, conversion_factor, note) VALUES
(3, 2, 12, '1 Thùng = 12 Hộp / 1 Carton = 12 Boxes'),
(2, 1, 10, '1 Hộp = 10 Cái / 1 Box = 10 Pieces');

CREATE TABLE brands (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name_vi VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    logo_url TEXT,
    description_vi TEXT,
    description_en TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO brands (id, code, name_vi, name_en, description_vi, description_en) VALUES
(1, 'DOUBLE-A', 'Double A', 'Double A', 'Thương hiệu giấy in cao cấp Thái Lan', 'Premium Thailand paper brand'),
(2, 'THIEN-LONG', 'Thiên Long', 'Thien Long Group', 'Tập đoàn văn phòng phẩm hàng đầu Việt Nam', 'Leading stationery group in Vietnam'),
(3, 'HP', 'Hewlett-Packard (HP)', 'Hewlett-Packard (HP)', 'Hãng sản xuất thiết bị & mực in Hoa Kỳ', 'US printing technology & hardware manufacturer'),
(4, 'CANON', 'Canon', 'Canon', 'Thương hiệu máy in & thiết bị văn phòng Nhật Bản', 'Japanese printer & office hardware manufacturer');

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name_vi VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    parent_id INT REFERENCES categories(id) ON DELETE SET NULL,
    description_vi TEXT,
    description_en TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO categories (id, code, name_vi, name_en, description_vi, description_en) VALUES
(1, 'TB-VANPHONG', 'Thiết bị Văn phòng', 'Office Equipment', 'Máy in, máy chiếu, laptop văn phòng', 'Printers, projectors, office laptops'),
(2, 'GIAY-IN', 'Giấy in & Giấy văn phòng', 'Printing & Copy Paper', 'Các loại giấy in A4, A3', 'A4, A3 printing and copy paper'),
(3, 'MUC-IN', 'Mực in & Phụ kiện', 'Toner & Ink Cartridges', 'Hộp mực máy in các loại', 'Printer toner and ink cartridges'),
(4, 'DUNG-CU-HOC-TAP', 'Dụng cụ Học tập & VP', 'Stationery Supplies', 'Bút bi, bìa hồ sơ, thước kẻ', 'Pens, file folders, rulers');

-- ------------------------------------------------------------
-- 6. PRODUCTS & VARIANTS
-- ------------------------------------------------------------
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    barcode VARCHAR(100),
    name_vi VARCHAR(200) NOT NULL,
    name_en VARCHAR(200) NOT NULL,
    category_id INT REFERENCES categories(id),
    brand_id INT REFERENCES brands(id),
    uom_id INT REFERENCES uom(id),
    cost_price NUMERIC(15, 2) DEFAULT 0 CHECK (cost_price >= 0),
    selling_price NUMERIC(15, 2) DEFAULT 0 CHECK (selling_price >= 0),
    web_price NUMERIC(15, 2) DEFAULT 0 CHECK (web_price >= 0),
    stock_quantity INT DEFAULT 0 CHECK (stock_quantity >= 0),
    min_stock INT DEFAULT 5 CHECK (min_stock >= 0),
    max_stock INT DEFAULT 1000 CHECK (max_stock >= min_stock),
    description_vi TEXT,
    description_en TEXT,
    image_url TEXT,
    is_published BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_products_upd BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

INSERT INTO products (id, sku, barcode, name_vi, name_en, category_id, brand_id, uom_id, cost_price, selling_price, web_price, stock_quantity, min_stock, description_vi, description_en, image_url, is_published) VALUES
(1, 'SP001', '8850360000012', 'Giấy In A4 Double A 70gsm', 'Double A A4 Paper 70gsm', 2, 1, 2, 65000, 85000, 82000, 150, 20, 'Giấy in nhập khẩu Thái Lan chất lượng cao', 'High quality imported A4 copy paper from Thailand', 'https://images.unsplash.com/photo-1586075010923-2dd4570fb338?auto=format&fit=crop&w=600&q=80', TRUE),
(2, 'SP002', '8935001234567', 'Bút Bi Thiên Long TL-027', 'Thien Long Ballpoint Pen TL-027', 4, 2, 1, 3000, 5000, 4800, 500, 50, 'Bút bi nét mực đều, mịn', 'Smooth writing ballpoint pen', 'https://images.unsplash.com/photo-1585336261026-6757f541a674?auto=format&fit=crop&w=600&q=80', TRUE),
(3, 'SP003', '8849620001234', 'Mực In HP LaserJet 12A', 'HP LaserJet Toner Cartridge 12A', 3, 3, 2, 350000, 480000, 450000, 42, 10, 'Hộp mực tương thích Canon 2900 & HP 1020', 'Compatible toner cartridge for Canon 2900 & HP 1020', 'https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?auto=format&fit=crop&w=600&q=80', TRUE),
(4, 'SP004', '8935009988771', 'Máy In Laser Canon LBP2900', 'Canon LBP2900 Laser Printer', 1, 4, 1, 3850000, 4500000, 4390000, 12, 3, 'Máy in laser trắng đen khổ A4 chính hãng', 'Genuine monochrome A4 laser printer', 'https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?auto=format&fit=crop&w=600&q=80', TRUE);

CREATE TABLE product_variants (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    sku VARCHAR(50) UNIQUE NOT NULL,
    variant_name_vi VARCHAR(100) NOT NULL,
    variant_name_en VARCHAR(100) NOT NULL,
    color VARCHAR(50),
    size VARCHAR(50),
    price_override NUMERIC(15, 2) CHECK (price_override >= 0),
    stock_quantity INT DEFAULT 0 CHECK (stock_quantity >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE product_images (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    display_order INT DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE
);

-- ------------------------------------------------------------
-- 7. CUSTOMERS, GROUPS & SUPPLIERS
-- ------------------------------------------------------------
CREATE TABLE customer_groups (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name_vi VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    discount_rate NUMERIC(5, 2) DEFAULT 0 CHECK (discount_rate >= 0 AND discount_rate <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO customer_groups (id, code, name_vi, name_en, discount_rate) VALUES
(1, 'VIP', 'Khách hàng VIP', 'VIP Enterprise Partner', 5.00),
(2, 'STANDARD', 'Khách hàng Thường', 'Standard Customer', 0.00);

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    group_id INT REFERENCES customer_groups(id),
    phone VARCHAR(20),
    email VARCHAR(100),
    address TEXT,
    tax_id VARCHAR(50),
    credit_limit NUMERIC(15, 2) DEFAULT 50000000 CHECK (credit_limit >= 0),
    current_debt NUMERIC(15, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_customers_upd BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

INSERT INTO customers (id, code, name, group_id, phone, email, address, tax_id) VALUES
(1, 'KH001', 'Công ty TNHH Giải pháp Công nghệ ABC', 1, '0243 999 888', 'contact@abc-tech.vn', 'Số 15 Lê Văn Lương, Cầu Giấy, Hà Nội', '0109887766'),
(2, 'KH002', 'Global Tech Solutions Corp', 2, '0283 555 444', 'info@globaltech.com', 'Suite 102, Innovation Tower, HCMC', '0301122334');

CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(100),
    address TEXT,
    tax_id VARCHAR(50),
    payment_terms VARCHAR(100) DEFAULT 'Thanh toán 30 ngày',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_suppliers_upd BEFORE UPDATE ON suppliers FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

INSERT INTO suppliers (id, code, name, phone, email, address, tax_id) VALUES
(1, 'NCC001', 'Tổng Công Ty Giấy & Bao Bì Việt Nam', '0243 888 777', 'sales@vnpaper.vn', 'KCN Phố Nối A, Hưng Yên', '0100123987'),
(2, 'NCC002', 'Thien Long Group Joint Stock Company', '0283 777 666', 'cskh@thienlong.vn', 'Tan Tao Industrial Park, HCMC', '0300987123');

-- ------------------------------------------------------------
-- 8. PURCHASING & PROCUREMENT (MUA HÀNG)
-- ------------------------------------------------------------
CREATE TABLE purchase_requests (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    requester_id INT REFERENCES sys_users(id),
    request_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(30) DEFAULT 'Chờ duyệt',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE purchase_request_items (
    id SERIAL PRIMARY KEY,
    request_id INT REFERENCES purchase_requests(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    uom_id INT REFERENCES uom(id),
    quantity INT NOT NULL CHECK (quantity > 0),
    estimated_price NUMERIC(15, 2) DEFAULT 0 CHECK (estimated_price >= 0)
);

CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    supplier_id INT REFERENCES suppliers(id),
    order_date DATE DEFAULT CURRENT_DATE,
    expected_delivery_date DATE,
    total_amount NUMERIC(15, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(30) DEFAULT 'Mới tạo',
    payment_status VARCHAR(30) DEFAULT 'Chưa thanh toán',
    notes TEXT,
    created_by INT REFERENCES sys_users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO purchase_orders (id, code, supplier_id, order_date, total_amount, status, payment_status, notes) VALUES
(1, 'PO-2026-001', 1, '2026-07-01', 16250000, 'Đã nhận hàng', 'Đã thanh toán', 'Nhập bổ sung kho tháng 7');

CREATE TABLE purchase_order_items (
    id SERIAL PRIMARY KEY,
    order_id INT REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    uom_id INT REFERENCES uom(id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(15, 2) NOT NULL CHECK (unit_price >= 0),
    subtotal NUMERIC(15, 2) NOT NULL CHECK (subtotal >= 0)
);

INSERT INTO purchase_order_items (order_id, product_id, uom_id, quantity, unit_price, subtotal) VALUES
(1, 1, 2, 250, 65000, 16250000);

-- ------------------------------------------------------------
-- 9. QUOTATIONS & COMMERCIAL SALES ORDERS
-- ------------------------------------------------------------
CREATE TABLE quotations (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT REFERENCES customers(id),
    quote_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expiry_date DATE,
    total_amount NUMERIC(15, 2) DEFAULT 0 CHECK (total_amount >= 0),
    status VARCHAR(30) DEFAULT 'Nháp',
    notes TEXT,
    created_by INT REFERENCES sys_users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO quotations (id, code, customer_id, quote_date, expiry_date, total_amount, status, notes, created_by) VALUES
(1, 'BG-2026-001', 1, '2026-07-25', '2026-08-25', 12750000, 'Đã duyệt', 'Báo giá vật tư văn phòng Q3/2026', 1);

CREATE TABLE quotation_items (
    id SERIAL PRIMARY KEY,
    quotation_id INT REFERENCES quotations(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    uom_id INT REFERENCES uom(id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(15, 2) NOT NULL CHECK (unit_price >= 0),
    discount_amount NUMERIC(15, 2) DEFAULT 0 CHECK (discount_amount >= 0),
    subtotal NUMERIC(15, 2) NOT NULL CHECK (subtotal >= 0)
);

INSERT INTO quotation_items (quotation_id, product_id, uom_id, quantity, unit_price, discount_amount, subtotal) VALUES
(1, 1, 2, 100, 85000, 0, 8500000),
(1, 3, 2, 10, 425000, 0, 4250000);

CREATE TABLE sales_orders (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    quotation_id INT REFERENCES quotations(id),
    customer_id INT REFERENCES customers(id),
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_amount NUMERIC(15, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(30) DEFAULT 'Mới tạo',
    payment_status VARCHAR(30) DEFAULT 'Chưa thanh toán',
    shipping_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO sales_orders (id, code, quotation_id, customer_id, order_date, total_amount, status, payment_status, shipping_address) VALUES
(1, 'DH-2026-001', 1, 1, '2026-07-26', 12750000, 'Hoàn thành', 'Đã thanh toán', 'Số 15 Lê Văn Lương, Cầu Giấy, Hà Nội');

CREATE TABLE sales_order_items (
    id SERIAL PRIMARY KEY,
    sales_order_id INT REFERENCES sales_orders(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    uom_id INT REFERENCES uom(id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(15, 2) NOT NULL CHECK (unit_price >= 0),
    subtotal NUMERIC(15, 2) NOT NULL CHECK (subtotal >= 0)
);

INSERT INTO sales_order_items (sales_order_id, product_id, uom_id, quantity, unit_price, subtotal) VALUES
(1, 1, 2, 100, 85000, 8500000),
(1, 3, 2, 10, 425000, 4250000);

-- ------------------------------------------------------------
-- 10. INVENTORY MOVEMENTS & STOCK BALANCES
-- ------------------------------------------------------------
CREATE TABLE warehouses (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name_vi VARCHAR(100) NOT NULL,
    name_en VARCHAR(100) NOT NULL,
    address_vi TEXT,
    address_en TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO warehouses (id, code, name_vi, name_en, address_vi, address_en) VALUES
(1, 'KHO-CHINH', 'Kho Tổng Hà Nội', 'Hanoi Central Warehouse', 'Lô 5 Cụm Industrial Zone Từ Liêm, Hà Nội', 'Lot 5 Tu Liem Industrial Zone, Hanoi'),
(2, 'KHO-HCM', 'Kho Chi nhánh HCM', 'HCM Branch Warehouse', '120 Quốc Lộ 13, Bình Thạnh, TP.HCM', '120 Highway 13, Binh Thanh, HCMC');

CREATE TABLE warehouse_locations (
    id SERIAL PRIMARY KEY,
    warehouse_id INT REFERENCES warehouses(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    zone_name VARCHAR(50),
    aisle VARCHAR(20),
    shelf VARCHAR(20)
);

CREATE TABLE stock_balances (
    id SERIAL PRIMARY KEY,
    warehouse_id INT REFERENCES warehouses(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    quantity_on_hand INT NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    quantity_reserved INT NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_wh_product UNIQUE(warehouse_id, product_id)
);

CREATE TRIGGER trg_stock_balances_upd BEFORE UPDATE ON stock_balances FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

INSERT INTO stock_balances (warehouse_id, product_id, quantity_on_hand, quantity_reserved) VALUES
(1, 1, 150, 0),
(1, 2, 500, 0),
(1, 3, 42, 0),
(1, 4, 12, 0);

CREATE TABLE stock_movements (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    movement_type VARCHAR(30) NOT NULL, -- NHAP_KHO, XUAT_KHO, DIEU_CHUYEN
    warehouse_id INT REFERENCES warehouses(id),
    reference_type VARCHAR(50),
    reference_id INT,
    movement_date DATE DEFAULT CURRENT_DATE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO stock_movements (id, code, movement_type, warehouse_id, reference_type, reference_id, note) VALUES
(1, 'NK-2026-001', 'NHAP_KHO', 1, 'PURCHASE_ORDER', 1, 'Nhập kho lô hàng giấy Double A đầu tháng'),
(2, 'XK-2026-001', 'XUAT_KHO', 1, 'SALES_ORDER', 1, 'Xuất kho cho đơn hàng DH-2026-001');

CREATE TABLE stock_movement_items (
    id SERIAL PRIMARY KEY,
    movement_id INT REFERENCES stock_movements(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    uom_id INT REFERENCES uom(id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_cost NUMERIC(15, 2) DEFAULT 0 CHECK (unit_cost >= 0)
);

INSERT INTO stock_movement_items (movement_id, product_id, uom_id, quantity, unit_cost) VALUES
(1, 1, 2, 250, 65000),
(2, 1, 2, 100, 65000);

CREATE TABLE stocktaking_sessions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    warehouse_id INT REFERENCES warehouses(id),
    session_date DATE DEFAULT CURRENT_DATE,
    status VARCHAR(30) DEFAULT 'Đang tiến hành',
    notes TEXT,
    created_by INT REFERENCES sys_users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stocktaking_items (
    id SERIAL PRIMARY KEY,
    session_id INT REFERENCES stocktaking_sessions(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    book_quantity INT NOT NULL CHECK (book_quantity >= 0),
    physical_quantity INT NOT NULL CHECK (physical_quantity >= 0),
    difference INT GENERATED ALWAYS AS (physical_quantity - book_quantity) STORED,
    reason TEXT
);

-- ------------------------------------------------------------
-- 11. FINANCIAL ACCOUNTING (TT200), INVOICES & GENERAL LEDGER
-- ------------------------------------------------------------
CREATE TABLE chart_of_accounts (
    account_code VARCHAR(20) PRIMARY KEY,
    account_name_vi VARCHAR(150) NOT NULL,
    account_name_en VARCHAR(150) NOT NULL,
    account_type VARCHAR(50) NOT NULL, -- Tài sản, Nợ phải trả, Vốn CSH, Doanh thu, Chi phí
    parent_code VARCHAR(20) REFERENCES chart_of_accounts(account_code),
    is_active BOOLEAN DEFAULT TRUE
);

INSERT INTO chart_of_accounts (account_code, account_name_vi, account_name_en, account_type, parent_code) VALUES
('111', 'Tiền mặt', 'Cash on Hand', 'Tài sản', NULL),
('1111', 'Tiền Việt Nam', 'VND Cash', 'Tài sản', '111'),
('112', 'Tiền gửi Ngân hàng', 'Bank Deposits', 'Tài sản', NULL),
('1121', 'Tiền gửi Ngân hàng VND', 'VND Bank Deposits', 'Tài sản', '112'),
('131', 'Phải thu của khách hàng', 'Accounts Receivable', 'Tài sản', NULL),
('133', 'Thuế GTGT được khấu trừ', 'Deductible Input VAT', 'Tài sản', NULL),
('1331', 'Thuế GTGT được khấu trừ của HHDV', 'Input VAT on Goods & Services', 'Tài sản', '133'),
('156', 'Hàng hóa tồn kho', 'Merchandise Inventory', 'Tài sản', NULL),
('331', 'Phải trả cho người bán', 'Accounts Payable', 'Nợ phải trả', NULL),
('333', 'Thuế và các khoản phải nộp Nhà nước', 'Taxes Payable', 'Nợ phải trả', NULL),
('3331', 'Thuế GTGT phải nộp', 'Output VAT Payable', 'Nợ phải trả', '333'),
('33311', 'Thuế GTGT đầu ra', 'Output VAT', 'Nợ phải trả', '3331'),
('411', 'Vốn đầu tư của chủ sở hữu', 'Owner Equity', 'Vốn CSH', NULL),
('511', 'Doanh thu bán hàng và cung cấp dịch vụ', 'Sales & Service Revenue', 'Doanh thu', NULL),
('5111', 'Doanh thu bán hàng hóa', 'Merchandise Revenue', 'Doanh thu', '511'),
('632', 'Giá vốn hàng bán', 'Cost of Goods Sold', 'Chi phí', NULL),
('641', 'Chi phí bán hàng', 'Selling Expenses', 'Chi phí', NULL),
('642', 'Chi phí quản lý doanh nghiệp', 'General & Admin Expenses', 'Chi phí', NULL);

CREATE TABLE invoices (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    order_id INT REFERENCES sales_orders(id),
    customer_id INT REFERENCES customers(id),
    invoice_date DATE DEFAULT CURRENT_DATE,
    due_date DATE,
    subtotal NUMERIC(15, 2) NOT NULL CHECK (subtotal >= 0),
    tax_amount NUMERIC(15, 2) DEFAULT 0 CHECK (tax_amount >= 0),
    total_amount NUMERIC(15, 2) NOT NULL CHECK (total_amount >= 0),
    status VARCHAR(30) DEFAULT 'Đã phát hành',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO invoices (id, code, order_id, customer_id, invoice_date, subtotal, tax_amount, total_amount, status) VALUES
(1, 'HD-2026-001', 1, 1, '2026-07-26', 12750000, 1275000, 14025000, 'Đã phát hành');

CREATE TABLE receipts_payments (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    voucher_type VARCHAR(20) NOT NULL, -- THU, CHI
    partner_type VARCHAR(20), -- KHACH_HANG, NHA_CUNG_CAP, KHAC
    partner_id INT,
    amount NUMERIC(15, 2) NOT NULL CHECK (amount > 0),
    payment_method VARCHAR(50) DEFAULT 'Chuyển khoản',
    account_code VARCHAR(20) REFERENCES chart_of_accounts(account_code),
    description TEXT,
    voucher_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO receipts_payments (id, code, voucher_type, partner_type, partner_id, amount, payment_method, account_code, description) VALUES
(1, 'PT-2026-001', 'THU', 'KHACH_HANG', 1, 14025000, 'Chuyển khoản', '112', 'Thu tiền đơn hàng DH-2026-001 từ Công ty ABC');

CREATE TABLE journal_entries (
    id SERIAL PRIMARY KEY,
    entry_code VARCHAR(50) UNIQUE NOT NULL,
    entry_date DATE DEFAULT CURRENT_DATE,
    description_vi TEXT,
    description_en TEXT,
    reference_type VARCHAR(50),
    reference_id INT,
    is_posted BOOLEAN DEFAULT TRUE,
    created_by INT REFERENCES sys_users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO journal_entries (id, entry_code, entry_date, description_vi, description_en, reference_type, reference_id) VALUES
(1, 'PKT-2026-001', '2026-07-26', 'Hạch toán doanh thu đơn hàng HD-2026-001', 'Recognize revenue for Invoice HD-2026-001', 'INVOICE', 1);

CREATE TABLE journal_entry_lines (
    id SERIAL PRIMARY KEY,
    entry_id INT REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_code VARCHAR(20) REFERENCES chart_of_accounts(account_code),
    debit_amount NUMERIC(15, 2) DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount NUMERIC(15, 2) DEFAULT 0 CHECK (credit_amount >= 0),
    partner_id INT,
    note TEXT
);

INSERT INTO journal_entry_lines (entry_id, account_code, debit_amount, credit_amount, partner_id, note) VALUES
(1, '131', 14025000, 0, 1, 'Phải thu KH ABC'),
(1, '511', 0, 12750000, 1, 'Doanh thu bán hàng'),
(1, '3331', 0, 1275000, 1, 'Thuế GTGT đầu ra');

-- ------------------------------------------------------------
-- 12. WEBSHOP E-COMMERCE TABLES
-- ------------------------------------------------------------
CREATE TABLE web_customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_web_customers_upd BEFORE UPDATE ON web_customers FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

INSERT INTO web_customers (id, name, email, phone, password_hash) VALUES
(1, 'Nguyễn Văn Khách', 'khachhang@gmail.com', '0912000111', '$2a$10$wT0C2c2E1v6cE8Xg8A3A8uQ4P0O6N9M8L7K6J5H4G3F2E1D0C');

CREATE TABLE web_carts (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE,
    customer_id INT REFERENCES web_customers(id) ON DELETE CASCADE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER trg_web_carts_upd BEFORE UPDATE ON web_carts FOR EACH ROW EXECUTE FUNCTION fn_update_timestamp();

CREATE TABLE web_cart_items (
    id SERIAL PRIMARY KEY,
    cart_id INT REFERENCES web_carts(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price NUMERIC(15, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE web_promotions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(30) UNIQUE NOT NULL,
    title_vi VARCHAR(150) NOT NULL,
    title_en VARCHAR(150) NOT NULL,
    discount_percent INT NOT NULL CHECK (discount_percent >= 0 AND discount_percent <= 100),
    min_order_value NUMERIC(15, 2) DEFAULT 0 CHECK (min_order_value >= 0),
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO web_promotions (code, title_vi, title_en, discount_percent, min_order_value, start_date, end_date, is_active) VALUES
('WELCOME2026', 'Giảm 10% cho đơn hàng đầu tiên', '10% OFF on your first order', 10, 500000, '2026-01-01', '2026-12-31', TRUE),
('SUMMER15', 'Ưu đãi hè giảm 15% vật tư văn phòng', 'Summer Sale 15% OFF office supplies', 15, 1000000, '2026-06-01', '2026-08-31', TRUE);

CREATE TABLE web_orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INT REFERENCES web_customers(id) ON DELETE SET NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_email VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    shipping_address TEXT NOT NULL,
    payment_method VARCHAR(50) DEFAULT 'COD',
    payment_status VARCHAR(30) DEFAULT 'Chờ thanh toán',
    order_status VARCHAR(30) DEFAULT 'Chờ xác nhận',
    subtotal NUMERIC(15, 2) NOT NULL CHECK (subtotal >= 0),
    discount_amount NUMERIC(15, 2) DEFAULT 0 CHECK (discount_amount >= 0),
    shipping_fee NUMERIC(15, 2) DEFAULT 30000 CHECK (shipping_fee >= 0),
    total_amount NUMERIC(15, 2) NOT NULL CHECK (total_amount >= 0),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO web_orders (id, order_number, customer_id, customer_name, customer_email, customer_phone, shipping_address, payment_method, payment_status, order_status, subtotal, discount_amount, shipping_fee, total_amount) VALUES
(1, 'WEB-2026-8801', 1, 'Nguyễn Văn Khách', 'khachhang@gmail.com', '0912000111', '120 Phố Huế, Hai Bà Trưng, Hà Nội', 'COD', 'Chưa thanh toán', 'Đang giao hàng', 410000, 41000, 30000, 399000);

CREATE TABLE web_order_items (
    id SERIAL PRIMARY KEY,
    web_order_id INT REFERENCES web_orders(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id),
    product_name_vi VARCHAR(200) NOT NULL,
    product_name_en VARCHAR(200) NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(15, 2) NOT NULL CHECK (unit_price >= 0),
    subtotal NUMERIC(15, 2) NOT NULL CHECK (subtotal >= 0)
);

INSERT INTO web_order_items (web_order_id, product_id, product_name_vi, product_name_en, quantity, unit_price, subtotal) VALUES
(1, 1, 'Giấy In A4 Double A 70gsm', 'Double A A4 Paper 70gsm', 5, 82000, 410000);

CREATE TABLE web_product_reviews (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    customer_name VARCHAR(100) NOT NULL,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    is_approved BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- 13. INDEXES FOR HIGH-PERFORMANCE SEARCH & LOOKUPS
-- ------------------------------------------------------------
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_barcode ON products(barcode);
CREATE INDEX idx_products_cat ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand_id);
CREATE INDEX idx_products_published ON products(is_published);

CREATE INDEX idx_sales_orders_cust ON sales_orders(customer_id);
CREATE INDEX idx_sales_orders_status ON sales_orders(status);
CREATE INDEX idx_sales_orders_date ON sales_orders(order_date);

CREATE INDEX idx_purchase_orders_supp ON purchase_orders(supplier_id);
CREATE INDEX idx_purchase_orders_status ON purchase_orders(status);

CREATE INDEX idx_stock_movements_wh ON stock_movements(warehouse_id);
CREATE INDEX idx_stock_movements_type ON stock_movements(movement_type);

CREATE INDEX idx_invoices_cust ON invoices(customer_id);
CREATE INDEX idx_invoices_status ON invoices(status);

CREATE INDEX idx_web_orders_number ON web_orders(order_number);
CREATE INDEX idx_web_orders_cust ON web_orders(customer_id);
CREATE INDEX idx_web_orders_status ON web_orders(order_status);

CREATE INDEX idx_sys_translations_lang ON sys_translations(lang_code, translation_key);

-- ------------------------------------------------------------
-- 14. REPORTING & ANALYTICS VIEWS
-- ------------------------------------------------------------

-- View 1: Product Stock Summary & Valuation
CREATE VIEW vw_product_stock_summary AS
SELECT 
    p.id as product_id,
    p.sku,
    p.barcode,
    p.name_vi,
    p.name_en,
    c.name_vi as category_name_vi,
    c.name_en as category_name_en,
    b.name_vi as brand_name_vi,
    b.name_en as brand_name_en,
    u.name_vi as uom_name_vi,
    u.name_en as uom_name_en,
    p.cost_price,
    p.selling_price,
    p.web_price,
    p.stock_quantity,
    p.min_stock,
    (p.stock_quantity * p.cost_price) as inventory_value_cost,
    (p.stock_quantity * p.selling_price) as inventory_value_selling,
    (p.stock_quantity <= p.min_stock) as is_low_stock
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN brands b ON p.brand_id = b.id
LEFT JOIN uom u ON p.uom_id = u.id;

-- View 2: Customer Debt & Accounts Receivable Summary
CREATE VIEW vw_customer_debt_summary AS
SELECT 
    c.id as customer_id,
    c.code,
    c.name as customer_name,
    c.phone,
    c.email,
    c.credit_limit,
    COALESCE(SUM(i.total_amount), 0) as total_invoiced,
    COALESCE(SUM(rp.amount), 0) as total_paid,
    (COALESCE(SUM(i.total_amount), 0) - COALESCE(SUM(rp.amount), 0)) as remaining_debt,
    CASE 
        WHEN (COALESCE(SUM(i.total_amount), 0) - COALESCE(SUM(rp.amount), 0)) > c.credit_limit THEN 'Vượt hạn mức'
        WHEN (COALESCE(SUM(i.total_amount), 0) - COALESCE(SUM(rp.amount), 0)) > 0 THEN 'Có công nợ'
        ELSE 'Bình thường'
    END as debt_status
FROM customers c
LEFT JOIN invoices i ON c.id = i.customer_id AND i.status != 'Đã hủy'
LEFT JOIN receipts_payments rp ON c.id = rp.partner_id AND rp.partner_type = 'KHACH_HANG' AND rp.voucher_type = 'THU'
GROUP BY c.id, c.code, c.name, c.phone, c.email, c.credit_limit;

-- View 3: Supplier Payable Summary
CREATE VIEW vw_supplier_payable_summary AS
SELECT 
    s.id as supplier_id,
    s.code,
    s.name as supplier_name,
    s.phone,
    s.payment_terms,
    COALESCE(SUM(po.total_amount), 0) as total_purchased,
    COALESCE(SUM(rp.amount), 0) as total_paid_supplier,
    (COALESCE(SUM(po.total_amount), 0) - COALESCE(SUM(rp.amount), 0)) as remaining_payable
FROM suppliers s
LEFT JOIN purchase_orders po ON s.id = po.supplier_id AND po.status != 'Hủy'
LEFT JOIN receipts_payments rp ON s.id = rp.partner_id AND rp.partner_type = 'NHA_CUNG_CAP' AND rp.voucher_type = 'CHI'
GROUP BY s.id, s.code, s.name, s.phone, s.payment_terms;

-- View 4: Sales Performance Summary
CREATE VIEW vw_sales_performance AS
SELECT 
    DATE_TRUNC('month', so.order_date) as order_month,
    COUNT(so.id) as total_orders,
    COALESCE(SUM(so.total_amount), 0) as total_revenue,
    COALESCE(SUM(soi.quantity * p.cost_price), 0) as total_cost_of_goods,
    (COALESCE(SUM(so.total_amount), 0) - COALESCE(SUM(soi.quantity * p.cost_price), 0)) as estimated_gross_profit
FROM sales_orders so
JOIN sales_order_items soi ON so.id = soi.sales_order_id
JOIN products p ON soi.product_id = p.id
WHERE so.status != 'Hủy'
GROUP BY DATE_TRUNC('month', so.order_date);

-- View 5: VAT Tax Filing Summary
CREATE VIEW vw_vat_tax_filing AS
SELECT 
    DATE_TRUNC('month', i.invoice_date) as tax_period,
    COALESCE(SUM(i.subtotal), 0) as taxable_revenue,
    COALESCE(SUM(i.tax_amount), 0) as output_vat,
    COALESCE(SUM(po.total_amount * 0.10), 0) as input_vat_estimated,
    (COALESCE(SUM(i.tax_amount), 0) - COALESCE(SUM(po.total_amount * 0.10), 0)) as vat_net_payable
FROM invoices i
LEFT JOIN sales_orders so ON i.order_id = so.id
LEFT JOIN purchase_orders po ON DATE_TRUNC('month', po.order_date) = DATE_TRUNC('month', i.invoice_date) AND po.status != 'Hủy'
WHERE i.status != 'Đã hủy'
GROUP BY DATE_TRUNC('month', i.invoice_date);

-- View 6: Trial Balance Summary (TT200)
CREATE VIEW vw_trial_balance_tt200 AS
SELECT 
    coa.account_code,
    coa.account_name_vi,
    coa.account_name_en,
    coa.account_type,
    COALESCE(SUM(jel.debit_amount), 0) as total_debit,
    COALESCE(SUM(jel.credit_amount), 0) as total_credit,
    (COALESCE(SUM(jel.debit_amount), 0) - COALESCE(SUM(jel.credit_amount), 0)) as net_balance
FROM chart_of_accounts coa
LEFT JOIN journal_entry_lines jel ON coa.account_code = jel.account_code
GROUP BY coa.account_code, coa.account_name_vi, coa.account_name_en, coa.account_type;

-- ============================================================
-- END OF ENHANCED SQL SCHEMA SCRIPT
-- ============================================================
