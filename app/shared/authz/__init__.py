from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def require_permission(module: str, action: str = "view"):
    module_key = (module or "").strip().lower()
    action_key = (action or "view").strip().lower()

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user
            if not user.is_authenticated:
                flash("Vui lòng đăng nhập để tiếp tục.", "warning")
                return redirect(url_for("auth.login"))

            role = (getattr(user, "role", "") or "").strip().lower()
            if role == "admin":
                return fn(*args, **kwargs)

            if not getattr(user, "has_permission", None):
                if role != "admin":
                    flash("Bạn không có quyền thực hiện thao tác này.", "danger")
                    return redirect(url_for("dashboard.index"))
                return fn(*args, **kwargs)

            try:
                if user.has_permission(module_key, action_key):
                    return fn(*args, **kwargs)
            except Exception:
                try:
                    from app.database import db
                    db.session.rollback()
                except Exception:
                    pass

            flash("Bạn không có quyền thực hiện thao tác này.", "danger")
            return redirect(url_for("dashboard.index"))

        return wrapper

    return decorator
