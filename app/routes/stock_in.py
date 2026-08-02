from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, send_file)
from flask_babel import gettext as _
from flask_login import login_required, current_user
from app.database import db
from sqlalchemy import func
from app.domains.master.models import Product, Supplier, Warehouse, Unit
from app.domains.inventory.models import (
    StockIn, StockInItem, UnitConversion,
    Inventory, InventoryHistory,
)
from app.domains.inventory.services.inventory_service import InventoryService
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.pdf_exporter import PdfExporter
from app.domains.platform.services.company_service import get_company_value
from app.domains.inventory.services.stock_document_service import StockDocumentService
from app.domains.finance.services.debt_service import DebtService
from app.domains.finance.services.vat_service import VatService
from app.shared.authz import require_permission
from app.domains.inventory.services.unit_display import build_item_qty_display_map
from app.shared.constants import DocStatus
from decimal import Decimal, ROUND_HALF_UP
def _dec(v): return Decimal(str(v or 0))
def _money(v): return _dec(v).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

stock_in_bp = Blueprint('stock_in', __name__, url_prefix='/stock-in')


def _is_confirmed(status_value):
    return (status_value or '').strip().lower() == DocStatus.CONFIRMED


def _generate_code():
    """Auto-generate phiếu nhập code theo tiền tố cấu hình: <prefix>-YYMMDD-XXX"""
    today = date.today().strftime('%y%m%d')
    prefix_cfg = (get_company_value('invoice_prefix_in', 'PN') or 'PN').upper()
    prefix = f'{prefix_cfg}-{today}-'
    last = StockIn.query.filter(StockIn.code.like(f'{prefix}%')).order_by(
        StockIn.code.desc()).first()
    if last:
        num = int(last.code.split('-')[-1]) + 1
    else:
        num = 1
    return f'{prefix}{num:03d}'



def _resolve_item_factor(product, item_unit_id):
    """Resolve conversion factor from item unit -> product base unit."""
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



@stock_in_bp.route('/')
@login_required
@require_permission('stock_in', 'view')
def index():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    supplier_id = request.args.get('supplier_id', '', type=str)
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    page = request.args.get('page', 1, type=int)

    q = StockIn.query
    if search:
        q = q.filter(db.or_(StockIn.code.ilike(f'%{search}%'),
                            StockIn.invoice_no.ilike(f'%{search}%')))
    if status:
        q = q.filter(func.lower(StockIn.status) == status.lower())
    if supplier_id:
        q = q.filter(StockIn.supplier_id == int(supplier_id))
    if from_date:
        q = q.filter(StockIn.date >= datetime.strptime(
            from_date, '%Y-%m-%d').date())
    if to_date:
        q = q.filter(StockIn.date <= datetime.strptime(
            to_date, '%Y-%m-%d').date())

    q = q.order_by(StockIn.date.desc(), StockIn.code.desc())
    stock_ins = q.paginate(page=page, per_page=20, error_out=False)
    suppliers = Supplier.query.filter_by(
        is_active=True).order_by(Supplier.name).all()

    return render_template('stock_in/index.html',
                           stock_ins=stock_ins, search=search,
                           status=status, suppliers=suppliers,
                           supplier_id=supplier_id, from_date=from_date,
                           to_date=to_date)


