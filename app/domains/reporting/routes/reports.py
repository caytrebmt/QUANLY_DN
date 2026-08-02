from datetime import datetime, date
import io

import pandas as pd
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import func

from app.shared.constants import DocStatus
from app.database import db
from app.shared.authz import require_permission
from app.domains.inventory.services.unit_display import build_conversion_map, format_multi_unit_qty
from app.domains.master.models import Product, Customer, Supplier, Warehouse
from app.domains.inventory.models import (
    Inventory,
    StockIn, StockInItem,
    StockOut, StockOutItem,
)
from app.domains.finance.models import Debt

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def _get_period(req):
    from_date = req.args.get('from_date', date.today().replace(day=1).isoformat())
    to_date = req.args.get('to_date', date.today().isoformat())
    return (
        datetime.strptime(from_date, '%Y-%m-%d').date(),
        datetime.strptime(to_date, '%Y-%m-%d').date(),
        from_date,
        to_date,
    )


def _build_stock_movement_rows(from_dt, to_dt,
                               warehouse_id=None,
                               category=None,
                               product_id=None):
    wh_id = int(warehouse_id) if warehouse_id else None

    inv_q = db.session.query(
        Inventory.product_id,
        func.sum(Inventory.quantity).label('qty'),
        func.sum(Inventory.quantity * Inventory.avg_cost).label('value'),
    )
    if wh_id:
        inv_q = inv_q.filter(Inventory.warehouse_id == wh_id)
    inv_map = {}
    for r in inv_q.group_by(Inventory.product_id).all():
        qty = float(r.qty or 0)
        value = float(r.value or 0)
        inv_map[r.product_id] = (qty, value / qty if qty > 0 else 0.0)

    in_q = (
        db.session.query(
            StockInItem.product_id,
            func.sum(
                StockInItem.quantity * func.coalesce(StockInItem.conversion_factor, 1)
            ).label('qty'),
            func.sum(StockInItem.amount).label('amt'),
        )
        .join(StockIn, StockInItem.stock_in_id == StockIn.id)
        .filter(
            func.lower(StockIn.status) == DocStatus.CONFIRMED,
            StockIn.date >= from_dt,
            StockIn.date <= to_dt,
        )
    )
    if wh_id:
        in_q = in_q.filter(StockIn.warehouse_id == wh_id)
    in_map = {
        r.product_id: (float(r.qty or 0), float(r.amt or 0))
        for r in in_q.group_by(StockInItem.product_id).all()
    }

    out_q = (
        db.session.query(
            StockOutItem.product_id,
            func.sum(
                StockOutItem.quantity * func.coalesce(StockOutItem.conversion_factor, 1)
            ).label('qty'),
            func.sum(StockOutItem.amount).label('amt'),
        )
        .join(StockOut, StockOutItem.stock_out_id == StockOut.id)
        .filter(
            func.lower(StockOut.status) == DocStatus.CONFIRMED,
            StockOut.date >= from_dt,
            StockOut.date <= to_dt,
        )
    )
    if wh_id:
        out_q = out_q.filter(StockOut.warehouse_id == wh_id)
    out_map = {
        r.product_id: (float(r.qty or 0), float(r.amt or 0))
        for r in out_q.group_by(StockOutItem.product_id).all()
    }

    pq = Product.query.filter_by(is_active=True)
    if product_id:
        pq = pq.filter(Product.id == int(product_id))
    if category:
        pq = pq.filter(Product.category == category)

    rows = []
    for p in pq.order_by(Product.code).all():
        current_qty, avg_cost = inv_map.get(p.id, (0.0, 0.0))
        in_qty, in_amt = in_map.get(p.id, (0.0, 0.0))
        out_qty, out_amt = out_map.get(p.id, (0.0, 0.0))

        if in_qty == 0 and out_qty == 0 and current_qty == 0:
            continue

        rows.append({
            'product': p,
            'opening_qty': current_qty - in_qty + out_qty,
            'in_qty': in_qty,
            'in_amt': in_amt,
            'out_qty': out_qty,
            'out_amt': out_amt,
            'closing_qty': current_qty,
            'avg_cost': avg_cost,
            'closing_val': current_qty * avg_cost,
        })
    return rows


PER_PAGE_MOVEMENT = 50


