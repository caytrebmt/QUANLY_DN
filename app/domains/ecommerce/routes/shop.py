import uuid
from datetime import datetime, timedelta

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_

from app.database import db
from app.domains.ecommerce.models import (
    Cart,
    CartItem,
    CustomerSession,
    OnlineOrder,
    OnlineOrderItem,
    ProductListing,
    Promotion,
    WebCustomer,
)
from app.domains.master.models import Customer, Product
from app.domains.ecommerce.services.ecommerce_sync_service import (
    _ensure_erp_customer_for_web,
    generate_online_order_code,
    generate_tracking_token,
    listing_query,
)
from app.domains.ecommerce.middleware.role_middleware import web_customer_only
from zoneinfo import ZoneInfo

shop_bp = Blueprint('shop', __name__, url_prefix='')

vn_tz = ZoneInfo('Asia/Ho_Chi_Minh')
def now_vn():
    return datetime.now(vn_tz)

def _is_web_customer():
    return bool(current_user.is_authenticated and isinstance(current_user._get_current_object(), WebCustomer))


def _shop_session_key():
    key = session.get('shop_session_key')
    if not key:
        key = uuid.uuid4().hex
        session['shop_session_key'] = key
    return key


def _get_or_create_customer_session():
    key = _shop_session_key()
    customer_session = CustomerSession.query.filter_by(session_key=key).first()
    if not customer_session:
        customer_session = CustomerSession(
            session_key=key,
            expires_at=now_vn() + timedelta(days=30),
        )
        db.session.add(customer_session)
        db.session.flush()

    if _is_web_customer():
        customer_session.customer_id = current_user.customer_id
        customer_session.name = current_user.name
        customer_session.email = current_user.email
        customer_session.phone = current_user.phone
    customer_session.last_seen_at = now_vn()
    return customer_session

def _web_customer_sessions():
    ids = set()

    key = session.get('shop_session_key')
    if key:
        cs = CustomerSession.query.filter_by(session_key=key).first()
        if cs:
            ids.add(cs.id)

    if _is_web_customer():
        if current_user.email:
            by_email = CustomerSession.query.filter_by(
                email=current_user.email
            ).with_entities(CustomerSession.id).all()
            ids.update(r.id for r in by_email)

        if current_user.customer_id is not None:
            by_cid = CustomerSession.query.filter_by(
                customer_id=current_user.customer_id
            ).with_entities(CustomerSession.id).all()
            ids.update(r.id for r in by_cid)

    return list(ids)


def _user_orders_query():
    if not _is_web_customer():
        return None

    conditions = []

    if hasattr(OnlineOrder, 'web_customer_id'):
        conditions.append(OnlineOrder.web_customer_id == current_user.id)

    if current_user.customer_id is not None:
        conditions.append(OnlineOrder.customer_id == current_user.customer_id)

    session_ids = _web_customer_sessions()
    if session_ids:
        conditions.append(OnlineOrder.session_id.in_(session_ids))

    if not conditions:
        return OnlineOrder.query.filter(db.false())

    from sqlalchemy import or_
    return OnlineOrder.query.filter(or_(*conditions))


def _get_user_orders():
    return _user_orders_query()


def _get_user_order_by_code(code):
    if not _is_web_customer():
        return None
    q = _user_orders_query()
    if q is None:
        return None
    return q.filter_by(code=code).first()


def _get_user_orders_by_status(status):
    q = _user_orders_query()
    if q is None:
        return None
    return q.filter_by(status=status)


def _get_user_order_count():
    q = _user_orders_query()
    if q is None:
        return 0
    return q.count()

def _active_cart():
    customer_session = _get_or_create_customer_session()
    cart = Cart.query.filter_by(session_id=customer_session.id, status='active').first()
    if not cart:
        cart = Cart(session_id=customer_session.id, customer_id=customer_session.customer_id)
        db.session.add(cart)
        db.session.flush()
    elif _is_web_customer() and not cart.customer_id:
        cart.customer_id = current_user.customer_id
    return cart


