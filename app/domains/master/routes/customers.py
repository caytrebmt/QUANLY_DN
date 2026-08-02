from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, send_file)
from flask_login import login_required
from app.database import db
from app.domains.master.models import Customer
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.excel_importer import ExcelImporter
from app.shared.authz import require_permission
import io
import math
import unicodedata

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')


def _normalize_text(value):
    s = unicodedata.normalize('NFD', str(value or ''))
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    s = s.replace('đ', 'd').replace('Đ', 'D')
    return s.casefold().strip()


class _SimplePagination:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max(1, math.ceil(total / per_page)) if total else 1

    def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (self.page - left_current - 1 < num < self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num


@customers_bp.route('/')
@login_required
@require_permission('customers', 'view')
def index():
    search = request.args.get('search', '')
    ctype = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    q = Customer.query
    if search:
        q = q.filter(
            db.or_(Customer.code.ilike(f'%{search}%'),
                   Customer.name.ilike(f'%{search}%'),
                   Customer.phone.ilike(f'%{search}%'),
                   Customer.tax_code.ilike(f'%{search}%'))
        )
    if ctype:
        q = q.filter(Customer.customer_type == ctype)
    q = q.order_by(Customer.code)
    customers = q.paginate(page=page, per_page=20, error_out=False)

    if search and customers.total == 0:
        base_q = Customer.query
        if ctype:
            base_q = base_q.filter(Customer.customer_type == ctype)
        rows = base_q.order_by(Customer.code).all()
        needle = _normalize_text(search)
        matched = []
        for c in rows:
            haystack = " ".join([
                c.code or '',
                c.name or '',
                c.phone or '',
                c.tax_code or '',
            ])
            if needle in _normalize_text(haystack):
                matched.append(c)

        per_page = 20
        start = (page - 1) * per_page
        end = start + per_page
        customers = _SimplePagination(
            items=matched[start:end],
            page=page,
            per_page=per_page,
            total=len(matched),
        )

    return render_template('customers/index.html', customers=customers,
                           search=search, ctype=ctype)


@customers_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('customers', 'create')
def create():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        if not code or not name:
            flash('Mã KH và tên không được để trống!', 'danger')
            return render_template('customers/form.html', customer=None)
        if Customer.query.filter_by(code=code).first():
            flash(f'Mã KH {code} đã tồn tại!', 'danger')
            return render_template('customers/form.html', customer=None)
        c = Customer(
            code=code, name=name,
            short_name=request.form.get('short_name', '').strip(),
            customer_type=request.form.get('customer_type', 'retail'),
            address=request.form.get('address', '').strip(),
            phone=request.form.get('phone', '').strip(),
            email=request.form.get('email', '').strip(),
            tax_code=request.form.get('tax_code', '').strip(),
            contact_person=request.form.get('contact_person', '').strip(),
            bank_account=request.form.get('bank_account', '').strip(),
            bank_name=request.form.get('bank_name', '').strip(),
            payment_terms=int(request.form.get('payment_terms', 30) or 30),
            credit_limit=float(request.form.get('credit_limit', 0) or 0),
            discount_rate=float(request.form.get('discount_rate', 0) or 0),
            note=request.form.get('note', '').strip(),
        )
        db.session.add(c)
        db.session.commit()
        flash(f'Thêm khách hàng {code} thành công!', 'success')
        return redirect(url_for('customers.index'))
    return render_template('customers/form.html', customer=None)


@customers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('customers', 'edit')
def edit(id):
    c = Customer.query.get_or_404(id)
    if request.method == 'POST':
        c.name = request.form.get('name', '').strip()
        c.short_name = request.form.get('short_name', '').strip()
        c.customer_type = request.form.get('customer_type', 'retail')
        c.address = request.form.get('address', '').strip()
        c.phone = request.form.get('phone', '').strip()
        c.email = request.form.get('email', '').strip()
        c.tax_code = request.form.get('tax_code', '').strip()
        c.contact_person = request.form.get('contact_person', '').strip()
        c.bank_account = request.form.get('bank_account', '').strip()
        c.bank_name = request.form.get('bank_name', '').strip()
        c.payment_terms = int(request.form.get('payment_terms', 30) or 30)
        c.credit_limit = float(request.form.get('credit_limit', 0) or 0)
        c.discount_rate = float(request.form.get('discount_rate', 0) or 0)
        c.note = request.form.get('note', '').strip()
        c.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash(f'Cập nhật khách hàng {c.code} thành công!', 'success')
        return redirect(url_for('customers.index'))
    return render_template('customers/form.html', customer=c)


@customers_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('customers', 'delete')
def delete(id):
    c = Customer.query.get_or_404(id)
    from app.domains.inventory.models import StockOut
    if db.session.query(StockOut).filter_by(customer_id=c.id).count() > 0:
        c.is_active = False
        db.session.commit()
        flash(f'KH {c.code} đã được vô hiệu hóa (có giao dịch liên quan).', 'warning')
    else:
        db.session.delete(c)
        db.session.commit()
        flash(f'Xóa khách hàng {c.code} thành công!', 'success')
    return redirect(url_for('customers.index'))


@customers_bp.route('/export/excel')
@login_required
@require_permission('customers', 'export')
def export_excel():
    customers = Customer.query.order_by(Customer.code).all()
    output = ExcelExporter.export_customers(customers)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='khach_hang.xlsx')


@customers_bp.route('/import/excel', methods=['POST'])
@login_required
@require_permission('customers', 'create')
def import_excel():
    if 'file' not in request.files:
        flash('Vui lòng chọn file!', 'danger')
        return redirect(url_for('customers.index'))

    file = request.files['file']

    try:
        imported, updated, errors = ExcelImporter.import_customers(file)

        flash(f'Import thành công: {imported} mới, {updated} cập nhật.', 'success')
        for err in errors[:5]:
            flash(f'Lỗi: {err}', 'warning')

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f'Lỗi import: {str(e)}', 'danger')

    return redirect(url_for('customers.index'))


@customers_bp.route('/template/excel')
@login_required
@require_permission('customers', 'view')
def download_template():
    import pandas as pd
    sample = pd.DataFrame([{
        'Mã KH': 'KH001', 'Tên khách hàng': 'Khách hàng mẫu',
        'Địa chỉ': '123 Đường XYZ', 'Điện thoại': '090-1234-567',
        'Email': 'kh@example.com', 'Mã số thuế': '0987654321',
    }])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sample.to_excel(writer, index=False, sheet_name='Khách hàng')
    output.seek(0)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='mau_import_khach_hang.xlsx')
