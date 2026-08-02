from datetime import date, datetime, timedelta
from decimal import Decimal
from itertools import zip_longest

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.database import db
from app.domains.master.models import Customer, Product, Unit, Warehouse
from app.models.transaction import Quotation, QuotationItem
from app.domains.inventory.models import StockOut, StockOutItem, UnitConversion, Inventory
from app.shared.authz import require_permission
from app.domains.platform.services.company_service import get_company_value
from app.shared.print import render_pdf
from app.domains.inventory.services.unit_display import build_item_qty_display_map

quotations_bp = Blueprint('quotations', __name__, url_prefix='/quotations')


def _generate_code():
    today = date.today().strftime('%y%m%d')
    prefix = (get_company_value('quotation_prefix', 'BG') or 'BG').upper()
    stem = f'{prefix}-{today}-'
    last = Quotation.query.filter(Quotation.code.like(f'{stem}%')).order_by(
        Quotation.code.desc()).first()
    num = int(last.code.split('-')[-1]) + 1 if last else 1
    return f'{stem}{num:03d}'


def _resolve_item_factor(product, item_unit_id):
    base_unit_id = product.unit_id
    line_unit_id = item_unit_id or base_unit_id
    if not base_unit_id or not line_unit_id or int(line_unit_id) == int(base_unit_id):
        return True, 1.0, None

    conv = UnitConversion.query.filter_by(
        product_id=product.id,
        from_unit_id=int(line_unit_id),
        to_unit_id=int(base_unit_id),
    ).first()
    if conv and float(conv.conversion_factor or 0) > 0:
        return True, float(conv.conversion_factor), None

    rev = UnitConversion.query.filter_by(
        product_id=product.id,
        from_unit_id=int(base_unit_id),
        to_unit_id=int(line_unit_id),
    ).first()
    if rev and float(rev.conversion_factor or 0) > 0:
        return True, 1.0 / float(rev.conversion_factor), None

    from_unit = Unit.query.get(line_unit_id)
    to_unit = Unit.query.get(base_unit_id)
    return False, None, (
        f"Thiếu quy đổi đơn vị: {from_unit.name if from_unit else line_unit_id} -> "
        f"{to_unit.name if to_unit else base_unit_id}"
    )


def _build_unit_conv_map(products):
    conv_rows = UnitConversion.query.all()
    product_base_units = {p.id: p.unit_id for p in products}
    unit_conv_map = {}
    for c in conv_rows:
        pid = str(c.product_id)
        unit_conv_map.setdefault(pid, {})
        base_uid = product_base_units.get(c.product_id)
        factor = float(c.conversion_factor or 1)
        if factor <= 0:
            continue
        if base_uid and c.to_unit_id == base_uid:
            unit_conv_map[pid][str(c.from_unit_id)] = factor
        elif base_uid and c.from_unit_id == base_uid:
            unit_conv_map[pid][str(c.to_unit_id)] = 1 / factor
        else:
            unit_conv_map[pid][str(c.from_unit_id)] = factor
    return unit_conv_map


def _parse_items():
    product_ids = request.form.getlist('product_id[]')
    quantities = request.form.getlist('quantity[]')
    unit_prices = request.form.getlist('unit_price[]')
    vat_rates = request.form.getlist('vat_rate[]')
    unit_ids = request.form.getlist('unit_item_id[]')
    factors = request.form.getlist('factor_item[]')
    notes = request.form.getlist('note_item[]')

    normalized = []
    for idx, (pid, qty, price, vat, u, _f, note) in enumerate(
        zip_longest(product_ids, quantities, unit_prices, vat_rates, unit_ids, factors, notes, fillvalue=''),
        start=1,
    ):
        try:
            qty_val = float(qty or 0)
        except Exception:
            qty_val = 0
        if not pid or qty_val <= 0:
            continue
        product = Product.query.get(int(pid))
        if not product:
            raise ValueError(f"Dòng {idx}: không tìm thấy sản phẩm.")
        item_unit_id = int(u) if u else None
        ok, factor, err = _resolve_item_factor(product, item_unit_id)
        if not ok:
            raise ValueError(f"Dòng {idx} - {product.code}: {err}.")
        normalized.append({
            'product_id': int(pid),
            'quantity': qty_val,
            'unit_price': float(price or 0),
            'vat_rate': float(vat or 0),
            'unit_id': item_unit_id,
            'factor': factor,
            'note': (note or '').strip(),
        })

    if not normalized:
        raise ValueError('Vui lòng thêm ít nhất một dòng hàng hợp lệ.')
    return normalized


