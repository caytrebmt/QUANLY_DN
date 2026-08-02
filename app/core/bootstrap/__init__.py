from app.database import db
from sqlalchemy import inspect, text


def _normalize_legacy_status_values():
    inspector = inspect(db.engine)
    with db.engine.begin() as conn:
        if inspector.has_table('stock_ins'):
            conn.execute(text("""
                UPDATE stock_ins
                SET status = CASE
                    WHEN status IS NULL OR btrim(status) = '' THEN 'draft'
                    WHEN lower(status) IN ('draft', 'nháp', 'nhap moi') THEN 'draft'
                    WHEN lower(status) IN ('confirmed', 'xác nhận', 'xac nhan', 'đã xác nhận', 'da xac nhan', 'nhập', 'nhap') THEN 'confirmed'
                    WHEN lower(status) IN ('cancelled', 'cancel', 'đã hủy', 'da huy', 'hủy', 'huy') THEN 'cancelled'
                    ELSE lower(status)
                END
                WHERE status IS NULL OR status <> CASE
                    WHEN status IS NULL OR btrim(status) = '' THEN 'draft'
                    WHEN lower(status) IN ('draft', 'nháp', 'nhap moi') THEN 'draft'
                    WHEN lower(status) IN ('confirmed', 'xác nhận', 'xac nhan', 'đã xác nhận', 'da xac nhan', 'nhập', 'nhap') THEN 'confirmed'
                    WHEN lower(status) IN ('cancelled', 'cancel', 'đã hủy', 'da huy', 'hủy', 'huy') THEN 'cancelled'
                    ELSE lower(status)
                END
            """))
        if inspector.has_table('stock_outs'):
            conn.execute(text("""
                UPDATE stock_outs
                SET status = CASE
                    WHEN status IS NULL OR btrim(status) = '' THEN 'draft'
                    WHEN lower(status) IN ('draft', 'nháp', 'nhap moi') THEN 'draft'
                    WHEN lower(status) IN ('confirmed', 'xác nhận', 'xac nhan', 'đã xác nhận', 'da xac nhan', 'xuất', 'xuat') THEN 'confirmed'
                    WHEN lower(status) IN ('cancelled', 'cancel', 'đã hủy', 'da huy', 'hủy', 'huy') THEN 'cancelled'
                    ELSE lower(status)
                END
                WHERE status IS NULL OR status <> CASE
                    WHEN status IS NULL OR btrim(status) = '' THEN 'draft'
                    WHEN lower(status) IN ('draft', 'nháp', 'nhap moi') THEN 'draft'
                    WHEN lower(status) IN ('confirmed', 'xác nhận', 'xac nhan', 'đã xác nhận', 'da xac nhan', 'xuất', 'xuat') THEN 'confirmed'
                    WHEN lower(status) IN ('cancelled', 'cancel', 'đã hủy', 'da huy', 'hủy', 'huy') THEN 'cancelled'
                    ELSE lower(status)
                END
            """))
        if inspector.has_table('debts'):
            conn.execute(text("""
                UPDATE debts
                SET status = CASE
                    WHEN status IS NULL OR btrim(status) = '' THEN 'open'
                    WHEN lower(status) IN ('open', 'phải thu', 'phai thu', 'phải trả', 'phai tra', 'mở', 'mo') THEN 'open'
                    WHEN lower(status) IN ('một phần', 'mot phan', 'partial') THEN 'partial'
                    WHEN lower(status) IN ('đã thanh toán', 'da thanh toan', 'paid') THEN 'paid'
                    WHEN lower(status) IN ('quá hạn', 'qua han', 'overdue') THEN 'overdue'
                    ELSE lower(status)
                END
                WHERE status IS NULL OR status <> CASE
                    WHEN status IS NULL OR btrim(status) = '' THEN 'open'
                    WHEN lower(status) IN ('open', 'phải thu', 'phai thu', 'phải trả', 'phai tra', 'mở', 'mo') THEN 'open'
                    WHEN lower(status) IN ('một phần', 'mot phan', 'partial') THEN 'partial'
                    WHEN lower(status) IN ('đã thanh toán', 'da thanh toan', 'paid') THEN 'paid'
                    WHEN lower(status) IN ('quá hạn', 'qua han', 'overdue') THEN 'overdue'
                    ELSE lower(status)
                END
            """))


