from datetime import timedelta
from app.database import db
from app.models.transaction import Debt, VatRecord


class DebtService:
    @staticmethod
    def create_from_stock_in(stock_in):
        balance = float(stock_in.total_amount or 0) - float(stock_in.paid_amount or 0)
        if balance > 0 and stock_in.supplier_id:
            from app.domains.master.models import Supplier
            supplier = Supplier.query.get(stock_in.supplier_id)
            due_days = supplier.payment_terms if supplier else 30
            debt = Debt(
                partner_type='supplier',
                partner_id=stock_in.supplier_id,
                reference_type='stock_in',
                reference_id=stock_in.id,
                reference_code=stock_in.code,
                date=stock_in.date,
                due_date=stock_in.date + timedelta(days=due_days),
                amount=float(stock_in.total_amount),
                paid_amount=float(stock_in.paid_amount or 0),
                balance=balance,
                status='open',
            )
            db.session.add(debt)

    @staticmethod
    def create_from_stock_out(stock_out):
        balance = float(stock_out.total_amount or 0) - float(stock_out.paid_amount or 0)
        if balance > 0 and stock_out.customer_id:
            from app.domains.master.models import Customer
            customer = Customer.query.get(stock_out.customer_id)
            due_days = customer.payment_terms if customer else 30
            debt = Debt(
                partner_type='customer',
                partner_id=stock_out.customer_id,
                reference_type='stock_out',
                reference_id=stock_out.id,
                reference_code=stock_out.code,
                date=stock_out.date,
                due_date=stock_out.date + timedelta(days=due_days),
                amount=float(stock_out.total_amount),
                paid_amount=float(stock_out.paid_amount or 0),
                balance=balance,
                status='open',
            )
            db.session.add(debt)

    @staticmethod
    def cleanup_reference_records(reference_type, reference_id):
        debts = Debt.query.filter_by(
            reference_type=reference_type,
            reference_id=reference_id,
        ).all()
        for debt in debts:
            if debt.payments.count() > 0:
                raise ValueError(
                    f"Không thể hủy vì công nợ {debt.reference_code or debt.id} đã có thanh toán."
                )
        for debt in debts:
            db.session.delete(debt)
        VatRecord.query.filter_by(
            reference_type=reference_type,
            reference_id=reference_id,
        ).delete(synchronize_session=False)
