from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.database import db
from app.domains.master.models import Product, Warehouse
from app.domains.inventory.models import OpeningStock, Inventory, InventoryHistory
from app.domains.master.services.product_code_service import get_or_create_product_by_name
from app.shared.authz import require_permission
import io, pandas as pd
import re
from itertools import zip_longest

opening_stock_bp = Blueprint('opening_stock', __name__, url_prefix='/opening-stock')


@opening_stock_bp.route('/')
@login_required
@require_permission('opening_stock', 'view')
def index():
    page = request.args.get('page', 1, type=int)
    warehouse_id = request.args.get('warehouse_id', '')
    period_date  = request.args.get('period_date', '')
    search       = request.args.get('search', '').strip()

    q = OpeningStock.query
    if warehouse_id:
        q = q.filter_by(warehouse_id=int(warehouse_id))
    if period_date:
        q = q.filter_by(period_date=datetime.strptime(period_date, '%Y-%m-%d').date())
    if search:
        q = q.join(Product).filter(
            db.or_(
                Product.code.ilike(f'%{search}%'),
                Product.name.ilike(f'%{search}%'),
            )
        )

    records = q.order_by(OpeningStock.period_date.desc()).paginate(
        page=page, per_page=30, error_out=False)

    warehouses = Warehouse.query.filter_by(is_active=True).all()
    return render_template('opening_stock/index.html',
                           records=records, warehouses=warehouses,
                           warehouse_id=warehouse_id, period_date=period_date,
                           search=search)


@opening_stock_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('opening_stock', 'create')
def create():
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    products   = Product.query.filter_by(is_active=True).order_by(Product.code).all()

    if request.method == 'POST':
        period_date  = request.form.get('period_date', '')
        warehouse_id = request.form.get('warehouse_id', type=int)

        # Backward compatible: support both product_id[] (old UI) and product_name[] (new UI)
        product_ids   = request.form.getlist('product_id[]')
        product_names = request.form.getlist('product_name[]')

        quantities = request.form.getlist('quantity[]')
        unit_costs = request.form.getlist('unit_cost[]')
        notes      = request.form.getlist('note[]')

        if not period_date or not warehouse_id:
            flash('Vui lòng chọn ngày và kho!', 'danger')
            return render_template('opening_stock/form.html',
                                   warehouses=warehouses, products=products)
        pdate = datetime.strptime(period_date, '%Y-%m-%d').date()
        saved = 0
        for pid, pname, qty, cost, note in zip_longest(
            product_ids, product_names, quantities, unit_costs, notes, fillvalue=''
        ):
            pid = (pid or '').strip()
            pname = (pname or '').strip()
            if (not pid and not pname) or not qty:
                continue

            qty_val = float(qty or 0)
            # Giảm rác SKU: nếu quantity <= 0 thì bỏ qua (không tạo Product mới)
            if qty_val <= 0:
                continue
            cost_val = float(cost or 0)

            # UI: ưu tiên product_id nếu có; nếu không có hoặc product_id trống
            product_obj = None
            if pid:
                try:
                    product_obj = Product.query.get(int(pid))
                except Exception:
                    product_obj = None

            # Nếu pid tồn tại nhưng user không nhập tên, vẫn lấy product_id (không tạo theo tên)

            # Nếu người dùng không chọn product (pid rỗng) nhưng có nhập tên thì auto-create/find
            # Nếu pid có giá trị nhưng không có tên thì vẫn dùng product_id (không bắt buộc phải nhập Tên hàng)
            
            if (not product_obj) and pname:
                product_obj = get_or_create_product_by_name(
                    pname,
                    created_by=current_user.id if getattr(current_user, 'is_authenticated', False) else None
                )

            if not product_obj:
                continue


            pid_int = int(product_obj.id)

            # Check if already exists, update
            existing = OpeningStock.query.filter_by(
                period_date=pdate, product_id=pid_int, warehouse_id=warehouse_id
            ).first()
            if existing:
                existing.quantity = qty_val
                existing.unit_cost = cost_val
                existing.amount = qty_val * cost_val
                existing.note = note.strip() if note else ''
                existing.is_posted = False
            else:
                os = OpeningStock(
                    period_date=pdate, product_id=pid_int,
                    warehouse_id=warehouse_id,
                    quantity=qty_val, unit_cost=cost_val,
                    amount=qty_val * cost_val,
                    note=note.strip() if note else '',
                    created_by=current_user.id
                )
                db.session.add(os)

            saved += 1
        db.session.commit()
        flash(f'Đã lưu {saved} dòng tồn đầu kỳ!', 'success')
        return redirect(url_for('opening_stock.index'))

    from datetime import date
    return render_template('opening_stock/form.html',
                           warehouses=warehouses, products=products,
                           today=date.today().isoformat())


