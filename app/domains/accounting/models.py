from datetime import datetime
from app.database import db


class AccountChart(db.Model):
    __tablename__ = 'account_charts'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    name_en = db.Column(db.String(200), nullable=True)
    account_type = db.Column(db.String(20), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('account_charts.id'), nullable=True)
    level = db.Column(db.Integer, default=1)
    normal_balance = db.Column(db.String(10), default='debit')
    is_detail = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    children = db.relationship('AccountChart', backref=db.backref('parent', remote_side=[id]), lazy='select')
    journal_lines = db.relationship('JournalLine', backref='account', lazy='select')
    def __repr__(self): return f'<Account {self.code}>'


class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    __table_args__ = (
        db.Index('ix_je_reference', 'reference_type', 'reference_id'),
        db.Index('ix_je_date', 'date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(300), nullable=False)
    reference_type = db.Column(db.String(50), nullable=True)
    reference_id = db.Column(db.Integer, nullable=True)
    reference_code = db.Column(db.String(50), nullable=True)
    total_debit = db.Column(db.Numeric(18,2), default=0)
    total_credit = db.Column(db.Numeric(18,2), default=0)
    status = db.Column(db.String(20), default='posted')
    note = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    lines = db.relationship('JournalLine', backref='entry', lazy='dynamic', cascade='all, delete-orphan')
    def __repr__(self): return f'<JournalEntry {self.code}>'


class JournalLine(db.Model):
    __tablename__ = 'journal_lines'
    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('journal_entries.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account_charts.id'), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    debit = db.Column(db.Numeric(18,2), default=0)
    credit = db.Column(db.Numeric(18,2), default=0)
    partner_type = db.Column(db.String(20), nullable=True)
    partner_id = db.Column(db.Integer, nullable=True)
    order_no = db.Column(db.Integer, default=0)


__all__ = ['AccountChart', 'JournalEntry', 'JournalLine']
