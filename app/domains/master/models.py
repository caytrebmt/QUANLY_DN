from datetime import datetime
from app.database import db
from app.shared.constants import DocStatus


class Unit(db.Model):
    __tablename__ = 'units'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(60), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    products = db.relationship('Product', backref='unit_ref', lazy='select',
                               foreign_keys='Product.unit_id',
                               overlaps='unit_obj,unit_ref')

    def __repr__(self):
        return f'<Unit {self.code}>'

    def to_dict(self):
        return {'id': self.id, 'code': self.code, 'name': self.name}


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    description = db.Column(db.String(300), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy='select')
    products = db.relationship('Product', backref='category_ref', lazy='select',
                               foreign_keys='Product.category_id',
                               overlaps='cat_obj,category_ref')

    def __repr__(self):
        return f'<Category {self.code}>'

    def to_dict(self):
        return {'id': self.id, 'code': self.code, 'name': self.name}


class Product(db.Model):
    __tablename__ = 'products'

    __table_args__ = (
        db.Index('ix_products_name', 'name'),
        db.Index('ix_products_category_id', 'category_id'),
    )

    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(50), unique=True, nullable=False)
    barcode = db.Column(db.String(60))

    name = db.Column(db.String(200), nullable=False)
    name_en = db.Column(db.String(200))
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=True)
    unit = db.Column(db.String(30), nullable=False, default='Cai')
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    purchase_price = db.Column(db.Numeric(18, 2), default=0)
    sale_price = db.Column(db.Numeric(18, 2), default=0)
    retail_price = db.Column(db.Numeric(18, 2), default=0)
    vat_rate = db.Column(db.Numeric(5, 2), default=10)
    min_stock = db.Column(db.Numeric(18, 3), default=0)
    max_stock = db.Column(db.Numeric(18, 3), default=0)
    allow_negative = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    unit_obj = db.relationship('Unit', foreign_keys=[unit_id], lazy='select', overlaps='unit_ref,products')
    cat_obj = db.relationship('Category', foreign_keys=[category_id], lazy='select', overlaps='category_ref,products')
    stock_in_items = db.relationship('StockInItem', backref='product', lazy='select')
    stock_out_items = db.relationship('StockOutItem', backref='product', lazy='select')
    inventory = db.relationship('Inventory', backref='product', lazy='select')

    images = db.relationship('ProductImage', back_populates='product', cascade='all, delete-orphan',
                             order_by='ProductImage.sort_order', lazy='select')

    def __repr__(self):
        return f'<Product {self.code}>'

    def get_unit_name(self):
        return self.unit_obj.name if self.unit_obj else self.unit

    def get_category_name(self):
        return (
            self.cat_obj.name
            if self.cat_obj
            else (self.category or '')
        )

    @property
    def main_image(self):
        for img in self.images:
            if img.is_main:
                return img.image_url

        if self.images:
            return self.images[0].image_url

        return None

    @property
    def gallery(self):
        return sorted(
            self.images,
            key=lambda x: x.sort_order
        )

    def get_current_stock(self, warehouse_id=None):
        from app.models.transaction import Inventory

        q = Inventory.query.filter_by(
            product_id=self.id
        )

        if warehouse_id:
            q = q.filter_by(
                warehouse_id=warehouse_id
            )

        return sum(
            float(i.quantity or 0)
            for i in q.all()
        )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,

            'unit': self.get_unit_name(),
            'unit_id': self.unit_id,

            'category': self.get_category_name(),
            'category_id': self.category_id,

            'purchase_price': float(self.purchase_price or 0),

            'sale_price': float(self.sale_price or 0),

            'vat_rate': float(self.vat_rate or 0),

            'allow_negative': self.allow_negative,

            'main_image': self.main_image
        }


class ProductImage(db.Model):
    __tablename__ = 'product_images'
    __table_args__ = (db.Index('ix_product_images_product_id', 'product_id'),)

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    image_name = db.Column(db.String(255))
    sort_order = db.Column(db.Integer, default=1)
    is_main = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product', back_populates='images')

    def __repr__(self):
        return (
            f'<ProductImage '
            f'{self.product_id} '
            f'{self.image_name}>'
        )


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    short_name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    fax = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    tax_code = db.Column(db.String(20), nullable=True)
    contact_person = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(30), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_branch = db.Column(db.String(100), nullable=True)
    payment_terms = db.Column(db.Integer, default=30)
    credit_limit = db.Column(db.Numeric(18, 2), default=0)
    note = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stock_ins = db.relationship('StockIn', backref='supplier', lazy='select')

    def __repr__(self):
        return f'<Supplier {self.code}>'

    def to_dict(self):
        return {'id': self.id, 'code': self.code, 'name': self.name, 'phone': self.phone, 'email': self.email,
                'tax_code': self.tax_code}

    def get_total_debt(self):
        from app.models.transaction import Debt
        from sqlalchemy import func
        r = db.session.query(func.sum(Debt.balance)).filter(Debt.partner_type == 'supplier', Debt.partner_id == self.id,
                                                             Debt.status != 'paid').scalar()
        return float(r or 0)

    def get_total_purchase(self):
        from app.models.transaction import StockIn
        from sqlalchemy import func
        r = db.session.query(func.sum(StockIn.total_amount)).filter(StockIn.supplier_id == self.id,
                                                                    StockIn.status == DocStatus.CONFIRMED).scalar()
        return float(r or 0)


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    short_name = db.Column(db.String(100), nullable=True)
    customer_type = db.Column(db.String(20), default='retail')
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    tax_code = db.Column(db.String(20), nullable=True)
    contact_person = db.Column(db.String(100), nullable=True)
    bank_account = db.Column(db.String(30), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_branch = db.Column(db.String(100), nullable=True)
    payment_terms = db.Column(db.Integer, default=30)
    credit_limit = db.Column(db.Numeric(18, 2), default=0)
    discount_rate = db.Column(db.Numeric(5, 2), default=0)
    note = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stock_outs = db.relationship('StockOut', backref='customer', lazy='select')

    def __repr__(self):
        return f'<Customer {self.code}>'

    def to_dict(self):
        return {'id': self.id, 'code': self.code, 'name': self.name, 'phone': self.phone, 'email': self.email,
                'tax_code': self.tax_code, 'credit_limit': float(self.credit_limit or 0)}

    def get_total_debt(self):
        from app.models.transaction import Debt
        from sqlalchemy import func
        r = db.session.query(func.sum(Debt.balance)).filter(Debt.partner_type == 'customer', Debt.partner_id == self.id,
                                                             Debt.status != 'paid').scalar()
        return float(r or 0)

    def get_total_revenue(self):
        from app.models.transaction import StockOut
        from sqlalchemy import func
        r = db.session.query(func.sum(StockOut.total_amount)).filter(StockOut.customer_id == self.id,
                                                                     StockOut.status == DocStatus.CONFIRMED).scalar()
        return float(r or 0)

    def get_total_orders(self):
        return self.stock_outs.filter_by(status=DocStatus.CONFIRMED).count()


class Warehouse(db.Model):
    __tablename__ = 'warehouses'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(300), nullable=True)
    manager = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Warehouse {self.code}>'