def _ensure_user_permissions_table():
    inspector = inspect(db.engine)
    if inspector.has_table('user_permissions'):
        return
    with db.engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_permissions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                module VARCHAR(50) NOT NULL,
                can_view BOOLEAN DEFAULT FALSE,
                can_add BOOLEAN DEFAULT FALSE,
                can_edit BOOLEAN DEFAULT FALSE,
                can_delete BOOLEAN DEFAULT FALSE,
            CONSTRAINT uq_user_module UNIQUE (user_id, module)
            )
        """))


def _ensure_user_menu_overrides_table():
    inspector = inspect(db.engine)
    if inspector.has_table('user_menu_overrides'):
        return
    with db.engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_menu_overrides (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                menu_id INTEGER NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
                is_visible BOOLEAN NOT NULL,
                PRIMARY KEY (user_id, menu_id)
            )
        """))


def _ensure_unit_conversion_menu():
    from app.domains.platform.models import Menu, MenuRole
    inspector = inspect(db.engine)
    if not inspector.has_table('menus'):
        return

    code = 'SETTINGS_UNIT_CONVERSIONS'
    exists = Menu.query.filter_by(code=code).first()
    roles_needed = ['admin', 'accountant', 'warehouse']
    if exists:
        current = {r.role for r in exists.roles_rel}
        for role in roles_needed:
            if role not in current:
                db.session.add(MenuRole(menu_id=exists.id, role=role))
        exists.roles = ''
        db.session.commit()
        return

    parent = Menu.query.filter(
        Menu.module == 'settings',
        Menu.parent_id.is_(None)
    ).order_by(Menu.order_no).first()

    menu = Menu(
        code=code,
        name='Quy đổi đơn vị',
        parent_id=parent.id if parent else None,
        url='/settings/unit-conversions',
        icon='fas fa-ruler-combined',
        order_no=97,
        module='settings',
        roles='',
        is_active=True,
    )
    db.session.add(menu)
    db.session.flush()
    for role in roles_needed:
        db.session.add(MenuRole(menu_id=menu.id, role=role))
    db.session.commit()


def _ensure_tt99_sidebar_group():
    from app.domains.platform.models import Menu, MenuRole

    inspector = inspect(db.engine)
    if not inspector.has_table('menus'):
        return

    roles_needed = ['admin', 'accountant']

    def _ensure_roles(menu_obj):
        current = {r.role for r in menu_obj.roles_rel}
        for role in roles_needed:
            if role not in current:
                db.session.add(MenuRole(menu_id=menu_obj.id, role=role))
        menu_obj.roles = ''

    accounting_root = Menu.query.filter(
        Menu.module == 'accounting',
        Menu.parent_id.is_(None)
    ).order_by(Menu.order_no).first()
    if not accounting_root:
        return

    group_code = 'ACCOUNTING_TT99_GROUP'
    group = Menu.query.filter_by(code=group_code).first()
    if not group:
        group = Menu(
            code=group_code,
            name='Báo cáo',
            parent_id=accounting_root.id,
            url='/accounting/balance-sheet',
            icon='fas fa-file-invoice-dollar',
            order_no=65,
            module='accounting',
            roles='',
            is_active=True,
        )
        db.session.add(group)
        db.session.flush()
    else:
        group.name = 'Báo cáo'
        group.parent_id = accounting_root.id
        group.url = '/accounting/balance-sheet'
        group.icon = 'fas fa-file-invoice-dollar'
        group.order_no = 65
        group.module = 'accounting'
        group.is_active = True
    _ensure_roles(group)

    entries = [
        ('ACCOUNTING_TT99_INCOME_STATEMENT', 'Báo cáo KQKD', '/accounting/income-statement', 'fas fa-chart-line', 67),
        ('ACCOUNTING_TT99_GENERAL_LEDGER', 'Sổ cái (TK 156)', '/accounting/general-ledger/156', 'fas fa-book', 68),
        ('ACCOUNTING_TT99_DETAIL_LEDGER', 'Sổ chi tiết (TK 131)', '/accounting/detail-ledger/131', 'fas fa-list-alt', 69),
    ]
    for code, name, url, icon, order_no in entries:
        m = Menu.query.filter_by(code=code).first()
        if not m:
            m = Menu(
                code=code,
                name=name,
                parent_id=accounting_root.id,
                url=url,
                icon=icon,
                order_no=order_no,
                module='accounting',
                roles='',
                is_active=True,
            )
            db.session.add(m)
            db.session.flush()
        else:
            m.name = name
            m.parent_id = accounting_root.id
            m.url = url
            m.icon = icon
            m.order_no = order_no
            m.module = 'accounting'
            m.is_active = True
        _ensure_roles(m)

    legacy_bs_child = Menu.query.filter_by(code='ACCOUNTING_TT99_BALANCE_SHEET').first()
    if legacy_bs_child:
        legacy_bs_child.is_active = False

    db.session.commit()


