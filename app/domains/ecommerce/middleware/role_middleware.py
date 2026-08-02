from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def web_customer_only(f):
    """Chỉ cho phép Web Customer truy cập"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
            return redirect(url_for('shop.login'))

        if hasattr(current_user, 'role') and current_user.role != 'web_customer':
            flash('Bạn không có quyền truy cập khu vực này.', 'danger')
            abort(403)

        from app.domains.ecommerce.models import WebCustomer
        if not isinstance(current_user._get_current_object(), WebCustomer):
            flash('Truy cập bị từ chối.', 'danger')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def erp_user_only(f):
    """Chỉ cho phép ERP User (nội bộ) truy cập"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Vui lòng đăng nhập.', 'warning')
            return redirect(url_for('auth.login'))

        if hasattr(current_user, 'role') and current_user.role != 'erp_user':
            flash('Truy cập bị từ chối. Khu vực này chỉ dành cho nhân viên.', 'danger')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function