@reports_bp.route('/stock-movement')
@login_required
@require_permission('reports', 'view')
def stock_movement():
    from_dt, to_dt, from_date, to_date = _get_period(request)
    warehouse_id = request.args.get('warehouse_id', '')
    category = request.args.get('category', '')
    product_id = request.args.get('product_id', '')
    page = request.args.get('page', 1, type=int)

    products = Product.query.filter_by(is_active=True).order_by(Product.code).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    categories = [
        c[0] for c in
        db.session.query(Product.category)
        .filter(Product.category.isnot(None)).distinct().all()
        if c[0]
    ]

    all_rows = _build_stock_movement_rows(
        from_dt, to_dt,
        warehouse_id=warehouse_id or None,
        category=category or None,
        product_id=product_id or None,
    )
    conv_map = build_conversion_map([r['product'].id for r in all_rows])
    for r in all_rows:
        conv = conv_map.get(r['product'].id)
        r['opening_qty_text'] = format_multi_unit_qty(r['opening_qty'], conv)
        r['in_qty_text'] = format_multi_unit_qty(r['in_qty'], conv)
        r['out_qty_text'] = format_multi_unit_qty(r['out_qty'], conv)
        r['closing_qty_text'] = format_multi_unit_qty(r['closing_qty'], conv)

    total = len(all_rows)
    total_pages = max((total + PER_PAGE_MOVEMENT - 1) // PER_PAGE_MOVEMENT, 1)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PER_PAGE_MOVEMENT
    rows = all_rows[offset: offset + PER_PAGE_MOVEMENT]

    totals = {
        'opening_qty': sum(r['opening_qty'] for r in all_rows),
        'in_qty': sum(r['in_qty'] for r in all_rows),
        'in_amt': sum(r['in_amt'] for r in all_rows),
        'out_qty': sum(r['out_qty'] for r in all_rows),
        'out_amt': sum(r['out_amt'] for r in all_rows),
        'closing_qty': sum(r['closing_qty'] for r in all_rows),
        'closing_val': sum(r['closing_val'] for r in all_rows),
    }

    return render_template(
        'reports/stock_movement.html',
        rows=rows,
        totals=totals,
        page=page, total_pages=total_pages, total=total,
        per_page=PER_PAGE_MOVEMENT,
        from_date=from_date, to_date=to_date,
        warehouse_id=warehouse_id, category=category, product_id=product_id,
        products=products, warehouses=warehouses, categories=categories,
    )


@reports_bp.route('/export/stock-movement')
@login_required
@require_permission('reports', 'export')
def export_stock_movement():
    from_dt, to_dt, from_date, to_date = _get_period(request)

    rows = _build_stock_movement_rows(
        from_dt, to_dt,
        warehouse_id=request.args.get('warehouse_id') or None,
        category=request.args.get('category') or None,
        product_id=request.args.get('product_id') or None,
    )

    rows_data = [
        {
            'Mã hàng': r['product'].code,
            'Tên hàng': r['product'].name,
            'ĐVT': r['product'].get_unit_name(),
            'Tồn đầu kỳ': round(r['opening_qty'], 3),
            'Nhập kỳ SL': round(r['in_qty'], 3),
            'Nhập kỳ TT': round(r['in_amt'], 0),
            'Xuất kỳ SL': round(r['out_qty'], 3),
            'Xuất kỳ TT': round(r['out_amt'], 0),
            'Tồn cuối kỳ': round(r['closing_qty'], 3),
            'Giá trị tồn': round(r['closing_val'], 0),
        }
        for r in rows
    ]

    df = pd.DataFrame(rows_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as w:
        df.to_excel(w, index=False, sheet_name='Xuất nhập tồn')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'xuat_nhap_ton_{from_date}_{to_date}.xlsx',
    )


@reports_bp.route('/customer-revenue')
@login_required
@require_permission('reports', 'view')
def customer_revenue():
    from_dt, to_dt, from_date, to_date = _get_period(request)
    customer_id = request.args.get('customer_id', '')

    revenue_sub = (
        db.session.query(
            StockOut.customer_id.label('cid'),
            func.count(StockOut.id).label('order_count'),
            func.sum(StockOut.subtotal).label('subtotal'),
            func.sum(StockOut.vat_amount).label('vat'),
            func.sum(StockOut.discount_amount).label('discount'),
            func.sum(StockOut.total_amount).label('total'),
            func.sum(StockOut.paid_amount).label('paid'),
        )
        .filter(func.lower(StockOut.status) == DocStatus.CONFIRMED,
                StockOut.date >= from_dt,
                StockOut.date <= to_dt)
        .group_by(StockOut.customer_id)
        .subquery()
    )
    debt_sub = (
        db.session.query(
            Debt.partner_id.label('cid'),
            func.sum(Debt.balance).label('debt'),
        )
        .filter(Debt.partner_type == 'customer', Debt.status != 'paid')
        .group_by(Debt.partner_id)
        .subquery()
    )

    q = (
        db.session.query(
            Customer,
            func.coalesce(revenue_sub.c.order_count, 0),
            func.coalesce(revenue_sub.c.subtotal, 0),
            func.coalesce(revenue_sub.c.vat, 0),
            func.coalesce(revenue_sub.c.discount, 0),
            func.coalesce(revenue_sub.c.total, 0),
            func.coalesce(revenue_sub.c.paid, 0),
            func.coalesce(debt_sub.c.debt, 0),
        )
        .outerjoin(revenue_sub, revenue_sub.c.cid == Customer.id)
        .outerjoin(debt_sub, debt_sub.c.cid == Customer.id)
        .filter(Customer.is_active == True)
    )
    if customer_id:
        q = q.filter(Customer.id == int(customer_id))

    rows = [
        {
            'customer': r[0], 'order_count': int(r[1]),
            'subtotal': float(r[2]), 'vat': float(r[3]),
            'discount': float(r[4]), 'total': float(r[5]),
            'paid': float(r[6]), 'debt': float(r[7]),
        }
        for r in q.all() if r[1] > 0
    ]
    rows.sort(key=lambda x: x['total'], reverse=True)

    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    return render_template(
        'reports/customer_revenue.html',
        rows=rows,
        from_date=from_date, to_date=to_date,
        customer_id=customer_id, customers=customers,
        total_revenue=sum(r['total'] for r in rows),
        total_debt=sum(r['debt'] for r in rows),
    )


@reports_bp.route('/customer-detail/<int:customer_id>')
@login_required
@require_permission('reports', 'view')
def customer_detail(customer_id):
    from_dt, to_dt, from_date, to_date = _get_period(request)
    page = request.args.get('page', 1, type=int)
    customer = Customer.query.get_or_404(customer_id)

    total_debt = db.session.query(func.sum(Debt.balance)).filter(
        Debt.partner_type == 'customer',
        Debt.partner_id == customer_id,
        Debt.status != 'paid',
    ).scalar() or 0

    orders = (
        StockOut.query
        .filter(StockOut.customer_id == customer_id,
                func.lower(StockOut.status) == DocStatus.CONFIRMED,
                StockOut.date.between(from_dt, to_dt))
        .order_by(StockOut.date.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )

    top_products_raw = (
        db.session.query(
            Product.code, Product.name,
            func.sum(StockOutItem.quantity).label('total_qty'),
            func.sum(StockOutItem.amount).label('total_amt'),
            func.count(StockOutItem.id).label('order_count'),
        )
        .join(StockOutItem, Product.id == StockOutItem.product_id)
        .join(StockOut, StockOutItem.stock_out_id == StockOut.id)
        .filter(StockOut.customer_id == customer_id,
                func.lower(StockOut.status) == DocStatus.CONFIRMED,
                StockOut.date.between(from_dt, to_dt))
        .group_by(Product.id, Product.code, Product.name)
        .order_by(func.sum(StockOutItem.amount).desc())
        .limit(10).all()
    )
    top_products = [
        {'code': r.code, 'name': r.name,
         'total_qty': float(r.total_qty or 0),
         'total_amt': float(r.total_amt or 0),
         'order_count': int(r.order_count or 0)}
        for r in top_products_raw
    ]

    agg = db.session.query(
        func.sum(StockOut.total_amount).label('revenue'),
        func.count(StockOut.id).label('orders'),
    ).filter(StockOut.customer_id == customer_id,
             func.lower(StockOut.status) == DocStatus.CONFIRMED).first()

    return render_template(
        'reports/customer_detail.html',
        customer=customer,
        total_debt=float(total_debt),
        total_revenue=float(agg.revenue or 0),
        total_orders=int(agg.orders or 0),
        orders=orders, top_products=top_products,
        from_date=from_date, to_date=to_date,
    )


@reports_bp.route('/supplier-purchase')
@login_required
@require_permission('reports', 'view')
def supplier_purchase():
    from_dt, to_dt, from_date, to_date = _get_period(request)

    purchase_sub = (
        db.session.query(
            StockIn.supplier_id.label('sid'),
            func.count(StockIn.id).label('order_count'),
            func.sum(StockIn.subtotal).label('subtotal'),
            func.sum(StockIn.vat_amount).label('vat'),
            func.sum(StockIn.total_amount).label('total'),
            func.sum(StockIn.paid_amount).label('paid'),
        )
        .filter(func.lower(StockIn.status) == DocStatus.CONFIRMED,
                StockIn.date >= from_dt,
                StockIn.date <= to_dt)
        .group_by(StockIn.supplier_id)
        .subquery()
    )

    debt_sub = (
        db.session.query(
            Debt.partner_id.label('sid'),
            func.sum(Debt.balance).label('debt'),
        )
        .filter(Debt.partner_type == 'supplier', Debt.status != 'paid')
        .group_by(Debt.partner_id)
        .subquery()
    )

    data = (
        db.session.query(
            Supplier,
            func.coalesce(purchase_sub.c.order_count, 0),
            func.coalesce(purchase_sub.c.subtotal, 0),
            func.coalesce(purchase_sub.c.vat, 0),
            func.coalesce(purchase_sub.c.total, 0),
            func.coalesce(purchase_sub.c.paid, 0),
            func.coalesce(debt_sub.c.debt, 0),
        )
        .outerjoin(purchase_sub, purchase_sub.c.sid == Supplier.id)
        .outerjoin(debt_sub, debt_sub.c.sid == Supplier.id)
        .filter(Supplier.is_active == True)
        .order_by(Supplier.code)
        .all()
    )

    rows = []
    for r in data:
        if int(r[1]) == 0:
            continue
        total = float(r[4])
        paid = float(r[5])
        rows.append({
            'supplier': r[0],
            'order_count': int(r[1]),
            'subtotal': float(r[2]),
            'vat': float(r[3]),
            'total': total,
            'paid': paid,
            'balance': total - paid,
            'debt': float(r[6]),
        })
    rows.sort(key=lambda x: x['total'], reverse=True)

    return render_template(
        'reports/supplier_purchase.html',
        rows=rows, from_date=from_date, to_date=to_date,
    )


@reports_bp.route('/realtime-inventory')
@login_required
@require_permission('reports', 'view')
def realtime_inventory():
    warehouse_id = request.args.get('warehouse_id', '')
    warehouses = Warehouse.query.filter_by(is_active=True).all()

    q = (
        db.session.query(
            Product.id, Product.code, Product.name,
            Product.unit, Product.category,
            Product.min_stock, Product.allow_negative,
            func.coalesce(func.sum(Inventory.quantity), 0).label('qty'),
            func.coalesce(func.avg(Inventory.avg_cost), 0).label('avg_cost'),
            func.coalesce(
                func.sum(Inventory.quantity * Inventory.avg_cost), 0
            ).label('value'),
        )
        .outerjoin(Inventory, Product.id == Inventory.product_id)
        .filter(Product.is_active == True)
    )
    if warehouse_id:
        q = q.filter(Inventory.warehouse_id == int(warehouse_id))

    data = (
        q.group_by(
            Product.id, Product.code, Product.name,
            Product.unit, Product.category,
            Product.min_stock, Product.allow_negative,
        )
        .order_by(Product.code)
        .all()
    )

    total_value = sum(float(r.value or 0) for r in data)
    conv_map = build_conversion_map([r.id for r in data])
    qty_display_map = {
        r.id: format_multi_unit_qty(float(r.qty or 0), conv_map.get(r.id))
        for r in data
    }
    low_count = sum(
        1 for r in data
        if float(r.qty or 0) <= float(r.min_stock or 0) > 0
    )

    return render_template(
        'reports/realtime_inventory.html',
        data=data, warehouses=warehouses,
        warehouse_id=warehouse_id,
        total_value=total_value, low_count=low_count,
        qty_display_map=qty_display_map,
    )
