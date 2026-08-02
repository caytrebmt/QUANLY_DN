from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.database import db
from app.domains.master.models import Product, Customer, Supplier, Warehouse, Unit, Category
from app.domains.inventory.models import Inventory
from app.shared.constants import DocStatus
from app.shared.authz import require_permission

api_bp = Blueprint('api', __name__, url_prefix='/api')



@api_bp.route('/products/search')
@login_required
@require_permission('products', 'view')
def search_products():
    q = request.args.get('q', '')
    products = Product.query.filter(
        db.or_(Product.code.ilike(f'%{q}%'), Product.name.ilike(f'%{q}%')),
        Product.is_active == True
    ).limit(20).all()
    return jsonify([p.to_dict() for p in products])


@api_bp.route('/products/<int:id>/stock')
@login_required
@require_permission('inventory', 'view')
def product_stock(id):
    warehouse_id = request.args.get('warehouse_id', type=int)
    q = Inventory.query.filter_by(product_id=id)
    if warehouse_id:
        q = q.filter_by(warehouse_id=warehouse_id)
    invs = q.all()
    result = [{'warehouse_id': i.warehouse_id,
               'warehouse': i.warehouse.name if i.warehouse else '',
               'quantity': float(i.quantity or 0),
               'avg_cost': float(i.avg_cost or 0)} for i in invs]
    return jsonify({'product_id': id, 'stock': result,
                    'total': sum(r['quantity'] for r in result)})


@api_bp.route('/customers/search')
@login_required
@require_permission('customers', 'view')
def search_customers():
    q = request.args.get('q', '')
    customers = Customer.query.filter(
        db.or_(Customer.code.ilike(f'%{q}%'), Customer.name.ilike(f'%{q}%')),
        Customer.is_active == True
    ).limit(20).all()
    return jsonify([c.to_dict() for c in customers])


@api_bp.route('/suppliers/search')
@login_required
@require_permission('suppliers', 'view')
def search_suppliers():
    q = request.args.get('q', '')
    suppliers = Supplier.query.filter(
        db.or_(Supplier.code.ilike(f'%{q}%'), Supplier.name.ilike(f'%{q}%')),
        Supplier.is_active == True
    ).limit(20).all()
    return jsonify([s.to_dict() for s in suppliers])


@api_bp.route('/dashboard/stats')
@login_required
@require_permission('dashboard', 'view')
def dashboard_stats():
    from sqlalchemy import func
    from datetime import date
    today = date.today()
    month_start = today.replace(day=1)
    from app.domains.inventory.models import StockIn, StockOut
    from app.domains.finance.models import Debt

    return jsonify({
        'products': Product.query.filter_by(is_active=True).count(),
        'customers': Customer.query.filter_by(is_active=True).count(),
        'suppliers': Supplier.query.filter_by(is_active=True).count(),
        'revenue_month': float(db.session.query(func.sum(StockOut.total_amount)).filter(
            StockOut.date >= month_start, StockOut.status == DocStatus.CONFIRMED).scalar() or 0),
        'receivable': float(db.session.query(func.sum(Debt.balance)).filter(
            Debt.partner_type == 'customer', Debt.status != 'paid').scalar() or 0),
        'payable': float(db.session.query(func.sum(Debt.balance)).filter(
            Debt.partner_type == 'supplier', Debt.status != 'paid').scalar() or 0),
    })


