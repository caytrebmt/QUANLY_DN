from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.database import db
from app.domains.master.models import Unit
from app.shared.authz import require_permission

units_bp = Blueprint('units', __name__, url_prefix='/units')


def _sync_units_id_sequence():
    db.session.execute(text("""
        SELECT setval(
            pg_get_serial_sequence('units', 'id'),
            COALESCE((SELECT MAX(id) FROM units), 1),
            true
        )
    """))


@units_bp.route('/')
@login_required
@require_permission('products', 'view')
def index():
    from sqlalchemy import func
    from app.domains.master.models import Product
    units = Unit.query.order_by(Unit.code).all()
    counts_raw = db.session.query(
        Product.unit_id, func.count(Product.id)
    ).filter(Product.unit_id.isnot(None)).group_by(Product.unit_id).all()
    product_counts = {uid: cnt for uid, cnt in counts_raw}
    return render_template('units/index.html', units=units, product_counts=product_counts)


@units_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('products', 'create')
def create():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        if not code or not name:
            flash('Mã và tên đơn vị tính không được để trống!', 'danger')
            return render_template('units/form.html', unit=None)
        if Unit.query.filter_by(code=code).first():
            flash(f'Mã ĐVT {code} đã tồn tại!', 'danger')
            return render_template('units/form.html', unit=None)
        u = Unit(code=code, name=name,
                 description=request.form.get('description', '').strip())
        db.session.add(u)
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            err = str(getattr(e, "orig", e))
            if "units_pkey" in err or "Key (id)=" in err:
                try:
                    _sync_units_id_sequence()
                    db.session.add(Unit(
                        code=code,
                        name=name,
                        description=request.form.get('description', '').strip(),
                    ))
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    if Unit.query.filter_by(code=code).first():
                        flash(f'Mã ĐVT {code} đã tồn tại!', 'danger')
                    else:
                        flash('Không thể thêm đơn vị do lỗi dữ liệu trùng. Vui lòng thử lại.', 'danger')
                    return render_template('units/form.html', unit=None)
            elif "units_code_key" in err:
                flash(f'Mã ĐVT {code} đã tồn tại!', 'danger')
                return render_template('units/form.html', unit=None)
            else:
                flash(f'Lỗi lưu dữ liệu: {err}', 'danger')
                return render_template('units/form.html', unit=None)
        flash(f'Thêm đơn vị tính {code} thành công!', 'success')
        return redirect(url_for('units.index'))
    return render_template('units/form.html', unit=None)


@units_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('products', 'edit')
def edit(id):
    u = Unit.query.get_or_404(id)
    if request.method == 'POST':
        u.name = request.form.get('name', '').strip()
        u.description = request.form.get('description', '').strip()
        u.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash(f'Cập nhật ĐVT {u.code} thành công!', 'success')
        return redirect(url_for('units.index'))
    return render_template('units/form.html', unit=u)


@units_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('products', 'delete')
def delete(id):
    u = Unit.query.get_or_404(id)
    if u.products.count() > 0:
        u.is_active = False
        db.session.commit()
        flash(f'ĐVT {u.code} đã vô hiệu hóa (đang được sử dụng).', 'warning')
    else:
        db.session.delete(u)
        db.session.commit()
        flash(f'Xóa ĐVT {u.code} thành công!', 'success')
    return redirect(url_for('units.index'))
