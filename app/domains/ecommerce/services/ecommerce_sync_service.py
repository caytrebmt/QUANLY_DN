import re
import secrets
from datetime import date, datetime

from app.database import db
from app.domains.ecommerce.models import OnlineOrder, OnlineOrderItem, ProductListing, WebCustomer
from app.domains.master.models import Product, Warehouse
from app.domains.inventory.models import StockOut, StockOutItem
from app.domains.inventory.services.inventory_service import InventoryService


def generate_tracking_token():
    return secrets.token_urlsafe(32)


def slugify(value):
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    return value.strip('-') or 'san-pham'


def make_unique_slug(product):
    base = slugify(f'{product.code}-{product.name}')
    slug = base
    counter = 2
    while ProductListing.query.filter_by(slug=slug).first():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


def generate_online_order_code():
    today = date.today().strftime('%y%m%d')
    stem = f'WEB-{today}-'

    last = (
        OnlineOrder.query
        .filter(OnlineOrder.code.like(f'{stem}%'))
        .order_by(OnlineOrder.code.desc())
        .first()
    )

    next_number = 1

    if last:
        try:
            next_number = int(last.code.rsplit('-', 1)[1]) + 1
        except (ValueError, IndexError):
            pass

    return f'{stem}{next_number:04d}'


def publish_product_listing(product_id):
    product = Product.query.get_or_404(product_id)
    listing = ProductListing.query.filter_by(product_id=product.id).first()
    if not listing:
        listing = ProductListing(
            product_id=product.id,
            slug=make_unique_slug(product),
            web_title=product.name,
            web_description=product.description,
            web_price=product.sale_price,
            retail_price=getattr(product, 'retail_price', None),
            contact_for_price=bool(getattr(product, 'contact_for_price', False)),
            image_url=None,
            seo_title=product.name,

        )
        db.session.add(listing)

    listing.is_published = True

    listing.stock_cached = product.get_current_stock()
    listing.stock_synced_at = datetime.utcnow()
    return listing


def sync_inventory_to_listings():
    listings = ProductListing.query.join(Product).filter(Product.is_active.is_(True)).all()
    for listing in listings:
        listing.stock_cached = listing.product.get_current_stock() if listing.product else 0
        listing.stock_synced_at = datetime.utcnow()
    db.session.commit()
    return len(listings)


def _default_warehouse():
    return Warehouse.query.filter_by(is_active=True).order_by(Warehouse.id.asc()).first()


