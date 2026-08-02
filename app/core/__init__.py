from app.core.extensions import cache, csrf, migrate, jwt
from app.database import db, login_manager
from app.filters import register_filters
from config.settings import config
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, flash, request, session, redirect, url_for
from sqlalchemy import inspect, text
from flask_babel import Babel
from flask_login import current_user, logout_user
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import RequestEntityTooLarge


def _resource_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _runtime_data_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def invalidate_nav_cache(role: str | None = None) -> None:
    cache.clear()


_VI_MAP: dict[str, str] = {
    'Edit': 'Sửa',
    'Confirm': 'Xác nhận',
    'Cancel': 'Hủy',
    'Print PDF': 'In PDF',
    'Back': 'Quay lại',
    'Status': 'Trạng thái',
    'Code': 'Số phiếu',
    'Date': 'Ngày',
    'Warehouse': 'Kho',
    'Supplier': 'Nhà cung cấp',
    'Customer': 'Khách hàng',
    'Customer tax code': 'MST Khách hàng',
    'Invoice no.': 'Số HĐ',
    'Supplier invoice no.': 'Số HĐ NCC',
    'Subtotal': 'Tiền hàng',
    'Total': 'Tổng cộng',
    'VAT': 'Thuế VAT',
    'Actions': 'Thao tác',
    'Export Excel': 'Xuất Excel',
    'Create': 'Tạo phiếu',
    'Stock-in list': 'Danh sách phiếu nhập',
    'Stock-out list': 'Danh sách phiếu xuất',
    'Stock-in detail': 'Chi tiết phiếu nhập kho',
    'Stock-out detail': 'Chi tiết phiếu xuất kho',
    'Filter code or invoice': 'Số phiếu, số HĐ...',
    'All suppliers': '-- Tất cả NCC --',
    'All customers': '-- Tất cả KH --',
    'All status': '-- Tất cả TT --',
    'From date': 'Từ ngày',
    'To date': 'Đến ngày',
    'Draft': 'Bản nháp',
    'Confirmed': 'Đã xác nhận',
    'Cancelled': 'Đã hủy',
    'Source': 'Nguồn',
}


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    resource_base = _resource_base_dir()
    runtime_data_dir = _runtime_data_dir()
    app_root = resource_base / 'app'
    template_dir = app_root / 'templates'
    static_dir = app_root / 'static'
    translations_dir = resource_base / 'translations'

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
        root_path=str(app_root),
    )
    app.config.from_object(config.get(config_name, config['default']))
    app.config.setdefault('BABEL_TRANSLATION_DIRECTORIES', str(translations_dir))

    upload_folder = Path(app.config.get('UPLOAD_FOLDER', 'app/static/uploads'))
    if not upload_folder.is_absolute():
        upload_folder = runtime_data_dir / upload_folder
    app.config['UPLOAD_FOLDER'] = str(upload_folder)

    if app.config.get('USE_PROXY_FIX'):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get('PROXY_FIX_X_FOR', 1),
            x_proto=app.config.get('PROXY_FIX_X_PROTO', 1),
            x_host=app.config.get('PROXY_FIX_X_HOST', 1),
        )

    logging.getLogger("fontTools").setLevel(logging.WARNING)
    logging.getLogger("weasyprint").setLevel(logging.WARNING)

    db.init_app(app)
    migrate.init_app(app, db)

    try:
        from sqlalchemy import text
        with app.app_context():
            db.session.execute(text("""
                ALTER TABLE online_orders 
                ADD COLUMN IF NOT EXISTS tracking_token VARCHAR(64) NULL
            """))
            db.session.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS ix_online_orders_tracking_token 
                ON online_orders (tracking_token)
            """))
            db.session.commit()
    except Exception as e:
        if db.session.is_active:
            db.session.rollback()
        app.logger.warning(f"Tracking token migration skipped/failed: {e}")

    login_manager.init_app(app)
    login_manager.session_protection = app.config.get('SESSION_PROTECTION', 'strong')

    # Tự động xóa cache menu/phân quyền khi các bảng liên quan thay đổi,
    # tránh quên gọi invalidate_nav_cache thủ công ở từng route.
    from sqlalchemy import event as _sa_event
    from app.domains.platform.models import Menu, UserMenuOverride
    from app.models.system import User, UserPermission
    _NAV_MODELS = {Menu, UserMenuOverride, User, UserPermission}

    @_sa_event.listens_for(db.session, 'after_commit')
    def _invalidate_nav_on_commit(session):
        for obj in session.new | session.dirty | session.deleted:
            if obj.__class__ in _NAV_MODELS:
                invalidate_nav_cache()
                break

    cache_config = {'CACHE_TYPE': app.config.get('CACHE_TYPE', 'SimpleCache'),
                    'CACHE_DEFAULT_TIMEOUT': 300}
    redis_url = app.config.get('REDIS_URL') or app.config.get('CACHE_REDIS_URL')
    if redis_url:
        cache_config['CACHE_TYPE'] = 'RedisCache'
        cache_config['CACHE_REDIS_URL'] = redis_url
    cache.init_app(app, config=cache_config)
    csrf.init_app(app)
    jwt.init_app(app)

    @jwt.user_identity_loader
    def _shop_jwt_identity(user):
        if hasattr(user, 'id'):
            return str(user.id)
        return str(user)

    @jwt.user_lookup_loader
    def _shop_jwt_lookup(_jwt_header, jwt_data):
        identity = jwt_data['sub']
        try:
            from app.domains.ecommerce.models import WebCustomer
            return WebCustomer.query.get(int(identity))
        except Exception:
            return None

    if app.config.get('SHOP_CORS_ORIGINS'):
        from flask_cors import CORS
        CORS(app, resources={r"/api/shop/*": {"origins": app.config['SHOP_CORS_ORIGINS']}})

    if config_name == 'production' and app.config.get('SECRET_KEY') == 'erpmini-secret-key-2024':
        app.logger.warning('SECURITY WARNING: SECRET_KEY is default value in production.')

    def _select_locale():
        return session.get('lang', 'vi')
    babel = Babel(app, locale_selector=_select_locale)

    @app.before_request
    def _load_lang_from_cookie():
        if 'lang' not in session and request.cookies.get('lang'):
            session['lang'] = request.cookies.get('lang')

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    register_filters(app)

    @app.after_request
    def _set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp
        return response

    @app.errorhandler(RequestEntityTooLarge)
    def _handle_request_too_large(error):
        max_mb = int(app.config.get('MAX_CONTENT_LENGTH', 0) / (1024 * 1024)) or 0
        flash(f'File upload quá lớn. Vui lòng chọn file nhỏ hơn {max_mb}MB hoặc nén ảnh trước khi tải lên.', 'warning')
        return redirect(request.referrer or url_for('products.index'))

    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.products import products_bp
    from app.routes.suppliers import suppliers_bp
    from app.routes.customers import customers_bp
    from app.routes.warehouses import warehouses_bp
    from app.routes.units import units_bp
    from app.routes.categories import categories_bp
    from app.routes.stock_in import stock_in_bp
    from app.routes.stock_out import stock_out_bp
    from app.routes.quotations import quotations_bp
    from app.routes.ecommerce import ecommerce_bp
    from app.routes.inventory import inventory_bp
    from app.routes.opening_stock import opening_stock_bp
    from app.domains.inventory.routes.stocktaking import stocktaking_bp
    from app.routes.accounting import accounting_bp
    from app.routes.debt import debt_bp
    from app.routes.vat import vat_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from app.routes.company import company_bp
    from app.routes.api import api_bp
    from app.domains.ecommerce.routes.shop_api import shop_api_bp

    for bp in [auth_bp, dashboard_bp, products_bp, suppliers_bp, customers_bp,
               warehouses_bp, units_bp, categories_bp,
               stock_in_bp, stock_out_bp, quotations_bp, ecommerce_bp, inventory_bp, opening_stock_bp, stocktaking_bp,
               accounting_bp, debt_bp, vat_bp, reports_bp,
               settings_bp, company_bp, api_bp, shop_api_bp]:
        app.register_blueprint(bp)

    @app.before_request
    def _security_guard():
        session.permanent = True
        if current_user.is_authenticated:
            now = datetime.now(timezone.utc).timestamp()
            last_seen = session.get('last_seen_ts')
            timeout_seconds = int(app.permanent_session_lifetime.total_seconds())
            if last_seen and (now - float(last_seen)) > timeout_seconds:
                logout_user()
                session.clear()
                return redirect(url_for('auth.login'))
            session['last_seen_ts'] = now

    @app.before_request
    def _ensure_tracking_token_column():
        if request.blueprint == 'shop_api' or request.path.startswith('/shop'):
            return
        try:
            from sqlalchemy import text
            has_col = db.session.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'online_orders' AND column_name = 'tracking_token'
            """)).fetchone()
            if not has_col:
                db.session.execute(text("""
                    ALTER TABLE online_orders ADD COLUMN tracking_token VARCHAR(64) NULL
                """))
                db.session.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_online_orders_tracking_token
                    ON online_orders (tracking_token)
                """))
                db.session.commit()
                app.logger.info("Auto-added tracking_token column to online_orders")
        except Exception:
            if db.session.is_active:
                db.session.rollback()

    def _get_nav_menus(role: str, user_id: int | None = None) -> list:
        from app.domains.platform.models import Menu, UserMenuOverride

        cache_key = f'nav_menus:{role}:{user_id or 0}'
        menus = cache.get(cache_key)
        if menus is not None:
            return menus

        override_rows = []
        if user_id:
            override_rows = UserMenuOverride.query.filter_by(user_id=user_id).all()
        # UserMenuOverride là quyền cao nhất (ghi đè từng user)
        override_map = {r.menu_id: bool(r.is_visible) for r in override_rows}

        roots = (
            Menu.query
            .filter_by(parent_id=None, is_active=True)
            .order_by(Menu.order_no)
            .all()
        )

        def _allowed(menu: Menu) -> bool:
            # 1. Ghi đè theo từng user (ưu tiên cao nhất)
            if menu.id in override_map:
                return override_map[menu.id]
            # 2. Đồng bộ với phân quyền nghiệp vụ: menu hiện khi user
            #    có quyền xem module tương ứng (trùng với require_permission)
            if menu.module:
                try:
                    return bool(current_user.has_permission(menu.module, 'view'))
                except Exception:
                    db.session.rollback()
                    return role == 'admin'
            # 3. Menu không gắn module: chỉ admin
            return role == 'admin'

        filtered = []
        for m in roots:
            if m.id in override_map and override_map[m.id] is False:
                continue
            visible_children = sorted(
                [c for c in m.children if c.is_active and _allowed(c)],
                key=lambda x: x.order_no,
            )
            if (not _allowed(m)) and (not visible_children):
                continue
            m.visible_children = visible_children
            filtered.append(m)

        cache.set(cache_key, filtered, timeout=300)
        return filtered

    def _get_company_name() -> str:
        from app.domains.platform.models import SystemConfig
        cached = cache.get('company_name')
        if cached is not None:
            return cached
        cfg = SystemConfig.query.filter_by(key='company_name').first()
        name = (cfg.value or 'ERP-VIET') if cfg else 'ERP-VIET'
        cache.set('company_name', name, timeout=600)
        return name

    @app.context_processor
    def inject_globals():
        def t(text: str) -> str:
            try:
                from flask_babel import gettext as _babel_gettext
                result = _babel_gettext(text)
                if result != text:
                    return result
            except Exception:
                pass
            if session.get('lang', 'vi') == 'vi':
                return _VI_MAP.get(text, text)
            return text

        def can(module: str, action: str = 'view') -> bool:
            try:
                if not current_user.is_authenticated:
                    return False
                if hasattr(current_user, 'has_permission'):
                    return bool(current_user.has_permission(module, action))
                return (current_user.role or '').strip().lower() == 'admin'
            except Exception:
                db.session.rollback()
                return False

        menus: list = []
        company_name: str = 'ERP-VIET'

        if current_user.is_authenticated:
            role = getattr(current_user, 'role', 'user')
            role = role.strip().lower()
            try:
                menus = _get_nav_menus(role, current_user.id)
                company_name = _get_company_name()
            except Exception:
                db.session.rollback()

        return dict(nav_menus=menus, app_name=company_name, t=t, can=can)

    try:
        from app.core.bootstrap import run_bootstrap
        with app.app_context():
            db.create_all()
        run_bootstrap(app)
    except Exception:
        pass

    return app
