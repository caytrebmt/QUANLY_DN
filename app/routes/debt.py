from datetime import datetime, date
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, send_file, jsonify)
from flask_login import login_required, current_user
from sqlalchemy import func
from app.database import db
from app.domains.master.models import Customer, Supplier
from app.domains.finance.models import Debt, DebtPayment
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.authz import require_permission
from app.domains.accounting.services.accounting_helper import create_entry
from app.domains.accounting.services.account_mapping_service import get_account_code

debt_bp = Blueprint('debt', __name__, url_prefix='/debt')


@debt_bp.route('/')
@login_required
@require_permission('debt', 'view')
def index():
    partner_type = request.args.get('partner_type', 'customer')
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)

    q = Debt.query.filter_by(partner_type=partner_type)
    if status:
        q = q.filter(Debt.status == status)

    debts = q.order_by(Debt.date.desc()).paginate(page=page, per_page=20, error_out=False)

    # Totals
    total_amount = db.session.query(func.sum(Debt.amount)).filter(
        Debt.partner_type == partner_type, Debt.status != 'paid').scalar() or 0
    total_paid = db.session.query(func.sum(Debt.paid_amount)).filter(
        Debt.partner_type == partner_type, Debt.status != 'paid').scalar() or 0
    total_balance = db.session.query(func.sum(Debt.balance)).filter(
        Debt.partner_type == partner_type, Debt.status != 'paid').scalar() or 0
    total_overdue = db.session.query(func.sum(Debt.balance)).filter(
        Debt.partner_type == partner_type, Debt.status == 'overdue').scalar() or 0

    # Enrich with partner info
    enriched = []
    for d in debts.items:
        if d.partner_type == 'customer':
            partner = Customer.query.get(d.partner_id)
        else:
            partner = Supplier.query.get(d.partner_id)
        enriched.append({'debt': d, 'partner': partner})

    return render_template('debt/index.html',
                           debts=debts, enriched=enriched,
                           partner_type=partner_type, status=status,
                           total_amount=float(total_amount),
                           total_paid=float(total_paid),
                           total_balance=float(total_balance),
                           total_overdue=float(total_overdue))


@debt_bp.route('/pay/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('debt', 'edit')
def pay(id):
    debt = Debt.query.get_or_404(id)
    if debt.partner_type == 'customer':
        partner = Customer.query.get(debt.partner_id)
    else:
        partner = Supplier.query.get(debt.partner_id)

    if request.method == 'POST':
        from decimal import Decimal, ROUND_HALF_UP
        try:
            amount = Decimal(request.form.get('amount', '0') or '0').quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            amount = Decimal('0')
        balance = Decimal(str(debt.balance or 0))
        paid_amt = Decimal(str(debt.paid_amount or 0))
        total_amt = Decimal(str(debt.amount or 0))

        if amount <= 0:
            flash('Số tiền thanh toán phải lớn hơn 0!', 'danger')
            return render_template('debt/pay.html', debt=debt, partner=partner)
        if amount > balance:
            flash(f'Số tiền vượt quá số dư! Còn lại: {balance:,.0f}', 'danger')
            return render_template('debt/pay.html', debt=debt, partner=partner)

        payment = DebtPayment(
            debt_id=debt.id,
            date=datetime.strptime(request.form.get('date', date.today().isoformat()), '%Y-%m-%d').date(),
            amount=amount,
            payment_method=request.form.get('payment_method', 'cash'),
            reference=request.form.get('reference', '').strip(),
            note=request.form.get('note', '').strip(),
            created_by=current_user.id,
        )
        db.session.add(payment)
        db.session.flush()
        debt.paid_amount = paid_amt + amount
        debt.balance = total_amt - debt.paid_amount
        debt.update_status()
        # Hạch toán thanh toán
        try:
            pm = request.form.get('payment_method', 'cash')
            cash_acc = get_account_code('acc_cash') if pm == 'cash' else get_account_code('acc_bank')
            acc_ar = get_account_code('acc_ar')
            acc_ap = get_account_code('acc_ap')
            amt_dec = amount
            if debt.partner_type == 'customer':
                lines = [
                    {'account_code': cash_acc, 'debit': amt_dec, 'credit': 0},
                    {'account_code': acc_ar, 'debit': 0, 'credit': amt_dec},
                ]
                desc = f'Thu công nợ {debt.reference_code or debt.id}'
            else:
                lines = [
                    {'account_code': acc_ap, 'debit': amt_dec, 'credit': 0},
                    {'account_code': cash_acc, 'debit': 0, 'credit': amt_dec},
                ]
                desc = f'Thanh toán công nợ {debt.reference_code or debt.id}'
            create_entry(
                code=f'JE-DP-{payment.id}',
                date=payment.date,
                description=desc,
                lines=lines,
                reference_type='debt_payment',
                reference_id=payment.id,
                reference_code=debt.reference_code
            )
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi hạch toán thanh toán: {e}', 'danger')
            return render_template('debt/pay.html', debt=debt, partner=partner)
        db.session.commit()
        flash(f'Thanh toán {amount:,.0f} VND thành công!', 'success')
        return redirect(url_for('debt.index', partner_type=debt.partner_type))

    return render_template('debt/pay.html', debt=debt, partner=partner)


@debt_bp.route('/summary')
@login_required
@require_permission('debt', 'view')
def summary():
    """Tổng hợp công nợ theo đối tác"""
    partner_type = request.args.get('partner_type', 'customer')

    if partner_type == 'customer':
        partners = Customer.query.filter_by(is_active=True).all()
    else:
        partners = Supplier.query.filter_by(is_active=True).all()

    summary_data = []
    for p in partners:
        total = db.session.query(func.sum(Debt.amount)).filter(
            Debt.partner_type == partner_type,
            Debt.partner_id == p.id,
            Debt.status != 'paid'
        ).scalar() or 0
        paid = db.session.query(func.sum(Debt.paid_amount)).filter(
            Debt.partner_type == partner_type,
            Debt.partner_id == p.id,
            Debt.status != 'paid'
        ).scalar() or 0
        balance = float(total) - float(paid)
        if balance > 0 or float(total) > 0:
            summary_data.append({
                'partner': p,
                'total': float(total),
                'paid': float(paid),
                'balance': balance,
            })

    summary_data.sort(key=lambda x: x['balance'], reverse=True)
    return render_template('debt/summary.html',
                           summary_data=summary_data, partner_type=partner_type)


@debt_bp.route('/export/excel')
@login_required
@require_permission('debt', 'export')
def export_excel():
    partner_type = request.args.get('partner_type', 'customer')
    debts = Debt.query.filter_by(partner_type=partner_type).order_by(Debt.date.desc()).all()
    output = ExcelExporter.export_debts(debts, partner_type)
    label = 'cong_no_phai_thu' if partner_type == 'customer' else 'cong_no_phai_tra'
    return send_file(output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=f'{label}_{datetime.now().strftime("%Y%m%d")}.xlsx')