def sync_online_order_to_stock_out(order_id, warehouse_id=None, user_id=None, confirm_inventory=False):
    order = OnlineOrder.query.get_or_404(order_id)
    if order.stock_out_id:
        return order.stock_out

    if order.web_customer_id:
        web_customer = WebCustomer.query.get(order.web_customer_id)
        if web_customer and web_customer.customer_id and web_customer.customer_id != order.customer_id:
            order.customer_id = web_customer.customer_id

    warehouse = Warehouse.query.get(warehouse_id) if warehouse_id else _default_warehouse()
    if not warehouse:
        raise ValueError('Chưa có kho mặc định để sync đơn online sang phiếu xuất.')

    from app.routes.stock_out import _generate_code as generate_stock_out_code

    px_code = None
    try:
        code_str = (order.code or '').strip().upper()
        m = re.fullmatch(r'WEB-(\d{6})-(\d+)', code_str)
        if m:
            px_code = (f'PX-WEB-{m.group("date")}-{m.group("seq")}')
    except Exception:
        px_code = None

    stock_out_code = px_code or generate_stock_out_code()

    if stock_out_code and StockOut.query.filter_by(code=stock_out_code).first():
        stock_out_code = f"{stock_out_code}-{order.id}"

    stock_out = StockOut(
        code=stock_out_code,
        date=date.today(),
        customer_id=order.customer_id,
        warehouse_id=warehouse.id,
        reference=order.code,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        vat_amount=0,
        total_amount=order.total_amount,
        vat_mode='grouped',
        vat_rate_grouped=0,
        status='draft',
        note=f'Sync từ đơn online {order.code}. {order.note or ""}'.strip(),
        created_by=user_id,
    )
    db.session.add(stock_out)
    db.session.flush()

    for online_item in order.items.order_by(OnlineOrderItem.id.asc()).all():
        product = online_item.product
        line = StockOutItem(
            stock_out_id=stock_out.id,
            product_id=online_item.product_id,
            unit_id=product.unit_id if product else None,
            conversion_factor=1,
            quantity=online_item.quantity,
            unit_price=online_item.unit_price,
            vat_rate=0,
            amount=online_item.amount,
            total_amount=online_item.amount,
        )
        line.calculate()
        db.session.add(line)

    db.session.flush()
    stock_out.calculate_totals()

    if confirm_inventory:
        for line in stock_out.items.all():
            qty_base = float(line.quantity or 0) * float(line.conversion_factor or 1)
            _, cost_price = InventoryService.stock_out(
                line.product_id,
                stock_out.warehouse_id,
                qty_base,
                stock_out.code,
                note=f'Đơn online {order.code}',
                user_id=user_id,
            )
            line.cost_price = cost_price
        stock_out.status = 'confirmed'
        stock_out.confirmed_by = user_id
        stock_out.confirmed_at = datetime.utcnow()

    order.stock_out_id = stock_out.id
    order.sync_status = 'synced'
    order.sync_error = None
    order.synced_at = datetime.utcnow()
    order.update_erp_status(source='auto')
    db.session.commit()
    return stock_out


def listing_query(search=None, published=None):
    q = db.session.query(ProductListing).join(Product)
    if search:
        pattern = f'%{search}%'
        q = q.filter(db.or_(
            Product.code.ilike(pattern),
            Product.name.ilike(pattern),
            ProductListing.web_title.ilike(pattern),
        ))
    if published in ('1', 'true', True):
        q = q.filter(ProductListing.is_published.is_(True))
    elif published in ('0', 'false', False):
        q = q.filter(ProductListing.is_published.is_(False))
    return q


def ensure_listing_for_all_active_products():
    product_ids = {
        row[0]
        for row in db.session.query(ProductListing.product_id).all()
    }
    created = 0
    products = Product.query.filter(Product.is_active.is_(True)).order_by(Product.code).all()
    for product in products:
        if product.id in product_ids:
            continue
        db.session.add(ProductListing(
            product_id=product.id,
            slug=make_unique_slug(product),
            web_title=product.name,
            web_description=product.description,
            web_price=product.sale_price,
            retail_price=getattr(product, 'retail_price', None),
            contact_for_price=bool(getattr(product, 'contact_for_price', False)),

            image_url=None,
            seo_title=product.name,

            stock_cached=product.get_current_stock(),
            stock_synced_at=datetime.utcnow(),
            is_published=False,
        ))

        created += 1
    db.session.commit()
    return created

def _ensure_erp_customer_for_web(web_customer: WebCustomer) -> Customer:
    filters = []
    if web_customer.email:
        filters.append(Customer.email == web_customer.email)
    if web_customer.phone:
        filters.append(Customer.phone == web_customer.phone)
    if filters:
        existing = Customer.query.filter(db.or_(*filters)).first()
        if existing:
            web_customer.customer_id = existing.id
            return existing
    if web_customer.customer_id:
        if web_customer.customer:
            return web_customer.customer
        customer = Customer.query.get(web_customer.customer_id)
        if customer:
            return customer
    code = f'WEB-{web_customer.id}'
    while Customer.query.filter_by(code=code).first():
        code = f'WEB-{web_customer.id}-{__import__("random").randint(100, 999)}'
    customer = Customer(
        code=code,
        name=web_customer.name,
        short_name=web_customer.name,
        customer_type='retail',
        phone=web_customer.phone,
        email=web_customer.email,
        address='',
    )
    db.session.add(customer)
    db.session.flush()
    web_customer.customer_id = customer.id
    return customer
