from datetime import datetime, date, timedelta
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, send_file, session)
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app.database import db
from sqlalchemy import func
from app.domains.master.models import Product, Customer, Warehouse, Supplier, Unit
from app.domains.inventory.models import (
    StockOut, StockOutItem, Inventory, UnitConversion,
    InventoryHistory,
)
from app.domains.ecommerce.models import OnlineOrder
from app.domains.inventory.services.inventory_service import InventoryService
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.pdf_exporter import PdfExporter
from app.domains.platform.services.company_service import get_company_value
from app.domains.inventory.services.stock_document_service import StockDocumentService
from app.domains.finance.services.debt_service import DebtService
from app.domains.finance.services.vat_service import VatService
from app.shared.authz import require_permission
from app.domains.accounting.services.account_mapping_service import get_account_code
from app.domains.inventory.services.unit_display import build_item_qty_display_map
from app.shared.constants import DocStatus
from decimal import Decimal, ROUND_HALF_UP
from weasyprint import HTML
from flask import render_template, request

stock_out_bp = Blueprint('stock_out', __name__, url_prefix='/stock-out')


def _is_confirmed(status_value):
    return (status_value or '').strip().lower() == DocStatus.CONFIRMED


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


def _generate_code():
    today = date.today().strftime('%y%m%d')
    prefix_cfg = (get_company_value(
        'invoice_prefix_out', 'PX') or 'PX').upper()
    prefix = f'{prefix_cfg}-{today}-'
    last = StockOut.query.filter(StockOut.code.like(f'{prefix}%')).order_by(
        StockOut.code.desc()).first()
    num = int(last.code.split('-')[-1]) + 1 if last else 1
    return f'{prefix}{num:03d}'



