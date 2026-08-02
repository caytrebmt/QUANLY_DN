from datetime import datetime, date
import io
import pandas as pd
from flask import (Blueprint, render_template, request, send_file, flash, redirect, url_for)
from flask_login import login_required, current_user
from sqlalchemy import func
from app.database import db
from app.domains.accounting.models import AccountChart
from app.domains.platform.models import SystemConfig
from app.domains.inventory.models import StockIn, StockOut
from app.domains.accounting.models import JournalEntry, JournalLine
from app.domains.finance.models import Debt, DebtPayment, VatRecord
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.pdf_exporter import PdfExporter
from app.shared.authz import require_permission
from app.shared.constants import DocStatus
from app.domains.accounting.services.account_mapping_service import ACCOUNT_MAPPING_DEFAULTS

from app.domains.accounting.services.tt99_service import TT99ReportService
from app.domains.accounting.services.tt99_mapper import TT99Mapper

accounting_bp = Blueprint('accounting', __name__, url_prefix='/accounting')


ACCOUNT_MAPPING_FIELDS = [
    ('acc_cash', 'Tiền mặt', 'TK tiền mặt khi thu/chi công nợ'),
    ('acc_bank', 'Tiền gửi ngân hàng', 'TK ngân hàng khi thu/chi công nợ'),
    ('acc_ar', 'Phải thu khách hàng', 'TK công nợ phải thu'),
    ('acc_ap', 'Phải trả người bán', 'TK công nợ phải trả'),
    ('acc_inventory', 'Hàng tồn kho', 'TK hàng hóa/tồn kho'),
    ('acc_vat_in', 'VAT đầu vào', 'TK thuế GTGT được khấu trừ'),
    ('acc_vat_out', 'VAT đầu ra', 'TK thuế GTGT phải nộp'),
    ('acc_revenue', 'Doanh thu', 'TK doanh thu bán hàng'),
    ('acc_cogs', 'Giá vốn', 'TK giá vốn hàng bán'),
]


@accounting_bp.route('/')
@login_required
@require_permission('accounting', 'view')
def index():
    from_date = request.args.get('from_date', date.today().replace(day=1).isoformat())
    to_date = request.args.get('to_date', date.today().isoformat())
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    q = JournalEntry.query
    if from_date:
        q = q.filter(JournalEntry.date >= datetime.strptime(from_date, '%Y-%m-%d').date())
    if to_date:
        q = q.filter(JournalEntry.date <= datetime.strptime(to_date, '%Y-%m-%d').date())
    if search:
        q = q.filter(db.or_(
            JournalEntry.code.ilike(f'%{search}%'),
            JournalEntry.description.ilike(f'%{search}%'),
            JournalEntry.reference_code.ilike(f'%{search}%'),
        ))

    entries = q.order_by(JournalEntry.date.desc(), JournalEntry.code.desc()).paginate(
        page=page, per_page=20, error_out=False)

    total_debit = db.session.query(func.sum(JournalEntry.total_debit)).filter(
        JournalEntry.date >= datetime.strptime(from_date, '%Y-%m-%d').date(),
        JournalEntry.date <= datetime.strptime(to_date, '%Y-%m-%d').date(),
    ).scalar() or 0

    return render_template('accounting/index.html',
                           entries=entries, from_date=from_date,
                           to_date=to_date, search=search,
                           total_debit=float(total_debit))


@accounting_bp.route('/entry/<int:id>')
@login_required
@require_permission('accounting', 'view')
def detail(id):
    entry = JournalEntry.query.get_or_404(id)
    return render_template('accounting/detail.html', entry=entry)


@accounting_bp.route('/accounts')
@login_required
@require_permission('accounting', 'view')
def accounts():
    """Hệ thống tài khoản kế toán"""
    search = request.args.get('search', '')
    account_type = request.args.get('account_type', '')

    q = AccountChart.query
    if search:
        q = q.filter(db.or_(
            AccountChart.code.ilike(f'%{search}%'),
            AccountChart.name.ilike(f'%{search}%'),
        ))
    if account_type:
        q = q.filter(AccountChart.account_type == account_type)

    accounts_list = q.order_by(AccountChart.code).all()
    return render_template('accounting/accounts.html',
                           accounts=accounts_list, search=search,
                           account_type=account_type)


