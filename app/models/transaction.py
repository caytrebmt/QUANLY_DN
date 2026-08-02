from app.domains.inventory.models import (
    OpeningStock,
    StockIn, StockInItem,
    StockOut, StockOutItem,
    Inventory, InventoryHistory,
    UnitConversion,
    _dec, _money, _allocated_vat,
)
from app.domains.accounting.models import AccountChart, JournalEntry, JournalLine
from app.domains.finance.models import Debt, DebtPayment, VatRecord

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app.database import db


class Quotation(db.Model):
    __tablename__ = 'quotations'
    __table_args__ = (
        db.Index('ix_quotations_date', 'date'),
        db.Index('ix_quotations_status', 'status'),
        db.Index('ix_quotations_customer_date', 'customer_id', 'date'),
    )
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    valid_until = db.Column(db.Date, nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    recipient_name = db.Column(db.String(200), nullable=True)
    recipient_address = db.Column(db.String(300), nullable=True)
    recipient_phone = db.Column(db.String(50), nullable=True)
    recipient_email = db.Column(db.String(120), nullable=True)
    subtotal = db.Column(db.Numeric(18, 2), default=0)
    discount_amount = db.Column(db.Numeric(18, 2), default=0)
    vat_amount = db.Column(db.Numeric(18, 2), default=0)
    total_amount = db.Column(db.Numeric(18, 2), default=0)
    vat_mode = db.Column(db.String(20), default='grouped')
    vat_rate_grouped = db.Column(db.Numeric(5, 2), default=0)
    status = db.Column(db.String(20), default='draft')
    note = db.Column(db.Text, nullable=True)
    terms = db.Column(db.Text, nullable=True)
    stock_out_id = db.Column(db.Integer, db.ForeignKey('stock_outs.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('QuotationItem', backref='quotation', lazy='dynamic', cascade='all, delete-orphan')
    customer = db.relationship('Customer', foreign_keys=[customer_id])
    stock_out = db.relationship('StockOut', foreign_keys=[stock_out_id])
    creator = db.relationship('User', foreign_keys=[created_by])

    def calculate_totals(self):
        items = list(self.items)
        sub = _money(sum(_dec(i.amount) for i in items))
        disc = min(max(_dec(self.discount_amount), Decimal("0")), sub)
        taxable = sub - disc
        if self.vat_mode == 'grouped':
            vat = _money(taxable * _dec(self.vat_rate_grouped) / Decimal("100"))
        else:
            vat = _allocated_vat(items, sub, disc)
        self.subtotal = sub
        self.discount_amount = disc
        self.vat_amount = vat
        self.total_amount = taxable + vat


class QuotationItem(db.Model):
    __tablename__ = 'quotation_items'
    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotations.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=True)
    conversion_factor = db.Column(db.Numeric(12, 4), default=1)
    quantity = db.Column(db.Numeric(18, 3), nullable=False)
    unit_price = db.Column(db.Numeric(18, 2), nullable=False)
    vat_rate = db.Column(db.Numeric(5, 2), default=10)
    vat_amount = db.Column(db.Numeric(18, 2), default=0)
    amount = db.Column(db.Numeric(18, 2), default=0)
    total_amount = db.Column(db.Numeric(18, 2), default=0)
    note = db.Column(db.String(200), nullable=True)
    product = db.relationship('Product', foreign_keys=[product_id])
    unit = db.relationship('Unit', foreign_keys=[unit_id])

    def calculate(self):
        qty = _dec(self.quantity)
        price = _dec(self.unit_price)
        vat = _dec(self.vat_rate)
        self.amount = _money(qty * price)
        self.vat_amount = _money(_dec(self.amount) * vat / Decimal("100"))
        self.total_amount = _dec(self.amount) + _dec(self.vat_amount)


__all__ = [
    'OpeningStock',
    'StockIn', 'StockInItem',
    'StockOut', 'StockOutItem',
    'Inventory', 'InventoryHistory',
    'UnitConversion',
    'Quotation', 'QuotationItem',
    'AccountChart', 'JournalEntry', 'JournalLine',
    'Debt', 'DebtPayment',
    'VatRecord',
    '_dec', '_money', '_allocated_vat',
]