@stock_in_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('stock_in', 'create')
def create():
    if request.method == 'POST':
        warehouse_id = request.form.get('warehouse_id', type=int)
        if not warehouse_id:
            flash(_('Please select warehouse!'), 'danger')
            return _render_form(None)

        vat_manual = request.form.get('vat_manual') == 'on'
        si = StockIn(
            code=_generate_code(),
            date=datetime.strptime(request.form.get(
                'date', date.today().isoformat()), '%Y-%m-%d').date(),
            supplier_id=request.form.get('supplier_id', type=int) or None,
            warehouse_id=warehouse_id,
            unit_id=request.form.get('unit_id', type=int) or None,
            conversion_factor=_dec(
                request.form.get('conversion_factor', 1) or 1),
            invoice_no=request.form.get('invoice_no', '').strip(),
            invoice_series=request.form.get('invoice_series', '').strip(),
            invoice_date=_parse_date(request.form.get('invoice_date', '')),
            discount_amount=_dec(request.form.get('discount_amount', 0) or 0),
            note=request.form.get('note', '').strip(),
            vat_manual=vat_manual,
            vat_manual_val=_dec(request.form.get(
                'vat_manual_val', 0) or 0) if vat_manual else _dec(0),
            status=DocStatus.DRAFT,
            created_by=current_user.id,
        )

        # Parse items
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        vat_rates = request.form.getlist('vat_rate[]')
        unit_ids = request.form.getlist('unit_item_id[]')
        factors = request.form.getlist('factor_item[]')

        from itertools import zip_longest
        items_data = []
        for pid, qty, price, vat, u, f in zip_longest(product_ids, quantities, unit_prices, vat_rates, unit_ids, factors, fillvalue=''):
            try:
                qty_val = float(qty or 0)
            except Exception:
                qty_val = 0
            if not pid or qty_val <= 0:
                continue
            items_data.append((pid, qty_val, price, vat, u, f))

        if not items_data:
            flash(_('Please add at least one valid item!'), 'danger')
            return _render_form(None)

        normalized_items = []
        for idx, (pid, qty, price, vat, u, _f) in enumerate(items_data, start=1):
            product = Product.query.get(int(pid))
            if not product:
                flash(
                    f"Dòng {idx}: không tìm thấy sản phẩm (ID={pid}).", 'danger')
                return _render_form(None)
            item_unit_id = int(u) if u else None
            ok, factor, err = _resolve_item_factor(product, item_unit_id)
            if not ok:
                flash(
                    f"Dòng {idx} - {product.code}: {err}. Vui lòng khai báo tại Cài đặt > Quy đổi đơn vị.",
                    'danger'
                )
                return _render_form(None)
            # Nếu không nhập giá, lấy purchase_price từ sản phẩm
            resolved_price = _dec(price) if price and _dec(price) > 0 else _dec(product.purchase_price or 0)
            # Nếu không nhập VAT, lấy vat_rate từ sản phẩm
            resolved_vat = _dec(vat) if vat and _dec(vat) >= 0 and str(vat).strip() != '' else _dec(product.vat_rate or 0)
            normalized_items.append((int(pid), _dec(qty), resolved_price, resolved_vat, item_unit_id, _dec(factor) if factor else _dec(1)))

        db.session.add(si)
        db.session.flush()

        for pid, qty, price, vat, u, factor in normalized_items:
            item = StockInItem(
                stock_in_id=si.id,
                product_id=pid,
                quantity=qty,
                unit_id=u,
                conversion_factor=factor,
                unit_price=price,
                vat_rate=vat,
            )
            item.calculate()
            db.session.add(item)

        db.session.flush()
        si.calculate_totals()
        db.session.commit()
        flash(_('Created stock-in %(code)s successfully!', code=si.code), 'success')
        return redirect(url_for('stock_in.detail', id=si.id))

    return _render_form(None)


@stock_in_bp.route('/<int:id>')
@login_required
@require_permission('stock_in', 'view')
def detail(id):
    si = StockIn.query.get_or_404(id)
    items = StockInItem.query.filter_by(
        stock_in_id=si.id).order_by(StockInItem.id).all()
    qty_display_map = build_item_qty_display_map(items)
    return render_template(
        'stock_in/detail.html',
        stock_in=si,
        items=items,
        qty_display_map=qty_display_map,
    )