@accounting_bp.route('/accounts/create', methods=['GET', 'POST'])
@login_required
@require_permission('accounting', 'create')
def create_account():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        name = request.form.get('name', '').strip()
        if not code or not name:
            flash('Số hiệu và tên tài khoản không được để trống!', 'danger')
            return render_template('accounting/account_form.html',
                                   account=None, all_accounts=AccountChart.query.order_by(AccountChart.code).all())
        if AccountChart.query.filter_by(code=code).first():
            flash(f'Tài khoản {code} đã tồn tại!', 'danger')
            return render_template('accounting/account_form.html',
                                   account=None, all_accounts=AccountChart.query.order_by(AccountChart.code).all())
        acc = AccountChart(
            code=code, name=name,
            name_en=request.form.get('name_en', '').strip(),
            account_type=request.form.get('account_type', 'asset'),
            parent_id=request.form.get('parent_id', type=int) or None,
            level=int(request.form.get('level', 1)),
            normal_balance=request.form.get('normal_balance', 'debit'),
            is_detail=request.form.get('is_detail') == 'on',
            description=request.form.get('description', '').strip(),
        )
        db.session.add(acc)
        db.session.commit()
        flash(f'Thêm tài khoản {code} thành công!', 'success')
        return redirect(url_for('accounting.accounts'))
    return render_template('accounting/account_form.html',
                           account=None, all_accounts=AccountChart.query.order_by(AccountChart.code).all())


