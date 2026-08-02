from datetime import datetime, date
from flask import (Blueprint, render_template, request, send_file, flash, redirect, url_for)
from flask_login import login_required
from sqlalchemy import func
from app.database import db
from app.domains.finance.models import VatRecord
from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.pdf_exporter import PdfExporter
from app.shared.authz import require_permission

vat_bp = Blueprint('vat', __name__, url_prefix='/vat')


@vat_bp.route('/')
@login_required
@require_permission('accounting', 'view')
def index():
    vat_type = request.args.get('vat_type', 'output')
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    page = request.args.get('page', 1, type=int)

    q = VatRecord.query.filter_by(vat_type=vat_type)
    if month:
        q = q.filter(VatRecord.period_month == month)
    if year:
        q = q.filter(VatRecord.period_year == year)

    records = q.order_by(VatRecord.date.desc()).paginate(page=page, per_page=30, error_out=False)

    # Summary
    total_taxable = db.session.query(func.sum(VatRecord.taxable_amount)).filter(
        VatRecord.vat_type == vat_type,
        VatRecord.period_month == month,
        VatRecord.period_year == year
    ).scalar() or 0

    total_vat = db.session.query(func.sum(VatRecord.vat_amount)).filter(
        VatRecord.vat_type == vat_type,
        VatRecord.period_month == month,
        VatRecord.period_year == year
    ).scalar() or 0

    total_amount = db.session.query(func.sum(VatRecord.total_amount)).filter(
        VatRecord.vat_type == vat_type,
        VatRecord.period_month == month,
        VatRecord.period_year == year
    ).scalar() or 0

    # VAT balance (output - input)
    vat_output = db.session.query(func.sum(VatRecord.vat_amount)).filter(
        VatRecord.vat_type == 'output',
        VatRecord.period_month == month,
        VatRecord.period_year == year
    ).scalar() or 0

    vat_input = db.session.query(func.sum(VatRecord.vat_amount)).filter(
        VatRecord.vat_type == 'input',
        VatRecord.period_month == month,
        VatRecord.period_year == year
    ).scalar() or 0

    years = list(range(date.today().year - 2, date.today().year + 2))

    return render_template('vat/index.html',
                           records=records, vat_type=vat_type,
                           month=month, year=year, years=years,
                           total_taxable=float(total_taxable),
                           total_vat=float(total_vat),
                           total_amount=float(total_amount),
                           vat_output=float(vat_output),
                           vat_input=float(vat_input),
                           vat_net=float(vat_output) - float(vat_input))


@vat_bp.route('/export/excel')
@login_required
@require_permission('accounting', 'export')
def export_excel():
    vat_type = request.args.get('vat_type', 'output')
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    records = VatRecord.query.filter_by(
        vat_type=vat_type, period_month=month, period_year=year
    ).order_by(VatRecord.date).all()
    output = ExcelExporter.export_vat(records, vat_type)
    label = 'vat_dau_ra' if vat_type == 'output' else 'vat_dau_vao'
    return send_file(output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True, download_name=f'{label}_{month:02d}{year}.xlsx')


@vat_bp.route('/export/pdf')
@login_required
@require_permission('accounting', 'export')
def export_pdf():
    vat_type = request.args.get('vat_type', 'output')
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    records = VatRecord.query.filter_by(
        vat_type=vat_type, period_month=month, period_year=year
    ).order_by(VatRecord.date).all()
    period = f"Thang {month:02d}/{year}"
    buffer = PdfExporter.export_vat_report(records, vat_type, period)
    label = 'bang_ke_ban_ra' if vat_type == 'output' else 'bang_ke_mua_vao'
    return send_file(buffer, mimetype='application/pdf', as_attachment=False,
                     download_name=f'{label}_{month:02d}{year}.pdf')