def _ensure_quotations_module():
    from app.domains.platform.models import Menu, MenuRole

    inspector = inspect(db.engine)
    with db.engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quotations (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                date DATE NOT NULL,
                valid_until DATE NULL,
                customer_id INTEGER NULL REFERENCES customers(id),
                recipient_name VARCHAR(200) NULL,
                recipient_address VARCHAR(300) NULL,
                recipient_phone VARCHAR(50) NULL,
                recipient_email VARCHAR(120) NULL,
                subtotal NUMERIC(18,2) DEFAULT 0,
                discount_amount NUMERIC(18,2) DEFAULT 0,
                vat_amount NUMERIC(18,2) DEFAULT 0,
                total_amount NUMERIC(18,2) DEFAULT 0,
                vat_mode VARCHAR(20) DEFAULT 'grouped',
                vat_rate_grouped NUMERIC(5,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'draft',
                note TEXT NULL,
                terms TEXT NULL,
                stock_out_id INTEGER NULL REFERENCES stock_outs(id),
                created_by INTEGER NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        for col, ddl in [
            ('recipient_name', 'ALTER TABLE quotations ADD COLUMN recipient_name VARCHAR(200) NULL'),
            ('recipient_address', 'ALTER TABLE quotations ADD COLUMN recipient_address VARCHAR(300) NULL'),
            ('recipient_phone', 'ALTER TABLE quotations ADD COLUMN recipient_phone VARCHAR(50) NULL'),
            ('recipient_email', 'ALTER TABLE quotations ADD COLUMN recipient_email VARCHAR(120) NULL'),
        ]:
            if inspector.has_table('quotations') and col not in [c['name'] for c in inspector.get_columns('quotations')]:
                conn.execute(text(ddl))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quotation_items (
                id SERIAL PRIMARY KEY,
                quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
                product_id INTEGER NOT NULL REFERENCES products(id),
                unit_id INTEGER NULL REFERENCES units(id),
                conversion_factor NUMERIC(12,4) DEFAULT 1,
                quantity NUMERIC(18,3) NOT NULL,
                unit_price NUMERIC(18,2) NOT NULL,
                vat_rate NUMERIC(5,2) DEFAULT 10,
                vat_amount NUMERIC(18,2) DEFAULT 0,
                amount NUMERIC(18,2) DEFAULT 0,
                total_amount NUMERIC(18,2) DEFAULT 0,
                note VARCHAR(200) NULL
            )
        """))

    if not inspector.has_table('menus'):
        return

    sales_root = Menu.query.filter(
        Menu.module == 'stock_out',
        Menu.parent_id.is_(None)
    ).order_by(Menu.order_no).first()
    if not sales_root:
        sales_root = Menu.query.filter(
            Menu.name.ilike('%Bán hàng%'),
            Menu.parent_id.is_(None),
        ).order_by(Menu.order_no).first()

    menu = Menu.query.filter_by(code='SALES_QUOTATIONS').first()
    if not menu:
        menu = Menu(
            code='SALES_QUOTATIONS',
            name='Bảng báo giá',
            parent_id=sales_root.id if sales_root else None,
            url='/quotations',
            icon='fas fa-file-signature',
            order_no=54,
            module='quotations',
            roles='',
            is_active=True,
        )
        db.session.add(menu)
        db.session.flush()
    else:
        menu.name = 'Bảng báo giá'
        menu.parent_id = sales_root.id if sales_root else menu.parent_id
        menu.url = '/quotations'
        menu.icon = 'fas fa-file-signature'
        menu.order_no = 54
        menu.module = 'quotations'
        menu.is_active = True
        menu.roles = ''

    roles_needed = ['admin', 'accountant', 'warehouse']
    current = {r.role for r in menu.roles_rel}
    for role in roles_needed:
        if role not in current:
            db.session.add(MenuRole(menu_id=menu.id, role=role))
    db.session.commit()


def _ensure_ecommerce_module():
    from app.domains.platform.models import Menu, MenuRole

    with db.engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_accounts (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NULL REFERENCES customers(id),
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                name VARCHAR(200) NOT NULL,
                phone VARCHAR(50) NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_listings (
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL UNIQUE REFERENCES products(id),
                slug VARCHAR(220) UNIQUE NOT NULL,
                web_title VARCHAR(220) NULL,
                web_description TEXT NULL,
                web_price NUMERIC(18,2) NULL,
                compare_at_price NUMERIC(18,2) NULL,
                image_url VARCHAR(500) NULL,
                seo_title VARCHAR(220) NULL,
                seo_description VARCHAR(300) NULL,
                stock_cached NUMERIC(18,3) DEFAULT 0,
                stock_synced_at TIMESTAMP NULL,
                is_published BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_sessions (
                id SERIAL PRIMARY KEY,
                session_key VARCHAR(120) UNIQUE NOT NULL,
                customer_id INTEGER NULL REFERENCES customers(id),
                name VARCHAR(200) NULL,
                email VARCHAR(120) NULL,
                phone VARCHAR(50) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cart (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES customer_sessions(id),
                customer_id INTEGER NULL REFERENCES customers(id),
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id SERIAL PRIMARY KEY,
                cart_id INTEGER NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
                listing_id INTEGER NOT NULL REFERENCES product_listings(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                quantity NUMERIC(18,3) NOT NULL DEFAULT 1,
                unit_price NUMERIC(18,2) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS promotions (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT NULL,
                discount_type VARCHAR(20) DEFAULT 'percent',
                discount_value NUMERIC(18,2) DEFAULT 0,
                min_order_amount NUMERIC(18,2) DEFAULT 0,
                starts_at TIMESTAMP NULL,
                ends_at TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER NOT NULL REFERENCES product_listings(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                customer_id INTEGER NULL REFERENCES customers(id),
                customer_name VARCHAR(200) NULL,
                rating INTEGER NOT NULL DEFAULT 5,
                title VARCHAR(200) NULL,
                content TEXT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS online_orders (
                id SERIAL PRIMARY KEY,
                code VARCHAR(50) UNIQUE NOT NULL,
                session_id INTEGER NULL REFERENCES customer_sessions(id),
                customer_id INTEGER NULL REFERENCES customers(id),
                promotion_id INTEGER NULL REFERENCES promotions(id),
                customer_name VARCHAR(200) NOT NULL,
                customer_phone VARCHAR(50) NULL,
                customer_email VARCHAR(120) NULL,
                shipping_address VARCHAR(500) NULL,
                subtotal NUMERIC(18,2) DEFAULT 0,
                discount_amount NUMERIC(18,2) DEFAULT 0,
                shipping_fee NUMERIC(18,2) DEFAULT 0,
                vat_amount NUMERIC(18,2) DEFAULT 0,
                total_amount NUMERIC(18,2) DEFAULT 0,
                status VARCHAR(20) DEFAULT 'new',
                sync_status VARCHAR(20) DEFAULT 'pending',
                sync_error TEXT NULL,
                stock_out_id INTEGER NULL REFERENCES stock_outs(id),
                note TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS online_order_items (
                id SERIAL PRIMARY KEY,
                online_order_id INTEGER NOT NULL REFERENCES online_orders(id) ON DELETE CASCADE,
                listing_id INTEGER NULL REFERENCES product_listings(id),
                product_id INTEGER NOT NULL REFERENCES products(id),
                product_name_snapshot VARCHAR(250) NULL,
                quantity NUMERIC(18,3) NOT NULL,
                unit_price NUMERIC(18,2) NOT NULL,
                amount NUMERIC(18,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        for ddl in [
            "CREATE INDEX IF NOT EXISTS ix_product_listings_published ON product_listings(is_published)",
            "CREATE INDEX IF NOT EXISTS ix_online_orders_sync_status ON online_orders(sync_status)",
            "CREATE INDEX IF NOT EXISTS ix_online_orders_created_at ON online_orders(created_at)",
            "CREATE INDEX IF NOT EXISTS ix_cart_session_status ON cart(session_id, status)",
        ]:
            conn.execute(text(ddl))

    inspector = inspect(db.engine)
    if not inspector.has_table('menus'):
        return

    root = Menu.query.filter_by(code='ECOMMERCE_ROOT').first()
    if not root:
        root = Menu(
            code='ECOMMERCE_ROOT',
            name='E-commerce',
            parent_id=None,
            url=None,
            icon='fas fa-store',
            order_no=58,
            module='ecommerce',
            roles='',
            is_active=True,
        )
        db.session.add(root)
        db.session.flush()
    else:
        root.name = 'E-commerce'
        root.icon = 'fas fa-store'
        root.order_no = 58
        root.module = 'ecommerce'
        root.is_active = True
        root.roles = ''

    children = [
        ('ECOMMERCE_LISTINGS', 'Sản phẩm web', '/ecommerce/listings', 'fas fa-tags', 1),
        ('ECOMMERCE_ORDERS', 'Đơn online', '/ecommerce/orders', 'fas fa-receipt', 2),
    ]
    for code, name, url, icon, order_no in children:
        menu = Menu.query.filter_by(code=code).first()
        if not menu:
            menu = Menu(
                code=code,
                name=name,
                parent_id=root.id,
                url=url,
                icon=icon,
                order_no=order_no,
                module='ecommerce',
                roles='',
                is_active=True,
            )
            db.session.add(menu)
            db.session.flush()
        else:
            menu.name = name
            menu.parent_id = root.id
            menu.url = url
            menu.icon = icon
            menu.order_no = order_no
            menu.module = 'ecommerce'
            menu.is_active = True
            menu.roles = ''

        current = {r.role for r in menu.roles_rel}
        for role in ['admin', 'accountant', 'warehouse']:
            if role not in current:
                db.session.add(MenuRole(menu_id=menu.id, role=role))

    current = {r.role for r in root.roles_rel}
    for role in ['admin', 'accountant', 'warehouse']:
        if role not in current:
            db.session.add(MenuRole(menu_id=root.id, role=role))

    db.session.commit()


def _ensure_online_orders_status_columns():
    inspector = inspect(db.engine)
    if not inspector.has_table('online_orders'):
        return
    existing = {c['name'] for c in inspector.get_columns('online_orders')}
    with db.engine.begin() as conn:
        if 'erp_status' not in existing:
            conn.execute(text("""
                ALTER TABLE online_orders
                ADD COLUMN erp_status VARCHAR(20) NULL,
                ADD COLUMN erp_note TEXT NULL
            """))
            conn.execute(text("""
                COMMENT ON COLUMN online_orders.erp_status IS 'Trạng thái bản ghi xuất kho ERP'
            """))
            conn.execute(text("""
                COMMENT ON COLUMN online_orders.erp_note IS 'Ghi chú cập nhật từ ERP'
            """))


def _fix_menu_modules():
    from app.domains.platform.models import Menu
    inspector = inspect(db.engine)
    if not inspector.has_table('menus'):
        return

    module_fixes = {
        'WAREHOUSE': None,
        'PRODUCTS': 'products',
        'WAREHOUSES': 'inventory',
        'INVENTORY': 'inventory',
        'INVENTORY_HIST': 'inventory',
        'STOCKTAKING': 'inventory',
        'PURCHASE': None,
        'SUPPLIERS': 'suppliers',
        'STOCK_IN': 'stock_in',
        'SALES': None,
        'CUSTOMERS': 'customers',
        'STOCK_OUT': 'stock_out',
        'OPENING_STOCK': 'opening_stock',
    }

    updated = 0
    for code, new_module in module_fixes.items():
        menu = Menu.query.filter_by(code=code).first()
        if menu and menu.module != new_module:
            menu.module = new_module
            updated += 1

    if updated:
        db.session.commit()
        print(f"  [OK] Fixed {updated} menu modules")


def run_bootstrap(app):
    with app.app_context():
        try:
            from app.core import invalidate_nav_cache
            invalidate_nav_cache()
        except Exception:
            pass
        try:
            _normalize_legacy_status_values()
        except Exception:
            db.session.rollback()
            pass
        try:
            _ensure_user_permissions_table()
        except Exception:
            db.session.rollback()
            pass
        try:
            _ensure_user_menu_overrides_table()
        except Exception:
            db.session.rollback()
            pass
        try:
            _ensure_unit_conversion_menu()
        except Exception:
            db.session.rollback()
            pass
        try:
            _ensure_tt99_sidebar_group()
            invalidate_nav_cache()
        except Exception:
            db.session.rollback()
            pass
        try:
            _ensure_quotations_module()
            invalidate_nav_cache()
        except Exception:
            db.session.rollback()
            pass
        try:
            _ensure_ecommerce_module()
            invalidate_nav_cache()
        except Exception:
            db.session.rollback()
            pass
        try:
            ensure_account_mapping_configs()
        except Exception:
            db.session.rollback()
            pass
        try:
            _ensure_online_orders_status_columns()
        except Exception:
            db.session.rollback()
            pass
        try:
            _fix_menu_modules()
            invalidate_nav_cache()
        except Exception:
            db.session.rollback()
            pass