@api_bp.route('/products/quick-create', methods=['POST'])
@login_required
@require_permission('products', 'create')
def quick_create_product():
    """Tạo nhanh hàng hóa từ form phiếu nhập/xuất."""
    payload = request.get_json(silent=True) or {}
    code = (payload.get('code') or '').strip().upper()
    name = (payload.get('name') or '').strip()
    if not code or not name:
        return jsonify({'ok': False, 'message': 'Mã hàng và tên hàng không được để trống.'}), 400

    exists = Product.query.filter_by(code=code).first()
    if exists:
        return jsonify({'ok': False, 'message': f'Mã hàng {code} đã tồn tại.'}), 409

    unit_id = payload.get('unit_id')
    category_id = payload.get('category_id')
    try:
        unit_id = int(unit_id) if unit_id else None
    except Exception:
        unit_id = None
    try:
        category_id = int(category_id) if category_id else None
    except Exception:
        category_id = None

    unit_name = 'Cai'
    if unit_id:
        u = Unit.query.get(unit_id)
        if not u:
            return jsonify({'ok': False, 'message': 'Đơn vị tính không hợp lệ.'}), 400
        unit_name = u.name
    category_name = ''
    if category_id:
        c = Category.query.get(category_id)
        if c:
            category_name = c.name

    def _num(v, default=0.0):
        try:
            return float(v or default)
        except Exception:
            return float(default)

    p = Product(
        code=code,
        name=name,
        unit_id=unit_id,
        unit=unit_name,
        category_id=category_id,
        category=category_name,
        purchase_price=_num(payload.get('purchase_price'), 0),
        sale_price=_num(payload.get('sale_price'), 0),
        vat_rate=_num(payload.get('vat_rate'), 0),
        min_stock=0,
        allow_negative=True,
        is_active=True,
    )
    db.session.add(p)
    db.session.commit()

    return jsonify({
        'ok': True,
        'message': f'Đã tạo hàng hóa {code}.',
        'product': {
            'id': p.id,
            'code': p.code,
            'name': p.name,
            'unit': p.get_unit_name(),
            'unit_id': p.unit_id,
            'purchase_price': float(p.purchase_price or 0),
            'sale_price': float(p.sale_price or 0),
            'vat_rate': float(p.vat_rate or 0),
        }
    })


@api_bp.route('/products/check-code')
@login_required
@require_permission('products', 'create')
def check_product_code():
    code = (request.args.get('code') or '').strip().upper()
    if not code:
        return jsonify({'ok': False, 'exists': False, 'message': 'Mã hàng trống.'}), 400
    exists = Product.query.filter_by(code=code).first() is not None
    return jsonify({'ok': True, 'exists': exists, 'code': code})


@api_bp.route('/products/next-code')
@login_required
@require_permission('products', 'create')
def next_product_code():
    """Gợi ý mã HH tăng dần: HH0001, HH0002, ..."""
    from app.domains.master.services.product_code_service import next_sequential_code

    prefix = (request.args.get('prefix') or 'HH').strip().upper()
    if not prefix:
        prefix = 'HH'
    width = request.args.get('width', default=4, type=int) or 4

    code = next_sequential_code(prefix=prefix, width=width)
    return jsonify({'ok': True, 'code': code, 'prefix': prefix, 'width': width})


@api_bp.route('/products/slug-code')
@login_required
@require_permission('products', 'create')
def slug_product_code():
    """Gợi ý base code từ tên hàng, dùng chung logic backend service."""
    from app.domains.master.services.product_code_service import slug_code_from_name

    name = (request.args.get('name') or '').strip()
    if not name:
        return jsonify({'ok': True, 'code': ''})
    return jsonify({'ok': True, 'code': slug_product_code(name)})


def _ss_page():
    return max(1, request.args.get('page', 1, type=int) or 1)


def _ss_per_page():
    per_page = min(100, max(1, request.args.get('per_page', 20, type=int) or 20))
    return per_page


def _ss_search(model, columns):
    term = (request.args.get('search', '') or '').strip()
    if not term:
        return None
    return db.or_(*[
        col.ilike(f'%{term}%') for col in columns
    ])


def _ss_sort(model, default_sort):
    sort_column = request.args.get('sort_column', '')
    sort_dir = (request.args.get('sort_dir', 'asc') or 'asc').lower()
    if sort_column and hasattr(model, sort_column):
        col = getattr(model, sort_column)
        return col.desc() if sort_dir == 'desc' else col.asc()
    return default_sort


def _ss_column_filters(model, column_map):
    filters = []
    for param, col_name in column_map.items():
        value = (request.args.get(param, '') or '').strip()
        if not value:
            continue
        col = getattr(model, col_name, None)
        if col is None:
            continue
        filters.append(col.ilike(f'%{value}%'))
    return filters


