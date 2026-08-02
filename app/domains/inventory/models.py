from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app.database import db
from app.domains.master.models import Unit


MONEY = Decimal("0.01")


def _dec(value):
    return Decimal(str(value or 0))


def _money(value):
    return _dec(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def _allocated_vat(items, subtotal, discount):
    if subtotal <= 0:
        return Decimal("0")
    discount = min(max(discount, Decimal("0")), subtotal)
    vat_total = Decimal("0")
    for item in items:
        amount = _dec(item.amount)
        rate = _dec(item.vat_rate)
        line_discount = (discount * amount / subtotal) if amount > 0 else Decimal("0")
        taxable = max(amount - line_discount, Decimal("0"))
        vat_total += taxable * rate / Decimal("100")
    return _money(vat_total)

class OpeningStock(db.Model):
    __tablename__ = 'opening_stocks'
    id = db.Column(db.Integer, primary_key=True)
    period_date = db.Column(db.Date, nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity = db.Column(db.Numeric(18,3), default=0)
    unit_cost = db.Column(db.Numeric(18,2), default=0)
    amount = db.Column(db.Numeric(18,2), default=0)
    note = db.Column(db.String(200), nullable=True)
    is_posted = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product', foreign_keys=[product_id], lazy='select')
    warehouse = db.relationship('Warehouse', foreign_keys=[warehouse_id], lazy='select')

class StockIn(db.Model):
    __tablename__ = 'stock_ins'
    __table_args__ = (
        db.Index('ix_stock_ins_date', 'date'),
        db.Index('ix_stock_ins_status', 'status'),
        db.Index('ix_stock_ins_supplier_date', 'supplier_id', 'date'),
        db.Index('ix_stock_ins_warehouse_date', 'warehouse_id', 'date'),
    )
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    invoice_no = db.Column(db.String(50), nullable=True)
    invoice_series = db.Column(db.String(10), nullable=True)
    invoice_date = db.Column(db.Date, nullable=True)
    reference = db.Column(db.String(100), nullable=True)
    subtotal = db.Column(db.Numeric(18,2), default=0)
    discount_pct = db.Column(db.Numeric(5,2), default=0)
    discount_amount = db.Column(db.Numeric(18,2), default=0)
    vat_amount = db.Column(db.Numeric(18,2), default=0)
    total_amount = db.Column(db.Numeric(18,2), default=0)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=True)
    conversion_factor = db.Column(db.Numeric(12,4), default=1)
    paid_amount = db.Column(db.Numeric(18,2), default=0)
    vat_manual = db.Column(db.Boolean, default=False)
    vat_manual_val = db.Column(db.Numeric(18,2), default=0)
    status = db.Column(db.String(20), default='draft')
    note = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('StockInItem', backref='stock_in', lazy='dynamic', cascade='all, delete-orphan')
    warehouse = db.relationship('Warehouse', foreign_keys=[warehouse_id])
    unit = db.relationship('Unit', foreign_keys=[unit_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    def __repr__(self): return f'<StockIn {self.code}>'
    def calculate_totals(self):
        items = list(self.items)
        sub = _money(sum(_dec(i.amount) for i in items))
        disc = min(max(_dec(self.discount_amount), Decimal("0")), sub)
        taxable = sub - disc
        vat = _money(self.vat_manual_val) if self.vat_manual else _allocated_vat(items, sub, disc)
        self.subtotal = sub; self.discount_amount = disc; self.vat_amount = vat; self.total_amount = taxable + vat
    def get_balance(self): return float(self.total_amount or 0) - float(self.paid_amount or 0)

class StockInItem(db.Model):
    __tablename__ = 'stock_in_items'
    id = db.Column(db.Integer, primary_key=True)
    stock_in_id = db.Column(db.Integer, db.ForeignKey('stock_ins.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=True)
    conversion_factor = db.Column(db.Numeric(12,4), default=1)
    quantity = db.Column(db.Numeric(18,3), nullable=False)
    unit_price = db.Column(db.Numeric(18,2), nullable=False)
    vat_rate = db.Column(db.Numeric(5,2), default=10)
    vat_amount = db.Column(db.Numeric(18,2), default=0)
    amount = db.Column(db.Numeric(18,2), default=0)
    total_amount = db.Column(db.Numeric(18,2), default=0)
    note = db.Column(db.String(200), nullable=True)
    unit = db.relationship('Unit', foreign_keys=[unit_id])
    def calculate(self):
        qty = _dec(self.quantity); price = _dec(self.unit_price); vat = _dec(self.vat_rate)
        self.amount = _money(qty * price); self.vat_amount = _money(_dec(self.amount) * vat / Decimal("100")); self.total_amount = _dec(self.amount) + _dec(self.vat_amount)

class StockOut(db.Model):
    __tablename__ = 'stock_outs'
    __table_args__ = (
        db.Index('ix_stock_outs_date', 'date'),
        db.Index('ix_stock_outs_status', 'status'),
        db.Index('ix_stock_outs_customer_date', 'customer_id', 'date'),
    )
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    invoice_no = db.Column(db.String(50), nullable=True)
    invoice_series = db.Column(db.String(10), nullable=True)
    reference = db.Column(db.String(100), nullable=True)
    subtotal = db.Column(db.Numeric(18,2), default=0)
    discount_pct = db.Column(db.Numeric(5,2), default=0)
    discount_amount = db.Column(db.Numeric(18,2), default=0)
    vat_amount = db.Column(db.Numeric(18,2), default=0)
    total_amount = db.Column(db.Numeric(18,2), default=0)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=True)
    conversion_factor = db.Column(db.Numeric(12,4), default=1)
    paid_amount = db.Column(db.Numeric(18,2), default=0)
    vat_manual = db.Column(db.Boolean, default=False)
    vat_manual_val = db.Column(db.Numeric(18,2), default=0)
    vat_mode = db.Column(db.String(20), default='per_item')
    vat_rate_grouped = db.Column(db.Numeric(5,2), default=0)
    status = db.Column(db.String(20), default='draft')
    note = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('StockOutItem', backref='stock_out', lazy='dynamic', cascade='all, delete-orphan')
    warehouse = db.relationship('Warehouse', foreign_keys=[warehouse_id])
    unit = db.relationship('Unit', foreign_keys=[unit_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    def __repr__(self): return f'<StockOut {self.code}>'
    def calculate_totals(self):
        items = list(self.items)
        sub = _money(sum(_dec(i.amount) for i in items))
        disc = min(max(_dec(self.discount_amount), Decimal("0")), sub)
        taxable = sub - disc
        if self.vat_mode == 'grouped':
            vat = _money(taxable * _dec(self.vat_rate_grouped) / Decimal("100"))
        else:
            vat = _money(self.vat_manual_val) if self.vat_manual else _allocated_vat(items, sub, disc)
        self.subtotal = sub; self.discount_amount = disc; self.vat_amount = vat; self.total_amount = taxable + vat
    def get_balance(self): return float(self.total_amount or 0) - float(self.paid_amount or 0)
    @property
    def total_boxes(self):
        total = 0
        for item in self.items:
            if item.box_note:
                import re
                nums = re.findall(r'\d+', str(item.box_note))
                if nums:
                    total += int(nums[0])
        return total

class StockOutItem(db.Model):
    __tablename__ = 'stock_out_items'
    id = db.Column(db.Integer, primary_key=True)
    stock_out_id = db.Column(db.Integer, db.ForeignKey('stock_outs.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=True)
    conversion_factor = db.Column(db.Numeric(12,4), default=1)
    quantity = db.Column(db.Numeric(18,3), nullable=False)
    unit_price = db.Column(db.Numeric(18,2), nullable=False)
    cost_price = db.Column(db.Numeric(18,2), default=0)
    vat_rate = db.Column(db.Numeric(5,2), default=10)
    vat_amount = db.Column(db.Numeric(18,2), default=0)
    amount = db.Column(db.Numeric(18,2), default=0)
    total_amount = db.Column(db.Numeric(18,2), default=0)
    note = db.Column(db.String(200), nullable=True)
    box_note = db.Column(db.String(100), nullable=True)
    unit = db.relationship('Unit', foreign_keys=[unit_id])
    def calculate(self):
        qty = _dec(self.quantity); price = _dec(self.unit_price); vat = _dec(self.vat_rate)
        self.amount = _money(qty * price); self.vat_amount = _money(_dec(self.amount) * vat / Decimal("100")); self.total_amount = _dec(self.amount) + _dec(self.vat_amount)


class Inventory(db.Model):
    __tablename__ = 'inventory'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity = db.Column(db.Numeric(18,3), default=0)
    avg_cost = db.Column(db.Numeric(18,2), default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    warehouse = db.relationship('Warehouse', foreign_keys=[warehouse_id])
    __table_args__ = (db.UniqueConstraint('product_id','warehouse_id', name='uq_inv_prod_wh'),)

class InventoryHistory(db.Model):
    __tablename__ = 'inventory_history'
    __table_args__ = (
        db.Index('ix_inv_hist_product_wh', 'product_id', 'warehouse_id'),
        db.Index('ix_inv_hist_created_at', 'created_at'),
    )
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    reference_code = db.Column(db.String(50), nullable=True)
    quantity_change = db.Column(db.Numeric(18,3), nullable=False)
    quantity_before = db.Column(db.Numeric(18,3), default=0)
    quantity_after = db.Column(db.Numeric(18,3), default=0)
    unit_cost = db.Column(db.Numeric(18,2), default=0)
    note = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    product = db.relationship('Product', foreign_keys=[product_id])
    warehouse = db.relationship('Warehouse', foreign_keys=[warehouse_id])

class UnitConversion(db.Model):
    __tablename__ = 'unit_conversions'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    from_unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    to_unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False)
    conversion_factor = db.Column(db.Numeric(12,4), nullable=False)
    __table_args__ = (db.UniqueConstraint('product_id','from_unit_id','to_unit_id', name='uq_unit_conv'),)
    product = db.relationship('Product', foreign_keys=[product_id])
    from_unit = db.relationship('Unit', foreign_keys=[from_unit_id])
    to_unit = db.relationship('Unit', foreign_keys=[to_unit_id])


class Stocktaking(db.Model):
    __tablename__ = 'stocktakings'
    id = db.Column(db.Integer, primary_key=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    count_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='draft')
    note = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    completed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    cancelled_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    warehouse = db.relationship('Warehouse', foreign_keys=[warehouse_id])
    creator = db.relationship('User', foreign_keys=[created_by])
    completer = db.relationship('User', foreign_keys=[completed_by])
    items = db.relationship('StocktakingItem', backref='stocktaking', lazy='dynamic', cascade='all, delete-orphan')


class StocktakingItem(db.Model):
    __tablename__ = 'stocktaking_items'
    id = db.Column(db.Integer, primary_key=True)
    stocktaking_id = db.Column(db.Integer, db.ForeignKey('stocktakings.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    book_quantity = db.Column(db.Numeric(18,3), default=0)
    actual_quantity = db.Column(db.Numeric(18,3), nullable=True)
    difference = db.Column(db.Numeric(18,3), default=0)
    note = db.Column(db.String(200), nullable=True)
    is_adjusted = db.Column(db.Boolean, default=False)
    product = db.relationship('Product', foreign_keys=[product_id])


__all__ = [
    'OpeningStock',
    'StockIn', 'StockInItem',
    'StockOut', 'StockOutItem',
    'Inventory', 'InventoryHistory',
    'UnitConversion',
    'Stocktaking', 'StocktakingItem',
    '_dec', '_money', '_allocated_vat'
]