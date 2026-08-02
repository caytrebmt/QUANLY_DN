Kế hoạch tái cấu trúc ERPACC Dựa trên khảo sát codebase (~54 file Python trong app/, monolith Flask + SQLAlchemy), dưới đây là kế hoạch tái cấu trúc chi tiết với ranh giới module và thứ tự thực hiện.
________________________________________
1. Hiện trạng và vấn đề cốt lõi
Cấu trúc hiện tại
app/
├── routes/      (26 blueprint — HTTP + orchestration nghiệp vụ)
├── services/    (15 module — logic rải rác, chưa đủ domain)
├── models/      (4 file active + 1 orphan)
├── templates/   (104 file Jinja2)
├── constants/, middleware/, filters.py
└── __init__.py  (856 dòng — factory + migration + seed menu)
Pain points ưu tiên cao
Mức	Vấn đề	File liên quan
P0	Orchestration nghiệp vụ nằm trong route	stock_in.py (~580 dòng), stock_out.py (~674 dòng)
P0	God file export	export_service.py (~1.041 dòng)
P0	Migration DDL chạy mỗi lần boot	__init__.py (_ensure_* × 6+)
P1	God file settings	settings.py (~872 dòng)
P1	Module chết / trùng lặp	models_settings.py, routes_settings.py, system.py, app/api/, shop_api.py
P1	Entry point không nhất quán	run.py (ERP+Shop) vs wsgi.py (ERP only)
P2	reports_service.py không được dùng	Logic duplicate trong reports.py
P2	Auth phân mảnh	system.User, master.ERPUser, WebCustomer
Chuỗi nghiệp vụ trọng yếu (cần tách trước)
StockIn/StockOut ConfirmInventoryServiceaccounting_helper.create_entryDebt recordVatRecord
Hiện tại bước A→E nằm trực tiếp trong confirm() / cancel() của route — đây là điểm coupling cao nhất.
________________________________________
2. Kiến trúc mục tiêu
Nguyên tắc thiết kế
1.	Domain-first, không microservice — vẫn monolith Flask, nhưng có ranh giới package rõ ràng.
2.	Routes mỏng — chỉ HTTP, validation form, render template; gọi domain service.
3.	Một chiều phụ thuộc — routes → domains → shared → core.
4.	Không đổi schema DB trong giai đoạn 1–3 (tránh rủi ro production).
5.	Strangler pattern — tách dần, giữ blueprint URL cũ, không big-bang rewrite.
Cấu trúc thư mục đề xuất
app/
├── core/                          # Hạ tầng Flask
│   ├── __init__.py                # create_app() — chỉ factory, không DDL
│   ├── database.py
│   ├── extensions.py              # cache, csrf, babel
│   ├── filters.py
│   └── bootstrap/                 # menu seed, startup tasks
│       ├── menus.py
│       └── migrations/            # Flask-Migrate / Alembic
│
├── shared/                        # Cross-cutting, không nghiệp vụ
│   ├── authz/                     # authz_service, decorators
│   ├── export/                    # ExcelExporter, PdfExporter, ExcelImporter
│   ├── print/                     # print_service
│   ├── formatting/                # format_currency, so_thanh_chu
│   └── constants/                 # statuses.py
│
├── domains/
│   ├── platform/                  # Auth, user, menu, notification, backup
│   │   ├── models.py              # system.User, Menu, SystemConfig...
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── settings.py        # tách nhỏ thành users, menus, backup
│   │   │   └── company.py
│   │   └── services/
│   │       ├── security_service.py
│   │       └── company_service.py
│   │
│   ├── master/                    # Danh mục
│   │   ├── models.py              # Product, Supplier, Customer, Warehouse...
│   │   ├── routes/
│   │   │   ├── products.py
│   │   │   ├── suppliers.py
│   │   │   ├── customers.py
│   │   │   ├── warehouses.py
│   │   │   ├── categories.py
│   │   │   └── units.py
│   │   └── services/
│   │       └── product_code_service.py
│   │
│   ├── inventory/                 # Kho & giao dịch kho
│   │   ├── models.py              # StockIn/Out, Inventory, OpeningStock
│   │   ├── routes/
│   │   │   ├── stock_in.py
│   │   │   ├── stock_out.py
│   │   │   ├── inventory.py
│   │   │   └── opening_stock.py
│   │   └── services/
│   │       ├── inventory_service.py
│   │       ├── stock_document_service.py   # ★ MỚI — confirm/cancel pipeline
│   │       └── unit_display.py
│   │
│   ├── accounting/                # Kế toán
│   │   ├── models.py              # JournalEntry, AccountChart
│   │   ├── routes/
│   │   │   └── accounting.py
│   │   └── services/
│   │       ├── accounting_helper.py
│   │       ├── account_mapping_service.py
│   │       ├── tt99_service.py
│   │       └── tt99_mapper.py
│   │
│   ├── finance/                   # Công nợ & VAT (tách khỏi accounting)
│   │   ├── models.py              # Debt, DebtPayment, VatRecord
│   │   ├── routes/
│   │   │   ├── debt.py
│   │   │   └── vat.py
│   │   └── services/
│   │       ├── debt_service.py            # ★ MỚI
│   │       └── vat_service.py             # ★ MỚI
│   │
│   ├── sales/                     # Bán hàng
│   │   ├── models.py              # Quotation
│   │   ├── routes/
│   │   │   ├── quotations.py
│   │   │   └── dashboard.py             # KPI doanh thu
│   │   └── services/
│   │       └── quotation_service.py       # ★ MỚI (tùy chọn)
│   │
│   ├── ecommerce/                 # TMĐT + Shop
│   │   ├── models.py              # WebCustomer, OnlineOrder, ProductListing...
│   │   ├── routes/
│   │   │   ├── ecommerce.py       # Admin TMĐT
│   │   │   ├── shop.py            # Customer-facing
│   │   │   └── shop_api.py        # Gộp API shop
│   │   ├── services/
│   │   │   └── ecommerce_sync_service.py
│   │   └── shop_app.py
│   │
│   └── reporting/                 # Báo cáo tổng hợp
│       ├── routes/
│       │   └── reports.py
│       └── services/
│           └── reports_service.py
│
├── api/                           # REST API ERP (gộp routes/api.py)
│   └── v1/
│       └── ...
│
└── templates/                     # Giữ cấu trúc hiện tại, alias theo domain
    ├── inventory/
    ├── accounting/
    └── ...
