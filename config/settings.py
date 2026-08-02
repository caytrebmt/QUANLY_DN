import os
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv


def _runtime_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


ENV_PATH = _runtime_base_dir() / '.env'

if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=False)
else:
    load_dotenv(override=False)


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError('SECRET_KEY is not configured. Set it in .env or environment variables.')
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 'postgresql://postgres:password@localhost:5432/erpmini')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_size': 10,
        'max_overflow': 20,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    }
    # Company info
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'Công ty TNHH ERP-VIET')
    COMPANY_ADDRESS = os.getenv('COMPANY_ADDRESS', '123 Đường ABC, TP.HCM')
    COMPANY_PHONE = os.getenv('COMPANY_PHONE', '028-1234-5678')
    COMPANY_TAX_CODE = os.getenv('COMPANY_TAX_CODE', '0123456789')
    COMPANY_EMAIL = os.getenv('COMPANY_EMAIL', 'info@erpmini.com')
    # Upload
    UPLOAD_FOLDER = 'app/static/uploads'
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_MB', '64')) * 1024 * 1024
    PRODUCT_IMAGE_MAX_PX = int(os.getenv('PRODUCT_IMAGE_MAX_PX', '1600'))
    PRODUCT_IMAGE_QUALITY = int(os.getenv('PRODUCT_IMAGE_QUALITY', '82'))
    # Pagination
    ITEMS_PER_PAGE = 20
    # VAT rates available
    VAT_RATES = [0, 5, 8, 10]
    # Inventory
    ALLOW_NEGATIVE_STOCK = os.getenv(
        'ALLOW_NEGATIVE_STOCK', 'false').lower() == 'true'

    # Security / Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.getenv(
        'SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    # Cookie dành cho ERP (mặc định)
    SESSION_COOKIE_NAME = 'erp_session'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_NAME = 'erp_remember'
    REMEMBER_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')


    REMEMBER_COOKIE_SECURE = os.getenv(
        'SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.getenv('SESSION_TIMEOUT_MINUTES', '120'))
    )
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_PROTECTION = 'strong'

    # Reverse proxy / HTTPS
    USE_PROXY_FIX = os.getenv('USE_PROXY_FIX', 'false').lower() == 'true'
    PROXY_FIX_X_FOR = int(os.getenv('PROXY_FIX_X_FOR', '1'))
    PROXY_FIX_X_PROTO = int(os.getenv('PROXY_FIX_X_PROTO', '1'))
    PROXY_FIX_X_HOST = int(os.getenv('PROXY_FIX_X_HOST', '1'))
    PREFERRED_URL_SCHEME = os.getenv('PREFERRED_URL_SCHEME', 'http')
    WTF_CSRF_TIME_LIMIT = 3600   # token hết hạn sau 1 giờ (default)
    WTF_CSRF_SSL_STRICT = True   # production: chỉ chấp nhận HTTPS referer

    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    JWT_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_NAME = 'shop_access_token'
    JWT_REFRESH_COOKIE_NAME = 'shop_refresh_token'

    _raw_cors_origins = os.getenv('SHOP_CORS_ORIGINS', 'http://localhost:3000,http://localhost:5000')
    SHOP_CORS_ORIGINS = [o.strip() for o in _raw_cors_origins.split(',') if o.strip()]

    GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
    GOOGLE_OAUTH_REDIRECT_URI = os.getenv('GOOGLE_OAUTH_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

    BABEL_DEFAULT_LOCALE = os.getenv('BABEL_DEFAULT_LOCALE', 'vi')
    BABEL_LANGUAGES = ['vi', 'en']

class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
}
