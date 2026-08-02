from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from app.database import db
from app.domains.master.models import Product
from app.domains.inventory.models import (
    StockIn, StockInItem,
    StockOut, StockOutItem,
    Inventory, InventoryHistory,
)
from app.domains.inventory.services.inventory_service import InventoryService
from app.shared.constants import DocStatus

def _dec(v):
    return Decimal(str(v or 0))


def _money(v):
    return _dec(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ConfirmResult:
    def __init__(self, ok, code=None, error=None):
        self.ok = ok
        self.code = code
        self.error = error


class CancelResult:
    def __init__(self, ok, code=None, error=None):
        self.ok = ok
        self.code = code
        self.error = error


class StockDocumentService:
    @staticmethod
    def confirm_stock_in(doc_id: int, user_id: int) -> ConfirmResult:
        si = StockIn.query.get_or_404(doc_id)
        if (si.status or '').strip().lower() == DocStatus.CONFIRMED:
            return ConfirmResult(False, si.code, 'This voucher was already Confirmed!')

        try:
            if si.items.count() == 0:
                return ConfirmResult(False, si.code, 'Voucher has no item, cannot confirm!')

            items = si.items.order_by(StockInItem.id.asc()).all()
            for idx, item in enumerate(items, start=1):
                product = Product.query.get(item.product_id)
                if not product:
                    return ConfirmResult(False, si.code, f'Dòng {idx}: không tìm thấy sản phẩm (ID={item.product_id}).')

                ok, factor, err = _resolve_item_factor(product, item.unit_id)
                if not ok:
                    return ConfirmResult(False, si.code, f'Dòng {idx} - {product.code}: {err}. Vui lòng khai báo tại Cài đặt > Quy đổi đơn vị.')

                item.conversion_factor = factor
                unit_cost_base = _dec(item.unit_price or 0) / _dec(factor or 1)
                InventoryService.stock_in(
                    product_id=item.product_id,
                    warehouse_id=si.warehouse_id,
                    quantity=_dec(item.quantity) * _dec(factor),
                    unit_cost=unit_cost_base,
                    reference_code=si.code,
                    user_id=user_id
                )

            from app.domains.finance.services.debt_service import DebtService
            DebtService.create_from_stock_in(si)

            from app.domains.finance.services.vat_service import VatService
            VatService.record_from_stock_in(si)

            si.status = DocStatus.CONFIRMED
            si.confirmed_by = user_id
            si.confirmed_at = datetime.utcnow()
            _post_journal_for_stock_in(si)
            db.session.commit()
            return ConfirmResult(True, si.code)

        except Exception as e:
            db.session.rollback()
            return ConfirmResult(False, si.code, str(e))

    @staticmethod
    def cancel_stock_in(doc_id: int, user_id: int) -> CancelResult:
        si = StockIn.query.get_or_404(doc_id)
        if (si.status or '').strip().lower() == DocStatus.CONFIRMED:
            try:
                StockDocumentService._reverse_stock_in_inventory(si, user_id)
                from app.domains.finance.services.debt_service import DebtService
                DebtService.cleanup_reference_records('stock_in', si.id)
                from app.domains.accounting.services.accounting_helper import reverse_entries
                reverse_entries('stock_in', si.id)
            except Exception as e:
                db.session.rollback()
                return CancelResult(False, si.code, f'Lỗi đảo bút toán: {e}')
        si.status = DocStatus.CANCELLED
        db.session.commit()
        return CancelResult(True, si.code)

    @staticmethod
    def confirm_stock_out(doc_id: int, user_id: int) -> ConfirmResult:
        so = StockOut.query.get_or_404(doc_id)
        if (so.status or '').strip().lower() == DocStatus.CONFIRMED:
            return ConfirmResult(False, so.code, 'This voucher was already confirmed!')

        try:
            if so.items.count() == 0:
                return ConfirmResult(False, so.code, 'Voucher has no item, cannot confirm!')

            items = so.items.order_by(StockOutItem.id.asc()).all()
            for idx, item in enumerate(items, start=1):
                product = Product.query.get(item.product_id)
                if not product:
                    return ConfirmResult(False, so.code, f'Dòng {idx}: không tìm thấy sản phẩm (ID={item.product_id}).')

                ok, factor, err = _resolve_item_factor(product, item.unit_id)
                if not ok:
                    return ConfirmResult(False, so.code, f'Dòng {idx} - {product.code}: {err}. Vui lòng khai báo tại Cài đặt > Quy đổi đơn vị.')

                item.conversion_factor = factor
                inv_entry, cost_price = InventoryService.stock_out(
                    product_id=item.product_id,
                    warehouse_id=so.warehouse_id,
                    quantity=float(item.quantity) * factor,
                    reference_code=so.code,
                    user_id=user_id
                )
                item.cost_price = cost_price

            from app.domains.finance.services.debt_service import DebtService
            DebtService.create_from_stock_out(so)

            from app.domains.finance.services.vat_service import VatService
            VatService.record_from_stock_out(so)

            so.status = DocStatus.CONFIRMED
            so.confirmed_by = user_id
            so.confirmed_at = datetime.utcnow()
            _post_journal_for_stock_out(so)
            db.session.commit()

            from app.domains.ecommerce.models import OnlineOrder
            for online_order in OnlineOrder.query.filter_by(stock_out_id=so.id).all():
                online_order.update_erp_status(source='auto')
            db.session.commit()
            return ConfirmResult(True, so.code)

        except Exception as e:
            db.session.rollback()
            return ConfirmResult(False, so.code, str(e))

    @staticmethod
    def cancel_stock_out(doc_id: int, user_id: int) -> CancelResult:
        so = StockOut.query.get_or_404(doc_id)
        if (so.status or '').strip().lower() == DocStatus.CONFIRMED:
            try:
                StockDocumentService._reverse_stock_out_inventory(so, user_id)
                from app.domains.finance.services.debt_service import DebtService
                DebtService.cleanup_reference_records('stock_out', so.id)
                from app.domains.accounting.services.accounting_helper import reverse_entries
                reverse_entries('stock_out', so.id)
            except Exception as e:
                db.session.rollback()
                return CancelResult(False, so.code, f'Reverse entry failed: {e}')
        so.status = DocStatus.CANCELLED
        db.session.commit()

        from app.domains.ecommerce.models import OnlineOrder
        for online_order in OnlineOrder.query.filter_by(stock_out_id=so.id).all():
            online_order.update_erp_status(source='auto')
        db.session.commit()
        return CancelResult(True, so.code)

    @staticmethod
    def _reverse_stock_in_inventory(si, user_id):
        from app.domains.master.models import Product
        from app.models.transaction import UnitConversion
        items = si.items.order_by(StockInItem.id.asc()).all()
        for item in items:
            qty_cancel = Decimal(str(item.quantity or 0)) * Decimal(str(item.conversion_factor or 1))
            if qty_cancel <= 0:
                continue

            inv = (
                Inventory.query
                .filter_by(product_id=item.product_id, warehouse_id=si.warehouse_id)
                .with_for_update()
                .first()
            )
            if not inv:
                raise ValueError(f"Không tìm thấy tồn kho để hủy dòng hàng ID={item.product_id}.")

            qty_before = Decimal(str(inv.quantity or 0))
            cost_before = Decimal(str(inv.avg_cost or 0))
            new_qty = qty_before - qty_cancel
            if new_qty < 0:
                raise ValueError(f"Không thể hủy phiếu nhập {si.code}: tồn hiện tại không đủ để trừ lại hàng đã nhập.")

            unit_cost = Decimal(str(item.unit_price or 0)) / Decimal(str(item.conversion_factor or 1))
            if new_qty > 0:
                new_cost = ((qty_before * cost_before) - (qty_cancel * unit_cost)) / new_qty
                if new_cost < 0:
                    new_cost = cost_before
            else:
                new_cost = Decimal("0")

            inv.quantity = new_qty
            inv.avg_cost = new_cost
            inv.last_updated = datetime.utcnow()
            db.session.add(InventoryHistory(
                product_id=item.product_id,
                warehouse_id=si.warehouse_id,
                transaction_type='cancel_stock_in',
                reference_code=si.code,
                quantity_change=-qty_cancel,
                quantity_before=qty_before,
                quantity_after=new_qty,
                unit_cost=unit_cost,
                note=f'Hủy phiếu nhập {si.code}',
                created_by=user_id,
            ))

    @staticmethod
    def _reverse_stock_out_inventory(so, user_id):
        from app.domains.master.models import Product
        items = so.items.order_by(StockOutItem.id.asc()).all()
        for item in items:
            qty_return = Decimal(str(item.quantity or 0)) * Decimal(str(item.conversion_factor or 1))
            if qty_return <= 0:
                continue

            inv = (
                Inventory.query
                .filter_by(product_id=item.product_id, warehouse_id=so.warehouse_id)
                .with_for_update()
                .first()
            )
            if not inv:
                inv = Inventory(
                    product_id=item.product_id,
                    warehouse_id=so.warehouse_id,
                    quantity=0,
                    avg_cost=0,
                )
                db.session.add(inv)
                db.session.flush()

            qty_before = Decimal(str(inv.quantity or 0))
            cost_before = Decimal(str(inv.avg_cost or 0))
            unit_cost = Decimal(str(item.cost_price or 0))
            new_qty = qty_before + qty_return
            new_cost = (
                ((qty_before * cost_before) + (qty_return * unit_cost)) / new_qty
                if new_qty > 0 else Decimal("0")
            )

            inv.quantity = new_qty
            inv.avg_cost = new_cost
            inv.last_updated = datetime.utcnow()
            db.session.add(InventoryHistory(
                product_id=item.product_id,
                warehouse_id=so.warehouse_id,
                transaction_type='cancel_stock_out',
                reference_code=so.code,
                quantity_change=qty_return,
                quantity_before=qty_before,
                quantity_after=new_qty,
                unit_cost=unit_cost,
                note=f'Hủy phiếu xuất {so.code}',
                created_by=user_id,
            ))


def _post_journal_for_stock_in(si):
    from app.domains.accounting.services.accounting_helper import create_entry
    from app.domains.accounting.services.account_mapping_service import get_account_code
    def dec(v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inv_val = max(dec(si.subtotal) - dec(si.discount_amount or 0), Decimal("0"))
    vat_in = dec(si.vat_amount)
    total = dec(si.total_amount)
    entry_code = f"JE-{si.code}"
    acc_inventory = account_mapping_service.get_account_code('acc_inventory')
    acc_vat_in = get_account_code('acc_vat_in')
    acc_ap = get_account_code('acc_ap')
    lines = [
        {'account_code': acc_inventory, 'debit': inv_val, 'credit': 0},
    ]
    if vat_in > 0:
        lines.append({'account_code': acc_vat_in, 'debit': vat_in, 'credit': 0})
        lines.append({'account_code': acc_ap, 'debit': 0, 'credit': total})
    create_entry(
        code=entry_code,
        date=si.date or date.today(),
        description=f'Hạch toán phiếu nhập {si.code}',
        lines=lines,
        reference_type='stock_in',
        reference_id=si.id,
        reference_code=si.code
    )


def _post_journal_for_stock_out(so):
    from app.domains.accounting.services.accounting_helper import create_entry
    from app.domains.accounting.services.account_mapping_service import get_account_code
    def dec(v):
        return Decimal(str(v or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    from app.domains.accounting.services.accounting_helper import create_entry
    from app.domains.accounting.services.account_mapping_service import get_account_code
    revenue = max(dec(so.subtotal) - dec(so.discount_amount or 0), Decimal('0'))
    vat_out = dec(so.vat_amount)
    total = dec(so.total_amount)
    cost_total = sum(
        dec(item.cost_price) * dec(item.quantity) * dec(item.conversion_factor or 1)
        for item in so.items
    )
    entry_code = f"JE-{so.code}"
    acc_ar = get_account_code('acc_ar')
    acc_revenue = get_account_code('acc_revenue')
    acc_vat_out = get_account_code('acc_vat_out')
    acc_cogs = get_account_code('acc_cogs')
    acc_inventory = account_mapping_service.get_account_code('acc_inventory')
    lines = [
        {'account_code': acc_ar, 'debit': total, 'credit': 0},
        {'account_code': acc_revenue, 'debit': 0, 'credit': revenue},
    ]
    if vat_out > 0:
        lines.append({'account_code': acc_vat_out, 'debit': 0, 'credit': vat_out})
    if cost_total > 0:
        lines.append({'account_code': acc_cogs, 'debit': cost_total, 'credit': 0})
        lines.append({'account_code': acc_inventory, 'debit': 0, 'credit': cost_total})
    create_entry(
        code=entry_code,
        date=so.date or date.today(),
        description=f'Hạch toán phiếu xuất {so.code}',
        lines=lines,
        reference_type='stock_out',
        reference_id=so.id,
        reference_code=so.code
    )


def _resolve_item_factor(product, item_unit_id):
    from app.domains.master.models import Unit
    from app.models.transaction import UnitConversion
    base_unit_id = product.unit_id
    line_unit_id = item_unit_id or base_unit_id

    if not base_unit_id or not line_unit_id or int(line_unit_id) == int(base_unit_id):
        return True, 1.0, None

    conv = UnitConversion.query.filter_by(
        product_id=product.id,
        from_unit_id=int(line_unit_id),
        to_unit_id=int(base_unit_id),
    ).first()
    if conv and float(conv.conversion_factor or 0) > 0:
        return True, float(conv.conversion_factor), None

    rev = UnitConversion.query.filter_by(
        product_id=product.id,
        from_unit_id=int(base_unit_id),
        to_unit_id=int(line_unit_id),
    ).first()
    if rev and float(rev.conversion_factor or 0) > 0:
        return True, 1.0 / float(rev.conversion_factor), None

    from_unit = Unit.query.get(line_unit_id)
    to_unit = Unit.query.get(base_unit_id)
    return False, None, (
        f"Thiếu quy đổi đơn vị: {from_unit.name if from_unit else line_unit_id} -> "
        f"{to_unit.name if to_unit else base_unit_id}"
    )