@stock_in_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('stock_in', 'edit')
def edit(id):
    si = StockIn.query.get_or_404(id)
    if _is_confirmed(si.status):
        flash('Không thể chỉnh sửa phiếu đã xác nhận!', 'danger')
        return redirect(url_for('stock_in.detail', id=id))

    if request.method == 'POST':
        si.date = datetime.strptime(request.form.get(
            'date', date.today().isoformat()), '%Y-%m-%d').date()
        si.supplier_id = request.form.get('supplier_id', type=int) or None
        si.warehouse_id = request.form.get('warehouse_id', type=int)
        si.invoice_no = request.form.get('invoice_no', '').strip()
        si.invoice_date = _parse_date(request.form.get('invoice_date', ''))
        si.discount_amount = _dec(request.form.get('discount_amount', 0) or 0)
        si.note = request.form.get('note', '').strip()
        si.unit_id = request.form.get('unit_id', type=int) or None
        si.conversion_factor = _dec(
            request.form.get('conversion_factor', 1) or 1)

        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        vat_rates = request.form.getlist('vat_rate[]')
        unit_ids = request.form.getlist('unit_item_id[]')
        factors = request.form.getlist('factor_item[]')

        from itertools import zip_longest
        items_data = []
        for pid, qty, price, vat, u, f in zip_longest(product_ids, quantities, unit_prices, vat_rates, unit_ids, factors, fillvalue=''):
            try:
                qty_val = float(qty or 0)
            except Exception:
                qty_val = 0
            if not pid or qty_val <= 0:
                continue
            items_data.append((pid, qty_val, price, vat, u, f))

        if not items_data:
            flash(_('Please add at least one valid item!'), 'danger')
            db.session.rollback()
            return _render_form(si)

        normalized_items = []
        for idx, (pid, qty, price, vat, u, _f) in enumerate(items_data, start=1):
            product = Product.query.get(int(pid))
            if not product:
                flash(
                    f"Dòng {idx}: không tìm thấy sản phẩm (ID={pid}).", 'danger')
                return _render_form(si)
            item_unit_id = int(u) if u else None
            ok, factor, err = _resolve_item_factor(product, item_unit_id)
            if not ok:
                flash(
                    f"Dòng {idx} - {product.code}: {err}. Vui lòng khai báo tại Cài đặt > Quy đổi đơn vị.",
                    'danger'
                )
                return _render_form(si)
            # Nếu không nhập giá, lấy purchase_price từ sản phẩm
            resolved_price = _dec(price) if price and _dec(price) > 0 else _dec(product.purchase_price or 0)
            # Nếu không nhập VAT, lấy vat_rate từ sản phẩm
            resolved_vat = _dec(vat) if vat and _dec(vat) >= 0 and str(vat).strip() != '' else _dec(product.vat_rate or 0)
            normalized_items.append((int(pid), _dec(qty), resolved_price, resolved_vat, item_unit_id, _dec(factor) if factor else _dec(1)))

        # Delete existing items only after validations pass
        StockInItem.query.filter_by(stock_in_id=si.id).delete()

        for pid, qty, price, vat, u, factor in normalized_items:
            item = StockInItem(
                stock_in_id=si.id,
                product_id=pid,
                quantity=qty,
                unit_id=u,
                conversion_factor=factor,
                unit_price=price,
                vat_rate=vat,
            )
            item.calculate()
            db.session.add(item)

        db.session.flush()
        si.calculate_totals()
        db.session.commit()
        flash(_('Updated stock-in %(code)s successfully!', code=si.code), 'success')
        return redirect(url_for('stock_in.detail', id=si.id))

    return _render_form(si)


@stock_in_bp.route('/confirm/<int:id>', methods=['POST'])
@login_required
@require_permission('stock_in', 'confirm')
def confirm(id):
    result = StockDocumentService.confirm_stock_in(id, current_user.id)
    if result.ok:
        flash(_('Confirmed stock-in %(code)s. Inventory updated.', code=result.code), 'success')
    else:
        flash(result.error or _('Error confirming'), 'danger')
    return redirect(url_for('stock_in.detail', id=id))


@stock_in_bp.route('/cancel/<int:id>', methods=['POST'])
@login_required
@require_permission('stock_in', 'delete')
def cancel(id):
    result = StockDocumentService.cancel_stock_in(id, current_user.id)
    if result.ok:
        flash(_('Cancelled stock-in %(code)s.', code=result.code), 'warning')
    else:
        flash(result.error or _('Error cancelling'), 'danger')
    return redirect(url_for('stock_in.index'))