@stock_out_bp.route('/')
@login_required
@require_permission('stock_out', 'view')
def index():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    customer_id = request.args.get('customer_id', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    page = request.args.get('page', 1, type=int)

    q = StockOut.query
    if search:
        q = q.filter(db.or_(StockOut.code.ilike(f'%{search}%'),
                            StockOut.invoice_no.ilike(f'%{search}%')))
    if status:
        q = q.filter(func.lower(StockOut.status) == status.lower())
    if customer_id:
        q = q.filter(StockOut.customer_id == int(customer_id))
    if from_date:
        q = q.filter(StockOut.date >= datetime.strptime(
            from_date, '%Y-%m-%d').date())
    if to_date:
        q = q.filter(StockOut.date <= datetime.strptime(
            to_date, '%Y-%m-%d').date())

    q = q.order_by(StockOut.date.desc(), StockOut.code.desc())
    stock_outs = q.paginate(page=page, per_page=20, error_out=False)
    customers = Customer.query.filter_by(
        is_active=True).order_by(Customer.name).all()

    # Nhận diện nguồn phiếu xuất: có OnlineOrder nào trỏ tới stock_out.id hay không
    so_ids = [so.id for so in stock_outs.items]
    shop_synced_map = {}
    if so_ids:
        rows = (OnlineOrder.query
                .filter(OnlineOrder.stock_out_id.in_(so_ids))
                .with_entities(OnlineOrder.stock_out_id, OnlineOrder.code)
                .all())
        for so_id, code in rows:
            if so_id is not None and code:
                shop_synced_map[int(so_id)] = code

    return render_template('stock_out/index.html',
                           stock_outs=stock_outs, search=search,
                           status=status, customers=customers,
                           customer_id=customer_id, from_date=from_date, to_date=to_date,
                           shop_synced_map=shop_synced_map)



@stock_out_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('stock_out', 'create')
def create():
    if request.method == 'POST':
        warehouse_id = request.form.get('warehouse_id', type=int)
        if not warehouse_id:
            flash(_('Please select warehouse!'), 'danger')
            return _render_form(None)

        vat_manual = request.form.get('vat_manual') == 'on'
        vat_mode = request.form.get('vat_mode', 'per_item')
        so = StockOut(
            code=_generate_code(),
            date=datetime.strptime(request.form.get(
                'date', date.today().isoformat()), '%Y-%m-%d').date(),
            customer_id=request.form.get('customer_id', type=int) or None,
            warehouse_id=warehouse_id,
            unit_id=request.form.get('unit_id', type=int) or None,
            conversion_factor=float(
                request.form.get('conversion_factor', 1) or 1),
            invoice_no=request.form.get('invoice_no', '').strip(),
            invoice_series=request.form.get('invoice_series', '').strip(),
            discount_amount=float(request.form.get('discount_amount', 0) or 0),
            note=request.form.get('note', '').strip(),
            vat_manual=vat_manual,
            vat_manual_val=float(request.form.get(
                'vat_manual_val', 0) or 0) if vat_manual else 0,
            vat_mode=vat_mode,
            vat_rate_grouped=float(request.form.get('vat_rate_grouped', 0) or 0) if vat_mode == 'grouped' else 0,
            status=DocStatus.DRAFT,
            created_by=current_user.id,
        )

        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        vat_rates = request.form.getlist('vat_rate[]')
        unit_ids = request.form.getlist('unit_item_id[]')
        factors = request.form.getlist('factor_item[]')
        box_notes = request.form.getlist('box_note[]')

        from itertools import zip_longest
        items_data = []
        for pid, qty, price, vat, u, f, bnote in zip_longest(product_ids, quantities, unit_prices, vat_rates, unit_ids, factors, box_notes, fillvalue=''):
            try:
                qty_val = float(qty or 0)
            except Exception:
                qty_val = 0
            if not pid or qty_val <= 0:
                continue
            items_data.append((pid, qty_val, price, vat, u, f, bnote))

        if not items_data:
            flash(_('Please add at least one valid item!'), 'danger')
            return _render_form(None)

        normalized_items = []
        for idx, (pid, qty_val, price, vat, u, _f, bnote) in enumerate(items_data, start=1):
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
            normalized_items.append((int(pid), float(qty_val), float(
                price or 0), float(vat or 0), item_unit_id, factor, bnote))

        db.session.add(so)
        db.session.flush()

        for pid, qty_val, price, vat, u, factor, bnote in normalized_items:
            # Lấy giá bình quân từ hàng tồn kho inventory
            inv = Inventory.query.filter_by(
                product_id=pid, warehouse_id=warehouse_id
            ).first()
            cost = float(inv.avg_cost or 0) if inv else 0

            item = StockOutItem(
                stock_out_id=so.id,
                product_id=pid,
                quantity=qty_val,
                unit_id=u,
                conversion_factor=factor,
                unit_price=price,
                cost_price=cost,
                vat_rate=0 if vat_mode == 'grouped' else vat,
                box_note=bnote,
            )
            item.calculate()
            db.session.add(item)

        db.session.flush()
        so.calculate_totals()
        db.session.commit()
        flash(_('Created stock-out %(code)s successfully!', code=so.code), 'success')
        return redirect(url_for('stock_out.detail', id=so.id))

    return _render_form(None)


@stock_out_bp.route('/<int:id>')
@login_required
@require_permission('stock_out', 'view')
def detail(id):
    so = StockOut.query.get_or_404(id)
    items = StockOutItem.query.filter_by(
        stock_out_id=so.id).order_by(StockOutItem.id).all()
    qty_display_map = build_item_qty_display_map(items)
    return render_template(
        'stock_out/detail.html',
        stock_out=so,
        items=items,
        qty_display_map=qty_display_map,
    )


@stock_out_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('stock_out', 'edit')
def edit(id):
    so = StockOut.query.get_or_404(id)
    if _is_confirmed(so.status):
        flash('Không thể chỉnh sửa phiếu đã xác nhận!', 'danger')
        return redirect(url_for('stock_out.detail', id=id))

    if request.method == 'POST':
        vat_manual = request.form.get('vat_manual') == 'on'
        vat_mode = request.form.get('vat_mode', 'per_item')
        so.date = datetime.strptime(request.form.get(
            'date', date.today().isoformat()), '%Y-%m-%d').date()
        so.customer_id = request.form.get('customer_id', type=int) or None
        so.warehouse_id = request.form.get('warehouse_id', type=int)
        so.invoice_no = request.form.get('invoice_no', '').strip()
        so.invoice_series = request.form.get('invoice_series', '').strip()
        so.discount_amount = float(request.form.get('discount_amount', 0) or 0)
        so.note = request.form.get('note', '').strip()
        so.vat_manual = vat_manual
        so.vat_manual_val = float(request.form.get(
            'vat_manual_val', 0) or 0) if vat_manual else 0
        so.vat_mode = vat_mode
        so.vat_rate_grouped = float(request.form.get('vat_rate_grouped', 0) or 0) if vat_mode == 'grouped' else 0
        so.unit_id = request.form.get('unit_id', type=int) or None
        so.conversion_factor = float(
            request.form.get('conversion_factor', 1) or 1)

        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        vat_rates = request.form.getlist('vat_rate[]')
        unit_ids = request.form.getlist('unit_item_id[]')
        factors = request.form.getlist('factor_item[]')
        box_notes = request.form.getlist('box_note[]')

        from itertools import zip_longest
        items_data = []
        for pid, qty, price, vat, u, f, bnote in zip_longest(product_ids, quantities, unit_prices, vat_rates, unit_ids, factors, box_notes, fillvalue=''):
            try:
                qty_val = float(qty or 0)
            except Exception:
                qty_val = 0
            if not pid or qty_val <= 0:
                continue
            items_data.append((pid, qty_val, price, vat, u, f, bnote))

        if not items_data:
            flash(_('Please add at least one valid item!'), 'danger')
            return _render_form(so)

        normalized_items = []
        for idx, (pid, qty_val, price, vat, u, _f, bnote) in enumerate(items_data, start=1):
            product = Product.query.get(int(pid))
            if not product:
                flash(
                    f"Dòng {idx}: không tìm thấy sản phẩm (ID={pid}).", 'danger')
                return _render_form(so)
            item_unit_id = int(u) if u else None
            ok, factor, err = _resolve_item_factor(product, item_unit_id)
            if not ok:
                flash(
                    f"Dòng {idx} - {product.code}: {err}. Vui lòng khai báo tại Cài đặt > Quy đổi đơn vị.",
                    'danger'
                )
                return _render_form(so)
            normalized_items.append((int(pid), float(qty_val), float(
                price or 0), float(vat or 0), item_unit_id, factor, bnote))

        # Delete existing items only after validations pass
        StockOutItem.query.filter_by(stock_out_id=so.id).delete()

        for pid, qty_val, price, vat, u, factor, bnote in normalized_items:
            inv = Inventory.query.filter_by(
                product_id=pid, warehouse_id=so.warehouse_id
            ).first()
            cost = float(inv.avg_cost or 0) if inv else 0
            item = StockOutItem(
                stock_out_id=so.id,
                product_id=pid,
                quantity=qty_val,
                unit_id=u,
                conversion_factor=factor,
                unit_price=price,
                cost_price=cost,
                vat_rate=0 if vat_mode == 'grouped' else vat,
                box_note=bnote,
            )
            item.calculate()
            db.session.add(item)

        db.session.flush()
        so.calculate_totals()
        db.session.commit()
        flash(_('Updated stock-out %(code)s successfully!', code=so.code), 'success')
        return redirect(url_for('stock_out.detail', id=so.id))

    return _render_form(so)


@stock_out_bp.route('/confirm/<int:id>', methods=['POST'])
@login_required
@require_permission('stock_out', 'confirm')
def confirm(id):
    result = StockDocumentService.confirm_stock_out(id, current_user.id)
    if result.ok:
            flash(_('Confirmed stock-out %(code)s successfully!', code=result.code), 'success')
    else:
            flash(result.error or _('Error: %(err)s', err='Error confirming'), 'danger')
    return redirect(url_for('stock_out.detail', id=id))


@stock_out_bp.route('/cancel/<int:id>', methods=['POST'])
@login_required
@require_permission('stock_out', 'delete')
def cancel(id):
    result = StockDocumentService.cancel_stock_out(id, current_user.id)
    if result.ok:
        flash(_('Cancelled stock-out %(code)s.', code=result.code), 'warning')
    else:
        flash(result.error or _('Error cancelling'), 'danger')
    return redirect(url_for('stock_out.index'))


@stock_out_bp.route('/print/<int:id>')
@login_required
@require_permission('stock_out', 'view')
def print_pdf(id):
    so = StockOut.query.get_or_404(id)
    # In mặc định bằng WeasyPrint layout kế toán
    from app.shared.print import render_pdf
    from app.domains.platform.models import SystemConfig
    from app.shared.export.pdf_exporter import PdfExporter
    items = StockOutItem.query.filter_by(
        stock_out_id=so.id).order_by(StockOutItem.id).all()
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
            'print/stock_out.html',
            {
                'stock_out': so,
                'items': items,
                'company': company,
                'qty_display_map': qty_display_map,
            },
            base_url=request.host_url
        )
    except Exception:
        # Fallback engine to avoid browser hanging on intermittent WeasyPrint issues.
        pdf = PdfExporter.export_stock_out_pdf(so)
    return send_file(pdf, mimetype='application/pdf', as_attachment=False,
                     download_name=f'phieu_xuat_{so.code}.pdf')


