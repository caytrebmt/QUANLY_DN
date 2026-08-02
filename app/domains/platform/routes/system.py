from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.database import db
from app.domains.platform.models import SystemConfig
from app.domains.master.models import Product, Unit
from app.domains.inventory.models import UnitConversion
from app.shared.authz import require_permission
from app.shared.constants import Roles

system_bp = Blueprint('system', __name__, url_prefix='')


def _admin_only():
    if current_user.role != Roles.ADMIN:
        flash('Chỉ quản trị viên mới có quyền thực hiện!', 'danger')
        return False
    return True


def _normalize_unit_conversion_factor(raw_factor, factor_mode):
    factor = float(raw_factor or 0)
    mode = (factor_mode or 'from_to_base').strip()
    if factor <= 0:
        return 0.0
    if mode == 'base_to_from':
        return 1.0 / factor
    return factor


@system_bp.route('/')
@login_required
@require_permission('settings', 'view')
def index():
    configs = SystemConfig.query.order_by(
        SystemConfig.group_name, SystemConfig.key).all()
    return render_template('settings/index.html', configs=configs)


@system_bp.route('/save', methods=['POST'])
@login_required
@require_permission('settings', 'edit')
def save():
    for key, value in request.form.items():
        if key.startswith('cfg_'):
            cfg_key = key[4:]
            cfg = SystemConfig.query.filter_by(key=cfg_key).first()
            if cfg:
                cfg.value = value
    db.session.commit()
    flash('Lưu cấu hình thành công!', 'success')
    return redirect(url_for('system.index'))


@system_bp.route('/unit-conversions')
@login_required
@require_permission('settings', 'view')
def unit_conversions():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    product_id = request.args.get('product_id', type=int)
    search = (request.args.get('search', '') or '').strip()

    q = UnitConversion.query.join(Product, UnitConversion.product_id == Product.id)
    if product_id:
        q = q.filter(UnitConversion.product_id == product_id)
    if search:
        q = q.filter(db.or_(
            Product.code.ilike(f'%{search}%'),
            Product.name.ilike(f'%{search}%'),
        ))

    rows = q.order_by(Product.code, UnitConversion.id).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.code).all()
    return render_template(
        'settings/unit_conversions.html',
        rows=rows,
        products=products,
        product_id=product_id,
        search=search,
    )


@system_bp.route('/unit-conversions/create', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'create')
def create_unit_conversion():
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    products = Product.query.filter_by(is_active=True).order_by(Product.code).all()
    units = Unit.query.filter_by(is_active=True).order_by(Unit.name).all()

    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        from_unit_id = request.form.get('from_unit_id', type=int)
        factor_mode = request.form.get('factor_mode', 'from_to_base')
        factor = _normalize_unit_conversion_factor(
            request.form.get('conversion_factor', 0),
            factor_mode
        )
        product = Product.query.get(product_id) if product_id else None
        if not product or not product.unit_id:
            flash('Sản phẩm chưa có đơn vị gốc. Vui lòng cấu hình đơn vị gốc ở danh mục hàng hóa.', 'danger')
            return render_template('settings/unit_conversion_form.html', row=None, products=products, units=units)
        if not from_unit_id:
            flash('Vui lòng chọn đơn vị quy đổi.', 'danger')
            return render_template('settings/unit_conversion_form.html', row=None, products=products, units=units)
        if from_unit_id == product.unit_id:
            flash('Đơn vị quy đổi không được trùng đơn vị gốc của sản phẩm.', 'warning')
            return render_template('settings/unit_conversion_form.html', row=None, products=products, units=units)
        if factor <= 0:
            flash('Hệ số phải lớn hơn 0.', 'danger')
            return render_template('settings/unit_conversion_form.html', row=None, products=products, units=units)

        exists = UnitConversion.query.filter_by(
            product_id=product.id,
            from_unit_id=from_unit_id,
            to_unit_id=product.unit_id,
        ).first()
        if exists:
            flash('Phép quy đổi này đã tồn tại.', 'warning')
            return render_template('settings/unit_conversion_form.html', row=None, products=products, units=units)

        row = UnitConversion(
            product_id=product.id,
            from_unit_id=from_unit_id,
            to_unit_id=product.unit_id,
            conversion_factor=factor,
        )
        db.session.add(row)
        db.session.commit()
        flash('Đã tạo quy đổi đơn vị thành công.', 'success')
        return redirect(url_for('system.unit_conversions'))

    return render_template('settings/unit_conversion_form.html', row=None, products=products, units=units)


@system_bp.route('/unit-conversions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'edit')
def edit_unit_conversion(id):
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    row = UnitConversion.query.get_or_404(id)
    products = Product.query.filter_by(is_active=True).order_by(Product.code).all()
    units = Unit.query.filter_by(is_active=True).order_by(Unit.name).all()

    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        from_unit_id = request.form.get('from_unit_id', type=int)
        factor_mode = request.form.get('factor_mode', 'from_to_base')
        factor = _normalize_unit_conversion_factor(
            request.form.get('conversion_factor', 0),
            factor_mode
        )
        product = Product.query.get(product_id) if product_id else None
        if not product or not product.unit_id:
            flash('Sản phẩm chưa có đơn vị gốc. Vui lòng cấu hình đơn vị gốc ở danh mục hàng hóa.', 'danger')
            return render_template('settings/unit_conversion_form.html', row=row, products=products, units=units)
        if not from_unit_id:
            flash('Vui lòng chọn đơn vị quy đổi.', 'danger')
            return render_template('settings/unit_conversion_form.html', row=row, products=products, units=units)
        if from_unit_id == product.unit_id:
            flash('Đơn vị quy đổi không được trùng đơn vị gốc của sản phẩm.', 'warning')
            return render_template('settings/unit_conversion_form.html', row=row, products=products, units=units)
        if factor <= 0:
            flash('Hệ số phải lớn hơn 0.', 'danger')
            return render_template('settings/unit_conversion_form.html', row=row, products=products, units=units)

        exists = UnitConversion.query.filter(
            UnitConversion.id != row.id,
            UnitConversion.product_id == product.id,
            UnitConversion.from_unit_id == from_unit_id,
            UnitConversion.to_unit_id == product.unit_id,
        ).first()
        if exists:
            flash('Phép quy đổi này đã tồn tại.', 'warning')
            return render_template('settings/unit_conversion_form.html', row=row, products=products, units=units)

        row.product_id = product.id
        row.from_unit_id = from_unit_id
        row.to_unit_id = product.unit_id
        row.conversion_factor = factor
        db.session.commit()
        flash('Đã cập nhật quy đổi đơn vị.', 'success')
        return redirect(url_for('system.unit_conversions'))

    return render_template('settings/unit_conversion_form.html', row=row, products=products, units=units)


@system_bp.route('/unit-conversions/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('settings', 'delete')
def delete_unit_conversion(id):
    if not _admin_only():
        return redirect(url_for('dashboard.index'))
    row = UnitConversion.query.get_or_404(id)
    db.session.delete(row)
    db.session.commit()
    flash('Đã xóa quy đổi đơn vị.', 'success')
    return redirect(url_for('system.unit_conversions'))
