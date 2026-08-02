def get_customer_detail_report(customer_id, from_dt, to_dt, page=1, per_page=20):
    from app.domains.inventory.models import StockOut, StockOutItem
    from app.domains.finance.models import Debt
    from app.domains.master.models import Product, Customer
    from sqlalchemy import func
    from app.database import db
    from app.shared.constants import DocStatus

    customer_data = db.session.query(
        Customer,
        func.coalesce(func.sum(Debt.balance), 0).label("debt"),
        func.coalesce(func.sum(StockOut.total_amount), 0).label("revenue"),
        func.count(StockOut.id).label("order_count")
    ).outerjoin(
        Debt,
        (Debt.partner_id == Customer.id) &
        (Debt.partner_type == 'customer') &
        (Debt.status != 'paid')
    ).outerjoin(
        StockOut,
        (StockOut.customer_id == Customer.id) &
        (func.lower(StockOut.status) == DocStatus.CONFIRMED)
    ).filter(
        Customer.id == customer_id
    ).group_by(Customer.id).first()

    customer = customer_data[0]

    from sqlalchemy.orm import joinedload

    orders = StockOut.query.options(
        joinedload(StockOut.warehouse)
    ).filter(
        StockOut.customer_id == customer_id,
        func.lower(StockOut.status) == DocStatus.CONFIRMED,
        StockOut.date >= from_dt,
        StockOut.date <= to_dt
    ).order_by(
        StockOut.date.desc()
    ).paginate(
        page=page,
        per_page=20,
        error_out=False
    )

    top_products = db.session.query(
        Product.code,
        Product.name,
        func.sum(StockOutItem.quantity).label('total_qty'),
        func.sum(StockOutItem.amount).label('total_amt'),
        func.count(StockOutItem.id).label('order_count')
    ).join(
        StockOutItem, Product.id == StockOutItem.product_id
    ).join(
        StockOut, StockOutItem.stock_out_id == StockOut.id
    ).filter(
        StockOut.customer_id == customer_id,
        func.lower(StockOut.status) == DocStatus.CONFIRMED,
        StockOut.date >= from_dt,
        StockOut.date <= to_dt
    ).group_by(
        Product.id
    ).order_by(
        func.sum(StockOutItem.amount).desc()
    ).limit(10).all()

    top_products = [{
        "code": r.code,
        "name": r.name,
        "total_qty": float(r.total_qty or 0),
        "total_amt": float(r.total_amt or 0),
        "order_count": r.order_count
    } for r in top_products]

    return {
        "customer": customer,
        "debt": float(customer_data.debt or 0),
        "revenue": float(customer_data.revenue or 0),
        "order_count": customer_data.order_count or 0,
        "orders": orders,
        "top_products": top_products
    }
