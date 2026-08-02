from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.database import db
from app.models.system import User, UserPermission
from app.domains.platform.models import Menu, UserMenuOverride
from app.shared.authz import require_permission
from app.shared.constants import Roles
from app.domains.platform.services.security_service import validate_password_strength

users_bp = Blueprint('users', __name__, url_prefix='')


def _admin_only():
    if current_user.role != Roles.ADMIN:
        flash('Chỉ quản trị viên mới có quyền thực hiện!', 'danger')
        return False
    return True


def _get_role_options():
    # Chỉ dùng tập vai trò chuẩn hóa, không lấy distinct tự do từ DB
    return sorted(r for r in Roles.INTERNAL)


def _permissions_form_context(user=None):
    modules = UserPermission.MODULES
    perms = {}
    menu_overrides = {}
    menus_for_override = []
    if user:
        perms = user.get_permissions_dict()
        try:
            rows = UserMenuOverride.query.filter_by(user_id=user.id).all()
            menu_overrides = {r.menu_id: ('show' if r.is_visible else 'hide') for r in rows}
        except Exception:
            db.session.rollback()
            menu_overrides = {}
    try:
        menus_for_override = (
            Menu.query.filter_by(is_active=True)
            .order_by(Menu.parent_id.isnot(None), Menu.order_no, Menu.code)
            .all()
        )
    except Exception:
        db.session.rollback()
        menus_for_override = []
    return modules, perms, menus_for_override, menu_overrides


def _save_permissions(user, form_data):
    try:
        UserPermission.query.filter_by(user_id=user.id).delete()
    except Exception:
        db.session.rollback()
        return

    role = Roles.normalize(user.role)
    for module_key, _ in UserPermission.MODULES:
        if role == Roles.ADMIN:
            can_view = can_add = can_edit = can_delete = True
        else:
            can_view = form_data.get(f'perm_{module_key}_view') == '1'
            can_add = form_data.get(f'perm_{module_key}_add') == '1'
            can_edit = form_data.get(f'perm_{module_key}_edit') == '1'
            can_delete = form_data.get(f'perm_{module_key}_delete') == '1'
        row = UserPermission(
            user_id=user.id,
            module=module_key,
            can_view=can_view,
            can_add=can_add,
            can_edit=can_edit,
            can_delete=can_delete,
        )
        db.session.add(row)


def _save_user_menu_overrides(user, form_data):
    UserMenuOverride.query.filter_by(user_id=user.id).delete()
    menu_ids = form_data.getlist('menu_override_ids')
    for menu_id_raw in menu_ids:
        key = f'menu_override_{menu_id_raw}'
        val = (form_data.get(key) or 'default').strip().lower()
        if val not in {'show', 'hide'}:
            continue
        try:
            menu_id = int(menu_id_raw)
        except Exception:
            continue
        db.session.add(UserMenuOverride(
            user_id=user.id,
            menu_id=menu_id,
            is_visible=(val == 'show'),
        ))


@users_bp.route('/users')
@login_required
@require_permission('settings', 'view')
def users_list():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    users_list = User.query.order_by(User.username).all()
    return render_template('settings/users.html', users=users_list)


