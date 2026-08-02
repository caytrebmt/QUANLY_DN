# -*- coding: utf-8 -*-
"""
ERPmini - Database Initialization & Seed Data
Run this file ONCE after setting up PostgreSQL:
    python init_db.py
"""
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.database import db
from app.models.system import User
from app.domains.platform.models import Menu, Notification, SystemConfig
from app.domains.master.models import Product, Supplier, Customer, Warehouse
from app.domains.inventory.models import (
    StockIn, StockOut, Inventory, InventoryHistory,
)
from app.models.transaction import (
    JournalEntry,
    JournalLine, Debt, DebtPayment, VatRecord,
)

app = create_app('development')

def init_database():
    with app.app_context():
        print("[..] Creating database tables...")
        db.create_all()
        print("[OK] Tables created successfully!\n")

        # ──────────────────────────────────────────
        # SYSTEM CONFIG
        # ──────────────────────────────────────────
        print("[**] Initializing system config...")
        configs = [
            ('company_name', 'Công ty TNHH ERPmini', 'Tên công ty', 'company'),
            ('company_address', '4367/3 Nguyễn Cửu Phú, Phường Tân Tạo, Tp.HCM', 'Địa chỉ công ty', 'company'),
            ('company_phone', '028-1234-5678', 'Số điện thoại', 'company'),
            ('company_fax', '028-1234-5679', 'Số fax', 'company'),
            ('company_email', 'info@erpmini.com', 'Email', 'company'),
            ('company_tax_code', '0312345678', 'Mã số thuế', 'company'),
            ('company_website', 'www.erpmini.com', 'Website', 'company'),
            ('default_vat_rate', '10', 'Thuế suất VAT mặc định (%)', 'accounting'),
            ('payment_terms_default', '30', 'Thời hạn TT mặc định (ngày)', 'accounting'),
            ('currency', 'VND', 'Đơn vị tiền tệ', 'accounting'),
            ('fiscal_year_start', '01-01', 'Bắt đầu năm tài chính (MM-DD)', 'accounting'),
            ('low_stock_alert', 'true', 'Cảnh báo hàng sắp hết', 'inventory'),
            ('auto_create_debt', 'true', 'Tự động tạo công nợ khi xác nhận phiếu', 'accounting'),
            ('auto_create_vat', 'true', 'Tự động tạo bản ghi VAT', 'accounting'),
        ]
        for key, val, desc, grp in configs:
            if not SystemConfig.query.filter_by(key=key).first():
                db.session.add(SystemConfig(key=key, value=val, description=desc, group_name=grp))
        db.session.commit()
        print(f"  [OK] {len(configs)} config entries\n")

        # ──────────────────────────────────────────
        # MENU DEFINITIONS (table-driven)
        # ──────────────────────────────────────────
        print("[**] Initializing menus...")
        menus_data = [
            # (code, name, parent_code, url, icon, order, module)
            ('DASHBOARD', 'Tổng quan', None, '/dashboard', 'fas fa-tachometer-alt', 1, 'dashboard'),
            # Hàng hóa & Kho
            ('WAREHOUSE', 'Kho hàng & Hàng hóa', None, None, 'fas fa-warehouse', 2, None),
            ('PRODUCTS', 'Hàng hóa', 'WAREHOUSE', '/products/', 'fas fa-box', 21, 'products'),
            ('WAREHOUSES', 'Danh mục kho', 'WAREHOUSE', '/warehouses/', 'fas fa-building', 22, 'inventory'),
            ('INVENTORY', 'Tồn kho (real-time)', 'WAREHOUSE', '/inventory/', 'fas fa-boxes', 23, 'inventory'),
            ('INVENTORY_HIST', 'Lịch sử biến động', 'WAREHOUSE', '/inventory/history', 'fas fa-history', 24, 'inventory'),
            ('STOCKTAKING', 'Kiểm kê hàng tồn', 'WAREHOUSE', '/inventory/stocktaking/', 'fas fa-clipboard-check', 26, 'inventory'),
            # Mua hàng
            ('PURCHASE', 'Mua hàng', None, None, 'fas fa-shopping-cart', 3, None),
            ('SUPPLIERS', 'Nhà cung cấp', 'PURCHASE', '/suppliers/', 'fas fa-truck', 31, 'suppliers'),
            ('STOCK_IN', 'Phiếu nhập kho', 'PURCHASE', '/stock-in/', 'fas fa-arrow-circle-down', 32, 'stock_in'),
            # Bán hàng
            ('SALES', 'Bán hàng', None, None, 'fas fa-store', 4, None),
            ('CUSTOMERS', 'Khách hàng', 'SALES', '/customers/', 'fas fa-users', 41, 'customers'),
            ('STOCK_OUT', 'Phiếu xuất kho', 'SALES', '/stock-out/', 'fas fa-arrow-circle-up', 42, 'stock_out'),
            # Kế toán
            ('ACCOUNTING', 'Kế toán', None, None, 'fas fa-calculator', 5, 'accounting'),
            ('DEBT', 'Công nợ phải thu', 'ACCOUNTING', '/debt/?partner_type=customer', 'fas fa-hand-holding-usd', 51, 'accounting'),
            ('DEBT_PAY', 'Công nợ phải trả', 'ACCOUNTING', '/debt/?partner_type=supplier', 'fas fa-file-invoice', 52, 'accounting'),
            ('DEBT_SUMMARY', 'Tổng hợp công nợ', 'ACCOUNTING', '/debt/summary', 'fas fa-table', 53, 'accounting'),
            ('VAT_OUT', 'VAT đầu ra', 'ACCOUNTING', '/vat/?vat_type=output', 'fas fa-percent', 54, 'accounting'),
            ('VAT_IN', 'VAT đầu vào', 'ACCOUNTING', '/vat/?vat_type=input', 'fas fa-receipt', 55, 'accounting'),
            ('JOURNAL', 'Nhật ký kế toán', 'ACCOUNTING', '/accounting/', 'fas fa-book', 56, 'accounting'),
            ('TRIAL_BAL', 'Cân đối số PS', 'ACCOUNTING', '/accounting/trial-balance', 'fas fa-balance-scale', 57, 'accounting'),
            ('ACCOUNTS', 'Hệ thống TK', 'ACCOUNTING', '/accounting/accounts', 'fas fa-sitemap', 58, 'accounting'),
            # Cài đặt
            ('SETTINGS', 'Cài đặt', None, None, 'fas fa-cogs', 9, 'settings'),
            ('SETTINGS_SYS', 'Cấu hình hệ thống', 'SETTINGS', '/settings/', 'fas fa-sliders-h', 91, 'settings'),
            ('SETTINGS_USERS', 'Quản lý users', 'SETTINGS', '/settings/users', 'fas fa-users-cog', 92, 'settings'),
            ('SETTINGS_MENU', 'Cấu hình menu', 'SETTINGS', '/settings/menus', 'fas fa-bars', 93, 'settings'),
            ('SETTINGS_NOTIF', 'Mẫu thông báo', 'SETTINGS', '/settings/notifications', 'fas fa-bell', 94, 'settings'),
            ('OPENING_STOCK', 'Tồn đầu kỳ', 'WAREHOUSE', '/opening-stock/', 'fas fa-box-open', 25, 'opening_stock'),
            ('UNITS', 'Đơn vị tính', 'SETTINGS', '/units/', 'fas fa-ruler', 95, 'settings'),
            ('CATEGORIES', 'Nhóm hàng hóa', 'SETTINGS', '/categories/', 'fas fa-tags', 96, 'settings'),
            ('COMPANY_INFO', 'Thông tin công ty', 'SETTINGS', '/company/', 'fas fa-building', 90, 'settings'),
            # Reports
            ('REPORTS', 'Báo cáo', None, None, 'fas fa-chart-bar', 6, 'reports'),
            ('RPT_MOVEMENT', 'Sổ nhập xuất tồn', 'REPORTS', '/reports/stock-movement', 'fas fa-exchange-alt', 61, 'reports'),
            ('RPT_REALTIME', 'Tồn kho realtime', 'REPORTS', '/reports/realtime-inventory', 'fas fa-satellite-dish', 62, 'reports'),
            ('RPT_CUSTOMER', 'DT theo khách hàng', 'REPORTS', '/reports/customer-revenue', 'fas fa-chart-line', 63, 'reports'),
            ('RPT_SUPPLIER', 'Nhập theo NCC', 'REPORTS', '/reports/supplier-purchase', 'fas fa-truck', 64, 'reports'),
        ]

        menu_map = {}
        for code, name, parent_code, url, icon, order, module in menus_data:
            if not Menu.query.filter_by(code=code).first():
                m = Menu(code=code, name=name, url=url, icon=icon,
                         order_no=order, module=module)
                if parent_code and parent_code in menu_map:
                    m.parent_id = menu_map[parent_code].id
                db.session.add(m)
                db.session.flush()
                menu_map[code] = m
            else:
                menu_map[code] = Menu.query.filter_by(code=code).first()

        db.session.commit()
        print(f"  [OK] {len(menus_data)} menu items\n")

        # ──────────────────────────────────────────
        # NOTIFICATION TEMPLATES (table-driven)
        # ──────────────────────────────────────────
        print("[**] Initializing notifications...")
        notif_data = [
            ('STOCK_IN_CREATED', 'Tạo phiếu nhập thành công', 'Phiếu nhập {code} đã được tạo thành công!', 'success', 'warehouse'),
            ('STOCK_IN_CONFIRMED', 'Xác nhận nhập kho', 'Phiếu nhập {code} đã được xác nhận. Tồn kho đã cập nhật.', 'success', 'warehouse'),
            ('STOCK_IN_CANCELLED', 'Hủy phiếu nhập', 'Phiếu nhập {code} đã bị hủy.', 'warning', 'warehouse'),
            ('STOCK_OUT_CREATED', 'Tạo phiếu xuất thành công', 'Phiếu xuất {code} đã được tạo!', 'success', 'warehouse'),
            ('STOCK_OUT_CONFIRMED', 'Xác nhận xuất kho', 'Phiếu xuất {code} đã xác nhận. Tồn kho đã cập nhật.', 'success', 'warehouse'),
            ('LOW_STOCK_ALERT', 'Cảnh báo hàng sắp hết', 'Hàng hóa {product_name} còn {quantity} {unit} - dưới mức tối thiểu!', 'warning', 'inventory'),
            ('DEBT_PAYMENT_SUCCESS', 'Thanh toán thành công', 'Đã ghi nhận thanh toán {amount} VND cho {partner_name}.', 'success', 'accounting'),
            ('DEBT_OVERDUE', 'Công nợ quá hạn', 'Công nợ của {partner_name} đã quá hạn {days} ngày! Số dư: {balance} VND.', 'error', 'accounting'),
            ('IMPORT_SUCCESS', 'Import dữ liệu thành công', 'Import thành công {count} bản ghi từ file Excel.', 'success', 'system'),
            ('IMPORT_ERROR', 'Lỗi import dữ liệu', 'Có {error_count} lỗi trong quá trình import. Vui lòng kiểm tra lại file.', 'warning', 'system'),
            ('LOGIN_SUCCESS', 'Đăng nhập thành công', 'Chào mừng {name} đã đăng nhập hệ thống ERPmini!', 'success', 'auth'),
            ('PRODUCT_CREATED', 'Thêm hàng hóa', 'Hàng hóa {code} - {name} đã được thêm vào hệ thống.', 'success', 'warehouse'),
            ('CUSTOMER_CREATED', 'Thêm khách hàng', 'Khách hàng {code} - {name} đã được thêm.', 'success', 'sales'),
            ('SUPPLIER_CREATED', 'Thêm nhà cung cấp', 'Nhà cung cấp {code} - {name} đã được thêm.', 'success', 'purchase'),
        ]
        for code, name, tmpl, ntype, module in notif_data:
            if not Notification.query.filter_by(code=code).first():
                db.session.add(Notification(code=code, name=name, message_template=tmpl,
                                             noti_type=ntype, module=module))
        db.session.commit()
        print(f"  [OK] {len(notif_data)} notifications\n")

        # ──────────────────────────────────────────
        # ADMIN USER
        # ──────────────────────────────────────────

        # ── UNITS (ĐVT) ────────────────────────────────────────
        print("[**] Creating units of measure...")
        from app.domains.master.models import Unit, Category
        for code, name in [('CAI','Cái'),('CHIEC','Chiếc'),('BO','Bộ'),('HOP','Hộp'),
                            ('GOI','Gói'),('THUNG','Thùng'),('KG','Kilogram'),('GRAM','Gram'),
                            ('LIT','Lít'),('MET','Mét'),('M2','Mét vuông'),('CUON','Cuộn'),
                            ('CHAI','Chai'),('LON','Lon'),('BICH','Bịch'),('TO','Tờ')]:
            if not Unit.query.filter_by(code=code).first():
                db.session.add(Unit(code=code, name=name))
        db.session.commit()
        print("  [OK] Units created\n")

        # ── CATEGORIES (Nhóm hàng) ─────────────────────────────
        print("[**] Creating product categories...")
        cats = [('DIEN_TU','Điện tử'),('LAPTOP','Laptop','DIEN_TU'),
                ('VAN_PHONG','Văn phòng phẩm'),('THUC_PHAM','Thực phẩm'),
                ('O_TO','Ô tô - Xe máy'),('NGUYEN_LIEU','Nguyên vật liệu'),
                ('HANG_TD','Hàng tiêu dùng')]
        cmap = {}
        for item in cats:
            code, name = item[0], item[1]
            parent_code = item[2] if len(item) > 2 else None
            if not Category.query.filter_by(code=code).first():
                c = Category(code=code, name=name,
                             parent_id=cmap.get(parent_code) if parent_code else None)
                db.session.add(c); db.session.flush(); cmap[code] = c.id
            else:
                cmap[code] = Category.query.filter_by(code=code).first().id
        db.session.commit()
        print("  [OK] Categories created\n")

        print("[**] Creating admin account...")
        import secrets
        admin_password = secrets.token_hex(8)
        accountant_password = secrets.token_hex(8)
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@erpmini.com',
                         full_name='Quản trị viên', role='admin')
            admin.set_password(admin_password)
            db.session.add(admin)
            accountant = User(username='ketoan', email='ketoan@erpmini.com',
                               full_name='Kế toán viên', role='accountant')
            accountant.set_password(accountant_password)
            db.session.add(accountant)
            db.session.commit()
            print(f"  [OK]  admin (password: {admin_password}) và ketoan (password: {accountant_password})")
            print("  [!!]  LƯU Ý: Lưu mật khẩu này và đổi ngay sau lần đăng nhập đầu tiên!")
        else:
            print("  [!!]   admin da ton tai")

        # ──────────────────────────────────────────
        # WAREHOUSES
        # ──────────────────────────────────────────
        print("[**] Creating sample warehouses...")
        warehouses_data = [
            ('KHO_HN', 'Kho Hà Nội', '15 Trần Hưng Đạo, Hoàn Kiếm, Hà Nội', 'Nguyễn Văn A', '024-1234-5678'),
            ('KHO_HCM', 'Kho TP.HCM', '200 Nguyễn Thị Minh Khai, Q3, TP.HCM', 'Trần Thị B', '028-9876-5432'),
            ('KHO_TP', 'Kho thành phẩm', 'Cùng địa chỉ nhà máy', 'Lê Văn C', ''),
        ]
        for code, name, address, manager, phone in warehouses_data:
            if not Warehouse.query.filter_by(code=code).first():
                db.session.add(Warehouse(code=code, name=name, address=address,
                                          manager=manager, phone=phone))
        db.session.commit()
        print(f"  [OK] {len(warehouses_data)} warehouses\n")

        # ──────────────────────────────────────────
        # CHART OF ACCOUNTS (Hệ thống tài khoản VN TT99/2025)
        # ──────────────────────────────────────────
        print("[**] Creating chart of accounts...")
        accounts_data = [
            # ================= LOẠI 1: TÀI SẢN NGẮN HẠN =================
            ('1', 'Tiền và các khoản tương đương tiền', 'asset', None, 1, 'debit'),
            ('11', 'Tiền mặt', 'asset', '1', 2, 'debit'),
            ('111', 'Tiền mặt', 'asset', '11', 3, 'debit'),          # TT99: Đổi từ "Tiền Việt Nam"
            ('112', 'Tiền gửi ngân hàng', 'asset', '11', 3, 'debit'),
            ('113', 'Tiền đang chuyển', 'asset', '11', 3, 'debit'),
            ('12', 'Đầu tư tài chính ngắn hạn', 'asset', '1', 2, 'debit'),
            ('121', 'Chứng khoán kinh doanh', 'asset', '12', 3, 'debit'),
            ('128', 'Đầu tư nắm giữ đến ngày đáo hạn', 'asset', '12', 3, 'debit'),
            ('1281', 'Tiền gửi có kỳ hạn', 'asset', '128', 4, 'debit'),
            ('13', 'Các khoản phải thu', 'asset', '1', 2, 'debit'),
            ('131', 'Phải thu khách hàng', 'asset', '13', 3, 'debit'),   # TT99: Chuẩn hóa tên
            ('1311', 'Phải thu khách hàng trong nước', 'asset', '131', 4, 'debit'),
            ('1312', 'Phải thu khách hàng nước ngoài', 'asset', '131', 4, 'debit'),
            ('133', 'Thuế GTGT được khấu trừ', 'asset', '13', 3, 'debit'),
            ('1331', 'Thuế GTGT được khấu trừ của hàng HH, DV', 'asset', '133', 4, 'debit'),
            ('1332', 'Thuế GTGT được khấu trừ của TSCĐ', 'asset', '133', 4, 'debit'),
            ('136', 'Phải thu nội bộ', 'asset', '13', 3, 'debit'),
            ('138', 'Phải thu khác', 'asset', '13', 3, 'debit'),
            ('14', 'Tạm ứng', 'asset', '1', 2, 'debit'),
            ('141', 'Tạm ứng', 'asset', '14', 3, 'debit'),
            ('15', 'Hàng tồn kho', 'asset', '1', 2, 'debit'),
            ('151', 'Hàng mua đang đi đường', 'asset', '15', 3, 'debit'),
            ('152', 'Nguyên liệu, vật liệu', 'asset', '15', 3, 'debit'),
            ('153', 'Công cụ, dụng cụ', 'asset', '15', 3, 'debit'),
            ('154', 'Chi phí sản xuất kinh doanh dở dang', 'asset', '15', 3, 'debit'),
            ('155', 'Sản phẩm', 'asset', '15', 3, 'debit'),            # TT99: Đổi từ "Thành phẩm"
            ('156', 'Hàng hóa', 'asset', '15', 3, 'debit'),
            ('1561', 'Giá mua hàng hóa', 'asset', '156', 4, 'debit'),
            ('1562', 'Chi phí thu mua hàng hóa', 'asset', '156', 4, 'debit'),
            ('157', 'Hàng gửi đi bán', 'asset', '15', 3, 'debit'),
            ('158', 'Hàng hóa kho bảo thuế', 'asset', '15', 3, 'debit'),
            ('16', 'Tài sản ngắn hạn khác', 'asset', '1', 2, 'debit'),
            ('161', 'Chi sự nghiệp', 'asset', '16', 3, 'debit'),

            # ================= LOẠI 2: TÀI SẢN DÀI HẠN =================
            ('2', 'Tài sản dài hạn', 'asset', None, 1, 'debit'),
            ('21', 'Tài sản cố định', 'asset', '2', 2, 'debit'),
            ('211', 'Tài sản cố định hữu hình', 'asset', '21', 3, 'debit'),
            ('212', 'Tài sản cố định thuê tài chính', 'asset', '21', 3, 'debit'),
            ('213', 'Tài sản cố định vô hình', 'asset', '21', 3, 'debit'),
            ('214', 'Hao mòn tài sản cố định', 'asset', '21', 3, 'credit'),
            ('22', 'Bất động sản đầu tư', 'asset', '2', 2, 'debit'),
            ('228', 'Đầu tư góp vốn vào đơn vị khác', 'asset', '22', 3, 'debit'),
            ('24', 'Xây dựng cơ bản dở dang', 'asset', '2', 2, 'debit'), # TT99: Sửa tên chuẩn

            # ================= LOẠI 3: NỢ PHẢI TRẢ =================
            ('3', 'Nợ phải trả', 'liability', None, 1, 'credit'),
            ('31', 'Nợ ngắn hạn', 'liability', '3', 2, 'credit'),
            ('311', 'Vay và nợ thuê tài chính ngắn hạn', 'liability', '31', 3, 'credit'),
            ('33', 'Phải trả', 'liability', '3', 2, 'credit'),
            ('331', 'Phải trả người bán', 'liability', '33', 3, 'credit'), # TT99: Chuẩn hóa tên
            ('3311', 'Phải trả người bán trong nước', 'liability', '331', 4, 'credit'),
            ('3312', 'Phải trả người bán nước ngoài', 'liability', '331', 4, 'credit'),
            ('333', 'Thuế và các khoản phải nộp nhà nước', 'liability', '33', 3, 'credit'),
            ('3331', 'Thuế GTGT phải nộp', 'liability', '333', 4, 'credit'),
            ('33311', 'Thuế GTGT đầu ra', 'liability', '3331', 5, 'credit'),
            ('33312', 'Thuế GTGT hàng nhập khẩu', 'liability', '3331', 5, 'credit'),
            ('3332', 'Thuế tiêu thụ đặc biệt', 'liability', '333', 4, 'credit'),
            ('3333', 'Thuế xuất khẩu, nhập khẩu', 'liability', '333', 4, 'credit'),
            ('3334', 'Thuế thu nhập doanh nghiệp', 'liability', '333', 4, 'credit'),
            ('3335', 'Thuế thu nhập cá nhân', 'liability', '333', 4, 'credit'),
            ('332', 'Phải trả cổ tức', 'liability', '33', 3, 'credit'),   # TT99: Bổ sung mới
            ('334', 'Phải trả người lao động', 'liability', '33', 3, 'credit'),
            ('335', 'Chi phí phải trả', 'liability', '33', 3, 'credit'),
            ('336', 'Phải trả nội bộ', 'liability', '33', 3, 'credit'),
            ('338', 'Phải trả, phải nộp khác', 'liability', '33', 3, 'credit'),
            ('341', 'Vay và nợ thuê tài chính dài hạn', 'liability', None, 3, 'credit'),
            ('343', 'Trái phiếu phát hành', 'liability', None, 3, 'credit'),

            # ================= LOẠI 4: VỐN CHỦ SỞ HỮU =================
            ('4', 'Vốn chủ sở hữu', 'equity', None, 1, 'credit'),
            ('41', 'Vốn chủ sở hữu', 'equity', '4', 2, 'credit'),
            ('411', 'Vốn đầu tư của chủ sở hữu', 'equity', '41', 3, 'credit'),
            ('412', 'Chênh lệch đánh giá lại tài sản', 'equity', '41', 3, 'credit'),
            ('413', 'Chênh lệch tỷ giá hối đoái', 'equity', '41', 3, 'credit'),
            ('414', 'Quỹ đầu tư phát triển', 'equity', '41', 3, 'credit'),
            ('417', 'Quỹ hỗ trợ sắp xếp doanh nghiệp', 'equity', '41', 3, 'credit'),
            ('418', 'Các quỹ khác thuộc vốn chủ sở hữu', 'equity', '41', 3, 'credit'),
            ('419', 'Cổ phiếu mua lại của chính mình', 'equity', '41', 3, 'debit'), # TT99: Đổi tên
            ('421', 'Lợi nhuận sau thuế chưa phân phối', 'equity', None, 3, 'credit'),
            ('4211', 'Lợi nhuận sau thuế năm trước', 'equity', '421', 4, 'credit'),
            ('4212', 'Lợi nhuận sau thuế năm nay', 'equity', '421', 4, 'credit'),

            # ================= LOẠI 5: DOANH THU =================
            ('5', 'Doanh thu', 'revenue', None, 1, 'credit'),
            ('51', 'Doanh thu bán hàng và cung cấp dịch vụ', 'revenue', '5', 2, 'credit'),
            ('511', 'Doanh thu bán hàng và cung cấp dịch vụ', 'revenue', '51', 3, 'credit'),
            ('5111', 'Doanh thu bán hàng hóa', 'revenue', '511', 4, 'credit'),
            ('5112', 'Doanh thu bán các thành phẩm', 'revenue', '511', 4, 'credit'),
            ('5113', 'Doanh thu cung cấp dịch vụ', 'revenue', '511', 4, 'credit'),
            ('5114', 'Doanh thu trợ cấp, trợ giá', 'revenue', '511', 4, 'credit'),
            ('512', 'Doanh thu bán hàng nội bộ', 'revenue', '51', 3, 'credit'),
            ('515', 'Doanh thu hoạt động tài chính', 'revenue', '51', 3, 'credit'),
            ('521', 'Các khoản giảm trừ doanh thu', 'revenue', None, 2, 'debit'),
            ('5211', 'Chiết khấu thương mại', 'revenue', '521', 3, 'debit'),
            ('5212', 'Hàng bán bị trả lại', 'revenue', '521', 3, 'debit'),
            ('5213', 'Giảm giá hàng bán', 'revenue', '521', 3, 'debit'),

            # ================= LOẠI 6: CHI PHÍ & GIÁ VỐN =================
            ('6', 'Chi phí', 'expense', None, 1, 'debit'),
            ('611', 'Mua hàng', 'expense', None, 2, 'debit'),
            ('62', 'Chi phí sản xuất', 'expense', '6', 2, 'debit'),
            ('621', 'Chi phí nguyên liệu, vật liệu trực tiếp', 'expense', '62', 3, 'debit'),
            ('622', 'Chi phí nhân công trực tiếp', 'expense', '62', 3, 'debit'),
            ('623', 'Chi phí sử dụng máy thi công', 'expense', '62', 3, 'debit'),
            ('627', 'Chi phí sản xuất chung', 'expense', '62', 3, 'debit'),
            ('63', 'Giá vốn hàng bán', 'cogs', '6', 2, 'debit'),
            ('632', 'Giá vốn hàng bán', 'cogs', '63', 3, 'debit'),
            ('635', 'Chi phí tài chính', 'expense', '63', 3, 'debit'),
            ('641', 'Chi phí bán hàng', 'expense', None, 2, 'debit'),
            ('642', 'Chi phí quản lý doanh nghiệp', 'expense', None, 2, 'debit'),

            # ================= LOẠI 7 & 8: KHÁC =================
            ('7', 'Thu nhập khác', 'other_income', None, 1, 'credit'),
            ('711', 'Thu nhập khác', 'other_income', '7', 2, 'credit'),
            ('8', 'Chi phí khác', 'other_expense', None, 1, 'debit'),
            ('811', 'Chi phí khác', 'other_expense', '8', 2, 'debit'),
            ('821', 'Chi phí thuế thu nhập doanh nghiệp', 'other_expense', None, 2, 'debit'), # TT99: Chuẩn hóa tên
            ('82112', 'Chi phí thuế TNDN bổ sung (Pillar 2)', 'other_expense', None, 3, 'debit'), # TT99: Mới

            # ================= LOẠI 9: XÁC ĐỊNH KẾT QUẢ =================
            ('9', 'Xác định kết quả kinh doanh', 'closing', None, 1, 'credit'),
            ('911', 'Xác định kết quả kinh doanh', 'closing', '9', 2, 'credit'),
        ]

        acc_map = {}
        for code, name, atype, parent_code, level, normal_bal in accounts_data:
            if not AccountChart.query.filter_by(code=code).first():
                acc = AccountChart(
                    code=code, name=name, account_type=atype,
                    level=level, normal_balance=normal_bal,
                    is_detail=(level >= 2),
                )
                if parent_code and parent_code in acc_map:
                    acc.parent_id = acc_map[parent_code].id
                db.session.add(acc)
                db.session.flush()
                acc_map[code] = acc
            else:
                acc_map[code] = AccountChart.query.filter_by(code=code).first()
        db.session.commit()
        print(f"  [OK] {len(accounts_data)} accounts\n")

        # ──────────────────────────────────────────
        # SAMPLE PRODUCTS
        # ──────────────────────────────────────────
        print("[**] Creating sample products...")
        products_data = [
            ('SP001', 'Laptop Dell Inspiron 15', 'Cái', 'Điện tử', 15000000, 18000000, 10),
            ('SP002', 'Chuột không dây Logitech M235', 'Cái', 'Điện tử', 250000, 350000, 10),
            ('SP003', 'Bàn phím cơ Keychron K2', 'Cái', 'Điện tử', 1200000, 1600000, 10),
            ('SP004', 'Màn hình Samsung 24"', 'Cái', 'Điện tử', 3500000, 4500000, 10),
            ('SP005', 'Tai nghe Sony WH-1000XM4', 'Cái', 'Điện tử', 4500000, 5800000, 10),
            ('VT001', 'Giấy A4 (1 ream 500 tờ)', 'Ream', 'Văn phòng phẩm', 45000, 65000, 10),
            ('VT002', 'Bút bi Thiên Long (hộp 20 cái)', 'Hộp', 'Văn phòng phẩm', 25000, 40000, 10),
            ('VT003', 'Mực in HP 85A', 'Hộp', 'Văn phòng phẩm', 350000, 480000, 10),
            ('HH001', 'Dầu nhớt Shell Helix 5W-40 (4L)', 'Thùng', 'Ô tô', 280000, 380000, 8),
            ('HH002', 'Lốp xe Michelin 205/55R16', 'Cái', 'Ô tô', 1800000, 2300000, 10),
        ]
        for code, name, unit, cat, buy, sell, vat in products_data:
            if not Product.query.filter_by(code=code).first():
                db.session.add(Product(
                    code=code, name=name, unit=unit, category=cat,
                    purchase_price=buy, sale_price=sell, vat_rate=vat,
                    min_stock=5
                ))
        db.session.commit()
        print(f"  [OK] {len(products_data)} products\n")

        # ──────────────────────────────────────────
        # SAMPLE SUPPLIERS
        # ──────────────────────────────────────────
        print("[**] Creating sample suppliers...")
        suppliers_data = [
            ('NCC001', 'Công ty CP Phân phối FPT', '261 Cầu Giấy, Hà Nội', '024-7300-7300', 'fpt@example.com', '0101234567'),
            ('NCC002', 'Công ty TNHH Samsung Vina', 'Khu CN Yên Phong, Bắc Ninh', '0222-1234-567', 'samsung@example.com', '2300123456'),
            ('NCC003', 'Cty CP Văn phòng phẩm Thiên Long', '43 Đốc Ngữ, Q5, TP.HCM', '028-3835-3835', 'thienlongvpp@example.com', '0302345678'),
            ('NCC004', 'Công ty TNHH Shell Việt Nam', '47 Đinh Tiên Hoàng, Q1, TP.HCM', '028-3521-3456', 'shell@example.com', '0304567890'),
        ]
        for code, name, address, phone, email, tax in suppliers_data:
            if not Supplier.query.filter_by(code=code).first():
                db.session.add(Supplier(code=code, name=name, address=address,
                                         phone=phone, email=email, tax_code=tax,
                                         payment_terms=30))
        db.session.commit()
        print(f"  [OK] {len(suppliers_data)} suppliers\n")

        # ──────────────────────────────────────────
        # SAMPLE CUSTOMERS
        # ──────────────────────────────────────────
        print("[**] Creating sample customers...")
        customers_data = [
            ('KH001', 'Công ty CP Công nghệ ABC', 'wholesale', '10 Láng Hạ, Đống Đa, HN', '024-1234-5678', 'abc@example.com', '0100987654'),
            ('KH002', 'Công ty TNHH XYZ Trading', 'wholesale', '55 Lê Đại Hành, Q11, HCM', '028-3456-7890', 'xyz@example.com', '0312345678'),
            ('KH003', 'Đại lý Điện tử Minh Phát', 'agent', '123 Hùng Vương, Q5, HCM', '028-3837-1234', 'minhphat@example.com', '0309876543'),
            ('KH004', 'Siêu thị Điện máy Xanh', 'retail', '25 Phan Đình Phùng, HN', '024-3556-7890', 'dienmayx@example.com', '0100234567'),
            ('KH005', 'Cty TNHH Tư vấn IT DEF', 'wholesale', '88 Bạch Đằng, Đà Nẵng', '0236-1234-567', 'def@example.com', '0401234567'),
        ]
        for code, name, ctype, addr, phone, email, tax in customers_data:
            if not Customer.query.filter_by(code=code).first():
                db.session.add(Customer(code=code, name=name, customer_type=ctype,
                                         address=addr, phone=phone, email=email,
                                         tax_code=tax, credit_limit=100000000,
                                         payment_terms=30))
        db.session.commit()
        print(f"  [OK] {len(customers_data)} customers\n")

        print("=" * 50)
        print("[OK]  KHOI TAO CO SO DU LIEU HOAN TAT!")
        print("=" * 50)
        print("\n[**]  Tai khoan dang nhap:")
        print(f"   Admin  : admin / {admin_password}")
        print(f"   Accountant: ketoan / {accountant_password}")
        print("\n[**]  Chay ung dung:")
        print("   python run.py")
        print("   Open browser: http://localhost:5000")
        print()


if __name__ == '__main__':
    init_database()
