from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.database import db
from app.domains.master.models import Warehouse
from app.shared.authz import require_permission

warehouses_bp = Blueprint('warehouses', __name__, url_prefix='/warehouses')


@warehouses_bp.route('/')
@login_required
@require_permission('inventory', 'view')
def index():
    warehouses = Warehouse.query.order_by(Warehouse.code).all()
    return render_template('warehouses/index.html', warehouses=warehouses)


@warehouses_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('inventory', 'create')
def create():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        if not code or not name:
            flash('Mã kho và tên kho không được để trống!', 'danger')
            return render_template('warehouses/form.html', warehouse=None)
        if Warehouse.query.filter_by(code=code).first():
            flash(f'Mã kho {code} đã tồn tại!', 'danger')
            return render_template('warehouses/form.html', warehouse=None)
        w = Warehouse(code=code, name=name,
                      address=request.form.get('address', '').strip(),
                      manager=request.form.get('manager', '').strip(),
                      phone=request.form.get('phone', '').strip())
        db.session.add(w)
        db.session.commit()
        flash(f'Thêm kho {code} thành công!', 'success')
        return redirect(url_for('warehouses.index'))
    return render_template('warehouses/form.html', warehouse=None)


@warehouses_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('inventory', 'edit')
def edit(id):
    w = Warehouse.query.get_or_404(id)
    if request.method == 'POST':
        w.name = request.form.get('name', '').strip()
        w.address = request.form.get('address', '').strip()
        w.manager = request.form.get('manager', '').strip()
        w.phone = request.form.get('phone', '').strip()
        w.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash(f'Cập nhật kho {w.code} thành công!', 'success')
        return redirect(url_for('warehouses.index'))
    return render_template('warehouses/form.html', warehouse=w)


@warehouses_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('inventory', 'delete')
def delete(id):
    w = Warehouse.query.get_or_404(id)
    w.is_active = False
    db.session.commit()
    flash(f'Đã vô hiệu hóa kho {w.code}.', 'warning')
    return redirect(url_for('warehouses.index'))