@opening_stock_bp.route('/post/<int:id>', methods=['POST'])
@login_required
@require_permission('opening_stock', 'edit')
def post_single(id):
    """Cập nhật 1 dòng tồn đầu kỳ vào tồn kho"""
    os = OpeningStock.query.get_or_404(id)
    _post_to_inventory(os)
    db.session.commit()
    flash(f'Đã cập nhật tồn đầu kỳ cho hàng {os.product.code if os.product else ""}!', 'success')
    return redirect(url_for('opening_stock.index'))


@opening_stock_bp.route('/post-all', methods=['POST'])
@login_required
@require_permission('opening_stock', 'edit')
def post_all():
    """Cập nhật tất cả dòng chưa được post"""
    records = OpeningStock.query.filter_by(is_posted=False).all()
    count = 0
    for os in records:
        _post_to_inventory(os)
        count += 1
    db.session.commit()
    flash(f'Đã cập nhật {count} dòng tồn đầu kỳ vào tồn kho!', 'success')
    return redirect(url_for('opening_stock.index'))


def _post_to_inventory(os_record):
    """Helper: ghi tồn đầu kỳ vào bảng inventory + history"""
    inv = Inventory.query.filter_by(
        product_id=os_record.product_id,
        warehouse_id=os_record.warehouse_id
    ).first()
    if not inv:
        inv = Inventory(product_id=os_record.product_id,
                        warehouse_id=os_record.warehouse_id,
                        quantity=0, avg_cost=0)
        db.session.add(inv)
        db.session.flush()

    qty_before = float(inv.quantity or 0)
    qty_add    = float(os_record.quantity or 0)
    cost       = float(os_record.unit_cost or 0)
    new_qty    = qty_before + qty_add
    # Weighted average cost
    if new_qty > 0:
        new_avg = ((qty_before * float(inv.avg_cost or 0)) + (qty_add * cost)) / new_qty
    else:
        new_avg = cost
    inv.quantity     = new_qty
    inv.avg_cost     = new_avg
    inv.last_updated = datetime.utcnow()

    hist = InventoryHistory(
        product_id=os_record.product_id,
        warehouse_id=os_record.warehouse_id,
        transaction_type='opening',
        reference_code=f'OPEN-{os_record.period_date}',
        quantity_change=qty_add,
        quantity_before=qty_before,
        quantity_after=new_qty,
        unit_cost=cost,
        note=f'Tồn đầu kỳ {os_record.period_date}'
    )
    db.session.add(hist)
    os_record.is_posted = True