________________________________________
3. Ranh giới module chi tiết
3.1 Ma trận phụ thuộc cho phép
Module	Được import từ	Không được import
core	stdlib, Flask, SQLAlchemy	domains/*, shared/*
shared	core	domains/*
master	core, shared	inventory, accounting, finance
inventory	core, shared, master.models	ecommerce.routes
accounting	core, shared, master.models	inventory.routes
finance	core, shared, master.models, accounting.services	inventory.routes
sales	core, shared, master, inventory.services	—
ecommerce	core, shared, master, inventory.services	accounting.routes
reporting	Tất cả domains/*/models, domains/*/services	Không ghi DB trực tiếp
platform	core, shared	Nghiệp vụ domain khác
3.2 Public API của từng domain
Mỗi domain export qua domains/<name>/__init__.py:
# domains/inventory/__init__.py
from .services.stock_document_service import StockDocumentService
from .services.inventory_service import InventoryService
from .routes import register_blueprints
__all__ = ['StockDocumentService', 'InventoryService', 'register_blueprints']
Route chỉ gọi public API — không import model cross-domain trực tiếp (trừ reporting).
3.3 Phân chia StockDocumentService (module then chốt)
Đây là service mới, trích từ stock_in.confirm() / stock_out.confirm():
# domains/inventory/services/stock_document_service.py
class StockDocumentService:
    """Orchestrator cho confirm/cancel phiếu nhập/xuất."""
    @staticmethod
    def confirm_stock_in(doc_id: int, user_id: int) -> ConfirmResult:
        # 1. Validate trạng thái draft
        # 2. InventoryService.update_on_stock_in()
        # 3. AccountingService.post_stock_in_journal()  → gọi accounting_helper
        # 4. DebtService.create_supplier_debt()           → gọi finance
        # 5. VatService.record_input_vat()                → gọi finance
        # 6. Commit + return result
    @staticmethod
    def cancel_stock_in(doc_id: int, user_id: int) -> CancelResult:
        # Reverse theo thứ tự ngược
    @staticmethod
    def confirm_stock_out(...)  # tương tự
    @staticmethod
    def cancel_stock_out(...)
Route sau refactor (~30 dòng mỗi action):
@stock_in_bp.route('/<int:id>/confirm', methods=['POST'])
@require_permission('stock_in', 'confirm')
def confirm(id):
    result = StockDocumentService.confirm_stock_in(id, current_user.id)
    if result.ok:
        flash('Đã xác nhận phiếu nhập', 'success')
    else:
        flash(result.error, 'danger')
    return redirect(url_for('stock_in.detail', id=id))
3.4 Phân chia export_service.py
File mới	Nội dung trích
shared/export/excel_exporter.py	ExcelExporter, _auto_fit_columns
shared/export/pdf_exporter.py	PdfExporter
shared/export/excel_importer.py	ExcelImporter
shared/formatting/currency.py	format_currency, format_number, so_thanh_chu
shared/formatting/company_info.py	get_company_info() → chuyển sang platform/services/company_service.py
3.5 Phân chia settings.py
Blueprint mới	Chức năng	Ước tính dòng
settings_users.py	CRUD user, phân quyền	~200
settings_menus.py	Menu, role, override	~150
settings_system.py	SystemConfig, unit conversion	~150
settings_backup.py	Backup/restore DB	~200
settings_notifications.py	Thông báo	~100
Giữ settings_bp làm parent hoặc redirect URL cũ.
3.6 Gộp / xóa module chết
File	Hành động
app/models/models_settings.py	Xóa (orphan duplicate)
app/routes/routes_settings.py	Xóa
app/routes/system.py	Xóa hoặc merge vào platform/routes/settings_menus.py
app/api/__init__.py	Merge vào app/api/v1/ hoặc xóa nếu trùng routes/api.py
app/routes/shop_api.py	Register blueprint hoặc merge vào ecommerce/routes/shop_api.py
master.ERPUser	Audit usage trong auth.py → merge về system.User hoặc deprecate
________________________________________
4. Thứ tự thực hiện (6 phase)
Phase 0 — Chuẩn bị (1–2 ngày, rủi ro thấp)
Mục tiêu: Dọn nền, không đổi behavior.
#	Task	Output
0.1	Thêm dist/, build/, venv/ vào .gitignore nếu chưa có	Repo sạch
0.2	Xóa/ignore module orphan (models_settings.py, routes_settings.py, system.py) sau khi verify không import	−3 file
0.3	Tạo cấu trúc thư mục app/core/, app/shared/, app/domains/ (rỗng + __init__.py)	Skeleton
0.4	Viết docs/ARCHITECTURE.md ghi ranh giới module	Tài liệu
0.5	Thêm script smoke test thủ công (checklist login, tạo phiếu, confirm)	Baseline QA
Tiêu chí hoàn thành: App chạy bình thường, không regression.
________________________________________
Phase 1 — Tách core và shared (3–5 ngày)
Mục tiêu: Giảm __init__.py, tách export/formatting.
#	Task	File nguồn → đích
1.1	Tách create_app() logic khỏi DDL	__init__.py → core/__init__.py + core/bootstrap/
1.2	Move cache, csrf, babel setup	→ core/extensions.py
1.3	Tách export_service.py	→ shared/export/*, shared/formatting/*
1.4	Move authz_service, print_service	→ shared/authz/, shared/print/
1.5	Move constants/statuses.py	→ shared/constants/
1.6	Cập nhật import paths (grep + replace có kiểm soát)	Toàn bộ routes/services
Backward compat: Re-export từ path cũ trong 1 sprint:
# app/services/export_service.py  (deprecated shim)
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.pdf_exporter import PdfExporter
# ...
Tiêu chí: export_service.py < 50 dòng (shim only), __init__.py < 200 dòng.
________________________________________
Phase 2 — Tách domain inventory + StockDocumentService (5–7 ngày) ★ ROI cao nhất
Mục tiêu: Giải phóng god routes stock_in.py, stock_out.py.
#	Task	Chi tiết
2.1	Move models	transaction.py (StockIn/Out, Inventory, OpeningStock) → domains/inventory/models.py
2.2	Move services hiện có	inventory_service.py, unit_display.py
2.3	Tạo StockDocumentService	Trích logic từ confirm()/cancel() của stock_in + stock_out
2.4	Tạo DebtService.create_from_stock_in/out()	Trích phần tạo công nợ (hiện inline trong route)
2.5	Tạo VatService.record_from_stock_in/out()	Trích phần VAT
2.6	Refactor routes	stock_in.py, stock_out.py chỉ còn HTTP layer
2.7	Move routes còn lại	inventory.py, opening_stock.py
2.8	Test end-to-end	Confirm nhập → kiểm tra tồn kho, bút toán, công nợ, VAT
Thứ tự bên trong phase 2:
2.3 StockDocumentService (stock_in trước)
  → 2.4 DebtService
  → 2.5 VatService
  → 2.3b mở rộng cho stock_out
  → 2.6 refactor routes
Tiêu chí: stock_in.confirm() và stock_out.confirm() mỗi hàm < 15 dòng.
________________________________________
Phase 3 — Tách accounting + finance (3–4 ngày)
#	Task
3.1	Move JournalEntry, AccountChart → domains/accounting/models.py
3.2	Move accounting_helper, account_mapping_service, tt99_*
3.3	Move Debt, VatRecord → domains/finance/models.py
3.4	Refactor accounting_helper thành AccountingService với interface rõ (post_journal, reverse_journal)
3.5	Move routes accounting.py, debt.py, vat.py
3.6	StockDocumentService gọi qua interface, không import route
Lưu ý: finance phụ thuộc accounting.services (tạo bút toán khi thanh toán công nợ) — cho phép theo ma trận trên.
________________________________________
Phase 4 — Tách master, platform, sales (4–5 ngày)
#	Domain	Task
4.1	master	Move 6 route CRUD + master.py models + product_code_service
4.2	platform	Tách settings.py → 4–5 blueprint nhỏ; move auth.py, company.py
4.3	platform	Gộp system.User / ERPUser (nếu audit xong)
4.4	sales	Move quotations.py, dashboard.py
4.5	reporting	Kích hoạt reports_service.py, refactor reports.py dùng service
________________________________________
Phase 5 — Tách ecommerce + thống nhất entry point (3–4 ngày)
#	Task
5.1	Move ecommerce.py models/routes/services vào domains/ecommerce/
5.2	Gộp shop.py + shop_api.py, register blueprint đúng cách
5.3	shop_app.py import từ domains/ecommerce
5.4	Thống nhất prod entry: wsgi.py mount Shop qua DispatcherMiddleware (giống dev) hoặc tách deploy riêng — quyết định kiến trúc
5.5	Move middleware/shop_auth.py → domains/ecommerce/middleware/
________________________________________
Phase 6 — Migration framework + dọn dẹp (3–5 ngày)
#	Task
6.1	Cài Flask-Migrate, tạo migration baseline từ schema hiện tại
6.2	Chuyển tất cả _ensure_*() DDL trong __init__.py → Alembic revisions
6.3	Xóa deprecated shims (app/services/export_service.py cũ...)
6.4	Cập nhật README.md, Read.md với sơ đồ module mới
6.5	(Tùy chọn) Thêm lint rule import boundary (custom script hoặc import-linter)
________________________________________
5. Timeline tổng hợp
⚠️Mermaid Syntax Error
Tổng ước tính: 4–6 tuần (1 dev), có thể song song Phase 4.1 (master) với Phase 3 nếu 2 dev.
________________________________________
6. Quy tắc khi tách code (checklist mỗi PR)
•	 Không đổi URL blueprint (backward compatible)
•	 Không đổi tên bảng DB / cột
•	 Mỗi PR ≤ 500 dòng diff, 1 domain hoặc 1 service
•	 Giữ deprecated shim ít nhất 1 sprint
•	 Smoke test: login → tạo phiếu nhập → confirm → kiểm tra 4 bảng (inventory, journal, debt, vat)
•	 Ghi rõ trong PR: module nguồn → module đích
________________________________________
7. Rủi ro và giảm thiểu
Rủi ro	Mức	Giảm thiểu
Regression confirm/cancel	Cao	Phase 2 làm stock_in trước, test kỹ trước khi stock_out
Circular import models	Trung bình	Giữ lazy import trong relationship; dùng string reference SQLAlchemy
PyInstaller build break	Trung bình	Test build_exe.py sau Phase 1 và Phase 2
Prod schema drift	Cao	Phase 6 — không xóa _ensure_* cho đến khi migration baseline verified trên prod copy
Template path break	Thấp	Không move templates trong phase 1–3; chỉ đổi khi ổn định
________________________________________
8. Quick wins có thể làm ngay (trước Phase 1)
1.	Xóa 3 file orphan sau khi verify không import.
2.	Register hoặc xóa shop_api_bp.
3.	Thêm .gitignore cho dist/, build/.
4.	Tạo docs/ARCHITECTURE.md từ tài liệu này.
5.	Viết StockDocumentService skeleton (chưa wire) để team review interface trước.
________________________________________
Cấu trúc 8 domain (platform, master, inventory, accounting, finance, sales, ecommerce, reporting) + 2 lớp hạ tầng (core, shared) giữ monolith đơn giản nhưng có ranh giới rõ — phù hợp quy mô hiện tại (~70 file Python) và lộ trình mở rộng POS/TMĐT.

