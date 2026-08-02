from flask import Blueprint
from app.domains.platform.routes.users import users_bp
from app.domains.platform.routes.menus import menus_bp
from app.domains.platform.routes.system import system_bp
from app.domains.platform.routes.backup import backup_bp
from app.domains.platform.routes.notifications import notifications_bp

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

settings_bp.register_blueprint(users_bp)
settings_bp.register_blueprint(menus_bp)
settings_bp.register_blueprint(system_bp)
settings_bp.register_blueprint(backup_bp)
settings_bp.register_blueprint(notifications_bp)

__all__ = ['settings_bp']
