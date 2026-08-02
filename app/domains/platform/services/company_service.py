# -*- coding: utf-8 -*-
"""
CompanyService - Nguon du lieu duy nhat (single source of truth) cho thong tin cong ty.
Doc/Ghi tu bang system_configs trong PostgreSQL.
"""

COMPANY_KEYS = {
    'company_name':         'ERPmini',
    'company_name_en':      'ERPmini Co., Ltd.',
    'company_address':      '123 Duong ABC, TP.HCM',
    'company_phone':        '028-1234-5678',
    'company_fax':          '',
    'company_email':        'info@erpmini.com',
    'company_website':      '',
    'company_tax_code':     '0312345678',
    'company_bank_account': '',
    'company_bank_name':    '',
    'company_bank_branch':  '',
    'company_director':     '',
    'company_accountant':   '',
    'default_vat_rate':     '10',
    'payment_terms_default':'30',
    'allow_negative_stock': 'true',
    'invoice_prefix_in':    'PN',
    'invoice_prefix_out':   'PX',
    'currency':             'VND',
}


def get_all_company_info():
    """Lay toan bo thong tin cong ty tu system_configs, fallback ve mac dinh."""
    try:
        from app.domains.platform.models import SystemConfig
        rows = SystemConfig.query.filter(
            SystemConfig.key.in_(COMPANY_KEYS.keys())
        ).all()
        result = dict(COMPANY_KEYS)
        for row in rows:
            if row.value is not None:
                result[row.key] = row.value
        return result
    except Exception:
        return dict(COMPANY_KEYS)


def get_company_value(key, default=''):
    """Lay 1 gia tri cu the tu system_configs."""
    try:
        from app.domains.platform.models import SystemConfig
        row = SystemConfig.query.filter_by(key=key).first()
        if row and row.value:
            return row.value
        return COMPANY_KEYS.get(key, default)
    except Exception:
        return COMPANY_KEYS.get(key, default)


def get_company_info_for_pdf():
    """Tra ve dict gon cho xuat PDF/Excel."""
    info = get_all_company_info()
    bank_str = info.get('company_bank_account', '')
    if info.get('company_bank_name'):
        bank_str += f" - {info['company_bank_name']}"
    if info.get('company_bank_branch'):
        bank_str += f" ({info['company_bank_branch']})"
    return {
        'name':       info.get('company_name', 'ERPmini'),
        'name_en':    info.get('company_name_en', ''),
        'address':    info.get('company_address', ''),
        'phone':      info.get('company_phone', ''),
        'fax':        info.get('company_fax', ''),
        'email':      info.get('company_email', ''),
        'website':    info.get('company_website', ''),
        'tax_code':   info.get('company_tax_code', ''),
        'bank':       bank_str,
        'director':   info.get('company_director', ''),
        'accountant': info.get('company_accountant', ''),
        'currency':   info.get('currency', 'VND'),
    }


def save_company_info(data):
    """Luu thong tin cong ty vao system_configs."""
    from app.database import db
    from app.domains.platform.models import SystemConfig

    group_map = {
        'company_name': 'company', 'company_name_en': 'company',
        'company_address': 'company', 'company_phone': 'company',
        'company_fax': 'company', 'company_email': 'company',
        'company_website': 'company', 'company_tax_code': 'company',
        'company_bank_account': 'company', 'company_bank_name': 'company',
        'company_bank_branch': 'company', 'company_director': 'company',
        'company_accountant': 'company',
        'default_vat_rate': 'accounting', 'payment_terms_default': 'accounting',
        'currency': 'accounting', 'allow_negative_stock': 'inventory',
        'invoice_prefix_in': 'system', 'invoice_prefix_out': 'system',
    }
    for key, value in data.items():
        if key not in COMPANY_KEYS:
            continue
        row = SystemConfig.query.filter_by(key=key).first()
        if row:
            row.value = value
        else:
            db.session.add(SystemConfig(
                key=key, value=value,
                description=key.replace('_', ' ').title(),
                group_name=group_map.get(key, 'general')
            ))
    db.session.commit()
