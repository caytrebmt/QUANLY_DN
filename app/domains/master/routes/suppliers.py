from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, send_file)
from flask_login import login_required
from app.database import db
from app.domains.master.models import Supplier
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.excel_importer import ExcelImporter
from app.shared.authz import require_permission
import io

suppliers_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')


@suppliers_bp.route('/')
@login_required
@require_permission('suppliers', 'view')
def index():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    q = Supplier.query
    if search:
        q = q.filter(
            db.or_(Supplier.code.ilike(f'%{search}%'),
                   Supplier.name.ilike(f'%{search}%'),
                   Supplier.phone.ilike(f'%{search}%'),
                   Supplier.tax_code.ilike(f'%{search}%'))
        )
    q = q.order_by(Supplier.code)
    suppliers = q.paginate(page=page, per_page=20, error_out=False)
    return render_template('suppliers/index.html', suppliers=suppliers, search=search)


@suppliers_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('suppliers', 'create')
def create():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        if not code or not name:
            flash('Mã NCC và tên không được để trống!', 'danger')
            return render_template('suppliers/form.html', supplier=None)
        if Supplier.query.filter_by(code=code).first():
            flash(f'Mã NCC {code} đã tồn tại!', 'danger')
            return render_template('suppliers/form.html', supplier=None)
        s = Supplier(
            code=code, name=name,
            short_name=request.form.get('short_name', '').strip(),
            address=request.form.get('address', '').strip(),
            phone=request.form.get('phone', '').strip(),
            fax=request.form.get('fax', '').strip(),
            email=request.form.get('email', '').strip(),
            website=request.form.get('website', '').strip(),
            tax_code=request.form.get('tax_code', '').strip(),
            contact_person=request.form.get('contact_person', '').strip(),
            bank_account=request.form.get('bank_account', '').strip(),
            bank_name=request.form.get('bank_name', '').strip(),
            payment_terms=int(request.form.get('payment_terms', 30) or 30),
            credit_limit=float(request.form.get('credit_limit', 0) or 0),
            note=request.form.get('note', '').strip(),
        )
        db.session.add(s)
        db.session.commit()
        flash(f'Thêm nhà cung cấp {code} thành công!', 'success')
        return redirect(url_for('suppliers.index'))
    return render_template('suppliers/form.html', supplier=None)


@suppliers_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('suppliers', 'edit')
def edit(id):
    s = Supplier.query.get_or_404(id)
    if request.method == 'POST':
        s.name = request.form.get('name', '').strip()
        s.short_name = request.form.get('short_name', '').strip()
        s.address = request.form.get('address', '').strip()
        s.phone = request.form.get('phone', '').strip()
        s.fax = request.form.get('fax', '').strip()
        s.email = request.form.get('email', '').strip()
        s.website = request.form.get('website', '').strip()
        s.tax_code = request.form.get('tax_code', '').strip()
        s.contact_person = request.form.get('contact_person', '').strip()
        s.bank_account = request.form.get('bank_account', '').strip()
        s.bank_name = request.form.get('bank_name', '').strip()
        s.payment_terms = int(request.form.get('payment_terms', 30) or 30)
        s.credit_limit = float(request.form.get('credit_limit', 0) or 0)
        s.note = request.form.get('note', '').strip()
        s.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash(f'Cập nhật nhà cung cấp {s.code} thành công!', 'success')
        return redirect(url_for('suppliers.index'))
    return render_template('suppliers/form.html', supplier=s)


@suppliers_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('suppliers', 'delete')
def delete(id):
    s = Supplier.query.get_or_404(id)
    from app.domains.inventory.models import StockIn
    if db.session.query(StockIn).filter_by(supplier_id=s.id).count() > 0:
        s.is_active = False
        db.session.commit()
        flash(f'NCC {s.code} đã được vô hiệu hóa (có giao dịch liên quan).', 'warning')
    else:
        db.session.delete(s)
        db.session.commit()
        flash(f'Xóa nhà cung cấp {s.code} thành công!', 'success')
    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/export/excel')
@login_required
@require_permission('suppliers', 'export')
def export_excel():
    suppliers = Supplier.query.order_by(Supplier.code).all()
    output = ExcelExporter.export_suppliers(suppliers)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='nha_cung_cap.xlsx')


@suppliers_bp.route('/import/excel', methods=['POST'])
@login_required
@require_permission('suppliers', 'create')
def import_excel():
    if 'file' not in request.files:
        flash('Vui lòng chọn file!', 'danger')
        return redirect(url_for('suppliers.index'))
    file = request.files['file']
    imported, updated, errors = ExcelImporter.import_suppliers(file)
    flash(f'Import thành công: {imported} mới, {updated} cập nhật.', 'success')
    for err in errors[:5]:
        flash(f'Lỗi: {err}', 'warning')
    return redirect(url_for('suppliers.index'))


@suppliers_bp.route('/template/excel')
@login_required
@require_permission('suppliers', 'view')
def download_template():
    import pandas as pd
    sample = pd.DataFrame([{
        'Mã NCC': 'NCC001', 'Tên nhà cung cấp': 'Công ty mẫu',
        'Địa chỉ': '123 Đường ABC', 'Điện thoại': '028-1234-5678',
        'Email': 'ncc@example.com', 'Mã số thuế': '0123456789',
    }])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sample.to_excel(writer, index=False, sheet_name='Nhà cung cấp')
    output.seek(0)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='mau_import_nha_cung_cap.xlsx')
