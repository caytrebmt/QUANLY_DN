from app.database import db
from app.models.transaction import VatRecord


class VatService:
    @staticmethod
    def record_from_stock_in(stock_in):
        if float(stock_in.vat_amount or 0) > 0:
            from app.domains.master.models import Supplier
            supplier = Supplier.query.get(stock_in.supplier_id) if stock_in.supplier_id else None

            taxable_amount_val = max(float(stock_in.subtotal or 0) - float(stock_in.discount_amount or 0), 0)
            vat_amount_val = float(stock_in.vat_amount or 0)
            calculated_vat_rate = round((vat_amount_val / taxable_amount_val) * 100) if taxable_amount_val > 0 else 10

            vat = VatRecord(
                vat_type='input',
                date=stock_in.date,
                invoice_no=stock_in.invoice_no,
                reference_type='stock_in',
                reference_id=stock_in.id,
                reference_code=stock_in.code,
                partner_name=supplier.name if supplier else '',
                partner_tax_code=supplier.tax_code if supplier else '',
                partner_address=supplier.address if supplier else '',
                taxable_amount=taxable_amount_val,
                vat_rate=calculated_vat_rate,
                vat_amount=vat_amount_val,
                total_amount=float(stock_in.total_amount or 0),
                period_month=stock_in.date.month,
                period_year=stock_in.date.year,
            )
            db.session.add(vat)

    @staticmethod
    def record_from_stock_out(stock_out):
        if float(stock_out.vat_amount or 0) > 0:
            from app.domains.master.models import Customer
            customer = Customer.query.get(stock_out.customer_id) if stock_out.customer_id else None

            taxable_amount_val = max(float(stock_out.subtotal or 0) - float(stock_out.discount_amount or 0), 0)
            vat_amount_val = float(stock_out.vat_amount or 0)

            if stock_out.vat_mode == 'grouped':
                calculated_vat_rate = float(stock_out.vat_rate_grouped or 0)
            else:
                calculated_vat_rate = round((vat_amount_val / taxable_amount_val) * 100) if taxable_amount_val > 0 else 10

            vat = VatRecord(
                vat_type='output',
                date=stock_out.date,
                invoice_no=stock_out.invoice_no,
                reference_type='stock_out',
                reference_id=stock_out.id,
                reference_code=stock_out.code,
                partner_name=customer.name if customer else '',
                partner_tax_code=customer.tax_code if customer else '',
                partner_address=customer.address if customer else '',
                taxable_amount=taxable_amount_val,
                vat_rate=calculated_vat_rate,
                vat_amount=vat_amount_val,
                total_amount=float(stock_out.total_amount or 0),
                period_month=stock_out.date.month,
                period_year=stock_out.date.year,
            )
            db.session.add(vat)