def _ss_json_response(query, model, columns, default_sort):
    page = _ss_page()
    per_page = _ss_per_page()
    search_filter = _ss_search(model, columns)
    sort_expr = _ss_sort(model, default_sort)
    column_filters = _ss_column_filters(model, {
        'filter_code': 'code',
        'filter_name': 'name',
        'filter_status': 'status',
    })

    q = query
    if search_filter is not None:
        q = q.filter(search_filter)
    for f in column_filters:
        q = q.filter(f)

    total = q.count()
    items = q.order_by(sort_expr).offset((page - 1) * per_page).limit(per_page).all()

    data = []
    for item in items:
        row = {}
        for col in columns:
            val = getattr(item, col, None)
            if val is None:
                row[col] = ''
            elif isinstance(val, float):
                row[col] = val
            elif hasattr(val, 'isoformat'):
                row[col] = val.isoformat()
            else:
                row[col] = str(val)
        data.append(row)

    return jsonify({
        'draw': page,
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': data,
    })


@api_bp.route('/products')
@login_required
@require_permission('products', 'view')
def api_products():
    from app.domains.master.models import Product
    columns = ['id', 'code', 'name', 'unit', 'category', 'purchase_price', 'sale_price', 'vat_rate', 'min_stock']
    q = Product.query.filter_by(is_active=True)
    return _ss_json_response(q, Product, columns, Product.code)


@api_bp.route('/stock-in')
@login_required
@require_permission('stock_in', 'view')
def api_stock_in():
    from app.domains.inventory.models import StockIn
    from app.domains.master.models import Supplier, Warehouse
    columns = ['id', 'code', 'date', 'supplier_name', 'warehouse_name', 'subtotal', 'vat_amount', 'total_amount', 'status']
    q = db.session.query(
        StockIn.id,
        StockIn.code,
        StockIn.date,
        StockIn.subtotal,
        StockIn.vat_amount,
        StockIn.total_amount,
        StockIn.status,
        Supplier.name.label('supplier_name'),
        Warehouse.name.label('warehouse_name'),
    ).outerjoin(Supplier, StockIn.supplier_id == Supplier.id).outerjoin(Warehouse, StockIn.warehouse_id == Warehouse.id)
    return _ss_json_response(q, StockIn, columns, StockIn.date.desc())


@api_bp.route('/stock-out')
@login_required
@require_permission('stock_out', 'view')
def api_stock_out():
    from app.domains.inventory.models import StockOut
    from app.domains.master.models import Customer, Warehouse
    columns = ['id', 'code', 'date', 'customer_name', 'warehouse_name', 'subtotal', 'vat_amount', 'total_amount', 'status']
    q = db.session.query(
        StockOut.id,
        StockOut.code,
        StockOut.date,
        StockOut.subtotal,
        StockOut.vat_amount,
        StockOut.total_amount,
        StockOut.status,
        Customer.name.label('customer_name'),
        Warehouse.name.label('warehouse_name'),
    ).outerjoin(Customer, StockOut.customer_id == Customer.id).outerjoin(Warehouse, StockOut.warehouse_id == Warehouse.id)
    return _ss_json_response(q, StockOut, columns, StockOut.date.desc())


@api_bp.route('/customers')
@login_required
@require_permission('customers', 'view')
def api_customers():
    from app.domains.master.models import Customer
    columns = ['id', 'code', 'name', 'customer_type', 'phone', 'email', 'address', 'credit_limit']
    q = Customer.query.filter_by(is_active=True)
    return _ss_json_response(q, Customer, columns, Customer.code)


@api_bp.route('/suppliers')
@login_required
@require_permission('suppliers', 'view')
def api_suppliers():
    from app.domains.master.models import Supplier
    columns = ['id', 'code', 'name', 'phone', 'email', 'address', 'tax_code', 'payment_terms']
    q = Supplier.query.filter_by(is_active=True)
    return _ss_json_response(q, Supplier, columns, Supplier.code)


