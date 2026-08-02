from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app.database import db


class Debt(db.Model):
    __tablename__ = 'debts'
    __table_args__ = (
        db.Index('ix_debts_partner', 'partner_type', 'partner_id'),
        db.Index('ix_debts_status', 'status'),
    )
    id = db.Column(db.Integer, primary_key=True)
    partner_type = db.Column(db.String(20), nullable=False)
    partner_id = db.Column(db.Integer, nullable=False)
    reference_type = db.Column(db.String(50), nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)
    reference_code = db.Column(db.String(50), nullable=True)
    date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    amount = db.Column(db.Numeric(18,2), nullable=False)
    paid_amount = db.Column(db.Numeric(18,2), default=0)
    balance = db.Column(db.Numeric(18,2), nullable=False)
    currency = db.Column(db.String(5), default='VND')
    status = db.Column(db.String(20), default='open')
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    payments = db.relationship('DebtPayment', backref='debt', lazy='dynamic', cascade='all, delete-orphan')
    def update_status(self):
        from decimal import Decimal
        bal = Decimal(str(self.balance or 0))
        amt = Decimal(str(self.amount or 0))
        if bal <= 0: self.status = 'paid'
        elif bal < amt: self.status = 'partial'
        else: self.status = 'open'
        from datetime import date
        if self.due_date and self.due_date < date.today() and self.status != 'paid':
            self.status = 'overdue'


class DebtPayment(db.Model):
    __tablename__ = 'debt_payments'
    id = db.Column(db.Integer, primary_key=True)
    debt_id = db.Column(db.Integer, db.ForeignKey('debts.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(18,2), nullable=False)
    payment_method = db.Column(db.String(30), default='cash')
    reference = db.Column(db.String(100), nullable=True)
    note = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class VatRecord(db.Model):
    __tablename__ = 'vat_records'
    id = db.Column(db.Integer, primary_key=True)
    vat_type = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    invoice_no = db.Column(db.String(50), nullable=True)
    invoice_series = db.Column(db.String(10), nullable=True)
    reference_type = db.Column(db.String(50), nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)
    reference_code = db.Column(db.String(50), nullable=True)
    partner_name = db.Column(db.String(200), nullable=True)
    partner_tax_code = db.Column(db.String(20), nullable=True)
    partner_address = db.Column(db.String(300), nullable=True)
    taxable_amount = db.Column(db.Numeric(18,2), default=0)
    vat_rate = db.Column(db.Numeric(5,2), default=10)
    vat_amount = db.Column(db.Numeric(18,2), default=0)
    total_amount = db.Column(db.Numeric(18,2), default=0)
    is_deductible = db.Column(db.Boolean, default=True)
    period_month = db.Column(db.Integer, nullable=True)
    period_year = db.Column(db.Integer, nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def __repr__(self): return f'<VatRecord {self.vat_type} {self.invoice_no}>'


__all__ = ['Debt', 'DebtPayment', 'VatRecord']
