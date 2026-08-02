from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.database import db
from app.domains.platform.models import Menu
from app.shared.authz import require_permission
from app.shared.constants import Roles
from app.models.system import UserPermission

menus_bp = Blueprint('menus', __name__, url_prefix='')


def _admin_only():
    if current_user.role != Roles.ADMIN:
        flash('Chỉ quản trị viên mới có quyền thực hiện!', 'danger')
        return False
    return True


def _get_role_options():
    # Chỉ dùng tập vai trò chuẩn hóa, không lấy distinct tự do từ DB
    return sorted(r for r in Roles.INTERNAL)


def _default_visible_by_role(module: str | None) -> dict:
    """Quyền xem mặc định của từng vai trò với module này.
    Đồng bộ với UserPermission.DEFAULT_ROLE_PERMS (nguồn quyết định hiển thị)."""
    result = {}
    for role in Roles.INTERNAL:
        if role == Roles.ADMIN:
            result[role] = True
            continue
        vals = UserPermission.DEFAULT_ROLE_PERMS.get(role, {}).get((module or '').strip().lower(), {})
        result[role] = bool(vals.get('can_view', False))
    return result


@menus_bp.route('/menus')
@login_required
@require_permission('settings', 'view')
def menus():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    try:
        menus_list = Menu.query.order_by(Menu.order_no, Menu.code).all()
        parents = [m for m in menus_list if not m.parent_id]
        children = [m for m in menus_list if m.parent_id]
        role_options = _get_role_options()
        menus_json = [{
            'id': m.id,
            'name': m.name,
            'parent_id': m.parent_id,
            'icon': m.icon,
            'url': m.url,
            'order_no': m.order_no,
            'module': m.module,
            'is_active': m.is_active,
            # Hiển thị mặc định theo vai trò (dựa trên quyền xem module
            # của từng vai trò - đồng bộ với Quản lý users)
            'default_visible': _default_visible_by_role(m.module),
        } for m in menus_list]
        return render_template('settings/menus.html',
                               menus=menus_list, parents=parents, children=children,
                               menus_json=menus_json, role_options=role_options)
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi tải menu: {e}', 'danger')
        return render_template('settings/menus.html',
                               menus=[], parents=[], children=[],
                               menus_json=[], role_options=_get_role_options())


@menus_bp.route('/menus/create', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'create')
def create_menu():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    all_menus = Menu.query.order_by(Menu.order_no).all()
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        if not code or not name:
            flash('Mã và tên menu không được để trống!', 'danger')
            return render_template('settings/menu_form.html',
                                   menu=None, all_menus=all_menus)
        if Menu.query.filter_by(code=code).first():
            flash(f'Mã menu {code} đã tồn tại!', 'danger')
            return render_template('settings/menu_form.html',
                                   menu=None, all_menus=all_menus)
        m = Menu(
            code=code,
            name=name,
            parent_id=request.form.get('parent_id', type=int) or None,
            url=request.form.get('url', '').strip() or None,
            icon=request.form.get('icon', 'fas fa-circle').strip(),
            order_no=int(request.form.get('order_no', 0) or 0),
            module=request.form.get('module', '').strip() or None,
            is_active=request.form.get('is_active') == 'on',
        )
        db.session.add(m)
        db.session.commit()
        from app import invalidate_nav_cache
        invalidate_nav_cache()
        flash(f'Thêm menu [{code}] {name} thành công!', 'success')
        return redirect(url_for('menus.menus'))
    return render_template('settings/menu_form.html',
                           menu=None, all_menus=all_menus)


@menus_bp.route('/menus/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'edit')
def edit_menu(id):
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    m = Menu.query.get_or_404(id)
    all_menus = Menu.query.filter(Menu.id != id).order_by(Menu.order_no).all()
    if request.method == 'POST':
        m.name = request.form.get('name', '').strip()
        m.parent_id = request.form.get('parent_id', type=int) or None
        m.url = request.form.get('url', '').strip() or None
        m.icon = request.form.get('icon', 'fas fa-circle').strip()
        m.order_no = int(request.form.get('order_no', 0) or 0)
        m.module = request.form.get('module', '').strip() or None
        m.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        from app import invalidate_nav_cache
        invalidate_nav_cache()
        flash(f'Cập nhật menu [{m.code}] thành công!', 'success')
        return redirect(url_for('menus.menus'))
    return render_template('settings/menu_form.html', menu=m, all_menus=all_menus)


@menus_bp.route('/menus/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('settings', 'delete')
def delete_menu(id):
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    m = Menu.query.get_or_404(id)
    if len(m.children) > 0:
        flash(
            f'Menu [{m.code}] con menu con - hay xoa menu con truoc!', 'warning')
        return redirect(url_for('menus.menus'))
    code = m.code
    db.session.delete(m)
    db.session.commit()
    from app import invalidate_nav_cache
    invalidate_nav_cache()
    flash(f'Đã xóa menu [{code}]!', 'success')
    return redirect(url_for('menus.menus'))


@menus_bp.route('/menus/toggle/<int:id>', methods=['POST'])
@login_required
@require_permission('settings', 'edit')
def toggle_menu(id):
    if not _admin_only():
        return jsonify({'ok': False})
    m = Menu.query.get_or_404(id)
    m.is_active = not m.is_active
    db.session.commit()
    from app import invalidate_nav_cache
    invalidate_nav_cache()
    return jsonify({'ok': True, 'is_active': m.is_active})