def _apply_header(q):
    q.date = datetime.strptime(request.form.get('date', date.today().isoformat()), '%Y-%m-%d').date()
    valid_until = request.form.get('valid_until', '').strip()
    q.valid_until = datetime.strptime(valid_until, '%Y-%m-%d').date() if valid_until else None
    q.customer_id = request.form.get('customer_id', type=int) or None
    q.recipient_name = request.form.get('recipient_name', '').strip()
    q.recipient_address = request.form.get('recipient_address', '').strip()
    q.recipient_phone = request.form.get('recipient_phone', '').strip()
    q.recipient_email = request.form.get('recipient_email', '').strip()
    q.discount_amount = float(request.form.get('discount_amount', 0) or 0)
    q.vat_mode = request.form.get('vat_mode', 'grouped')
    q.vat_rate_grouped = float(request.form.get('vat_rate_grouped', 0) or 0) if q.vat_mode == 'grouped' else 0
    q.note = request.form.get('note', '').strip()
    q.terms = request.form.get('terms', '').strip()


def _add_items(q, items):
    for row in items:
        item = QuotationItem(
            quotation_id=q.id,
            product_id=row['product_id'],
            quantity=row['quantity'],
            unit_id=row['unit_id'],
            conversion_factor=row['factor'],
            unit_price=row['unit_price'],
            vat_rate=0 if q.vat_mode == 'grouped' else row['vat_rate'],
            note=row['note'],
        )
        item.calculate()
        db.session.add(item)


def _render_form(q):
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    products = Product.query.filter_by(is_active=True).order_by(Product.code).all()
    units = Unit.query.filter_by(is_active=True).order_by(Unit.name).all()
    return render_template(
        'quotations/form.html',
        quotation=q,
        customers=customers,
        products=products,
        units=units,
        unit_conv_map=_build_unit_conv_map(products),
        today=date.today(),
        default_valid_until=date.today() + timedelta(days=7),
    )


@quotations_bp.route('/')
@login_required
@require_permission('quotations', 'view')
def index():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    customer_id = request.args.get('customer_id', '')
    page = request.args.get('page', 1, type=int)

    q = Quotation.query
    if search:
        q = q.filter(db.or_(Quotation.code.ilike(f'%{search}%'),
                            Quotation.note.ilike(f'%{search}%'),
                            Quotation.recipient_name.ilike(f'%{search}%')))
    if status:
        q = q.filter(func.lower(Quotation.status) == status.lower())
    if customer_id:
        q = q.filter(Quotation.customer_id == int(customer_id))

    quotations = q.order_by(Quotation.date.desc(), Quotation.code.desc()).paginate(
        page=page, per_page=20, error_out=False)
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    return render_template('quotations/index.html', quotations=quotations,
                           customers=customers, search=search, status=status,
                           customer_id=customer_id)


@quotations_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('quotations', 'create')
def create():
    if request.method == 'POST':
        try:
            items = _parse_items()
            q = Quotation(code=_generate_code(), status='draft', created_by=current_user.id)
            _apply_header(q)
            db.session.add(q)
            db.session.flush()
            _add_items(q, items)
            db.session.flush()
            q.calculate_totals()
            db.session.commit()
            flash(f'Tạo bảng báo giá {q.code} thành công.', 'success')
            return redirect(url_for('quotations.detail', id=q.id))
        except Exception as e:
            db.session.rollback()
            flash(str(e), 'danger')
    return _render_form(None)


@quotations_bp.route('/<int:id>')
@login_required
@require_permission('quotations', 'view')
def detail(id):
    q = Quotation.query.get_or_404(id)
    items = q.items.order_by(QuotationItem.id.asc()).all()
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    qty_display_map = build_item_qty_display_map(items)
    return render_template('quotations/detail.html', quotation=q, items=items,
                           warehouses=warehouses, qty_display_map=qty_display_map)


@quotations_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('quotations', 'edit')
def edit(id):
    q = Quotation.query.get_or_404(id)
    if q.stock_out_id:
        flash('Báo giá đã chuyển phiếu xuất, không nên chỉnh sửa trực tiếp.', 'warning')
        return redirect(url_for('quotations.detail', id=q.id))

    if request.method == 'POST':
        try:
            items = _parse_items()
            _apply_header(q)
            QuotationItem.query.filter_by(quotation_id=q.id).delete()
            db.session.flush()
            _add_items(q, items)
            db.session.flush()
            q.calculate_totals()
            db.session.commit()
            flash(f'Cập nhật bảng báo giá {q.code} thành công.', 'success')
            return redirect(url_for('quotations.detail', id=q.id))
        except Exception as e:
            db.session.rollback()
            flash(str(e), 'danger')
    return _render_form(q)


