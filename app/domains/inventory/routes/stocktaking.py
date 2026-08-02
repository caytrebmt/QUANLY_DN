from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from datetime import datetime
import io
from app.database import db
from app.domains.master.models import Warehouse, Product
from app.domains.inventory.models import Stocktaking, StocktakingItem
from app.domains.inventory.services.stocktaking_service import StocktakingService
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.authz import require_permission

stocktaking_bp = Blueprint('stocktaking', __name__, url_prefix='/inventory/stocktaking')


@stocktaking_bp.route('/')
@login_required
@require_permission('inventory', 'view')
def index():
    warehouse_id = request.args.get('warehouse_id', '', type=str)
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    sessions = StocktakingService.get_sessions(
        warehouse_id=int(warehouse_id) if warehouse_id else None,
        status=status if status else None,
        page=page,
    )
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    return render_template('inventory/stocktaking/index.html',
                           sessions=sessions, warehouses=warehouses,
                           warehouse_id=warehouse_id, status=status)


@stocktaking_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('inventory', 'create')
def create():
    if request.method == 'POST':
        warehouse_id = request.form.get('warehouse_id', type=int)
        count_date = request.form.get('count_date', datetime.utcnow().date().isoformat())
        note = request.form.get('note', '').strip()

        if not warehouse_id:
            flash('Vui lòng chọn kho kiểm kê.', 'danger')
            return redirect(url_for('stocktaking.create'))

        session = StocktakingService.create_session(
            warehouse_id=warehouse_id,
            count_date=datetime.strptime(count_date, '%Y-%m-%d').date(),
            note=note,
            user_id=current_user.id,
        )
        flash(f'Tạo phiếu kiểm kê #{session.id:06d} thành công!', 'success')
        return redirect(url_for('stocktaking.detail', id=session.id))

    warehouses = Warehouse.query.filter_by(is_active=True).all()
    return render_template('inventory/stocktaking/create.html', warehouses=warehouses, today=datetime.utcnow().date().isoformat())


@stocktaking_bp.route('/<int:id>')
@login_required
@require_permission('inventory', 'view')
def detail(id):
    session = StocktakingService.get_session(id)
    items = StocktakingItem.query.filter_by(stocktaking_id=id).order_by(StocktakingItem.product_id).all()
    discrepancies = StocktakingService.get_discrepancy_report(id) if session.status == 'completed' else []
    return render_template('inventory/stocktaking/detail.html',
                           session=session, items=items, discrepancies=discrepancies)


@stocktaking_bp.route('/<int:id>/update-item', methods=['POST'])
@login_required
@require_permission('inventory', 'edit')
def update_item(id):
    session = StocktakingService.get_session(id)
    if session.status != 'draft':
        flash('Chỉ có thể cập nhật phiếu ở trạng thái nháp.', 'danger')
        return redirect(url_for('stocktaking.detail', id=id))

    item_id = request.form.get('item_id', type=int)
    actual_qty = request.form.get('actual_quantity', 0)
    note = request.form.get('note', '').strip()

    StocktakingService.update_item(item_id, actual_qty, note)
    flash('Đã cập nhật số liệu thực tế.', 'success')
    return redirect(url_for('stocktaking.detail', id=id))


@stocktaking_bp.route('/<int:id>/complete', methods=['POST'])
@login_required
@require_permission('inventory', 'edit')
def complete(id):
    try:
        session = StocktakingService.complete_session(id, user_id=current_user.id)
        flash(f'Phiếu kiểm kê #{session.id:06d} đã hoàn thành. Tồn kho đã được điều chỉnh.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('stocktaking.detail', id=id))


@stocktaking_bp.route('/<int:id>/cancel', methods=['POST'])
@login_required
@require_permission('inventory', 'delete')
def cancel(id):
    try:
        session = StocktakingService.cancel_session(id, user_id=current_user.id)
        flash(f'Phiếu kiểm kê #{session.id:06d} đã hủy.', 'warning')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('stocktaking.index'))


@stocktaking_bp.route('/<int:id>/export/excel')
@login_required
@require_permission('inventory', 'export')
def export_excel(id):
    output, filename = StocktakingService.export_excel(id)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )
