from datetime import datetime
from app.database import db
from app.domains.inventory.models import Inventory, InventoryHistory, StockInItem, StockIn
from decimal import Decimal, ROUND_HALF_UP

class InventoryService:
    """Dịch vụ quản lý tồn kho real-time"""

    @staticmethod
    def get_or_create_inventory(product_id, warehouse_id):
        inv = (
            db.session.query(Inventory)
            .filter_by(product_id=product_id, warehouse_id=warehouse_id)
            .with_for_update()
            .first()
        )
        if not inv:
            inv = Inventory(
                product_id=product_id,
                warehouse_id=warehouse_id,
                quantity=0,
                avg_cost=0
            )
            db.session.add(inv)
            db.session.flush()
        return inv

    @staticmethod
    def stock_in(product_id, warehouse_id, quantity, unit_cost, reference_code,
                 note=None, user_id=None):
        inv = InventoryService.get_or_create_inventory(product_id, warehouse_id)
        qty_before = Decimal(str(inv.quantity or 0))
        cost_before = Decimal(str(inv.avg_cost or 0))
        qty_in = Decimal(str(quantity))
        cost_in = Decimal(str(unit_cost))

        new_qty = qty_before + qty_in
        if new_qty > 0:
            new_avg_cost = ((qty_before * cost_before) + (qty_in * cost_in)) / new_qty
        else:
            new_avg_cost = cost_in

        inv.quantity = float(new_qty)
        inv.avg_cost = float(new_avg_cost)
        inv.last_updated = datetime.utcnow()

        history = InventoryHistory(
            product_id=product_id,
            warehouse_id=warehouse_id,
            transaction_type='stock_in',
            reference_code=reference_code,
            quantity_change=float(qty_in),
            quantity_before=float(qty_before),
            quantity_after=float(new_qty),
            unit_cost=float(cost_in),
            note=note,
            created_by=user_id
        )
        db.session.add(history)
        return inv

    @staticmethod
    def stock_out(product_id, warehouse_id, quantity, reference_code,
                  note=None, user_id=None):
        inv = InventoryService.get_or_create_inventory(product_id, warehouse_id)
        qty_before = Decimal(str(inv.quantity or 0))
        qty_out = Decimal(str(quantity))

        from flask import current_app
        from app.domains.master.models import Product
        product = Product.query.get(product_id)
        allow_negative_global = current_app.config.get("ALLOW_NEGATIVE_STOCK", True)
        allow_negative_item = product.allow_negative if product else False
        if not (allow_negative_global or allow_negative_item):
            if qty_before < qty_out:
                raise ValueError(
                    f"Tồn kho không đủ. Hiện có: {qty_before}, Cần xuất: {qty_out}"
                )

        new_qty = qty_before - qty_out
        cost_price = Decimal(str(inv.avg_cost or 0))
        # Nếu avg_cost = 0 hoặc chưa có tồn kho, lấy giá nhập gần nhất
        if cost_price == 0:
            last_in = db.session.query(StockInItem.unit_price).join(
                StockIn, StockInItem.stock_in_id == StockIn.id
            ).filter(
                StockInItem.product_id == product_id,
                StockIn.warehouse_id == warehouse_id,
                StockIn.status == 'confirmed'
            ).order_by(StockIn.date.desc()).first()
            if last_in and float(last_in.unit_price or 0) > 0:
                cost_price = Decimal(str(last_in.unit_price))
        # Fallback cuối: lấy purchase_price từ danh mục sản phẩm
        if cost_price == 0 and product:
            cost_price = Decimal(str(product.purchase_price or 0))

        inv.quantity = float(new_qty)
        inv.last_updated = datetime.utcnow()

        history = InventoryHistory(
            product_id=product_id,
            warehouse_id=warehouse_id,
            transaction_type='stock_out',
            reference_code=reference_code,
            quantity_change=float(-qty_out),
            quantity_before=float(qty_before),
            quantity_after=float(new_qty),
            unit_cost=float(cost_price),
            note=note,
            created_by=user_id
        )
        db.session.add(history)
        return inv, float(cost_price)

    @staticmethod
    def get_stock_summary():
        """Tổng hợp tồn kho tất cả sản phẩm"""
        from sqlalchemy import func
        from app.domains.master.models import Product, Warehouse

        result = db.session.query(
            Product.id,
            Product.code,
            Product.name,
            Product.unit,
            Product.category,
            Product.min_stock,
            func.sum(Inventory.quantity).label('total_qty'),
            func.avg(Inventory.avg_cost).label('avg_cost'),
            func.sum(Inventory.quantity * Inventory.avg_cost).label('total_value')
        ).outerjoin(
            Inventory, Product.id == Inventory.product_id
        ).filter(
            Product.is_active == True
        ).group_by(
            Product.id, Product.code, Product.name,
            Product.unit, Product.category, Product.min_stock
        ).all()

        return result

    @staticmethod
    def get_low_stock_products():
        """Danh sách hàng sắp hết / dưới mức tối thiểu"""
        from sqlalchemy import func
        from app.domains.master.models import Product

        result = db.session.query(
            Product,
            func.sum(Inventory.quantity).label('total_qty')
        ).outerjoin(
            Inventory, Product.id == Inventory.product_id
        ).filter(
            Product.is_active == True,
            Product.min_stock > 0
        ).group_by(Product.id).having(
            func.sum(Inventory.quantity) <= Product.min_stock
        ).all()

        return result

    @staticmethod
    def get_inventory_by_date(as_of_date, warehouse_id=None):
        """Tồn kho tại một thời điểm cụ thể (từ lịch sử)"""
        from sqlalchemy import func
        from app.domains.master.models import Product

        q = db.session.query(
            InventoryHistory.product_id,
            InventoryHistory.warehouse_id,
            func.max(InventoryHistory.id).label('last_id')
        ).filter(
            InventoryHistory.created_at <= as_of_date
        )

        if warehouse_id:
            q = q.filter(InventoryHistory.warehouse_id == warehouse_id)

        q = q.group_by(
            InventoryHistory.product_id,
            InventoryHistory.warehouse_id
        ).subquery()

        result = db.session.query(
            InventoryHistory
        ).join(
            q, InventoryHistory.id == q.c.last_id
        ).all()

        return result