@accounting_bp.route('/accounts/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('accounting', 'edit')
def edit_account(id):
    acc = AccountChart.query.get_or_404(id)
    if request.method == 'POST':
        acc.name = request.form.get('name', '').strip()
        acc.name_en = request.form.get('name_en', '').strip()
        acc.account_type = request.form.get('account_type', 'asset')
        acc.parent_id = request.form.get('parent_id', type=int) or None
        acc.level = int(request.form.get('level', 1))
        acc.normal_balance = request.form.get('normal_balance', 'debit')
        acc.is_detail = request.form.get('is_detail') == 'on'
        acc.description = request.form.get('description', '').strip()
        db.session.commit()
        flash(f'Cập nhật tài khoản {acc.code} thành công!', 'success')
        return redirect(url_for('accounting.accounts'))
    return render_template('accounting/account_form.html',
                           account=acc, all_accounts=AccountChart.query.filter(
                               AccountChart.id != id).order_by(AccountChart.code).all())


@accounting_bp.route('/trial-balance')
@login_required
@require_permission('accounting', 'view')
def trial_balance():
    """Bảng cân đối kế toán"""
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    from_date = date(year, month, 1)
    import calendar
    _, last_day = calendar.monthrange(year, month)
    to_date = date(year, month, last_day)

    trial_data = TT99ReportService.get_trial_balance(from_date, to_date)

    years = list(range(date.today().year - 2, date.today().year + 2))
    return render_template('accounting/trial_balance.html',
                           trial_data=trial_data, month=month, year=year, years=years,
                           from_date=from_date, to_date=to_date)


@accounting_bp.route('/export/excel')
@login_required
@require_permission('accounting', 'export')
def export_excel():
    from_date = request.args.get('from_date', date.today().replace(day=1).isoformat())
    to_date = request.args.get('to_date', date.today().isoformat())

    entries = JournalEntry.query.filter(
        JournalEntry.date >= datetime.strptime(from_date, '%Y-%m-%d').date(),
        JournalEntry.date <= datetime.strptime(to_date, '%Y-%m-%d').date(),
    ).order_by(JournalEntry.date, JournalEntry.code).all()

    output = ExcelExporter.export_journal(entries)
    return send_file(output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=f'nhat_ky_chung_{datetime.now().strftime("%Y%m%d")}.xlsx')


@accounting_bp.route('/account-mapping', methods=['GET', 'POST'])
@login_required
@require_permission('accounting', 'edit')
def account_mapping():
    accounts = AccountChart.query.filter_by(
        is_active=True).order_by(AccountChart.code).all()
    code_to_name = {a.code: a.name for a in accounts}

    if request.method == 'POST':
        errors = []
        for key, label, _hint in ACCOUNT_MAPPING_FIELDS:
            val = (request.form.get(key, '') or '').strip()
            if not val:
                errors.append(f'{label}: chưa chọn tài khoản.')
                continue
            if val not in code_to_name:
                errors.append(f'{label}: tài khoản {val} không tồn tại hoặc đã ngừng.')

        if errors:
            for e in errors:
                flash(e, 'danger')
        else:
            for key, _label, _hint in ACCOUNT_MAPPING_FIELDS:
                val = (request.form.get(key, '') or '').strip()
                cfg = SystemConfig.query.filter_by(key=key).first()
                if cfg:
                    cfg.value = val
                else:
                    db.session.add(SystemConfig(
                        key=key,
                        value=val,
                        description=f'Account mapping: {key}',
                        group_name='accounting',
                    ))
            db.session.commit()
            flash('Đã lưu mapping tài khoản thành công.', 'success')
            return redirect(url_for('accounting.account_mapping'))

    values = {}
    for key, _label, _hint in ACCOUNT_MAPPING_FIELDS:
        cfg = SystemConfig.query.filter_by(key=key).first()
        values[key] = (cfg.value if cfg and cfg.value else ACCOUNT_MAPPING_DEFAULTS.get(key, ''))

    return render_template(
        'accounting/account_mapping.html',
        fields=ACCOUNT_MAPPING_FIELDS,
        values=values,
        accounts=accounts,
        code_to_name=code_to_name,
    )


def _build_health_check_data():
    """Build data for accounting health check (UI + export)."""
    # 1) Journal lệch tổng Nợ/Có
    je_unbalanced = JournalEntry.query.filter(
        func.coalesce(JournalEntry.total_debit, 0) != func.coalesce(JournalEntry.total_credit, 0)
    ).count()

    # 2) Header journal lệch tổng line
    line_sum = db.session.query(
        JournalLine.entry_id.label('entry_id'),
        func.coalesce(func.sum(JournalLine.debit), 0).label('sum_debit'),
        func.coalesce(func.sum(JournalLine.credit), 0).label('sum_credit'),
    ).group_by(JournalLine.entry_id).subquery()

    je_header_line_mismatch = db.session.query(JournalEntry.id).join(
        line_sum, line_sum.c.entry_id == JournalEntry.id
    ).filter(
        db.or_(
            func.coalesce(JournalEntry.total_debit, 0) != func.coalesce(line_sum.c.sum_debit, 0),
            func.coalesce(JournalEntry.total_credit, 0) != func.coalesce(line_sum.c.sum_credit, 0),
        )
    ).count()

    # 3) Phiếu confirmed nhưng chưa có journal
    confirmed_stock_in_no_je = db.session.query(StockIn.id).outerjoin(
        JournalEntry,
        db.and_(JournalEntry.reference_type == 'stock_in', JournalEntry.reference_id == StockIn.id)
    ).filter(StockIn.status == DocStatus.CONFIRMED, JournalEntry.id.is_(None)).count()

    confirmed_stock_out_no_je = db.session.query(StockOut.id).outerjoin(
        JournalEntry,
        db.and_(JournalEntry.reference_type == 'stock_out', JournalEntry.reference_id == StockOut.id)
    ).filter(StockOut.status == DocStatus.CONFIRMED, JournalEntry.id.is_(None)).count()

    confirmed_no_je = confirmed_stock_in_no_je + confirmed_stock_out_no_je

    # 4) Duplicate journal theo reference (chỉ tính bút toán gốc, bỏ -REV)
    duplicate_primary_rows = db.session.query(
        JournalEntry.reference_type,
        JournalEntry.reference_id,
        func.count(JournalEntry.id).label('journal_count'),
        func.string_agg(JournalEntry.code, ', ').label('journal_codes')
    ).filter(
        JournalEntry.reference_type.in_(['stock_in', 'stock_out', 'debt_payment']),
        JournalEntry.reference_id.isnot(None),
        ~JournalEntry.code.like('%-REV')
    ).group_by(
        JournalEntry.reference_type, JournalEntry.reference_id
    ).having(
        func.count(JournalEntry.id) > 1
    ).order_by(
        func.count(JournalEntry.id).desc(),
        JournalEntry.reference_type.asc(),
        JournalEntry.reference_id.asc()
    ).all()
    duplicate_primary = len(duplicate_primary_rows)

    # 5) Debt balance lệch payment
    pay_sum = db.session.query(
        DebtPayment.debt_id.label('debt_id'),
        func.coalesce(func.sum(DebtPayment.amount), 0).label('paid')
    ).group_by(DebtPayment.debt_id).subquery()

    debt_balance_mismatch = db.session.query(Debt.id).outerjoin(
        pay_sum, pay_sum.c.debt_id == Debt.id
    ).filter(
        func.coalesce(Debt.balance, 0) !=
        (func.coalesce(Debt.amount, 0) - func.coalesce(pay_sum.c.paid, 0))
    ).count()

    # 6) Debt tham chiếu chứng từ chưa confirmed
    debt_ref_stock_in_not_confirmed = db.session.query(Debt.id).join(
        StockIn,
        db.and_(Debt.reference_type == 'stock_in', Debt.reference_id == StockIn.id)
    ).filter(StockIn.status != DocStatus.CONFIRMED).count()

    debt_ref_stock_out_not_confirmed = db.session.query(Debt.id).join(
        StockOut,
        db.and_(Debt.reference_type == 'stock_out', Debt.reference_id == StockOut.id)
    ).filter(StockOut.status != DocStatus.CONFIRMED).count()

    debt_ref_not_confirmed = debt_ref_stock_in_not_confirmed + debt_ref_stock_out_not_confirmed

    # 7) VAT lệch chứng từ gốc
    vat_input_mismatch = db.session.query(VatRecord.id).join(
        StockIn,
        db.and_(VatRecord.reference_type == 'stock_in', VatRecord.reference_id == StockIn.id)
    ).filter(
        db.or_(
            func.coalesce(VatRecord.vat_amount, 0) != func.coalesce(StockIn.vat_amount, 0),
            func.coalesce(VatRecord.total_amount, 0) != func.coalesce(StockIn.total_amount, 0),
            func.coalesce(VatRecord.taxable_amount, 0) != func.coalesce(StockIn.subtotal, 0),
        )
    ).count()

    vat_output_mismatch = db.session.query(VatRecord.id).join(
        StockOut,
        db.and_(VatRecord.reference_type == 'stock_out', VatRecord.reference_id == StockOut.id)
    ).filter(
        db.or_(
            func.coalesce(VatRecord.vat_amount, 0) != func.coalesce(StockOut.vat_amount, 0),
            func.coalesce(VatRecord.total_amount, 0) != func.coalesce(StockOut.total_amount, 0),
            func.coalesce(VatRecord.taxable_amount, 0) != func.coalesce(StockOut.subtotal, 0),
        )
    ).count()

    checks = [
        {'key': 'JE_UNBALANCED', 'label': 'Journal lệch tổng Nợ/Có', 'count': je_unbalanced},
        {'key': 'JE_HEADER_LINE_MISMATCH', 'label': 'Header journal lệch tổng dòng', 'count': je_header_line_mismatch},
        {'key': 'CONFIRMED_NO_JE', 'label': 'Phiếu confirmed chưa có journal', 'count': confirmed_no_je},
        {'key': 'DUPLICATE_PRIMARY_JE', 'label': 'Trùng journal gốc theo chứng từ', 'count': duplicate_primary},
        {'key': 'DEBT_BALANCE_MISMATCH', 'label': 'Lệch số dư công nợ', 'count': debt_balance_mismatch},
        {'key': 'DEBT_REF_NOT_CONFIRMED', 'label': 'Công nợ tham chiếu phiếu chưa confirmed', 'count': debt_ref_not_confirmed},
        {'key': 'VAT_INPUT_MISMATCH', 'label': 'VAT đầu vào lệch chứng từ', 'count': vat_input_mismatch},
        {'key': 'VAT_OUTPUT_MISMATCH', 'label': 'VAT đầu ra lệch chứng từ', 'count': vat_output_mismatch},
    ]
    total_issues = sum(x['count'] for x in checks)
    return {
        'checks': checks,
        'total_issues': total_issues,
        'duplicate_primary_rows': duplicate_primary_rows,
    }


@accounting_bp.route('/health-check')
@login_required
@require_permission('accounting', 'view')
def health_check():
    """Kiểm tra nhanh tính toàn vẹn dữ liệu kế toán."""
    data = _build_health_check_data()

    return render_template(
        'accounting/health_check.html',
        checks=data['checks'],
        total_issues=data['total_issues'],
        duplicate_primary_rows=data['duplicate_primary_rows'],
        generated_at=datetime.now(),
    )


@accounting_bp.route('/health-check/export/excel')
@login_required
@require_permission('accounting', 'export')
def export_health_check_excel():
    data = _build_health_check_data()
    output = ExcelExporter.export_health_check(
        checks=data['checks'],
        duplicate_rows=data['duplicate_primary_rows'],
        generated_at=datetime.now(),
    )
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'accounting_health_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


@accounting_bp.route('/health-check/export/pdf')
@login_required
@require_permission('accounting', 'export')
def export_health_check_pdf():
    data = _build_health_check_data()
    output = PdfExporter.export_health_check(
        checks=data['checks'],
        duplicate_rows=data['duplicate_primary_rows'],
        generated_at=datetime.now(),
    )
    return send_file(
        output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'accounting_health_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    )

def _parse_iso_date(value, fallback):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except Exception:
        return fallback


def _to_excel_file(df, filename):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename,
    )


@accounting_bp.route('/balance-sheet')
@login_required
@require_permission('accounting', 'view')
def balance_sheet():
    as_of_date = _parse_iso_date(request.args.get('date', ''), date.today())
    raw = TT99ReportService.get_balance_sheet(as_of_date)
    mapped = TT99Mapper.map_balance_sheet(raw)
    return render_template(
        'accounting/balance_sheet.html',
        data=mapped,
        as_of_date=as_of_date,
    )


@accounting_bp.route('/income-statement')
@login_required
@require_permission('accounting', 'view')
def income_statement():
    today = date.today()
    start_date = _parse_iso_date(request.args.get('start', ''), today.replace(day=1))
    end_date = _parse_iso_date(request.args.get('end', ''), today)
    raw = TT99ReportService.get_income_statement(start_date, end_date)
    mapped = TT99Mapper.map_income_statement(raw)
    return render_template(
        'accounting/income_statement.html',
        data=mapped,
        start_date=start_date,
        end_date=end_date,
    )


@accounting_bp.route('/general-ledger/<account_code>')
@login_required
@require_permission('accounting', 'view')
def general_ledger(account_code):
    today = date.today()
    start_date = _parse_iso_date(request.args.get('start', ''), today.replace(day=1))
    end_date = _parse_iso_date(request.args.get('end', ''), today)
    ledger = TT99ReportService.get_general_ledger(account_code, start_date, end_date)
    acc = AccountChart.query.filter_by(code=account_code).first()
    return render_template(
        'accounting/general_ledger.html',
        account=acc,
        account_code=account_code,
        lines=ledger['lines'],
        opening_balance=ledger['opening_balance'],
        closing_balance=ledger['closing_balance'],
        opening_debit=ledger.get('opening_debit', 0),
        opening_credit=ledger.get('opening_credit', 0),
        closing_debit=ledger.get('closing_debit', 0),
        closing_credit=ledger.get('closing_credit', 0),
        normal_balance=ledger['normal_balance'],
        start_date=start_date,
        end_date=end_date,
    )


@accounting_bp.route('/detail-ledger/<account_code>')
@login_required
@require_permission('accounting', 'view')
def detail_ledger(account_code):
    today = date.today()
    start_date = _parse_iso_date(request.args.get('start', ''), today.replace(day=1))
    end_date = _parse_iso_date(request.args.get('end', ''), today)
    partner_id = request.args.get('partner_id', type=int)
    lines = TT99ReportService.get_detail_ledger(account_code, start_date, end_date, partner_id)
    acc = AccountChart.query.filter_by(code=account_code).first()
    partners = []
    if account_code == '131':
        from app.domains.master.models import Customer
        partners = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    elif account_code == '331':
        from app.domains.master.models import Supplier
        partners = Supplier.query.filter_by(is_active=True).order_by(Supplier.name).all()

    return render_template(
        'accounting/detail_ledger.html',
        account=acc,
        account_code=account_code,
        lines=lines,
        start_date=start_date,
        end_date=end_date,
        partner_id=partner_id,
        partners=partners,
    )


@accounting_bp.route('/export/balance-sheet.xlsx')
@login_required
@require_permission('accounting', 'export')
def export_balance_sheet():
    as_of_date = _parse_iso_date(request.args.get('date', ''), date.today())
    raw = TT99ReportService.get_balance_sheet(as_of_date)
    mapped = TT99Mapper.map_balance_sheet(raw)
    rows = [
        {'Mã số': code, 'Chỉ tiêu': item['label'], 'Số tiền': abs(item['amount'])}
        for code, item in mapped.items()
    ]
    df = pd.DataFrame(rows)
    return _to_excel_file(df, f'bang_can_doi_ke_toan_{as_of_date.isoformat()}.xlsx')


@accounting_bp.route('/export/income-statement.xlsx')
@login_required
@require_permission('accounting', 'export')
def export_income_statement():
    today = date.today()
    start_date = _parse_iso_date(request.args.get('start', ''), today.replace(day=1))
    end_date = _parse_iso_date(request.args.get('end', ''), today)
    raw = TT99ReportService.get_income_statement(start_date, end_date)
    mapped = TT99Mapper.map_income_statement(raw)
    rows = [{'Mã số': r['ma_so'], 'Chỉ tiêu': r['chi_tieu'], 'Số tiền': r['so_tien']} for r in mapped]
    df = pd.DataFrame(rows)
    return _to_excel_file(df, f'bao_cao_kqkd_{start_date.isoformat()}_{end_date.isoformat()}.xlsx')


@accounting_bp.route('/export/general-ledger/<account_code>.xlsx')
@login_required
@require_permission('accounting', 'export')
def export_general_ledger(account_code):
    today = date.today()
    start_date = _parse_iso_date(request.args.get('start', ''), today.replace(day=1))
    end_date = _parse_iso_date(request.args.get('end', ''), today)
    ledger = TT99ReportService.get_general_ledger(account_code, start_date, end_date)
    rows = []
    for row in ledger['lines']:
        rows.append({
            'Ngày': row['date'],
            'Chứng từ': row['entry_code'],
            'Diễn giải': row['description'],
            'Nợ': row['debit'],
            'Có': row['credit'],
            'Dư Nợ': row['running_debit_balance'],
            'Dư Có': row['running_credit_balance'],
        })
    df = pd.DataFrame(rows)
    return _to_excel_file(df, f'so_cai_{account_code}_{start_date.isoformat()}_{end_date.isoformat()}.xlsx')


@accounting_bp.route('/export/detail-ledger/<account_code>.xlsx')
@login_required
@require_permission('accounting', 'export')
def export_detail_ledger(account_code):
    today = date.today()
    start_date = _parse_iso_date(request.args.get('start', ''), today.replace(day=1))
    end_date = _parse_iso_date(request.args.get('end', ''), today)
    partner_id = request.args.get('partner_id', type=int)
    lines = TT99ReportService.get_detail_ledger(account_code, start_date, end_date, partner_id)
    rows = []
    for row in lines:
        rows.append({
            'Đối tượng': row['partner_name'],
            'Ngày': row['date'],
            'Chứng từ': row['entry_code'],
            'Diễn giải': row['description'],
            'Nợ': row['debit'],
            'Có': row['credit'],
            'Dư Nợ': row['running_debit_balance'],
            'Dư Có': row['running_credit_balance'],
        })
    df = pd.DataFrame(rows)
    return _to_excel_file(df, f'so_chi_tiet_{account_code}_{start_date.isoformat()}_{end_date.isoformat()}.xlsx')


@accounting_bp.route('/export/trial-balance.xlsx')
@login_required
@require_permission('accounting', 'export')
def export_trial_balance():
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    from_date = date(year, month, 1)
    import calendar
    _, last_day = calendar.monthrange(year, month)
    to_date = date(year, month, last_day)

    trial_data = TT99ReportService.get_trial_balance(from_date, to_date)
    rows = []
    for row in trial_data:
        rows.append({
            'Số hiệu TK': row['account_code'],
            'Tên tài khoản': row['account_name'],
            'Số dư đầu kỳ Nợ': row['opening_debit'],
            'Số dư đầu kỳ Có': row['opening_credit'],
            'Phát sinh Nợ': row['period_debit'],
            'Phát sinh Có': row['period_credit'],
            'Số dư cuối kỳ Nợ': row['closing_debit'],
            'Số dư cuối kỳ Có': row['closing_credit'],
        })
    df = pd.DataFrame(rows)
    return _to_excel_file(df, f'can_doi_so_phat_sinh_{year}{month:02d}.xlsx')


@accounting_bp.route('/export/general-ledger/<account_code>.pdf')
@login_required
@require_permission('accounting', 'export')
def export_general_ledger_pdf(account_code):
    today = date.today()
    start_date = _parse_iso_date(request.args.get('start', ''), today.replace(day=1))
    end_date = _parse_iso_date(request.args.get('end', ''), today)
    ledger = TT99ReportService.get_general_ledger(account_code, start_date, end_date)
    acc = AccountChart.query.filter_by(code=account_code).first()
    output = PdfExporter.export_general_ledger(
        account=acc,
        lines=ledger['lines'],
        opening_balance=ledger['opening_balance'],
        closing_balance=ledger['closing_balance'],
        opening_debit=ledger.get('opening_debit', 0),
        opening_credit=ledger.get('opening_credit', 0),
        closing_debit=ledger.get('closing_debit', 0),
        closing_credit=ledger.get('closing_credit', 0),
        normal_balance=ledger['normal_balance'],
        start_date=start_date,
        end_date=end_date,
    )
    return send_file(
        output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'so_cai_{account_code}_{start_date.isoformat()}_{end_date.isoformat()}.pdf'
    )


@accounting_bp.route('/export/trial-balance.pdf')
@login_required
@require_permission('accounting', 'export')
def export_trial_balance_pdf():
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    from_date = date(year, month, 1)
    import calendar
    _, last_day = calendar.monthrange(year, month)
    to_date = date(year, month, last_day)

    trial_data = TT99ReportService.get_trial_balance(from_date, to_date)
    output = PdfExporter.export_trial_balance(
        trial_data=trial_data,
        month=month,
        year=year,
        from_date=from_date,
        to_date=to_date,
    )
    return send_file(
        output,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'can_doi_so_phat_sinh_{year}{month:02d}.pdf'
    )
