from app.database import db, login_manager
from flask_caching import Cache
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

cache = Cache()
csrf = CSRFProtect()
migrate = Migrate()
jwt = JWTManager()
