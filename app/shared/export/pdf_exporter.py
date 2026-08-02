import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from weasyprint import HTML
from flask import render_template, request
from app.shared.formatting.currency import format_currency, format_number, so_thanh_chu


def get_company_info():
    try:
        from app.domains.platform.services.company_service import get_company_info_for_pdf
        return get_company_info_for_pdf()
    except Exception:
        return {
            'name':     current_app.config.get('COMPANY_NAME', 'ERPmini'),
            'address':  current_app.config.get('COMPANY_ADDRESS', ''),
            'phone':    current_app.config.get('COMPANY_PHONE', ''),
            'fax':      current_app.config.get('COMPANY_FAX', ''),
            'tax_code': current_app.config.get('COMPANY_TAX_CODE', ''),
            'email':    current_app.config.get('COMPANY_EMAIL', ''),
            'website':  '', 'bank': '', 'director': '', 'accountant': '',
        }


class PdfExporter:
    FONT_NORMAL = 'Roboto-Italic'
    FONT_BOLD = 'Roboto-BoldItalic'
    _font_registered = False

    @staticmethod
    def _register_fonts():
        if PdfExporter._font_registered:
            return

        base_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.normpath(os.path.join(base_dir, '..', '..', '..'))
        root_dir = os.path.normpath(os.path.join(base_dir, '..', '..', '..', '..'))
        search_dirs = [
            os.path.join(app_dir,  'static', 'fonts'),
            os.path.join(root_dir, 'static', 'fonts'),
            os.path.join(base_dir, 'static', 'fonts'),
            os.path.join(app_dir,  'fonts'),
            os.path.join(root_dir, 'fonts'),
        ]
        win_fonts = os.path.join(os.environ.get(
            'WINDIR', 'C:\\Windows'), 'Fonts')
        search_dirs += [
            win_fonts,
            '/usr/share/fonts/truetype/dejavu',
            '/usr/share/fonts/dejavu',
            '/usr/share/fonts/truetype/msttcorefonts',
            '/Library/Fonts',
        ]

        font_candidates = [
            ('DejaVuSans.ttf',   'DejaVuSans-Bold.ttf',   'DejaVu',  'DejaVu-Bold'),
            ('arial.ttf',        'arialbd.ttf',            'Arial',   'Arial-Bold'),
            ('Roboto-Italic.ttf',        'Roboto-BoldItalic.ttf',
             'Roboto',   'Roboto-Bold'),
            ('times.ttf',        'timesbd.ttf',            'Times',   'Times-Bold'),
        ]

        for normal_file, bold_file, font_name, bold_name in font_candidates:
            for d in search_dirs:
                normal_path = os.path.join(d, normal_file)
                bold_path = os.path.join(d, bold_file)
                if os.path.exists(normal_path) and os.path.exists(bold_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, normal_path))
                        pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                        PdfExporter.FONT_NORMAL = font_name
                        PdfExporter.FONT_BOLD = bold_name
                        PdfExporter._font_registered = True
                        return
                    except Exception:
                        continue

        try:
            from reportlab.pdfbase.ttfonts import TTFont as _TTF
            import reportlab
            rl_dir = os.path.join(os.path.dirname(reportlab.__file__), 'fonts')
            deja = os.path.join(rl_dir, 'Vera.ttf')
            deja_b = os.path.join(rl_dir, 'VeraBd.ttf')
            if os.path.exists(deja) and os.path.exists(deja_b):
                pdfmetrics.registerFont(TTFont('Vera', deja))
                pdfmetrics.registerFont(TTFont('Vera-Bold', deja_b))
                PdfExporter.FONT_NORMAL = 'Vera'
                PdfExporter.FONT_BOLD = 'Vera-Bold'
                PdfExporter._font_registered = True
                return
        except Exception:
            pass

        import warnings
        warnings.warn(
            "Không tìm thấy font hỗ trợ tiếng Việt! "
            "Hãy đặt DejaVuSans.ttf và DejaVuSans-Bold.ttf vào static/fonts/",
            RuntimeWarning
        )
        PdfExporter.FONT_NORMAL = 'Roboto-Italic'
        PdfExporter.FONT_BOLD = 'Roboto-Bold'
        PdfExporter._font_registered = True

    @staticmethod
    def _get_base_styles():
        PdfExporter._register_fonts()
        styles = getSampleStyleSheet()
        if 'Normal' in styles:
            styles['Normal'].fontName = PdfExporter.FONT_NORMAL
        if 'BodyText' in styles:
            styles['BodyText'].fontName = PdfExporter.FONT_NORMAL
        styles.add(ParagraphStyle(
            name='CompanyName',
            fontName=PdfExporter.FONT_BOLD,
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=2,
        ))
        styles.add(ParagraphStyle(
            name='ReportTitle',
            fontName=PdfExporter.FONT_BOLD,
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name='SubTitle',
            fontName=PdfExporter.FONT_NORMAL,
            fontSize=9,
            alignment=TA_CENTER,
            spaceAfter=12,
        ))
        styles.add(ParagraphStyle(
            name='TableHeader',
            fontName=PdfExporter.FONT_BOLD,
            fontSize=8,
            alignment=TA_CENTER,
        ))
        styles.add(ParagraphStyle(
            name='CellText',
            fontName=PdfExporter.FONT_NORMAL,
            fontSize=8,
        ))
        return styles

    @staticmethod
    def _header_table_style():
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3a5c')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), PdfExporter.FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#f0f4f8')]),
            ('FONTNAME', (0, 1), (-1, -1), PdfExporter.FONT_NORMAL),
            ('FONTSIZE', (0, 1), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ])

    @staticmethod
    def export_stock_in_pdf(stock_in):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = PdfExporter._get_base_styles()
        company = get_company_info()
        elements = []

        elements.append(
            Paragraph(company['name'].upper(), styles['CompanyName']))
        elements.append(Paragraph(company['address'], styles['SubTitle']))
        elements.append(Paragraph(
            f"MST: {company['tax_code']} | Tel: {company['phone']}", styles['SubTitle']))
        elements.append(HRFlowable(width="100%", thickness=1,
                        color=colors.HexColor('#1a3a5c')))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("PHIẾU NHẬP KHO", styles['ReportTitle']))
        elements.append(Paragraph(
            f"Số phiếu: {stock_in.code} | Ngày: {stock_in.date.strftime('%d/%m/%Y') if stock_in.date else ''} | "
            f"Kho: {stock_in.warehouse.name if stock_in.warehouse else ''}",
            styles['SubTitle']
        ))

        supplier_name = stock_in.supplier.name if stock_in.supplier else 'Không có'
        elements.append(
            Paragraph(f"Nhà cung cấp: {supplier_name}", styles['Normal']))
        elements.append(
            Paragraph(f"Số HĐ NCC: {stock_in.invoice_no or ''}", styles['Normal']))
        elements.append(Spacer(1, 8))

        headers = ['STT', 'Mã hàng', 'Tên hàng', 'ĐVT', 'SL',
                   'Đơn giá', 'Thành tiền', 'VAT%', 'Tiền VAT', 'Tổng']
        col_widths = [1*cm, 2*cm, 5.5*cm, 1.5*cm,
                      1.5*cm, 2*cm, 2*cm, 1.2*cm, 2*cm, 2*cm]
        table_data = [headers]

        for idx, item in enumerate(stock_in.items, 1):
            table_data.append([
                str(idx),
                item.product.code if item.product else '',
                item.product.name if item.product else '',
                item.product.unit if item.product else '',
                format_number(item.quantity),
                format_currency(item.unit_price),
                format_currency(item.amount),
                f"{float(item.vat_rate or 0):.0f}%",
                format_currency(item.vat_amount),
                format_currency(item.total_amount),
            ])

        table_data.append(['', '', '', '', '', 'Tổng cộng:', format_currency(stock_in.subtotal),
                           '', format_currency(stock_in.vat_amount), format_currency(stock_in.total_amount)])

        t = Table(table_data, colWidths=col_widths)
        style = PdfExporter._header_table_style()
        style.add('SPAN', (5, -1), (5, -1))
        style.add('FONTNAME', (0, -1), (-1, -1), PdfExporter.FONT_BOLD)
        style.add('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe'))
        t.setStyle(style)
        elements.append(t)
        elements.append(Spacer(1, 6))

        so_chu = so_thanh_chu(stock_in.total_amount)
        elements.append(Paragraph(
            f"<i>Số tiền bằng chữ: <b>{so_chu}</b></i>",
            ParagraphStyle(
                'SoChuNK', fontName=PdfExporter.FONT_NORMAL, fontSize=9, leading=14)
        ))
        elements.append(Spacer(1, 12))

        sig_data = [
            ['Người lập phiếu', 'Thủ kho', 'Kế toán', 'Giám đốc'],
            ['', '', '', ''],
            ['', '', '', ''],
        ]
        sig_table = Table(sig_data, colWidths=[4*cm] * 4)
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), PdfExporter.FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, 2), 25),
        ]))
        elements.append(sig_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_stock_out_pdf(stock_out):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = PdfExporter._get_base_styles()
        company = get_company_info()
        elements = []

        elements.append(
            Paragraph(company['name'].upper(), styles['CompanyName']))
        elements.append(Paragraph(company['address'], styles['SubTitle']))
        elements.append(Paragraph(
            f"MST: {company['tax_code']} | Tel: {company['phone']}", styles['SubTitle']))
        elements.append(HRFlowable(width="100%", thickness=1,
                        color=colors.HexColor('#1a3a5c')))
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("PHIẾU XUẤT KHO", styles['ReportTitle']))
        elements.append(Paragraph(
            f"Số phiếu: {stock_out.code} | Ngày: {stock_out.date.strftime('%d/%m/%Y') if stock_out.date else ''} | "
            f"Kho: {stock_out.warehouse.name if stock_out.warehouse else ''}",
            styles['SubTitle']
        ))

        customer_name = stock_out.customer.name if stock_out.customer else ''
        customer_addr = stock_out.customer.address if stock_out.customer else ''
        customer_tax = stock_out.customer.tax_code if stock_out.customer else ''
        elements.append(
            Paragraph(f"Khách hàng: {customer_name}", styles['Normal']))
        elements.append(
            Paragraph(f"Địa chỉ: {customer_addr}", styles['Normal']))
        elements.append(Paragraph(f"MST: {customer_tax}", styles['Normal']))
        elements.append(Spacer(1, 8))

        headers = ['STT', 'Mã hàng', 'Tên hàng', 'ĐVT', 'SL',
                   'Đơn giá', 'Thành tiền', 'VAT%', 'Tiền VAT', 'Tổng']
        col_widths = [1*cm, 2*cm, 5.5*cm, 1.5*cm,
                      1.5*cm, 2*cm, 2*cm, 1.2*cm, 2*cm, 2*cm]
        table_data = [headers]

        for idx, item in enumerate(stock_out.items, 1):
            table_data.append([
                str(idx),
                item.product.code if item.product else '',
                item.product.name if item.product else '',
                item.product.unit if item.product else '',
                format_number(item.quantity),
                format_currency(item.unit_price),
                format_currency(item.amount),
                f"{float(item.vat_rate or 0):.0f}%",
                format_currency(item.vat_amount),
                format_currency(item.total_amount),
            ])

        table_data.append(['', '', '', '', '', 'Tổng cộng:',
                           format_currency(stock_out.subtotal), '',
                           format_currency(stock_out.vat_amount),
                           format_currency(stock_out.total_amount)])

        t = Table(table_data, colWidths=col_widths)
        style = PdfExporter._header_table_style()
        style.add('FONTNAME', (0, -1), (-1, -1), PdfExporter.FONT_BOLD)
        style.add('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe'))
        t.setStyle(style)
        elements.append(t)
        elements.append(Spacer(1, 6))

        so_chu = so_thanh_chu(stock_out.total_amount)
        elements.append(Paragraph(
            f"<i>Số tiền bằng chữ: <b>{so_chu}</b></i>",
            ParagraphStyle(
                'SoChuXK', fontName=PdfExporter.FONT_NORMAL, fontSize=9, leading=14)
        ))
        elements.append(Spacer(1, 12))

        sig_data = [
            ['Người mua hàng', 'Người giao hàng', 'Thủ kho', 'Kế toán'],
            ['', '', '', ''],
            ['', '', '', ''],
        ]
        sig_table = Table(sig_data, colWidths=[4*cm] * 4)
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), PdfExporter.FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, 2), 25),
        ]))
        elements.append(sig_table)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_inventory_report(inventory_data, title="BÁO CÁO TỒN KHO"):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = PdfExporter._get_base_styles()
        company = get_company_info()
        elements = []

        elements.append(
            Paragraph(company['name'].upper(), styles['CompanyName']))
        elements.append(Paragraph(title, styles['ReportTitle']))
        elements.append(Paragraph(
            f"Ngày in: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            styles['SubTitle']
        ))

        headers = ['STT', 'Mã hàng', 'Tên hàng', 'ĐVT', 'Nhóm',
                   'Tồn kho', 'Giá vốn BQ', 'Giá trị tồn', 'Ảnh báo']
        col_widths = [1*cm, 2.5*cm, 6*cm, 1.5*
                      cm, 3*cm, 2.5*cm, 3*cm, 3*cm, 3*cm]
        table_data = [headers]
        total_value = 0

        for idx, row in enumerate(inventory_data, 1):
            qty = float(row.total_qty or 0)
            avg_cost = float(row.avg_cost or 0)
            value = float(row.total_value or 0)
            total_value += value
            min_stock = float(row.min_stock or 0)
            warning = 'THIẾU HÀNG' if qty <= min_stock and min_stock > 0 else ''
            table_data.append([
                str(idx),
                row.code,
                row.name,
                row.unit,
                row.category or '',
                format_number(qty),
                format_currency(avg_cost),
                format_currency(value),
                warning,
            ])

        table_data.append(['', '', '', '', 'Tổng:', '', '',
                           format_currency(total_value), ''])

        t = Table(table_data, colWidths=col_widths)
        style = PdfExporter._header_table_style()
        style.add('FONTNAME', (0, -1), (-1, -1), PdfExporter.FONT_BOLD)
        style.add('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe'))
        style.add('TEXTCOLOR', (8, 1), (8, -2), colors.red)
        t.setStyle(style)
        elements.append(t)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_vat_report(vat_records, vat_type='output', period=None):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                                rightMargin=1.5*cm, leftMargin=1.5*cm,
                                topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = PdfExporter._get_base_styles()
        company = get_company_info()
        elements = []

        title = "BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HOÀNG HÓA, DỊCH VỤ BÁN RA" if vat_type == 'output' \
            else "BẢNG KÊ HÓA ĐƠN, CHỨNG TỪ HOÀNG HÓA, DỊCH VỤ MUA VÀO"

        elements.append(
            Paragraph(company['name'].upper(), styles['CompanyName']))
        elements.append(
            Paragraph(f"MST: {company['tax_code']}", styles['SubTitle']))
        elements.append(Paragraph(title, styles['ReportTitle']))
        if period:
            elements.append(
                Paragraph(f"Kỳ tính thuế: {period}", styles['SubTitle']))

        headers = ['STT', 'Ngày HĐ', 'Ký hiệu', 'Số HĐ', 'Tên đối tác',
                   'MST', 'Tiền hàng', 'Thuế suất', 'Tiền thuế', 'Tổng tiền']
        col_widths = [1*cm, 2*cm, 2*cm, 2.5*cm,
                      6*cm, 3*cm, 3*cm, 2*cm, 3*cm, 3*cm]
        table_data = [headers]
        total_taxable = 0
        total_vat = 0
        total_amount = 0

        for idx, v in enumerate(vat_records, 1):
            taxable = float(v.taxable_amount or 0)
            vat_amt = float(v.vat_amount or 0)
            total_amt = float(v.total_amount or 0)
            total_taxable += taxable
            total_vat += vat_amt
            total_amount += total_amt
            table_data.append([
                str(idx),
                v.date.strftime('%d/%m/%Y') if v.date else '',
                v.invoice_series or '',
                v.invoice_no or '',
                v.partner_name or '',
                v.partner_tax_code or '',
                format_currency(taxable),
                f"{float(v.vat_rate or 0):.0f}%",
                format_currency(vat_amt),
                format_currency(total_amt),
            ])

        table_data.append(['', '', '', '', '', 'Cộng:', format_currency(total_taxable), '',
                           format_currency(total_vat), format_currency(total_amount)])

        t = Table(table_data, colWidths=col_widths)
        style = PdfExporter._header_table_style()
        style.add('FONTNAME', (0, -1), (-1, -1), PdfExporter.FONT_BOLD)
        style.add('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe'))
        t.setStyle(style)
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_health_check(checks, duplicate_rows=None, generated_at=None):
        PdfExporter._register_fonts()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm
        )
        styles = PdfExporter._get_base_styles()
        company = get_company_info()
        elements = []

        elements.append(Paragraph(company.get(
            'name', 'ERPmini').upper(), styles['CompanyName']))
        elements.append(
            Paragraph("BAO CAO HEALTH CHECK KE TOAN", styles['ReportTitle']))
        if generated_at:
            elements.append(Paragraph(
                f"Thoi gian: {generated_at.strftime('%d/%m/%Y %H:%M:%S')}", styles['SubTitle']))
        elements.append(Spacer(1, 4 * mm))

        headers = ['Ma check', 'Noi dung', 'So loi', 'Trang thai']
        table_data = [headers]
        for c in checks or []:
            cnt = int(c.get('count', 0) or 0)
            table_data.append([
                c.get('key', ''),
                c.get('label', ''),
                str(cnt),
                'Co loi' if cnt > 0 else 'OK'
            ])
        t = Table(table_data, colWidths=[4.5*cm, 8.0*cm, 2.0*cm, 3.0*cm])
        style = PdfExporter._header_table_style()
        for idx, row in enumerate(table_data[1:], start=1):
            if row[3] == 'Co loi':
                style.add('TEXTCOLOR', (2, idx), (3, idx), colors.red)
            else:
                style.add('TEXTCOLOR', (2, idx), (3, idx), colors.green)
        t.setStyle(style)
        elements.append(t)

        if duplicate_rows:
            elements.append(Spacer(1, 6 * mm))
            elements.append(
                Paragraph("Chi tiet trung journal goc", styles['SubTitle']))
            dup_headers = ['Reference', 'Ref ID', 'So luong', 'Journal Codes']
            dup_data = [dup_headers]
            for r in duplicate_rows:
                dup_data.append([
                    str(r.reference_type),
                    str(r.reference_id),
                    str(int(r.journal_count or 0)),
                    str(r.journal_codes or ''),
                ])
            td = Table(dup_data, colWidths=[3.5*cm, 2.0*cm, 2.0*cm, 8.0*cm])
            dup_style = PdfExporter._header_table_style()
            dup_style.add('TEXTCOLOR', (2, 1), (2, -1), colors.red)
            td.setStyle(dup_style)
            elements.append(td)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_general_ledger(account, lines, opening_balance, closing_balance,
                              opening_debit, opening_credit, closing_debit, closing_credit,
                              normal_balance, start_date, end_date):
        PdfExporter._register_fonts()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm
        )
        styles = PdfExporter._get_base_styles()
        company = get_company_info()
        elements = []

        elements.append(
            Paragraph(company.get('name', 'ERPmini').upper(), styles['CompanyName']))
        elements.append(
            Paragraph("SO CAI TAI KHOAN KE TOAN", styles['ReportTitle']))
        elements.append(Paragraph(
            f"Tai khoan: {account.code} - {account.name if account else ''} | Tu {start_date.strftime('%d/%m/%Y')} den {end_date.strftime('%d/%m/%Y')}",
            styles['SubTitle']
        ))
        elements.append(Spacer(1, 4 * mm))

        info_data = [
            ['So du dau ky', format_currency(opening_debit) if opening_debit > 0 else '0',
             format_currency(opening_credit) if opening_credit > 0 else '0'],
            ['So du cuoi ky', format_currency(closing_debit) if closing_debit > 0 else '0',
             format_currency(closing_credit) if closing_credit > 0 else '0'],
        ]
        info_table = Table(info_data, colWidths=[4*cm, 4*cm, 4*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), PdfExporter.FONT_BOLD),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f4f8')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 4 * mm))

        headers = ['Ngay', 'Chung tu', 'Dien giai', 'No', 'Co', 'Du No', 'Du Co']
        col_widths = [2*cm, 2.5*cm, 7*cm, 2*cm, 2*cm, 2*cm, 2*cm]
        table_data = [headers]
        for line in lines:
            table_data.append([
                line['date'].strftime('%d/%m/%Y') if line.get('date') else '',
                line.get('entry_code', '') or '',
                line.get('description', '') or '',
                format_currency(line.get('debit', 0)) if line.get('debit') else '0',
                format_currency(line.get('credit', 0)) if line.get('credit') else '0',
                format_currency(line.get('running_debit_balance', 0)) if line.get('running_debit_balance') else '0',
                format_currency(line.get('running_credit_balance', 0)) if line.get('running_credit_balance') else '0',
            ])

        t = Table(table_data, colWidths=col_widths)
        t.setStyle(PdfExporter._header_table_style())
        elements.append(t)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def export_trial_balance(trial_data, month, year, from_date, to_date):
        PdfExporter._register_fonts()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            rightMargin=1.5*cm, leftMargin=1.5*cm,
            topMargin=1.5*cm, bottomMargin=1.5*cm
        )
        styles = PdfExporter._get_base_styles()
        company = get_company_info()
        elements = []

        elements.append(
            Paragraph(company.get('name', 'ERPmini').upper(), styles['CompanyName']))
        elements.append(
            Paragraph("BANG CAN DOI KE TOAN", styles['ReportTitle']))
        elements.append(Paragraph(
            f"Ky: Thang {month}/{year} ({from_date.strftime('%d/%m/%Y')} - {to_date.strftime('%d/%m/%Y')})",
            styles['SubTitle']
        ))
        elements.append(Spacer(1, 4 * mm))

        headers = ['So TK', 'Ten tai khoan', 'So du dau ky No', 'So du dau ky Co',
                   'Phat sinh No', 'Phat sinh Co', 'So du cuoi ky No', 'So du cuoi ky Co']
        col_widths = [2*cm, 6*cm, 3*cm, 3*cm, 3*cm, 3*cm, 3*cm, 3*cm]
        table_data = [headers]
        total_opening_debit = 0
        total_opening_credit = 0
        total_period_debit = 0
        total_period_credit = 0
        total_closing_debit = 0
        total_closing_credit = 0

        for row in trial_data:
            if not row.get('has_movement'):
                continue
            table_data.append([
                row['account_code'],
                row['account_name'],
                format_currency(row['opening_debit']) if row['opening_debit'] > 0 else '0',
                format_currency(row['opening_credit']) if row['opening_credit'] > 0 else '0',
                format_currency(row['period_debit']) if row['period_debit'] > 0 else '0',
                format_currency(row['period_credit']) if row['period_credit'] > 0 else '0',
                format_currency(row['closing_debit']) if row['closing_debit'] > 0 else '0',
                format_currency(row['closing_credit']) if row['closing_credit'] > 0 else '0',
            ])
            total_opening_debit += row['opening_debit']
            total_opening_credit += row['opening_credit']
            total_period_debit += row['period_debit']
            total_period_credit += row['period_credit']
            total_closing_debit += row['closing_debit']
            total_closing_credit += row['closing_credit']

        table_data.append([
            'Tong cong',
            '',
            format_currency(total_opening_debit),
            format_currency(total_opening_credit),
            format_currency(total_period_debit),
            format_currency(total_period_credit),
            format_currency(total_closing_debit),
            format_currency(total_closing_credit),
        ])

        t = Table(table_data, colWidths=col_widths)
        style = PdfExporter._header_table_style()
        style.add('FONTNAME', (0, -1), (-1, -1), PdfExporter.FONT_BOLD)
        style.add('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe'))
        t.setStyle(style)
        elements.append(t)

        doc.build(elements)
        buffer.seek(0)
        return buffer