@users_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'create')
def create_user():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        raw_role = request.form.get('role', Roles.USER)
        if not Roles.is_valid(raw_role):
            flash('Vai trò không hợp lệ!', 'danger')
            modules, perms, menus_for_override, menu_overrides = _permissions_form_context()
            return render_template('settings/user_form.html', user=None, modules=modules, perms=perms,
                                   role_options=_get_role_options(),
                                   menus_for_override=menus_for_override, menu_overrides=menu_overrides)
        role = Roles.normalize(raw_role)
        if not username or not full_name or not password:
            flash('Vui lòng nhập đầy đủ Username, Họ tên và Mật khẩu!', 'danger')
            modules, perms, menus_for_override, menu_overrides = _permissions_form_context()
            return render_template('settings/user_form.html', user=None, modules=modules, perms=perms,
                                   role_options=_get_role_options(),
                                   menus_for_override=menus_for_override, menu_overrides=menu_overrides)
        if User.query.filter_by(username=username).first():
            flash(f'Username {username} đã tồn tại!', 'danger')
            modules, perms, menus_for_override, menu_overrides = _permissions_form_context()
            return render_template('settings/user_form.html', user=None, modules=modules, perms=perms,
                                   role_options=_get_role_options(),
                                   menus_for_override=menus_for_override, menu_overrides=menu_overrides)
        if email and User.query.filter_by(email=email).first():
            flash(f'Email {email} đã tồn tại!', 'danger')
            modules, perms, menus_for_override, menu_overrides = _permissions_form_context()
            return render_template('settings/user_form.html', user=None, modules=modules, perms=perms,
                                   role_options=_get_role_options(),
                                   menus_for_override=menus_for_override, menu_overrides=menu_overrides)
        ok, msg = validate_password_strength(password)
        if not ok:
            flash(msg, 'warning')
            modules, perms, menus_for_override, menu_overrides = _permissions_form_context()
            return render_template('settings/user_form.html', user=None, modules=modules, perms=perms,
                                   role_options=_get_role_options(),
                                   menus_for_override=menus_for_override, menu_overrides=menu_overrides)
        u = User(username=username, email=email,
                 full_name=full_name, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.flush()
        _save_permissions(u, request.form)
        _save_user_menu_overrides(u, request.form)
        db.session.commit()
        from app import invalidate_nav_cache
        invalidate_nav_cache()
        flash(f'Tao user {username} thanh cong!', 'success')
        return redirect(url_for('settings.users.users_list'))
    modules, perms, menus_for_override, menu_overrides = _permissions_form_context()
    return render_template('settings/user_form.html', user=None, modules=modules, perms=perms,
                           role_options=_get_role_options(),
                           menus_for_override=menus_for_override, menu_overrides=menu_overrides)


@users_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'edit')
def edit_user(id):
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    u = User.query.get_or_404(id)
    if request.method == 'POST':
        u.full_name = request.form.get('full_name', '').strip()
        new_email = request.form.get('email', '').strip()
        if new_email and User.query.filter(User.email == new_email, User.id != u.id).first():
            flash(f'Email {new_email} da ton tai!', 'danger')
            modules, perms, menus_for_override, menu_overrides = _permissions_form_context(u)
            return render_template('settings/user_form.html', user=u, modules=modules, perms=perms,
                                   role_options=_get_role_options(),
                                   menus_for_override=menus_for_override, menu_overrides=menu_overrides)
        u.email = new_email
        raw_role = request.form.get('role', Roles.USER)
        u.role = Roles.normalize(raw_role) if Roles.is_valid(raw_role) else u.role
        u.is_active = request.form.get('is_active') == 'on'
        new_pw = request.form.get('new_password', '')
        if new_pw:
            ok, msg = validate_password_strength(new_pw)
            if not ok:
                flash(msg, 'warning')
                modules, perms, menus_for_override, menu_overrides = _permissions_form_context(u)
                return render_template('settings/user_form.html', user=u, modules=modules, perms=perms,
                                       role_options=_get_role_options(),
                                       menus_for_override=menus_for_override, menu_overrides=menu_overrides)
            u.set_password(new_pw)
        _save_permissions(u, request.form)
        _save_user_menu_overrides(u, request.form)
        db.session.commit()
        from app import invalidate_nav_cache
        invalidate_nav_cache()
        flash(f'Cap nhat user {u.username} thanh cong!', 'success')
        return redirect(url_for('settings.users.users_list'))
    modules, perms, menus_for_override, menu_overrides = _permissions_form_context(u)
    return render_template('settings/user_form.html', user=u, modules=modules, perms=perms,
                           role_options=_get_role_options(),
                           menus_for_override=menus_for_override, menu_overrides=menu_overrides)