@stock_in_bp.route('/print/<int:id>')
@login_required
@require_permission('stock_in', 'view')
def print_pdf(id):
    si = StockIn.query.get_or_404(id)
    from app.shared.print import render_pdf
    from app.domains.inventory.models import StockInItem
    from app.domains.platform.models import SystemConfig
    from app.shared.export.pdf_exporter import PdfExporter
    items = StockInItem.query.filter_by(
        stock_in_id=si.id).order_by(StockInItem.id).all()
    qty_display_map = build_item_qty_display_map(items)
    cfg = {c.key: c.value for c in SystemConfig.query.filter(SystemConfig.key.in_([
        'company_name', 'company_address', 'company_phone', 'company_tax_code'
    ])).all()}
    company = {
        'name': cfg.get('company_name', 'ERP-VIET'),
        'address': cfg.get('company_address', ''),
        'tax_code': cfg.get('company_tax_code', ''),
        'phone': cfg.get('company_phone', ''),
    }
    try:
        pdf = render_pdf(
            'print/stock_in.html',
            {
                'stock_in': si,
                'items': items,
                'company': company,
                'qty_display_map': qty_display_map,
            },
            base_url=request.host_url
        )
    except Exception:
        # Fallback engine to avoid browser hanging on intermittent WeasyPrint issues.
        pdf = PdfExporter.export_stock_in_pdf(si)
    return send_file(pdf, mimetype='application/pdf', as_attachment=False,
                     download_name=f'phieu_nhap_{si.code}.pdf')


@stock_in_bp.route('/print/html/<int:id>')
@login_required
@require_permission('stock_in', 'view')
def print_html(id):
    si = StockIn.query.get_or_404(id)
    from app.domains.inventory.models import StockInItem
    from app.domains.platform.models import SystemConfig
    items = StockInItem.query.filter_by(
        stock_in_id=si.id).order_by(StockInItem.id).all()
    qty_display_map = build_item_qty_display_map(items)
    cfg = {c.key: c.value for c in SystemConfig.query.filter(SystemConfig.key.in_([
        'company_name', 'company_address', 'company_phone', 'company_tax_code'
    ])).all()}
    company = {
        'name': cfg.get('company_name', 'ERP-VIET'),
        'address': cfg.get('company_address', ''),
        'tax_code': cfg.get('company_tax_code', ''),
        'phone': cfg.get('company_phone', ''),
    }
    html = render_template(
        'print/stock_in_browser.html',
        stock_in=si,
        items=items,
        company=company,
        qty_display_map=qty_display_map,
    )
    return jsonify({'ok': True, 'html': html})


@stock_in_bp.route('/export/excel')
@login_required
@require_permission('stock_in', 'export')
def export_excel():
    stock_ins = StockIn.query.order_by(StockIn.date.desc()).all()
    output = ExcelExporter.export_stock_in(stock_ins)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'phieu_nhap_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


def _render_form(si):
    from datetime import date
    from app.domains.master.models import Warehouse, Supplier, Product, Category
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    suppliers = Supplier.query.filter_by(
        is_active=True).order_by(Supplier.name).all()
    products = Product.query.filter_by(
        is_active=True).order_by(Product.code).all()
    categories = Category.query.filter_by(
        is_active=True).order_by(Category.name).all()
    units = Unit.query.filter_by(is_active=True).order_by(Unit.name).all(
    ) if hasattr(Unit, 'is_active') else Unit.query.order_by(Unit.name).all()
    conv_rows = UnitConversion.query.all()
    product_base_units = {p.id: p.unit_id for p in products}
    unit_conv_map = {}
    for c in conv_rows:
        pid = str(c.product_id)
        if pid not in unit_conv_map:
            unit_conv_map[pid] = {}
        base_uid = product_base_units.get(c.product_id)
        factor = float(c.conversion_factor or 1)
        if factor <= 0:
            continue
        # Chuẩn: from_unit -> base_unit
        if base_uid and c.to_unit_id == base_uid:
            unit_conv_map[pid][str(c.from_unit_id)] = factor
        # Dữ liệu nhập ngược: base_unit -> from_unit, tự đảo hệ số
        elif base_uid and c.from_unit_id == base_uid:
            unit_conv_map[pid][str(c.to_unit_id)] = 1 / factor
        else:
            unit_conv_map[pid][str(c.from_unit_id)] = factor
    return render_template('stock_in/form.html',
                           stock_in=si, warehouses=warehouses,
                           suppliers=suppliers, products=products, units=units, categories=categories,
                           unit_conv_map=unit_conv_map,
                           today=date.today())


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except Exception:
        return None