@quotations_bp.route('/status/<int:id>/<status>', methods=['POST'])
@login_required
@require_permission('quotations', 'edit')
def set_status(id, status):
    q = Quotation.query.get_or_404(id)
    if status not in {'draft', 'sent', 'accepted', 'cancelled'}:
        flash('Trạng thái báo giá không hợp lệ.', 'danger')
        return redirect(url_for('quotations.detail', id=id))
    q.status = status
    db.session.commit()
    flash(f'Đã cập nhật trạng thái báo giá {q.code}.', 'success')
    return redirect(url_for('quotations.detail', id=id))


@quotations_bp.route('/convert/<int:id>', methods=['POST'])
@login_required
@require_permission('stock_out', 'create')
def convert_to_stock_out(id):
    q = Quotation.query.get_or_404(id)
    if q.stock_out_id:
        return redirect(url_for('stock_out.detail', id=q.stock_out_id))

    warehouse_id = request.form.get('warehouse_id', type=int)
    if not warehouse_id:
        flash('Vui lòng chọn kho xuất để chuyển báo giá.', 'danger')
        return redirect(url_for('quotations.detail', id=id))

    from app.routes.stock_out import _generate_code as generate_stock_out_code

    so = StockOut(
        code=generate_stock_out_code(),
        date=date.today(),
        customer_id=q.customer_id,
        warehouse_id=warehouse_id,
        discount_amount=float(q.discount_amount or 0),
        vat_mode=q.vat_mode,
        vat_rate_grouped=float(q.vat_rate_grouped or 0),
        note=f'Chuyển từ bảng báo giá {q.code}. {q.note or ""}'.strip(),
        status='draft',
        created_by=current_user.id,
    )
    db.session.add(so)
    db.session.flush()

    for qi in q.items.order_by(QuotationItem.id.asc()).all():
        inv = Inventory.query.filter_by(product_id=qi.product_id, warehouse_id=warehouse_id).first()
        item = StockOutItem(
            stock_out_id=so.id,
            product_id=qi.product_id,
            quantity=float(qi.quantity or 0),
            unit_id=qi.unit_id,
            conversion_factor=float(qi.conversion_factor or 1),
            unit_price=float(qi.unit_price or 0),
            cost_price=float(inv.avg_cost or 0) if inv else 0,
            vat_rate=float(qi.vat_rate or 0),
        )
        item.calculate()
        db.session.add(item)

    db.session.flush()
    so.calculate_totals()
    q.stock_out_id = so.id
    q.status = 'converted'
    db.session.commit()
    flash(f'Đã chuyển bảng báo giá {q.code} sang phiếu xuất {so.code}.', 'success')
    return redirect(url_for('stock_out.detail', id=so.id))


@quotations_bp.route('/print/<int:id>')
@login_required
@require_permission('quotations', 'view')
def print_pdf(id):
    q = Quotation.query.get_or_404(id)
    items = q.items.order_by(QuotationItem.id.asc()).all()
    cfg = {
        'name': get_company_value('company_name', 'ERP-VIET'),
        'address': get_company_value('company_address', ''),
        'tax_code': get_company_value('company_tax_code', ''),
        'phone': get_company_value('company_phone', ''),
    }
    pdf = render_pdf(
        'print/quotation.html',
        {'quotation': q, 'items': items, 'company': cfg},
        base_url=request.host_url,
    )
    return send_file(pdf, mimetype='application/pdf', as_attachment=False,
                     download_name=f'bao_gia_{q.code}.pdf')


@quotations_bp.route('/print/html/<int:id>')
@login_required
@require_permission('quotations', 'view')
def print_html(id):
    q = Quotation.query.get_or_404(id)
    items = q.items.order_by(QuotationItem.id.asc()).all()
    cfg = {
        'name': get_company_value('company_name', 'ERP-VIET'),
        'address': get_company_value('company_address', ''),
        'tax_code': get_company_value('company_tax_code', ''),
        'phone': get_company_value('company_phone', ''),
    }
    html = render_template(
        'print/quotation_browser.html',
        quotation=q,
        items=items,
        company=cfg,
    )
    return jsonify({'ok': True, 'html': html})