@stock_out_bp.route('/delivery/<int:id>')
@login_required
@require_permission('stock_out', 'view')
def print_delivery_note(id):
    """In phiếu giao hàng theo dữ liệu phiếu xuất kho."""
    so = StockOut.query.get_or_404(id)
    from app.shared.print import render_pdf
    from app.domains.platform.models import SystemConfig
    from app.shared.export.pdf_exporter import PdfExporter
    items = StockOutItem.query.filter_by(
        stock_out_id=so.id).order_by(StockOutItem.id).all()
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
            'print/delivery_note.html',
            {
                'stock_out': so,
                'items': items,
                'company': company,
                'qty_display_map': qty_display_map,
            },
            base_url=request.host_url
        )
    except Exception:
        # Fallback engine to avoid browser hanging on intermittent WeasyPrint issues.
        pdf = PdfExporter.export_stock_out_pdf(so)
    return send_file(pdf, mimetype='application/pdf', as_attachment=False,
                     download_name=f'phieu_xuat_{so.code}.pdf')


@stock_out_bp.route('/print/html/<int:id>')
@login_required
@require_permission('stock_out', 'view')
def print_html(id):
    so = StockOut.query.get_or_404(id)
    from app.domains.inventory.models import StockOutItem
    from app.domains.platform.models import SystemConfig
    items = StockOutItem.query.filter_by(
        stock_out_id=so.id).order_by(StockOutItem.id).all()
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
        'print/stock_out_browser.html',
        stock_out=so,
        items=items,
        company=company,
        qty_display_map=qty_display_map,
    )
    return jsonify({'ok': True, 'html': html})


