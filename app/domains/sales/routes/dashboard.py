from datetime import datetime, date, timedelta
from flask import Blueprint, flash, render_template, request
from flask_login import login_required
from sqlalchemy import func, case
from app.database import db
from app.domains.master.models import Product, Supplier, Customer
from app.domains.inventory.models import (StockIn, StockOut, StockOutItem, Inventory)
from app.models.transaction import (Debt, VatRecord)
from app.domains.inventory.services.inventory_service import InventoryService
from app.shared.constants import DocStatus, DebtStatus

dashboard_bp = Blueprint('dashboard', __name__)


def _confirmed_filter(model):
    return model.status == DocStatus.CONFIRMED


def _stock_out_revenue_expr():
    return func.coalesce(StockOut.subtotal, 0) - func.coalesce(StockOut.discount_amount, 0)


def _stock_out_cogs_expr():
    unit_cost = case(
        (StockOutItem.cost_price > 0, StockOutItem.cost_price),
        else_=func.coalesce(Product.purchase_price, 0),
    )
    return (
        func.coalesce(StockOutItem.quantity, 0)
        * func.coalesce(StockOutItem.conversion_factor, 1)
        * unit_cost
    )


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()
    month_start = today.replace(day=1)
    from_date_raw = request.args.get('from_date', '')
    to_date_raw = request.args.get('to_date', '')

    try:
        chart_from = datetime.strptime(
            from_date_raw, '%Y-%m-%d').date() if from_date_raw else (today - timedelta(days=6))
    except Exception:
        chart_from = today - timedelta(days=6)
    try:
        chart_to = datetime.strptime(
            to_date_raw, '%Y-%m-%d').date() if to_date_raw else today
    except Exception:
        chart_to = today
    if chart_from > chart_to:
        chart_from, chart_to = chart_to, chart_from
     # Thêm đoạn check khoảng cách ngày tại đây
     
    if (chart_to - chart_from).days > 31:
        # Xử lý khi vượt quá 31 ngày (Ví dụ: báo lỗi hoặc tự động gán lại khoảng thời gian)
        flash('Bạn chỉ được phép xem báo cáo trong khoảng thời gian tối đa 31 ngày.', 'danger')
        # Hoặc đưa về mặc định là 6 ngày trước nếu người dùng chọn sai:
        chart_from = today - timedelta(days=6)
        chart_to = today
    total_products = Product.query.filter_by(is_active=True).count()
    total_customers = Customer.query.filter_by(is_active=True).count()
    total_suppliers = Supplier.query.filter_by(is_active=True).count()

    revenue_month = db.session.query(func.sum(_stock_out_revenue_expr())).filter(
        StockOut.date >= month_start,
        _confirmed_filter(StockOut)
    ).scalar() or 0

    purchase_month = db.session.query(
        func.sum(_stock_out_cogs_expr())
    ).join(StockOut, StockOutItem.stock_out_id == StockOut.id)\
        .join(Product, StockOutItem.product_id == Product.id)\
        .filter(
            StockOut.date >= month_start,
            _confirmed_filter(StockOut)
        ).scalar() or 0

    receivable = db.session.query(func.sum(Debt.balance)).filter(
        Debt.partner_type == 'customer',
        Debt.status.in_(DebtStatus.ACTIVE)
    ).scalar() or 0

    payable = db.session.query(func.sum(Debt.balance)).filter(
        Debt.partner_type == 'supplier',
        Debt.status.in_(DebtStatus.ACTIVE)
    ).scalar() or 0

    inv_value = db.session.query(
        func.sum(Inventory.quantity * Inventory.avg_cost)
    ).scalar() or 0

    low_stock = InventoryService.get_low_stock_products()

    recent_stock_ins = StockIn.query.order_by(
        StockIn.created_at.desc()).limit(5).all()

    recent_stock_outs = StockOut.query.order_by(
        StockOut.created_at.desc()).limit(5).all()

    overdue_debts = Debt.query.filter(
        Debt.status == DebtStatus.OVERDUE
    ).limit(5).all()

    chart_dates = []
    cur = chart_from
    while cur <= chart_to:
        chart_dates.append(cur)
        cur = cur + timedelta(days=1)

    rev_by_date = dict(
        db.session.query(StockOut.date, func.sum(_stock_out_revenue_expr()))
        .filter(StockOut.date >= chart_from, StockOut.date <= chart_to,
                StockOut.status == DocStatus.CONFIRMED)
        .group_by(StockOut.date).all()
    )
    cost_by_date = dict(
        db.session.query(StockOut.date, func.sum(_stock_out_cogs_expr()))
        .join(StockOutItem, StockOut.id == StockOutItem.stock_out_id)
        .join(Product, StockOutItem.product_id == Product.id)
        .filter(StockOut.date >= chart_from, StockOut.date <= chart_to,
                StockOut.status == DocStatus.CONFIRMED)
        .group_by(StockOut.date).all()
    )
    chart_revenue = [float(rev_by_date.get(d) or 0) for d in chart_dates]
    chart_purchase = [float(cost_by_date.get(d) or 0) for d in chart_dates]

    chart_labels = [d.strftime('%d/%m') for d in chart_dates]
    chart_profit = [rev - pur for rev, pur in zip(chart_revenue, chart_purchase)]

    vat_output = db.session.query(func.sum(VatRecord.vat_amount)).filter(
        VatRecord.vat_type == 'output',
        VatRecord.period_month == today.month,
        VatRecord.period_year == today.year
    ).scalar() or 0

    vat_input = db.session.query(func.sum(VatRecord.vat_amount)).filter(
        VatRecord.vat_type == 'input',
        VatRecord.period_month == today.month,
        VatRecord.period_year == today.year
    ).scalar() or 0

    return render_template('dashboard/index.html',
                           total_products=total_products,
                           total_customers=total_customers,
                           total_suppliers=total_suppliers,
                           revenue_month=float(revenue_month),
                           purchase_month=float(purchase_month),
                           receivable=float(receivable),
                           payable=float(payable),
                           inv_value=float(inv_value),
                           low_stock=low_stock,
                           recent_stock_ins=recent_stock_ins,
                           recent_stock_outs=recent_stock_outs,
                           overdue_debts=overdue_debts,
                           chart_labels=chart_labels,
                           chart_revenue=chart_revenue,
                           chart_purchase=chart_purchase,
                           chart_profit=chart_profit,
                           chart_from=chart_from,
                           chart_to=chart_to,
                           chart_from_val=chart_from.isoformat(),
                           chart_to_val=chart_to.isoformat(),
                           vat_output=float(vat_output),
                           vat_input=float(vat_input),
                           vat_net=float(vat_output) - float(vat_input),
                           today=today,
                           )
