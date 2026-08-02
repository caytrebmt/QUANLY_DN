from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import db


class MenuRole(db.Model):
    """Phân quyền menu theo vai trò"""
    __tablename__ = 'menu_roles'
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id', ondelete='CASCADE'), primary_key=True)
    role = db.Column(db.String(30), primary_key=True)


class UserMenuOverride(db.Model):
    """Ghi đè hiển thị menu theo từng user."""
    __tablename__ = 'user_menu_overrides'

    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id', ondelete='CASCADE'), primary_key=True)
    is_visible = db.Column(db.Boolean, nullable=False)


class Menu(db.Model):
    """Bảng định nghĩa menu - dễ mở rộng thêm menu mới"""
    __tablename__ = 'menus'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, comment='Mã menu')
    name = db.Column(db.String(100), nullable=False, comment='Tên menu')
    parent_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=True, comment='Menu cha')
    url = db.Column(db.String(200), nullable=True, comment='Đường dẫn URL')
    icon = db.Column(db.String(100), default='fas fa-circle', comment='Icon FontAwesome')
    order_no = db.Column(db.Integer, default=0, comment='Thứ tự hiển thị')
    module = db.Column(db.String(50), nullable=True, comment='Module chức năng')
    roles = db.Column(db.String(200), default='admin,user', comment='Quyền truy cập (CSV, legacy)')
    is_active = db.Column(db.Boolean, default=True, comment='Kích hoạt')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship('Menu', backref=db.backref('parent', remote_side=[id]),
                               lazy='select', order_by='Menu.order_no')
    roles_rel = db.relationship('MenuRole', backref='menu', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Menu {self.code}: {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'parent_id': self.parent_id,
            'url': self.url,
            'icon': self.icon,
            'order_no': self.order_no,
            'module': self.module,
            'is_active': self.is_active,
            'roles': self.roles_list(),
        }

    def roles_list(self):
        try:
            return sorted({r.role for r in self.roles_rel})
        except Exception:
            db.session.rollback()
            return [r.strip().lower() for r in (self.roles or '').split(',') if r.strip()]


class Notification(db.Model):
    """Bảng mẫu thông báo - định nghĩa tất cả messages trong hệ thống"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, comment='Mã thông báo')
    name = db.Column(db.String(200), nullable=False, comment='Tên thông báo')
    message_template = db.Column(db.Text, nullable=False, comment='Mẫu nội dung thông báo')
    noti_type = db.Column(db.String(20), default='info',
                          comment='Loại: success/error/warning/info')
    module = db.Column(db.String(50), nullable=True, comment='Module áp dụng')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification {self.code}>'

    def get_message(self, **kwargs):
        try:
            return self.message_template.format(**kwargs)
        except Exception:
            return self.message_template


class SystemConfig(db.Model):
    """Cấu hình hệ thống dạng key-value"""
    __tablename__ = 'system_configs'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(200), nullable=True)
    group_name = db.Column(db.String(50), default='general')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Config {self.key}={self.value}>'