@api_bp.route('/inventory')
@login_required
@require_permission('inventory', 'view')
def api_inventory():
    from sqlalchemy import func
    from app.domains.master.models import Product, Warehouse
    from app.domains.inventory.models import Inventory
    columns = ['id', 'code', 'name', 'unit', 'category', 'warehouse_name', 'quantity', 'avg_cost']
    q = db.session.query(
        Product.id,
        Product.code,
        Product.name,
        Product.unit,
        Product.category,
        Warehouse.name.label('warehouse_name'),
        Inventory.quantity,
        Inventory.avg_cost,
    ).join(Inventory, Product.id == Inventory.product_id).join(Warehouse, Inventory.warehouse_id == Warehouse.id).filter(Product.is_active == True)
    return _ss_json_response(q, Product, columns, Product.code)


@api_bp.route('/accounting/journal')
@login_required
@require_permission('accounting', 'view')
def api_journal():
    from app.domains.accounting.models import JournalEntry
    columns = ['id', 'code', 'date', 'description', 'reference_code', 'total_debit', 'total_credit', 'status']
    q = JournalEntry.query
    return _ss_json_response(q, JournalEntry, columns, JournalEntry.date.desc())


@api_bp.route('/debt')
@login_required
@require_permission('debt', 'view')
def api_debt():
    from app.domains.finance.models import Debt
    columns = ['id', 'partner_type', 'partner_id', 'reference_code', 'date', 'amount', 'paid_amount', 'balance', 'status']
    q = Debt.query
    return _ss_json_response(q, Debt, columns, Debt.date.desc())


@api_bp.route('/stock-in/detail')
@login_required
@require_permission('stock_in', 'view')
def api_stock_in_detail():
    from app.domains.inventory.models import StockIn, StockInItem
    from app.domains.master.models import Product
    q = request.args.get('id', '')
    si = StockIn.query.filter_by(code=q).first()
    if not si:
        return '<div class="text-center text-muted py-3">Không tìm thấy phiếu</div>'
    items = StockInItem.query.filter_by(stock_in_id=si.id).all()
    rows = ''.join([
        f'<tr><td>{item.product.code if item.product else ""}</td>'
        f'<td>{item.product.name if item.product else ""}</td>'
        f'<td class="text-end">{item.quantity}</td>'
        f'<td class="text-end">{item.unit_price:,.0f}</td>'
        f'<td class="text-end">{item.amount:,.0f}</td></tr>'
        for item in items
    ])
    return f'''
    <div class="table-responsive">
      <table class="table table-sm table-bordered mb-0">
        <thead class="table-light"><tr><th>Mã hàng</th><th>Tên hàng</th><th class="text-end">SL</th><th class="text-end">Đơn giá</th><th class="text-end">Thành tiền</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    '''


@api_bp.route('/stock-out/detail')
@login_required
@require_permission('stock_out', 'view')
def api_stock_out_detail():
    from app.domains.inventory.models import StockOut, StockOutItem
    from app.domains.master.models import Product
    q = request.args.get('id', '')
    so = StockOut.query.filter_by(code=q).first()
    if not so:
        return '<div class="text-center text-muted py-3">Không tìm thấy phiếu</div>'
    items = StockOutItem.query.filter_by(stock_out_id=so.id).all()
    rows = ''.join([
        f'<tr><td>{item.product.code if item.product else ""}</td>'
        f'<td>{item.product.name if item.product else ""}</td>'
        f'<td class="text-end">{item.quantity}</td>'
        f'<td class="text-end">{item.unit_price:,.0f}</td>'
        f'<td class="text-end">{item.amount:,.0f}</td></tr>'
        for item in items
    ])
    return f'''
    <div class="table-responsive">
      <table class="table table-sm table-bordered mb-0">
        <thead class="table-light"><tr><th>Mã hàng</th><th>Tên hàng</th><th class="text-end">SL</th><th class="text-end">Đơn giá</th><th class="text-end">Thành tiền</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    '''
