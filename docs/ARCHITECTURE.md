# Kiến trúc ERPACC — Domain-Driven Monolith

Tài liệu này ghi ranh giới module, nguyên tắc phụ thuộc và lộ trình tái cấu trúc.

## Nguyên tắc thiết kế

1. **Domain-first, không microservice** — monolith Flask, ranh giới package rõ ràng.
2. **Routes mỏng** — chỉ HTTP, validation form, render template; gọi domain service.
3. **Một chiều phụ thuộc** — `routes → domains → shared → core`.
4. **Không đổi schema DB** trong giai đoạn 1–3.
5. **Strangler pattern** — tách dần, giữ blueprint URL cũ.

## Cấu trúc thư mục

```
app/
├── core/                    # Hạ tầng Flask
│   ├── __init__.py          # create_app() — chỉ factory, không DDL
│   ├── database.py
│   ├── extensions.py        # cache, csrf, babel, migrate (Flask-Migrate)
│   ├── filters.py
│   └── bootstrap/           # (không còn gọi DDL; đã chuyển sang Alembic)
│
├── migrations/                  # Flask-Migrate / Alembic (tại repo root)
│   ├── env.py
│   ├── script.py.mako
│   ├── alembic.ini
│   └── versions/              # baseline + các revision thay thế bootstrap DDL
│
├── shared/                  # Cross-cutting, không nghiệp vụ
│   ├── authz/               # authz_service, decorators
│   ├── export/              # ExcelExporter, PdfExporter, ExcelImporter
│   ├── print/               # print_service
│   ├── formatting/          # format_currency, so_thanh_chu
│   └── constants/           # statuses.py
│
├── domains/
│   ├── platform/            # Auth, user, menu, notification, backup
│   │   ├── models.py
│   │   ├── routes/          # auth, settings (users/menus/backup), company
│   │   └── services/        # security_service, company_service
│   │
│   ├── master/              # Danh mục
│   │   ├── models.py        # Product, Supplier, Customer, Warehouse...
│   │   ├── routes/          # products, suppliers, customers, warehouses, categories, units
│   │   └── services/        # product_code_service
│   │
│   ├── inventory/           # Kho & giao dịch kho
│   │   ├── models.py        # StockIn/Out, Inventory, OpeningStock
│   │   ├── routes/          # stock_in, stock_out, inventory, opening_stock
│   │   └── services/        # inventory_service, stock_document_service, unit_display
│   │
│   ├── accounting/          # Kế toán
│   │   ├── models.py        # JournalEntry, AccountChart
│   │   ├── routes/          # accounting
│   │   └── services/        # accounting_helper, account_mapping_service, tt99_*
│   │
│   ├── finance/             # Công nợ & VAT (tách khỏi accounting)
│   │   ├── models.py        # Debt, DebtPayment, VatRecord
│   │   ├── routes/          # debt, vat
│   │   └── services/        # debt_service, vat_service
│   │
│   ├── sales/               # Bán hàng
│   │   ├── models.py        # Quotation
│   │   ├── routes/          # quotations, dashboard
│   │   └── services/        # quotation_service
│   │
│   ├── ecommerce/           # TMĐT + Shop
│   │   ├── models.py        # WebCustomer, OnlineOrder, ProductListing...
│   │   ├── routes/          # ecommerce, shop, shop_api
│   │   ├── services/        # ecommerce_sync_service
│   │   ├── middleware/      # shop_auth
│   │   └── shop_app.py
│   │
│   └── reporting/           # Báo cáo tổng hợp
│       ├── routes/          # reports
│       └── services/        # reports_service
│
├── api/                     # REST API ERP
│   └── v1/
│
└── templates/               # Giữ cấu trúc hiện tại
```

## Ma trận phụ thuộc

| Module | Được import từ | Không được import |
|--------|---------------|-------------------|
| core | stdlib, Flask, SQLAlchemy | domains/*, shared/* |
| shared | core | domains/* |
| master | core, shared | inventory, accounting, finance routes |
| inventory | core, shared, master.models | ecommerce.routes |
| accounting | core, shared, master.models | inventory.routes |
| finance | core, shared, master.models, accounting.services | inventory.routes |
| sales | core, shared, master, inventory.services | — |
| ecommerce | core, shared, master, inventory.services | accounting.routes |
| reporting | domains/*/models, domains/*/services | không ghi DB trực tiếp |
| platform | core, shared | nghiệp vụ domain khác |

## Public API của domain

Mỗi domain export qua `domains/<name>/__init__.py`. Route chỉ gọi public API — không import model cross-domain trực tiếp (trừ reporting).

## Trạng thái thực hiện

| Phase | Nội dung | Trạng thái |
|-------|----------|-----------|
| 0 | Chuẩn bị — dọn orphans, tạo thư mục, tài liệu | Hoàn thành |
| 1 | Tách core/ và shared/ | Hoàn thành |
| 2 | Tách inventory + StockDocumentService | Hoàn thành |
| 3 | Tách accounting + finance | Hoàn thành |
| 4 | Tách master, platform, sales | Hoàn thành |
| 5 | Tách ecommerce + thống nhất entry point | Hoàn thành |
| 6 | Flask-Migrate + dọn dẹp shims | Hoàn thành |
