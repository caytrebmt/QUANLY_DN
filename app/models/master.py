from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import db


class ERPUser(UserMixin, db.Model):
    __tablename__ = 'erp_users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255))
    role = db.Column(db.String(50), default='erp_user')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f"erp_{self.id}"


from app.domains.master.models import (
    Unit,
    Category,
    Product,
    ProductImage,
    Supplier,
    Customer,
    Warehouse,
)

__all__ = [
    'ERPUser',
    'Unit',
    'Category',
    'Product',
    'ProductImage',
    'Supplier',
    'Customer',
    'Warehouse',
]
