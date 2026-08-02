from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from app.database import db
from app.domains.platform.models import SystemConfig
from app.domains.platform.services.company_service import get_all_company_info, save_company_info, COMPANY_KEYS
from app.shared.authz import require_permission

company_bp = Blueprint('company', __name__, url_prefix='/company')


def get_config(key, default=''):
    c = SystemConfig.query.filter_by(key=key).first()
    return c.value if c else default


def set_config(key, value, description='', group='company'):
    c = SystemConfig.query.filter_by(key=key).first()
    if c:
        c.value = value
    else:
        db.session.add(SystemConfig(key=key, value=value,
                                    description=description, group_name=group))


@company_bp.route('/', methods=['GET', 'POST'])
@login_required
@require_permission('settings', 'edit')
def index():
    if request.method == 'POST':
        fields = [
            ('company_name', 'Tên công ty', 'company'),
            ('company_name_en', 'Tên tiếng Anh', 'company'),
            ('company_address', 'Địa chỉ', 'company'),
            ('company_phone', 'Điện thoại', 'company'),
            ('company_fax', 'Fax', 'company'),
            ('company_email', 'Email', 'company'),
            ('company_website', 'Website', 'company'),
            ('company_tax_code', 'Mã số thuế', 'company'),
            ('company_bank_account', 'Số tài khoản', 'company'),
            ('company_bank_name', 'Tên ngân hàng', 'company'),
            ('company_bank_branch', 'Chi nhánh NH', 'company'),
            ('company_director', 'Giám đốc', 'company'),
            ('company_accountant', 'Kế toán trưởng', 'company'),
            ('default_vat_rate', 'Thuế VAT mặc định %', 'accounting'),
            ('payment_terms_default', 'Hạn TT mặc định (ngày)', 'accounting'),
            ('allow_negative_stock', 'Cho phép xuất âm kho', 'inventory'),
            ('invoice_prefix_in', 'Tiền tố số phiếu nhập', 'system'),
            ('invoice_prefix_out', 'Tiền tố số phiếu xuất', 'system'),
            ('currency', 'Đơn vị tiền tệ', 'accounting'),
        ]
        for key, desc, grp in fields:
            val = request.form.get(key, '').strip()
            set_config(key, val, desc, grp)
        db.session.commit()
        flash('Lưu thông tin công ty thành công!', 'success')
        return redirect(url_for('company.index'))

    cfg = {
        'company_name': get_config('company_name'),
        'company_name_en': get_config('company_name_en'),
        'company_address': get_config('company_address'),
        'company_phone': get_config('company_phone'),
        'company_fax': get_config('company_fax'),
        'company_email': get_config('company_email'),
        'company_website': get_config('company_website'),
        'company_tax_code': get_config('company_tax_code'),
        'company_bank_account': get_config('company_bank_account'),
        'company_bank_name': get_config('company_bank_name'),
        'company_bank_branch': get_config('company_bank_branch'),
        'company_director': get_config('company_director'),
        'company_accountant': get_config('company_accountant'),
        'default_vat_rate': get_config('default_vat_rate', '10'),
        'payment_terms_default': get_config('payment_terms_default', '30'),
        'allow_negative_stock': get_config('allow_negative_stock', 'true'),
        'invoice_prefix_in': get_config('invoice_prefix_in', 'PN'),
        'invoice_prefix_out': get_config('invoice_prefix_out', 'PX'),
        'currency': get_config('currency', 'VND'),
    }
    return render_template('settings/company.html', cfg=cfg)
