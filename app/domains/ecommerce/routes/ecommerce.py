from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.database import db
from app.domains.ecommerce.models import OnlineOrder, OnlineOrderItem, ProductListing
from app.domains.master.models import Product, Warehouse
from app.shared.authz import require_permission
from app.domains.ecommerce.services.ecommerce_sync_service import (
    ensure_listing_for_all_active_products,
    listing_query,
    publish_product_listing,
    sync_inventory_to_listings,
    sync_online_order_to_stock_out,
)

ecommerce_bp = Blueprint('ecommerce', __name__, url_prefix='/ecommerce')


@ecommerce_bp.route('/')
@login_required
@require_permission('ecommerce', 'view')
def dashboard():
    return redirect(url_for('ecommerce.listings'))


@ecommerce_bp.route('/listings')
@login_required
@require_permission('ecommerce', 'view')
def listings():
    search = request.args.get('search', '')
    published = request.args.get('published', '')
    page = request.args.get('page', 1, type=int)
    rows = listing_query(search, published).order_by(Product.code.asc()).paginate(
        page=page, per_page=30, error_out=False
    )
    return render_template(
        'ecommerce/listings.html',
        listings=rows,
        search=search,
        published=published,
    )


@ecommerce_bp.post('/listings/ensure')
@login_required
@require_permission('ecommerce', 'create')
def ensure_listings():
    created = ensure_listing_for_all_active_products()
    flash(f'Đã tạo gợi ý listing web cho {created} sản phẩm.', 'success')
    return redirect(url_for('ecommerce.listings'))


@ecommerce_bp.post('/listings/publish/<int:product_id>')
@login_required
@require_permission('ecommerce', 'edit')
def publish_listing(product_id):
    listing = publish_product_listing(product_id)
    db.session.commit()
    flash(f'Đã bật bán web: {listing.display_name()}', 'success')
    return redirect(url_for('ecommerce.listings'))


@ecommerce_bp.post('/listings/<int:id>/toggle')
@login_required
@require_permission('ecommerce', 'edit')
def toggle_listing(id):
    listing = ProductListing.query.get_or_404(id)
    listing.is_published = not listing.is_published
    listing.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Đã cập nhật trạng thái hiển thị web.', 'success')
    return redirect(url_for('ecommerce.listings'))


@ecommerce_bp.post('/sync-inventory')
@login_required
@require_permission('ecommerce', 'edit')
def sync_inventory():
    count = sync_inventory_to_listings()
    flash(f'Đã đồng bộ tồn kho web cho {count} listing.', 'success')
    return redirect(url_for('ecommerce.listings'))


@ecommerce_bp.route('/orders')
@login_required
@require_permission('ecommerce', 'view')
def orders():
    search = request.args.get('search', '')
    sync_status = request.args.get('sync_status', '')
    page = request.args.get('page', 1, type=int)

    q = OnlineOrder.query
    if search:
        pattern = f'%{search}%'
        q = q.filter(db.or_(
            OnlineOrder.code.ilike(pattern),
            OnlineOrder.customer_name.ilike(pattern),
            OnlineOrder.customer_phone.ilike(pattern),
        ))
    if sync_status:
        q = q.filter(OnlineOrder.sync_status == sync_status)

    rows = q.order_by(OnlineOrder.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False
    )
    warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.name).all()
    return render_template(
        'ecommerce/orders.html',
        orders=rows,
        warehouses=warehouses,
        search=search,
        sync_status=sync_status,
    )


@ecommerce_bp.route('/orders/<int:id>')
@login_required
@require_permission('ecommerce', 'view')
def order_detail(id):
    order = OnlineOrder.query.get_or_404(id)
    items = order.items.order_by(OnlineOrderItem.created_at.asc()).all()
    return render_template(
        'ecommerce/orders_detail.html',
        order=order,
        items=items,
    )


@ecommerce_bp.post('/orders/<int:id>/sync')
@login_required
@require_permission('ecommerce', 'edit')
def sync_order(id):
    warehouse_id = request.form.get('warehouse_id', type=int)
    confirm_inventory = request.form.get('confirm_inventory') == '1'
    try:
        stock_out = sync_online_order_to_stock_out(
            id,
            warehouse_id=warehouse_id,
            user_id=current_user.id,
            confirm_inventory=confirm_inventory,
        )
        flash(f'Đã sync đơn online sang phiếu xuất {stock_out.code}.', 'success')
    except Exception as exc:
        order = OnlineOrder.query.get(id)
        if order:
            order.sync_status = 'failed'
            order.sync_error = str(exc)
            db.session.commit()
        flash(str(exc), 'danger')
    return redirect(url_for('ecommerce.orders'))
