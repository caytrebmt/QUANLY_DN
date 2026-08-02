from __future__ import annotations

from flask import Flask, request, session
from flask_babel import Babel
from flask_login import current_user, LoginManager
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect

from config.settings import config
from app.database import db
from app.domains.ecommerce.models import WebCustomer
from app.filters import register_filters
from app.domains.ecommerce.routes.shop import shop_bp


def create_shop_app(config_name: str | None = None) -> Flask:
    """Tạo Flask app riêng cho Shop để tách cookie/session ERP <-> Shop."""
    import os
    from datetime import timedelta
    from pathlib import Path
    import sys

    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    # Lấy template/static đúng theo cấu trúc dự án
    # shop_app.py nằm trong app/, nên templates/static nằm tại app/templates và app/static
    resource_base = Path(__file__).resolve().parent
    template_dir = resource_base / 'templates'
    static_dir = resource_base / 'static'
    translations_dir = resource_base.parent / 'translations'


    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
        root_path=str(resource_base),
    )
    app.config.from_object(config.get(config_name, config['default']))
    db.init_app(app)

    # Tách cookie riêng cho shop để cô lập hoàn toàn với ERP
    app.config['SESSION_COOKIE_NAME'] = 'shop_session'
    app.config['REMEMBER_COOKIE_NAME'] = 'shop_remember'

    # Tạo LoginManager riêng cho Shop để cô lập session/state khỏi ERP
    shop_login_manager = LoginManager()
    shop_login_manager.login_view = 'shop.login'
    shop_login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'
    shop_login_manager.login_message_category = 'warning'
    shop_login_manager.session_protection = app.config.get('SESSION_PROTECTION', 'strong')
    shop_login_manager.init_app(app)

    @shop_login_manager.user_loader
    def _load_shop_customer(user_id):
        if isinstance(user_id, str) and user_id.startswith('web:'):
            user_id = user_id[4:]
        return db.session.get(WebCustomer, int(user_id))

    # Tách cache/csrf/babel theo app shop (để không xung đột)
    cache = Cache()
    csrf = CSRFProtect()
    cache_config = {
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'SimpleCache'),
        'CACHE_DEFAULT_TIMEOUT': 300,
    }
    redis_url = app.config.get('REDIS_URL') or app.config.get('CACHE_REDIS_URL')
    if redis_url:
        cache_config['CACHE_TYPE'] = 'RedisCache'
        cache_config['CACHE_REDIS_URL'] = redis_url
    cache.init_app(app, config=cache_config)
    csrf.init_app(app)

    def _select_locale():
        return session.get('lang', 'vi')

    Babel(app, locale_selector=_select_locale)

    @app.before_request
    def _load_lang_from_cookie_shop():
        if 'lang' not in session and request.cookies.get('lang'):
            session['lang'] = request.cookies.get('lang')

    # Register filters
    register_filters(app)

    # Register blueprint shop
    app.register_blueprint(shop_bp)

    return app

