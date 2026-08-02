from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.products import products_bp
from app.routes.suppliers import suppliers_bp
from app.routes.customers import customers_bp
from app.routes.warehouses import warehouses_bp
from app.routes.stock_in import stock_in_bp
from app.routes.stock_out import stock_out_bp
from app.routes.quotations import quotations_bp
from app.routes.inventory import inventory_bp
from app.routes.accounting import accounting_bp
from app.routes.debt import debt_bp
from app.routes.vat import vat_bp
from app.routes.settings import settings_bp
from app.routes.api import api_bp

__all__ = [
    'auth_bp', 'dashboard_bp', 'products_bp', 'suppliers_bp',
    'customers_bp', 'warehouses_bp', 'stock_in_bp', 'stock_out_bp',
    'quotations_bp', 'inventory_bp', 'accounting_bp', 'debt_bp', 'vat_bp',
    'settings_bp', 'api_bp',
]