@stock_out_bp.route('/delivery/html/<int:id>')
@login_required
@require_permission('stock_out', 'view')
def delivery_note_html(id):
    so = StockOut.query.get_or_404(id)
    from app.domains.inventory.models import StockOutItem
    from app.domains.platform.models import SystemConfig
    items = StockOutItem.query.filter_by(
        stock_out_id=so.id).order_by(StockOutItem.id).all()
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
        'print/delivery_note_browser.html',
        stock_out=so,
        items=items,
        company=company,
        qty_display_map=qty_display_map,
    )
    return jsonify({'ok': True, 'html': html})


@stock_out_bp.route('/export/excel')
@login_required
@require_permission('stock_out', 'export')
def export_excel():
    stock_outs = StockOut.query.order_by(StockOut.date.desc()).all()
    output = ExcelExporter.export_stock_out(stock_outs)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'phieu_xuat_{datetime.now().strftime("%Y%m%d")}.xlsx'
    )


def _render_form(so):
    from datetime import date
    from app.domains.master.models import Category
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    customers = Customer.query.filter_by(
        is_active=True).order_by(Customer.name).all()
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
    return render_template('stock_out/form.html',
                           stock_out=so, warehouses=warehouses,
                           customers=customers, products=products, units=units, categories=categories,
                           unit_conv_map=unit_conv_map,
                           today=date.today())
