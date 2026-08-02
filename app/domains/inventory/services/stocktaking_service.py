from datetime import datetime
from decimal import Decimal
from app.database import db
from app.domains.inventory.models import Inventory, InventoryHistory, Stocktaking, StocktakingItem
from app.domains.master.models import Product, Warehouse


class StocktakingService:
    @staticmethod
    def create_session(warehouse_id, count_date, note, user_id):
        warehouse = Warehouse.query.get_or_404(warehouse_id)
        session = Stocktaking(
            warehouse_id=warehouse_id,
            count_date=count_date,
            note=note,
            status='draft',
            created_by=user_id,
        )
        db.session.add(session)
        db.session.flush()

        products = Product.query.filter_by(is_active=True).order_by(Product.code).all()
        for product in products:
            inv = Inventory.query.filter_by(
                product_id=product.id,
                warehouse_id=warehouse_id
            ).first()
            book_qty = float(inv.quantity or 0) if inv else 0.0

            item = StocktakingItem(
                stocktaking_id=session.id,
                product_id=product.id,
                book_quantity=book_qty,
                actual_quantity=None,
            )
            db.session.add(item)

        db.session.commit()
        return session

    @staticmethod
    def get_session(session_id):
        return Stocktaking.query.get_or_404(session_id)

    @staticmethod
    def get_sessions(warehouse_id=None, status=None, page=1, per_page=20):
        q = Stocktaking.query
        if warehouse_id:
            q = q.filter(Stocktaking.warehouse_id == warehouse_id)
        if status:
            q = q.filter(Stocktaking.status == status)
        return q.order_by(Stocktaking.count_date.desc(), Stocktaking.id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

    @staticmethod
    def update_item(item_id, actual_quantity, note):
        item = StocktakingItem.query.get_or_404(item_id)
        item.actual_quantity = float(actual_quantity or 0)
        if note is not None:
            item.note = note
        db.session.commit()
        return item

    @staticmethod
    def complete_session(session_id, user_id):
        session = Stocktaking.query.get_or_404(session_id)
        if session.status != 'draft':
            raise ValueError(f'Phiếu kiểm kê #{session.id} không ở trạng thái nháp.')

        items = StocktakingItem.query.filter_by(stocktaking_id=session.id).all()
        if not items:
            raise ValueError('Phiếu kiểm kê không có dòng hàng.')

        for item in items:
            if item.actual_quantity is None:
                raise ValueError(f'Sản phẩm {item.product.code} chưa nhập số liệu thực tế.')

            book_qty = Decimal(str(item.book_quantity or 0))
            actual_qty = Decimal(str(item.actual_quantity or 0))
            diff = actual_qty - book_qty

            item.difference = float(diff)
            item.is_adjusted = True

            if diff == 0:
                continue

            inv = InventoryService.get_or_create_inventory(
                item.product_id, session.warehouse_id
            )

            qty_before = Decimal(str(inv.quantity or 0))
            qty_after = qty_before + diff
            if qty_after < 0:
                qty_after = Decimal("0")

            unit_cost = Decimal(str(inv.avg_cost or 0))
            if unit_cost == 0 and item.product:
                unit_cost = Decimal(str(item.product.purchase_price or 0))

            inv.quantity = float(qty_after)
            inv.avg_cost = float(unit_cost)
            inv.last_updated = datetime.utcnow()

            transaction_type = 'stocktaking_in' if diff > 0 else 'stocktaking_out'
            history = InventoryHistory(
                product_id=item.product_id,
                warehouse_id=session.warehouse_id,
                transaction_type=transaction_type,
                reference_code=f'STK-{session.id:06d}',
                quantity_change=float(diff),
                quantity_before=float(qty_before),
                quantity_after=float(qty_after),
                unit_cost=float(unit_cost),
                note=f'Kiểm kê phiếu #{session.id}: {item.note or ""}'.strip(),
                created_by=user_id,
            )
            db.session.add(history)

        session.status = 'completed'
        session.completed_by = user_id
        session.completed_at = datetime.utcnow()
        db.session.commit()
        return session

    @staticmethod
    def cancel_session(session_id, user_id):
        session = Stocktaking.query.get_or_404(session_id)
        if session.status == 'completed':
            raise ValueError('Phiếu đã hoàn thành, không thể hủy.')
        if session.status == 'cancelled':
            return session

        session.status = 'cancelled'
        session.cancelled_by = user_id
        session.cancelled_at = datetime.utcnow()
        db.session.commit()
        return session

    @staticmethod
    def get_discrepancy_report(session_id):
        session = Stocktaking.query.get_or_404(session_id)
        items = StocktakingItem.query.filter_by(stocktaking_id=session.id).all()

        discrepancies = []
        for item in items:
            if item.actual_quantity is None:
                continue
            diff = float(item.actual_quantity or 0) - float(item.book_quantity or 0)
            if diff != 0:
                discrepancies.append({
                    'product_code': item.product.code,
                    'product_name': item.product.name,
                    'unit': item.product.unit,
                    'book_qty': float(item.book_quantity or 0),
                    'actual_qty': float(item.actual_quantity or 0),
                    'difference': diff,
                    'note': item.note or '',
                })
        return discrepancies

    @staticmethod
    def export_excel(session_id):
        session = Stocktaking.query.get_or_404(session_id)
        items = StocktakingItem.query.filter_by(stocktaking_id=session.id).order_by(
            StocktakingItem.product_id
        ).all()

        data = []
        for item in items:
            actual = item.actual_quantity if item.actual_quantity is not None else ''
            diff = ''
            if item.actual_quantity is not None:
                diff_val = float(item.actual_quantity or 0) - float(item.book_quantity or 0)
                diff = diff_val

            data.append({
                'Mã hàng': item.product.code,
                'Tên hàng': item.product.name,
                'Đơn vị': item.product.unit,
                'Kho': session.warehouse.name,
                'Số liệu sổ': float(item.book_quantity or 0),
                'Số liệu thực tế': actual,
                'Chênh lệch': diff,
                'Ghi chú': item.note or '',
            })

        import pandas as pd
        import io
        output = io.BytesIO()
        df = pd.DataFrame(data)
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Kiem ke', index=False)
            ws = writer.sheets['Kiem ke']
            from app.shared.export.excel_exporter import _auto_fit_columns
            _auto_fit_columns(ws)
        output.seek(0)
        return output, f'kiem_ke_{session.id:06d}_{session.count_date.isoformat()}.xlsx'


class StocktakingItemService:
    @staticmethod
    def bulk_update(session_id, updates, user_id):
        session = Stocktaking.query.get_or_404(session_id)
        if session.status != 'draft':
            raise ValueError('Chỉ có thể cập nhật phiếu ở trạng thái nháp.')

        for product_id, actual_qty in updates.items():
            item = StocktakingItem.query.filter_by(
                stocktaking_id=session_id,
                product_id=int(product_id)
            ).first()
            if item:
                item.actual_quantity = float(actual_qty or 0)
        db.session.commit()
        return session
