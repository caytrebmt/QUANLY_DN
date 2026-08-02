from datetime import datetime

from zoneinfo import ZoneInfo

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app.domains.master.models import ProductImage
from app.database import db


class WebCustomer(UserMixin, db.Model):
    """Customer account for the public shop, separate from ERP users."""
    __tablename__ = 'customer_accounts'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(50), default='web_customer')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    customer = db.relationship('Customer', foreign_keys=[customer_id])

    def get_id(self):
        return f'web:{self.id}'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

class ProductListing(db.Model):
    __tablename__ = 'product_listings'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('products.id'),
        nullable=False,
        unique=True
    )

    slug = db.Column(db.String(220), nullable=False, unique=True)

    web_title = db.Column(db.String(220))
    web_description = db.Column(db.Text)

    web_price = db.Column(db.Numeric(18, 2))
    retail_price = db.Column(db.Numeric(18, 2))

    contact_for_price = db.Column(db.Boolean, default=False)

    compare_at_price = db.Column(db.Numeric(18, 2))

    image_url = db.Column(db.String(500))

    seo_title = db.Column(db.String(220))
    seo_description = db.Column(db.String(300))

    stock_cached = db.Column(db.Numeric(18, 3), default=0)
    stock_synced_at = db.Column(db.DateTime)

    is_published = db.Column(db.Boolean, default=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    product = db.relationship(
        'Product',
        foreign_keys=[product_id]
    )

    cart_items = db.relationship(
        'CartItem',
        backref='listing',
        lazy='dynamic'
    )

    order_items = db.relationship(
        'OnlineOrderItem',
        backref='listing',
        lazy='dynamic'
    )

    def display_name(self):
        return self.web_title or (
            self.product.name if self.product else ''
        )

    def display_price(self):
        if self.web_price is not None:
            return float(self.web_price or 0)

        return float(
            self.product.sale_price or 0
        ) if self.product else 0

    def display_retail_price(self):
        if self.retail_price is not None:
            return float(self.retail_price or 0)

        return float(
            getattr(self.product, 'retail_price', 0) or 0
        ) if self.product else 0

    def get_main_image(self):
        if not self.product:
            return self.image_url

        images = list(getattr(self.product, 'images', []) or [])
        if not images:
            return self.image_url

        main = next((img for img in images if getattr(img, 'is_main', False)), None)
        if main:
            return main.image_url

        images_sorted = sorted(images, key=lambda img: (
            img.sort_order if getattr(img, 'sort_order', None) is not None else 999999,
            img.id if getattr(img, 'id', None) is not None else 999999,
        ))
        return images_sorted[0].image_url if images_sorted else self.image_url

    @property
    def display_image(self):
        if self.product:
            return self.get_main_image()
        return self.image_url

    def to_dict(self):
        product = self.product

        return {
            'id': self.id,
            'product_id': self.product_id,
            'code': product.code if product else '',
            'name': self.display_name(),
            'slug': self.slug,

            'description':
                self.web_description
                or (product.description if product else ''),

            'price': self.display_price(),

            'retail_price':
                self.display_retail_price(),

            'contact_for_price':
                bool(self.contact_for_price),

            'image_url':
                self.display_image,

            'stock':
                float(self.stock_cached or 0),

            'is_published':
                bool(self.is_published),
        }


class CustomerSession(db.Model):
    __tablename__ = 'customer_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_key = db.Column(db.String(120), nullable=False, unique=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    name = db.Column(db.String(200), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)

    customer = db.relationship('Customer', foreign_keys=[customer_id])
    carts = db.relationship('Cart', backref='customer_session', lazy='dynamic')


class Cart(db.Model):
    __tablename__ = 'cart'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('customer_sessions.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = db.relationship('Customer', foreign_keys=[customer_id])
    items = db.relationship('CartItem', backref='cart', lazy='dynamic', cascade='all, delete-orphan')

    def totals(self):
        subtotal = sum(int(i.quantity or 0) * float(i.unit_price or 0) for i in self.items)
        return {'subtotal': subtotal, 'total': subtotal}


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('product_listings.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(18, 3), nullable=False, default=1)
    unit_price = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship('Product', foreign_keys=[product_id])


class Promotion(db.Model):
    __tablename__ = 'promotions'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    discount_type = db.Column(db.String(20), default='percent')
    discount_value = db.Column(db.Numeric(18, 2), default=0)
    min_order_amount = db.Column(db.Numeric(18, 2), default=0)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def calculate_discount(self, amount):
        amount = float(amount or 0)
        if not self.is_active or amount < float(self.min_order_amount or 0):
            return 0
        if self.discount_type == 'amount':
            return min(float(self.discount_value or 0), amount)
        return amount * float(self.discount_value or 0) / 100


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey('product_listings.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    customer_name = db.Column(db.String(200), nullable=True)
    rating = db.Column(db.Integer, nullable=False, default=5)
    title = db.Column(db.String(200), nullable=True)
    content = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', foreign_keys=[product_id])
    customer = db.relationship('Customer', foreign_keys=[customer_id])


class OnlineOrder(db.Model):
    __tablename__ = 'online_orders'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), nullable=False, unique=True)
    session_id = db.Column(db.Integer, db.ForeignKey('customer_sessions.id'), nullable=True)
    web_customer_id = db.Column(db.Integer, db.ForeignKey('customer_accounts.id'), nullable=True, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    promotion_id = db.Column(db.Integer, db.ForeignKey('promotions.id'), nullable=True)
    tracking_token = db.Column(db.String(64), nullable=True, unique=True, index=True)
    customer_name = db.Column(db.String(200), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=True)
    customer_email = db.Column(db.String(120), nullable=True)
    shipping_address = db.Column(db.String(500), nullable=True)
    payment_method = db.Column(db.String(20), nullable=True)
    subtotal = db.Column(db.Numeric(18, 2), default=0)
    discount_amount = db.Column(db.Numeric(18, 2), default=0)
    shipping_fee = db.Column(db.Numeric(18, 2), default=0)
    vat_amount = db.Column(db.Numeric(18, 2), default=0)
    total_amount = db.Column(db.Numeric(18, 2), default=0)
    status = db.Column(db.String(20), default='new')
    sync_status = db.Column(db.String(20), default='pending')
    sync_error = db.Column(db.Text, nullable=True)
    stock_out_id = db.Column(db.Integer, db.ForeignKey('stock_outs.id'), nullable=True)
    erp_status = db.Column(db.String(20), nullable=True, comment='Trạng thái bản ghi xuất kho ERP')
    erp_note = db.Column(db.Text, nullable=True, comment='Ghi chú cập nhật từ ERP')
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    synced_at = db.Column(db.DateTime, nullable=True)

    customer = db.relationship('Customer', foreign_keys=[customer_id])
    web_customer = db.relationship('WebCustomer', foreign_keys=[web_customer_id], backref='orders')
    session = db.relationship('CustomerSession', foreign_keys=[session_id])
    promotion = db.relationship('Promotion', foreign_keys=[promotion_id])
    stock_out = db.relationship('StockOut', foreign_keys=[stock_out_id])
    items = db.relationship('OnlineOrderItem', backref='online_order', lazy='dynamic', cascade='all, delete-orphan')

    def calculate_totals(self):
        subtotal = sum(float(i.amount or 0) for i in self.items)
        self.subtotal = subtotal
        self.total_amount = subtotal - float(self.discount_amount or 0) + float(self.shipping_fee or 0) + float(self.vat_amount or 0)

    def update_erp_status(self, source: str = 'auto'):
        if not self.stock_out:
            self.erp_status = None
            self.erp_note = 'Chưa liên kết phiếu xuất kho.'
            return
        so = self.stock_out
        status_map = {
            'draft': 'Chờ xử lý',
            'confirmed': 'Đã xuất kho',
            'cancelled': 'Đã hủy',
        }
        self.erp_status = status_map.get((so.status or '').lower(), so.status)
        if source == 'auto':
            from zoneinfo import ZoneInfo
            vn_now = datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
            self.erp_note = f'Đồng bộ tự động từ phiếu xuất {so.code} lúc {vn_now.strftime("%d/%m/%Y %H:%M")}.'

class OnlineOrderItem(db.Model):
    __tablename__ = 'online_order_items'

    id = db.Column(db.Integer, primary_key=True)
    online_order_id = db.Column(db.Integer, db.ForeignKey('online_orders.id', ondelete='CASCADE'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('product_listings.id'), nullable=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name_snapshot = db.Column(db.String(250), nullable=True)
    quantity = db.Column(db.Numeric(18, 3), nullable=False)
    unit_price = db.Column(db.Numeric(18, 2), nullable=False)
    amount = db.Column(db.Numeric(18, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship('Product', foreign_keys=[product_id])

    def calculate(self):
        self.amount = float(self.quantity or 0) * float(self.unit_price or 0)