@opening_stock_bp.route('/import-excel', methods=['POST'])
@login_required
@require_permission('opening_stock', 'create')
def import_excel():
    if 'file' not in request.files:
        flash('Vui lòng chọn file!', 'danger')
        return redirect(url_for('opening_stock.index'))

    file         = request.files['file']
    period_date  = request.form.get('period_date', date.today().isoformat())
    warehouse_id = request.form.get('warehouse_id', type=int)

    if not warehouse_id:
        flash('Vui lòng chọn kho!', 'danger')
        return redirect(url_for('opening_stock.index'))

    try:
        df = pd.read_excel(file)
        pdate = datetime.strptime(period_date, '%Y-%m-%d').date()
        saved = 0
        for _, row in df.iterrows():
            code = str(row.get('Mã hàng', '')).strip()
            if not code: continue
            p = Product.query.filter_by(code=code).first()
            if not p: continue
            qty  = float(row.get('Số lượng', 0) or 0)
            cost = float(row.get('Giá vốn', 0) or 0)
            if qty <= 0: continue
            existing = OpeningStock.query.filter_by(
                period_date=pdate, product_id=p.id, warehouse_id=warehouse_id
            ).first()
            if existing:
                existing.quantity=qty; existing.unit_cost=cost
                existing.amount=qty*cost; existing.is_posted=False
            else:
                db.session.add(OpeningStock(
                    period_date=pdate, product_id=p.id,
                    warehouse_id=warehouse_id,
                    quantity=qty, unit_cost=cost, amount=qty*cost,
                    created_by=current_user.id
                ))
            saved += 1
        db.session.commit()
        flash(f'Import thành công {saved} dòng tồn đầu kỳ!', 'success')
    except Exception as e:
        flash(f'Lỗi import: {str(e)}', 'danger')
    return redirect(url_for('opening_stock.index'))


@opening_stock_bp.route('/template')
@login_required
@require_permission('opening_stock', 'view')
def download_template():
    sample = pd.DataFrame([{
        'Mã hàng': 'SP001', 'Tên hàng': 'Sản phẩm mẫu',
        'Đơn vị': 'Cái', 'Số lượng': 100, 'Giá vốn': 150000,
    }])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as w:
        sample.to_excel(w, index=False, sheet_name='Tồn đầu kỳ')
    output.seek(0)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='mau_ton_dau_ky.xlsx')


@opening_stock_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('opening_stock', 'edit')
def edit(id):
    """Sửa 1 dòng tồn đầu kỳ (chỉ khi chưa post)"""

    record = OpeningStock.query.get_or_404(id)

    if record.is_posted:
        flash('Không thể sửa dòng đã cập nhật vào kho!', 'warning')
        return redirect(url_for('opening_stock.index'))

    warehouses = Warehouse.query.filter_by(is_active=True).all()

    products = Product.query.filter_by(
        is_active=True
    ).order_by(Product.code).all()

    if request.method == 'POST':

        try:

            print(request.form)

            product_id = request.form.get('product_id', type=int)
            warehouse_id = request.form.get('warehouse_id', type=int)
            period_date = request.form.get('period_date', '')

            quantity = float(
                request.form.get('quantity', 0) or 0
            )

            unit_cost = float(
                request.form.get('unit_cost', 0) or 0
            )

            note = request.form.get('note', '').strip()

            # Validate
            if not product_id or not warehouse_id or not period_date:

                flash('Vui lòng điền đầy đủ thông tin!', 'danger')

                return render_template(
                    'opening_stock/edit.html',
                    record=record,
                    warehouses=warehouses,
                    products=products
                )

            # Update
            record.product_id = product_id
            record.warehouse_id = warehouse_id

            record.period_date = datetime.strptime(
                period_date,
                '%Y-%m-%d'
            ).date()

            record.quantity = quantity
            record.unit_cost = unit_cost
            record.amount = quantity * unit_cost
            record.note = note

            db.session.commit()

            flash('Cập nhật tồn đầu kỳ thành công!', 'success')

            return redirect(url_for('opening_stock.index'))

        except Exception as e:

            db.session.rollback()

            print('ERROR:', e)

            flash(f'Lỗi cập nhật: {str(e)}', 'danger')

    return render_template(
        'opening_stock/edit.html',
        record=record,
        warehouses=warehouses,
        products=products
    )


@opening_stock_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('opening_stock', 'delete')
def delete(id):
    """Xóa 1 dòng tồn đầu kỳ (chỉ khi chưa post)"""
    record = OpeningStock.query.get_or_404(id)

    if record.is_posted:
        flash('Không thể xóa dòng đã cập nhật vào kho!', 'warning')
        return redirect(url_for('opening_stock.index'))

    product_code = record.product.code if record.product else ''
    db.session.delete(record)
    db.session.commit()
    flash(f'Đã xóa tồn đầu kỳ của {product_code}!', 'success')
    return redirect(url_for('opening_stock.index'))
