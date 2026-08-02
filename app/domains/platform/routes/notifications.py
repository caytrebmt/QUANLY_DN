from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.database import db
from app.domains.platform.models import Notification
from app.shared.authz import require_permission
from app.shared.constants import Roles

notifications_bp = Blueprint('notifications', __name__, url_prefix='')


def _admin_only():
    if current_user.role != Roles.ADMIN:
        flash('Chỉ quản trị viên mới có quyền thực hiện!', 'danger')
        return False
    return True


@notifications_bp.route('/notifications')
@login_required
@require_permission('settings', 'view')
def notifications_list():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    search = request.args.get('search', '')
    module = request.args.get('module', '')
    ntype = request.args.get('ntype', '')

    q = Notification.query
    if search:
        q = q.filter(db.or_(
            Notification.code.ilike(f'%{search}%'),
            Notification.name.ilike(f'%{search}%'),
            Notification.message_template.ilike(f'%{search}%'),
        ))
    if module:
        q = q.filter(Notification.module == module)
    if ntype:
        q = q.filter(Notification.noti_type == ntype)

    notifs = q.order_by(Notification.module, Notification.code).all()
    modules = db.session.query(Notification.module).filter(
        Notification.module.isnot(None)).distinct().all()
    modules = sorted([m[0] for m in modules if m[0]])
    return render_template('settings/notifications.html',
                           notifications=notifs, search=search,
                           module=module, ntype=ntype, modules=modules)


@notifications_bp.route('/notifications/create', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'create')
def create_notification():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        tmpl = request.form.get('message_template', '').strip()
        if not code or not name or not tmpl:
            flash('Ma, ten va noi dung mau khong duoc de trong!', 'danger')
            return render_template('settings/notification_form.html', notif=None)
        if Notification.query.filter_by(code=code).first():
            flash(f'Ma thong bao {code} da ton tai!', 'danger')
            return render_template('settings/notification_form.html', notif=None)
        n = Notification(
            code=code,
            name=name,
            message_template=tmpl,
            noti_type=request.form.get('noti_type', 'info'),
            module=request.form.get('module', '').strip() or None,
            is_active=request.form.get('is_active') == 'on',
        )
        db.session.add(n)
        db.session.commit()
        flash(f'Them mau thong bao [{code}] thanh cong!', 'success')
        return redirect(url_for('notifications.notifications_list'))
    return render_template('settings/notification_form.html', notif=None)


@notifications_bp.route('/notifications/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'edit')
def edit_notification(id):
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    n = Notification.query.get_or_404(id)
    if request.method == 'POST':
        n.name = request.form.get('name', '').strip()
        n.message_template = request.form.get('message_template', '').strip()
        n.noti_type = request.form.get('noti_type', 'info')
        n.module = request.form.get('module', '').strip() or None
        n.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash(f'Cap nhat mau thong bao [{n.code}] thanh cong!', 'success')
        return redirect(url_for('notifications.notifications_list'))
    return render_template('settings/notification_form.html', notif=n)


@notifications_bp.route('/notifications/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('settings', 'delete')
def delete_notification(id):
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    n = Notification.query.get_or_404(id)
    code = n.code
    db.session.delete(n)
    db.session.commit()
    flash(f'Da xoa mau thong bao [{code}]!', 'success')
    return redirect(url_for('notifications.notifications_list'))


@notifications_bp.route('/notifications/toggle/<int:id>', methods=['POST'])
@login_required
@require_permission('settings', 'edit')
def toggle_notification(id):
    if not _admin_only():
        return jsonify({'ok': False})
    n = Notification.query.get_or_404(id)
    n.is_active = not n.is_active
    db.session.commit()
    return jsonify({'ok': True, 'is_active': n.is_active})


@notifications_bp.route('/notifications/preview/<int:id>')
@login_required
@require_permission('settings', 'view')
def preview_notification(id):
    import re
    n = Notification.query.get_or_404(id)
    placeholders = re.findall(r'\{(\w+)\}', n.message_template)
    sample = {p: f'<{p}>' for p in placeholders}
    try:
        preview = n.message_template.format(**sample)
    except Exception:
        preview = n.message_template
    return jsonify({
        'code': n.code, 'name': n.name,
        'template': n.message_template,
        'preview': preview,
        'placeholders': placeholders,
        'type': n.noti_type,
    })
