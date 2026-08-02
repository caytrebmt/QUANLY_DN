from flask import (Blueprint, render_template, request, send_file, flash, redirect, url_for)
from flask_login import login_required
from app.database import db
from app.domains.master.models import Warehouse, Product
from app.domains.inventory.models import Inventory, InventoryHistory
from app.domains.inventory.services.inventory_service import InventoryService
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.pdf_exporter import PdfExporter
from app.shared.authz import require_permission
from app.domains.inventory.services.unit_display import build_conversion_map, format_multi_unit_qty
from datetime import datetime

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@inventory_bp.route('/')
@login_required
@require_permission('inventory', 'view')
def index():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    warehouse_id = request.args.get('warehouse_id', '', type=str)
    low_stock_only = request.args.get('low_stock', '')

    from sqlalchemy import func
    q = db.session.query(
        Product.id, Product.code, Product.name, Product.unit,
        Product.category, Product.min_stock,
        func.coalesce(func.sum(Inventory.quantity), 0).label('total_qty'),
        func.coalesce(func.avg(Inventory.avg_cost), 0).label('avg_cost'),
        func.coalesce(func.sum(Inventory.quantity * Inventory.avg_cost), 0).label('total_value')
    ).outerjoin(Inventory, Product.id == Inventory.product_id)

    if warehouse_id:
        q = q.filter(Inventory.warehouse_id == int(warehouse_id))
    if search:
        q = q.filter(db.or_(Product.code.ilike(f'%{search}%'),
                             Product.name.ilike(f'%{search}%')))
    if category:
        q = q.filter(Product.category == category)

    q = q.filter(Product.is_active == True).group_by(
        Product.id, Product.code, Product.name,
        Product.unit, Product.category, Product.min_stock
    )

    if low_stock_only:
        q = q.having(func.coalesce(func.sum(Inventory.quantity), 0) <= Product.min_stock)

    inventory_data = q.order_by(Product.code).all()

    categories = db.session.query(Product.category).filter(
        Product.category.isnot(None)).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    warehouses = Warehouse.query.filter_by(is_active=True).all()

    total_value = sum(float(r.total_value or 0) for r in inventory_data)
    conv_map = build_conversion_map([r.id for r in inventory_data])
    qty_display_map = {
        r.id: format_multi_unit_qty(float(r.total_qty or 0), conv_map.get(r.id))
        for r in inventory_data
    }

    low_stock_count = sum(
        1 for r in inventory_data
        if float(r.total_qty or 0) <= float(r.min_stock or 0)
        and float(r.min_stock or 0) > 0
    )
    return render_template('inventory/index.html',
                           inventory_data=inventory_data, search=search,
                           category=category, categories=categories,
                           warehouses=warehouses, warehouse_id=warehouse_id,
                           low_stock_only=low_stock_only, total_value=total_value,
                           low_stock_count=low_stock_count,
                           qty_display_map=qty_display_map)


@inventory_bp.route('/history')
@login_required
@require_permission('inventory', 'view')
def history():
    product_id = request.args.get('product_id', '', type=str)
    warehouse_id = request.args.get('warehouse_id', '', type=str)
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    page = request.args.get('page', 1, type=int)

    q = InventoryHistory.query
    if product_id:
        q = q.filter(InventoryHistory.product_id == int(product_id))
    if warehouse_id:
        q = q.filter(InventoryHistory.warehouse_id == int(warehouse_id))
    if from_date:
        q = q.filter(InventoryHistory.created_at >= datetime.strptime(from_date, '%Y-%m-%d'))
    if to_date:
        q = q.filter(InventoryHistory.created_at <= datetime.strptime(to_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))

    histories = q.order_by(InventoryHistory.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False)

    products = Product.query.filter_by(is_active=True).order_by(Product.code).all()
    warehouses = Warehouse.query.filter_by(is_active=True).all()

    return render_template('inventory/history.html',
                           histories=histories, products=products,
                           warehouses=warehouses, product_id=product_id,
                           warehouse_id=warehouse_id, from_date=from_date, to_date=to_date)


@inventory_bp.route('/export/excel')
@login_required
@require_permission('inventory', 'export')
def export_excel():
    from sqlalchemy import func
    inventory_data = db.session.query(
        Product.id, Product.code, Product.name, Product.unit,
        Product.category, Product.min_stock,
        func.coalesce(func.sum(Inventory.quantity), 0).label('total_qty'),
        func.coalesce(func.avg(Inventory.avg_cost), 0).label('avg_cost'),
        func.coalesce(func.sum(Inventory.quantity * Inventory.avg_cost), 0).label('total_value')
    ).outerjoin(Inventory, Product.id == Inventory.product_id
    ).filter(Product.is_active == True
    ).group_by(Product.id, Product.code, Product.name,
               Product.unit, Product.category, Product.min_stock
    ).order_by(Product.code).all()

    output = ExcelExporter.export_inventory(inventory_data)
    return send_file(output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=f'ton_kho_{datetime.now().strftime("%Y%m%d")}.xlsx')


@inventory_bp.route('/export/pdf')
@login_required
@require_permission('inventory', 'export')
def export_pdf():
    from sqlalchemy import func
    inventory_data = db.session.query(
        Product.id, Product.code, Product.name, Product.unit,
        Product.category, Product.min_stock,
        func.coalesce(func.sum(Inventory.quantity), 0).label('total_qty'),
        func.coalesce(func.avg(Inventory.avg_cost), 0).label('avg_cost'),
        func.coalesce(func.sum(Inventory.quantity * Inventory.avg_cost), 0).label('total_value')
    ).outerjoin(Inventory, Product.id == Inventory.product_id
    ).filter(Product.is_active == True
    ).group_by(Product.id, Product.code, Product.name,
               Product.unit, Product.category, Product.min_stock
    ).order_by(Product.code).all()

    buffer = PdfExporter.export_inventory_report(inventory_data)
    return send_file(buffer, mimetype='application/pdf', as_attachment=False,
                     download_name='bao_cao_ton_kho.pdf')

