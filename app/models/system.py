from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import db
from app.shared.constants import Roles


class User(UserMixin, db.Model):
    """Bảng người dùng hệ thống"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default=Roles.USER,
                     comment='admin/accountant/warehouse/user')
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    permissions = db.relationship('UserPermission', backref='user',
                                  lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return (self.role or '').strip().lower() == 'admin'

    def has_permission(self, module, action='view'):
        module = (module or '').strip().lower()
        action = (action or 'view').strip().lower()
        action_map = {
            'view': 'can_view',
            'add': 'can_add',
            'create': 'can_add',
            'edit': 'can_edit',
            'update': 'can_edit',
            'confirm': 'can_edit',
            'delete': 'can_delete',
            'remove': 'can_delete',
            'export': 'can_view',
        }
        attr = action_map.get(action, 'can_view')
        if self.is_admin():
            return True
        try:
            perm = self.permissions.filter_by(module=module).first()
            if perm:
                return bool(getattr(perm, attr, False))
        except Exception:
            db.session.rollback()
            pass
        defaults = UserPermission.DEFAULT_ROLE_PERMS.get((self.role or 'user').strip().lower(), {})
        vals = defaults.get(module, {})
        return bool(vals.get(attr, False))

    def get_permissions_dict(self):
        data = {}
        try:
            for p in self.permissions.all():
                data[p.module] = {
                    'view': bool(p.can_view),
                    'add': bool(p.can_add),
                    'edit': bool(p.can_edit),
                    'delete': bool(p.can_delete),
                }
        except Exception:
            db.session.rollback()
            pass
        return data

    def __repr__(self):
        return f'<User {self.username}>'


class UserPermission(db.Model):
    __tablename__ = 'user_permissions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    can_view = db.Column(db.Boolean, default=False)
    can_add = db.Column(db.Boolean, default=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'module', name='uq_user_module'),
    )

    MODULES = [
        ('dashboard', 'Tổng quan'),
        ('products', 'Hàng hóa'),
        ('suppliers', 'Nhà cung cấp'),
        ('customers', 'Khách hàng'),
        ('stock_in', 'Phiếu nhập kho'),
        ('stock_out', 'Phiếu xuất kho'),
        ('quotations', 'Bảng báo giá'),
        ('ecommerce', 'E-commerce'),
        ('inventory', 'Tồn kho'),
        ('debt', 'Công nợ'),
        ('accounting', 'Kế toán'),
        ('reports', 'Báo cáo'),
        ('settings', 'Cài đặt'),
        ('opening_stock', 'Tồn đầu kỳ'),
    ]

    DEFAULT_ROLE_PERMS = {
        'user': {
            'dashboard': {'can_view': True},
            'products': {'can_view': True},
            'suppliers': {'can_view': True},
            'customers': {'can_view': True},
            'reports': {'can_view': True},
        },
        'warehouse': {
            'dashboard': {'can_view': True},
            'products': {'can_view': True, 'can_add': True, 'can_edit': True},
            'suppliers': {'can_view': True},
            'customers': {'can_view': True},
            'stock_in': {'can_view': True, 'can_add': True, 'can_edit': True, 'can_delete': True},
            'stock_out': {'can_view': True, 'can_add': True, 'can_edit': True, 'can_delete': True},
            'quotations': {'can_view': True, 'can_add': True, 'can_edit': True, 'can_delete': True},
            'ecommerce': {'can_view': True, 'can_add': True, 'can_edit': True},
            'inventory': {'can_view': True},
            'opening_stock': {'can_view': True, 'can_add': True, 'can_edit': True, 'can_delete': True},
            'reports': {'can_view': True},
        },
        'accountant': {
            'dashboard': {'can_view': True},
            'products': {'can_view': True},
            'suppliers': {'can_view': True, 'can_add': True, 'can_edit': True},
            'customers': {'can_view': True, 'can_add': True, 'can_edit': True},
            'stock_in': {'can_view': True, 'can_add': True, 'can_edit': True},
            'stock_out': {'can_view': True, 'can_add': True, 'can_edit': True},
            'quotations': {'can_view': True, 'can_add': True, 'can_edit': True},
            'ecommerce': {'can_view': True, 'can_add': True, 'can_edit': True},
            'inventory': {'can_view': True},
            'debt': {'can_view': True, 'can_add': True, 'can_edit': True},
            'accounting': {'can_view': True, 'can_add': True, 'can_edit': True},
            'opening_stock': {'can_view': True, 'can_add': True, 'can_edit': True, 'can_delete': True},
            'reports': {'can_view': True},
        },
    }


from app.domains.platform.models import (
    Menu,
    MenuRole,
    Notification,
    SystemConfig,
    UserMenuOverride,
)

__all__ = [
    'User',
    'UserPermission',
    'Menu',
    'MenuRole',
    'Notification',
    'SystemConfig',
    'UserMenuOverride',
]