def _cart_context():
    cart = _active_cart()
    items = cart.items.order_by(CartItem.id.asc()).all()
    total_qty = sum(float(i.quantity or 0) for i in items)
    subtotal = sum(float(i.quantity or 0) * float(i.unit_price or 0) for i in items)
    return cart, items, total_qty, subtotal


@shop_bp.context_processor
def inject_shop_globals():
    total_qty = 0
    key = session.get('shop_session_key')
    if key:
        customer_session = CustomerSession.query.filter_by(session_key=key).first()
        cart = Cart.query.filter_by(session_id=customer_session.id, status='active').first() if customer_session else None
        if cart:
            total_qty = sum(float(i.quantity or 0) for i in cart.items)
    categories = []
    try:
        from app.domains.master.models import Category
        categories = Category.query.filter_by(is_active=True, show_on_web=True).all()
        categories = [{'id': c.id, 'name': c.name, 'slug': c.slug} for c in categories]
    except:
        categories = [
            {'id': 1, 'name': 'Văn phòng phẩm', 'slug': 'van-phong'},
            {'id': 2, 'name': 'Máy in & Mực', 'slug': 'may-in'},
            {'id': 3, 'name': 'Thiết bị văn phòng', 'slug': 'thiet-bi'},
        ]
    order_count = _get_user_order_count() if _is_web_customer() else 0

    return {
        'shop_cart_qty': total_qty,
        'is_web_customer': _is_web_customer,
        'order_count': order_count,
        'categories': categories,
        'now': now_vn(),
    }


@shop_bp.route('/')
def catalog():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    listings = listing_query(search, True).order_by(Product.name.asc()).paginate(
        page=page, per_page=24, error_out=False
    )
    return render_template('shop/catalog.html', listings=listings, search=search)


@shop_bp.route('/spa-test')
def spa_test():
    return render_template('shop/spa_test.html')


@shop_bp.route('/placeholder.svg')
def product_placeholder():
    code = (request.args.get('code') or 'ERP').upper()[:18]
    name = (request.args.get('name') or 'Sản phẩm')[:40]

    words = name.split()[:2]
    initials = ''.join(word[0].upper() for word in words if word) if words else code[0] if code else 'P'

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f8f9fa"/>
      <stop offset="100%" stop-color="#e9ecef"/>
    </linearGradient>
    <linearGradient id="icon" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f3b2c"/>
      <stop offset="100%" stop-color="#d4a373"/>
    </linearGradient>
  </defs>

  <rect width="400" height="400" rx="16" fill="url(#bg)"/>

  <circle cx="200" cy="200" r="80" fill="url(#icon)" opacity="0.1"/>

  <g transform="translate(200, 170)" fill="url(#icon)" opacity="0.6">
    <rect x="-25" y="-15" width="50" height="30" rx="4"/>
    <rect x="-15" y="15" width="30" height="4" rx="2"/>
    <rect x="-20" y="-25" width="40" height="10" rx="2"/>
  </g>

  <text x="200" y="240" text-anchor="middle" font-family="Arial, sans-serif" font-size="32" font-weight="700" fill="#0f3b2c" opacity="0.8">
    {initials}
  </text>

  <text x="200" y="270" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#adb5bd">
    {code}
  </text>

  <text x="200" y="320" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#adb5bd">
    Hình ảnh minh họa
  </text>
