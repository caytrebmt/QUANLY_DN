from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app.database import db
from app.domains.accounting.models import AccountChart, JournalEntry, JournalLine


def _dec(val):
    return Decimal(str(val or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _get_account_id(code):
    acc = AccountChart.query.filter_by(code=str(code)).first()
    if not acc:
        raise ValueError(f"Không tìm thấy tài khoản {code}")
    return acc.id


def create_entry(code, date, description, lines, reference_type=None, reference_id=None, reference_code=None):
    existing = JournalEntry.query.filter_by(code=code).first()
    if existing:
        db.session.delete(existing)
        db.session.flush()

    je = JournalEntry(
        code=code,
        date=date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        reference_code=reference_code,
        status='posted'
    )
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for ln in lines:
        debit = _dec(ln.get('debit', 0))
        credit = _dec(ln.get('credit', 0))
        jl = JournalLine(
            account_id=_get_account_id(ln['account_code']),
            description=ln.get('description') or description,
            debit=debit,
            credit=credit,
        )
        je.lines.append(jl)
        total_debit += debit
        total_credit += credit
    je.total_debit = float(total_debit)
    je.total_credit = float(total_credit)
    db.session.add(je)
    return je


def reverse_entries(reference_type, reference_id, suffix='REV'):
    entries = JournalEntry.query.filter_by(
        reference_type=reference_type,
        reference_id=reference_id
    ).all()
    for src in entries:
        rev_code = f"{src.code}-{suffix}"
        lines = []
        for ln in src.lines:
            acc_code = None
            if hasattr(ln, 'account') and ln.account:
                acc_code = ln.account.code
            else:
                acc = AccountChart.query.get(ln.account_id)
                acc_code = acc.code if acc else None
            if not acc_code:
                continue
            lines.append({
                'account_code': acc_code,
                'debit': ln.credit,
                'credit': ln.debit,
                'description': f"Reversal {src.code}"
            })
        create_entry(
            code=rev_code,
            date=datetime.utcnow().date(),
            description=f"Reversal {src.code}",
            lines=lines,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_code=src.reference_code
        )