</svg>"""
    return Response(svg, mimetype='image/svg+xml')


@shop_bp.route('/product/<slug>')
def product_detail(slug):
    listing = ProductListing.query.filter_by(slug=slug, is_published=True).first_or_404()
    return render_template('shop/product_detail.html', listing=listing)


@shop_bp.route('/product/')
def product_missing_slug():
    flash('Bạn cần chọn một sản phẩm cụ thể để xem chi tiết.', 'info')
    return redirect(url_for('shop.catalog'))


@shop_bp.post('/cart/add/<int:listing_id>')
def add_to_cart(listing_id):
    listing = ProductListing.query.filter_by(
        id=listing_id,
        is_published=True
    ).first_or_404()

    quantity_raw = None
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        quantity_raw = payload.get('quantity')
    if quantity_raw is None:
        quantity_raw = request.form.get('quantity')

    quantity = max(int(quantity_raw or 1), 1)

    cart = _active_cart()

    item = CartItem.query.filter_by(
        cart_id=cart.id,
        listing_id=listing.id
    ).first()

    price = listing.display_retail_price()

    if item:
        item.quantity = int(item.quantity or 0) + quantity
        item.unit_price = price
    else:
        item = CartItem(
            cart_id=cart.id,
            listing_id=listing.id,
            product_id=listing.product_id,
            quantity=quantity,
            unit_price=price,
        )
        db.session.add(item)

    db.session.commit()

    total_qty = sum(float(i.quantity or 0) for i in cart.items)
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'ok': True,
            'message': 'Đã thêm sản phẩm vào giỏ hàng',
            'cart_qty': int(total_qty) if float(total_qty).is_integer() else total_qty,
            'cart_url': url_for('shop.cart'),
        })

    flash('Đã thêm sản phẩm vào giỏ hàng.', 'success')
    return redirect(request.referrer or url_for('shop.cart'))


@shop_bp.route('/cart')
def cart():
    _, items, _, subtotal = _cart_context()
    return render_template('shop/cart.html', items=items, subtotal=subtotal)


@shop_bp.post('/cart/update')
def update_cart():
    cart = _active_cart()
    for item in cart.items:
        qty = request.form.get(f'qty_{item.id}', type=float)
        if qty is None:
            continue
        if qty <= 0:
            db.session.delete(item)
        else:
            item.quantity = qty
    db.session.commit()
    flash('Đã cập nhật giỏ hàng.', 'success')
    return redirect(url_for('shop.cart'))


@shop_bp.post('/cart/remove/<int:item_id>')
def remove_cart_item(item_id):
    cart = _active_cart()
    item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash('Đã xóa sản phẩm khỏi giỏ hàng.', 'info')
    return redirect(url_for('shop.cart'))


@shop_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart, items, _, subtotal = _cart_context()
    if not items:
        flash('Giỏ hàng đang trống.', 'warning')
        return redirect(url_for('shop.catalog'))

    customer_id = None
    customer = None

    if _is_web_customer():
        customer_id = current_user.customer_id
        if customer_id is None:
            customer_id = _ensure_erp_customer_for_web(current_user).id
        customer = current_user
    else:
        email = (request.form.get('customer_email') or '').strip().lower()
        if email:
            existing_customer = WebCustomer.query.filter_by(email=email).first()
            if existing_customer:
                customer_id = existing_customer.customer_id

    if request.method == 'POST':
        promo_code = (request.form.get('promotion_code') or '').strip()
        promotion = None
        discount_amount = 0
        if promo_code:
            promotion = Promotion.query.filter(
                func.lower(Promotion.code) == promo_code.lower(),
                Promotion.is_active.is_(True),
            ).first()
            if promotion:
                discount_amount = promotion.calculate_discount(subtotal)

        order = OnlineOrder(
            code=generate_online_order_code(),
            tracking_token=generate_tracking_token(),
            session_id=cart.session_id,
            customer_id=customer_id,
            **({'web_customer_id': current_user.id} if _is_web_customer() and hasattr(OnlineOrder, 'web_customer_id') else {}),
            promotion_id=promotion.id if promotion else None,
            customer_name=request.form.get('customer_name') or (current_user.name if _is_web_customer() else 'Khách online'),
            customer_phone=request.form.get('customer_phone') or (current_user.phone if _is_web_customer() else None),
            customer_email=request.form.get('customer_email') or (current_user.email if _is_web_customer() else None),
            shipping_address=request.form.get('shipping_address'),
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_fee=float(request.form.get('shipping_fee') or 0),
            vat_amount=0,
            status='new',
            sync_status='pending',
            note=request.form.get('note'),
        )
        order.total_amount = float(order.subtotal or 0) - float(order.discount_amount or 0) + float(order.shipping_fee or 0)
        db.session.add(order)
        db.session.flush()

        for item in items:
            amount = float(item.quantity or 0) * float(item.unit_price or 0)
            db.session.add(OnlineOrderItem(
                online_order_id=order.id,
                listing_id=item.listing_id,
                product_id=item.product_id,
                product_name_snapshot=item.product.name if item.product else None,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=amount,
            ))

        cart.status = 'ordered'
        db.session.commit()

        if not _is_web_customer() and order.customer_email:
            pass

        flash(f'Đặt hàng thành công. Mã đơn của bạn: {order.code}', 'success')

        if _is_web_customer():
            return redirect(url_for('shop.order_detail', code=order.code))
        return redirect(url_for('shop.order_success', code=order.code))

    return render_template('shop/checkout.html', items=items, subtotal=subtotal)


@shop_bp.route('/order-success/<code>')
def order_success(code):
    order = OnlineOrder.query.filter_by(code=code).first_or_404()
    if _is_web_customer():
        allowed_q = _user_orders_query()
        if allowed_q is not None:
            owns = allowed_q.filter_by(code=code).first()
            if not owns:
                flash('Bạn không có quyền xem đơn hàng này.', 'danger')
                return redirect(url_for('shop.catalog'))
    return render_template('shop/order_success.html', order=order)

@shop_bp.route('/orders')
@login_required
@web_customer_only
def order_history():
    if not _is_web_customer():
        flash('Vui lòng đăng nhập để xem lịch sử đơn hàng.', 'warning')
        return redirect(url_for('shop.login'))

    page   = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')

    query = _user_orders_query()
    if query is None:
        flash('Không thể xác định tài khoản.', 'warning')
        return redirect(url_for('shop.login'))
    if status:
        query = query.filter_by(status=status)

    orders = query.order_by(OnlineOrder.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    for o in orders.items:
        if o.stock_out_id:
            o.update_erp_status('auto')
    if orders.items:
        db.session.commit()
    return render_template('shop/order_history.html', orders=orders, status=status)


@shop_bp.route('/orders/<code>')
@login_required
@web_customer_only
def order_detail(code):
    if not _is_web_customer():
        flash('Vui lòng đăng nhập để xem chi tiết đơn hàng.', 'warning')
        return redirect(url_for('shop.login'))
    order = _get_user_order_by_code(code)
    if not order:
        flash('Không tìm thấy đơn hàng.', 'warning')
        return redirect(url_for('shop.order_history'))
    if order.stock_out_id:
        order.update_erp_status('auto')
        db.session.commit()
    return render_template('shop/order_detail.html', order=order)


@shop_bp.route('/track', methods=['GET'])
def track_order():
    order = None
    token = (request.args.get('token') or '').strip()
    code = (request.args.get('code') or '').strip()
    if token:
        order = OnlineOrder.query.filter_by(tracking_token=token).first()
    elif code:
        order = OnlineOrder.query.filter_by(code=code).first()
    if not order:
        flash('Không tìm thấy đơn hàng. Vui lòng kiểm tra lại link tra cứu.', 'warning')
    return render_template('shop/track_order.html', order=order)

@shop_bp.route('/login', methods=['GET', 'POST'])
def login():
    if _is_web_customer():
        return redirect(url_for('shop.catalog'))
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        ip = (request.headers.get('X-Forwarded-For', request.remote_addr) or 'unknown').split(',')[0].strip()

        try:
            from app.core.extensions import cache
            fail_key = f'shop_login_fail:{ip}:{email}'
            fail_data = cache.get(fail_key)
            if fail_data and fail_data.get('lock_until') and datetime.utcnow() < fail_data['lock_until']:
                left = int((fail_data['lock_until'] - datetime.utcnow()).total_seconds() // 60) + 1
                flash(f'Tài khoản tạm khóa. Vui lòng thử lại sau {left} phút.', 'warning')
                return render_template('shop/login.html')
        except Exception:
            pass

        web_customer = WebCustomer.query.filter_by(email=email, is_active=True).first()
        if web_customer and web_customer.check_password(password):
            try:
                from app.core.extensions import cache
                cache.delete(f'shop_login_fail:{ip}:{email}')
            except Exception:
                pass
            web_customer.last_login = now_vn()
            db.session.commit()
            login_user(web_customer, remember=bool(request.form.get('remember')))
            _get_or_create_customer_session()
            db.session.commit()
            flash('Đăng nhập mua hàng thành công.', 'success')
            return redirect(request.args.get('next') or url_for('shop.catalog'))

        try:
            from app.core.extensions import cache
            fail_key = f'shop_login_fail:{ip}:{email}'
            fail_data = cache.get(fail_key) or {'count': 0, 'lock_until': None}
            fail_data['count'] = fail_data.get('count', 0) + 1
            if fail_data['count'] >= 5:
                fail_data['lock_until'] = datetime.utcnow() + timedelta(minutes=10)
                fail_data['count'] = 0
            cache.set(fail_key, fail_data, timeout=600)
        except Exception:
            pass
        flash('Email hoặc mật khẩu không đúng.', 'danger')
    return render_template('shop/login.html')

@shop_bp.route('/account')
@login_required
@web_customer_only
def account():
    if not _is_web_customer():
        return redirect(url_for('shop.login'))
    _q = _user_orders_query()
    orders = _q.order_by(OnlineOrder.created_at.desc()).limit(20).all() if _q is not None else []
    wishlist  = getattr(current_user, 'wishlist_listings', [])
    addresses = getattr(current_user, 'addresses', [])
    pending_orders = sum(1 for o in orders if o.status in ('new', 'processing'))
    return render_template('shop/account.html',
        orders=orders, wishlist=wishlist,
        addresses=addresses, pending_orders=pending_orders)

@shop_bp.route('/account/profile', methods=['POST'])
@login_required
def update_profile():
    current_user.name         = request.form.get('name', '').strip()
    current_user.phone        = request.form.get('phone', '').strip()
    current_user.company_name = request.form.get('company_name', '').strip()
    current_user.tax_code     = request.form.get('tax_code', '').strip()
    email = request.form.get('email')
    if email:
        current_user.email = email.strip().lower()
    customer = _ensure_erp_customer_for_web(current_user)
    customer.name = current_user.name
    customer.phone = current_user.phone
    if email:
        customer.email = current_user.email
    db.session.commit()
    flash('Đã cập nhật thông tin.', 'success')
    return redirect(url_for('shop.account'))

@shop_bp.route('/account/password', methods=['POST'])
@login_required
def change_password():
    cur = request.form.get('current_password', '')
    new = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    if not current_user.check_password(cur):
        flash('Mật khẩu hiện tại không đúng.', 'danger')
    elif new != confirm:
        flash('Mật khẩu xác nhận không khớp.', 'danger')
    elif len(new) < 8:
        flash('Mật khẩu mới tối thiểu 8 ký tự.', 'danger')
    else:
        current_user.set_password(new)
        db.session.commit()
        flash('Đổi mật khẩu thành công!', 'success')
    return redirect(url_for('shop.account'))


@shop_bp.route('/register', methods=['GET', 'POST'])
def register():
    if _is_web_customer():
        return redirect(url_for('shop.catalog'))
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''
        name = (request.form.get('name') or '').strip()
        phone = (request.form.get('phone') or '').strip()

        if not email or not password or not name:
            flash('Vui lòng nhập đầy đủ họ tên, email và mật khẩu.', 'warning')
        elif password != confirm:
            flash('Mật khẩu xác nhận không khớp.', 'warning')
        elif WebCustomer.query.filter_by(email=email).first():
            flash('Email này đã được đăng ký.', 'warning')
        else:
            web_customer = WebCustomer(
                customer_id=None,
                email=email,
                name=name,
                phone=phone,
            )
            web_customer.set_password(password)
            db.session.add(web_customer)
            db.session.commit()
            _ensure_erp_customer_for_web(web_customer)
            db.session.commit()
            login_user(web_customer)
            flash('Tạo tài khoản mua hàng thành công.', 'success')
            return redirect(url_for('shop.catalog'))
    return render_template('shop/register.html')



@shop_bp.post('/orders/<int:order_id>/reorder')
@login_required
@web_customer_only
def reorder(order_id):
    base_q = _user_orders_query()
    order = base_q.filter_by(id=order_id).first_or_404() if base_q is not None else None
    if not order:
        return jsonify({'ok': False, 'message': 'Không tìm thấy đơn hàng.'}), 404
    cart = _active_cart()
    added = 0
    for item in order.items:
        listing = ProductListing.query.filter_by(
            id=item.listing_id, is_published=True
        ).first()
        if not listing:
            continue
        existing = CartItem.query.filter_by(
            cart_id=cart.id, listing_id=listing.id
        ).first()
        if existing:
            existing.quantity = float(existing.quantity or 0) + float(item.quantity or 1)
        else:
            db.session.add(CartItem(
                cart_id=cart.id,
                listing_id=listing.id,
                product_id=listing.product_id,
                quantity=item.quantity,
                unit_price=listing.display_retail_price(),
            ))
        added += 1
    db.session.commit()
    total_qty = sum(float(i.quantity or 0) for i in cart.items)
    return jsonify({'ok': True, 'added': added, 'cart_qty': int(total_qty)})


@shop_bp.post('/orders/<int:order_id>/cancel')
@login_required
@web_customer_only
def cancel_order(order_id):
    base_q = _user_orders_query()
    order = base_q.filter_by(id=order_id).first() if base_q is not None else None
    if not order:
        return jsonify({'ok': False, 'message': 'Không tìm thấy đơn hàng.'}), 404
    if order.status != 'new':
        return jsonify({'ok': False, 'message': 'Chỉ có thể hủy đơn hàng ở trạng thái Mới.'}), 400
    order.status = 'cancelled'
    db.session.commit()
    return jsonify({'ok': True})


@shop_bp.route('/auth/google/login')
def google_login():
    flash('Tính năng đăng nhập Google chưa được cấu hình.', 'warning')
    return redirect(url_for('shop.login'))


@shop_bp.route('/auth/google/callback')
def google_callback():
    flash('Tính năng đăng nhập Google chưa được cấu hình.', 'warning')
    return redirect(url_for('shop.login'))


@shop_bp.route('/account/link/google')
@login_required
def link_google():
    flash('Tính năng liên kết Google chưa được cấu hình.', 'warning')
    return redirect(url_for('shop.account'))


@shop_bp.post('/account/unlink/google')
@login_required
def unlink_google():
    flash('Tính năng liên kết Google chưa được cấu hình.', 'warning')
    return redirect(url_for('shop.account'))

@shop_bp.route('/set-lang/<lang>')
def set_lang(lang):
    if lang not in {'vi', 'en'}:
        lang = 'vi'
    session['lang'] = lang
    resp = redirect(request.referrer or url_for('shop.catalog'))
    resp.set_cookie('lang', lang, max_age=30*24*3600, httponly=True)
    return resp


@shop_bp.route('/logout')
@login_required
def logout():
    if _is_web_customer():
        logout_user()
        flash('Đã đăng xuất tài khoản mua hàng.', 'info')
        return redirect(url_for('shop.catalog'))
    return redirect(url_for('auth.logout'))
