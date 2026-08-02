import io
import os
from datetime import datetime
import pandas as pd
from openpyxl.utils import get_column_letter
from flask import current_app
from app.database import db


def _auto_fit_columns(worksheet):
    for column in worksheet.columns:
        max_length = 0
        col_letter = get_column_letter(column[0].column)
        for cell in column:
            try:
                if cell.value:
                    cell_len = len(str(cell.value))
                    if cell_len > max_length:
                        max_length = cell_len
            except Exception:
                pass
        adjusted_width = min(max_length + 4, 50)
        worksheet.column_dimensions[col_letter].width = adjusted_width


class ExcelExporter:
    @staticmethod
    def export_products(products):
        data = []
        for p in products:
            data.append({
                'Mã hàng': p.code,
                'Tên hàng': p.name,
                'Đơn vị': p.unit,
                'Nhóm hàng': p.category or '',
                'Giá mua': float(p.purchase_price or 0),
                'Giá bán': float(p.sale_price or 0),
                'Thuế VAT (%)': float(p.vat_rate or 0),
                'Tồn tối thiểu': float(p.min_stock or 0),
                'Trạng thái': 'Hoạt động' if p.is_active else 'Ngừng',
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Hàng hóa', index=False)
            ws = writer.sheets['Hàng hóa']
            _auto_fit_columns(ws)
        output.seek(0)
        return output

    @staticmethod
    def export_suppliers(suppliers):
        data = []
        for s in suppliers:
            data.append({
                'Mã NCC': s.code,
                'Tên nhà cung cấp': s.name,
                'Địa chỉ': s.address or '',
                'Điện thoại': s.phone or '',
                'Email': s.email or '',
                'Mã số thuế': s.tax_code or '',
                'Người LH': s.contact_person or '',
                'Hạn TT (ngày)': s.payment_terms or 30,
                'Công nợ': s.get_total_debt(),
                'Trạng thái': 'Hoạt động' if s.is_active else 'Ngừng',
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Nhà cung cấp', index=False)
            _auto_fit_columns(writer.sheets['Nhà cung cấp'])
        output.seek(0)
        return output

    @staticmethod
    def export_customers(customers):
        data = []
        for c in customers:
            data.append({
                'Mã KH': c.code,
                'Tên khách hàng': c.name,
                'Loại KH': c.customer_type or '',
                'Địa chỉ': c.address or '',
                'Điện thoại': c.phone or '',
                'Email': c.email or '',
                'Mã số thuế': c.tax_code or '',
                'Hạn mức CN': float(c.credit_limit or 0),
                'Công nợ': c.get_total_debt(),
                'Trạng thái': 'Hoạt động' if c.is_active else 'Ngừng',
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Khách hàng', index=False)
            _auto_fit_columns(writer.sheets['Khách hàng'])
        output.seek(0)
        return output

    @staticmethod
    def export_inventory(inventory_data):
        data = []
        for row in inventory_data:
            data.append({
                'Mã hàng': row.code,
                'Tên hàng': row.name,
                'Đơn vị': row.unit,
                'Nhóm hàng': row.category or '',
                'Tồn kho': float(row.total_qty or 0),
                'Giá vốn BQ': float(row.avg_cost or 0),
                'Giá trị tồn': float(row.total_value or 0),
                'Tồn tối thiểu': float(row.min_stock or 0),
                'Cảnh báo': 'Thiếu hàng' if float(row.total_qty or 0) <= float(row.min_stock or 0) and float(row.min_stock or 0) > 0 else '',
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Tồn kho', index=False)
            _auto_fit_columns(writer.sheets['Tồn kho'])
        output.seek(0)
        return output

    @staticmethod
    def export_stock_in(stock_ins):
        from app.shared.formatting.currency import so_thanh_chu
        data = []
        for si in stock_ins:
            supplier_name = si.supplier.name if si.supplier else ''
            data.append({
                'Số phiếu': si.code,
                'Ngày nhập': si.date.strftime('%d/%m/%Y') if si.date else '',
                'Nhà cung cấp': supplier_name,
                'Số HĐ NCC': si.invoice_no or '',
                'Tiền hàng': float(si.subtotal or 0),
                'Tiền VAT': float(si.vat_amount or 0),
                'Tổng tiền': float(si.total_amount or 0),
                'Số tiền bằng chữ': so_thanh_chu(si.total_amount),
                'Đã TT': float(si.paid_amount or 0),
                'Còn lại': float(si.total_amount or 0) - float(si.paid_amount or 0),
                'Trạng thái': si.status,
                'Ghi chú': si.note or '',
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Phiếu nhập', index=False)
            _auto_fit_columns(writer.sheets['Phiếu nhập'])
        output.seek(0)
        return output

    @staticmethod
    def export_stock_out(stock_outs):
        from app.shared.formatting.currency import so_thanh_chu
        data = []
        for so in stock_outs:
            customer_name = so.customer.name if so.customer else ''
            data.append({
                'Số phiếu': so.code,
                'Ngày xuất': so.date.strftime('%d/%m/%Y') if so.date else '',
                'Khách hàng': customer_name,
                'Số HĐ': so.invoice_no or '',
                'Tiền hàng': float(so.subtotal or 0),
                'Tiền VAT': float(so.vat_amount or 0),
                'Tổng tiền': float(so.total_amount or 0),
                'Số tiền bằng chữ': so_thanh_chu(so.total_amount),
                'Đã TT': float(so.paid_amount or 0),
                'Còn lại': float(so.total_amount or 0) - float(so.paid_amount or 0),
                'Trạng thái': so.status,
                'Ghi chú': so.note or '',
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Phiếu xuất', index=False)
            _auto_fit_columns(writer.sheets['Phiếu xuất'])
        output.seek(0)
        return output

    @staticmethod
    def export_debts(debts, partner_type='customer'):
        from app.domains.master.models import Customer, Supplier
        data = []
        for d in debts:
            if d.partner_type == 'customer':
                partner = Customer.query.get(d.partner_id)
                partner_name = partner.name if partner else ''
            else:
                partner = Supplier.query.get(d.partner_id)
                partner_name = partner.name if partner else ''

            data.append({
                'Loại': 'Phải thu' if d.partner_type == 'customer' else 'Phải trả',
                'Đối tác': partner_name,
                'Số chứng từ': d.reference_code or '',
                'Ngày phát sinh': d.date.strftime('%d/%m/%Y') if d.date else '',
                'Ngày đến hạn': d.due_date.strftime('%d/%m/%Y') if d.due_date else '',
                'Số tiền': float(d.amount or 0),
                'Đã thanh toán': float(d.paid_amount or 0),
                'Còn lại': float(d.balance or 0),
                'Trạng thái': d.status,
                'Ghi chú': d.note or '',
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Công nợ', index=False)
            _auto_fit_columns(writer.sheets['Công nợ'])
        output.seek(0)
        return output

    @staticmethod
    def export_vat(vat_records, vat_type='output'):
        data = []
        for v in vat_records:
            data.append({
                'Loại': 'Đầu ra' if v.vat_type == 'output' else 'Đầu vào',
                'Ngày HĐ': v.date.strftime('%d/%m/%Y') if v.date else '',
                'Ký hiệu HĐ': v.invoice_series or '',
                'Số HĐ': v.invoice_no or '',
                'Tên đối tác': v.partner_name or '',
                'MST đối tác': v.partner_tax_code or '',
                'Tiền hàng': float(v.taxable_amount or 0),
                'Thuế suất (%)': float(v.vat_rate or 0),
                'Tiền thuế': float(v.vat_amount or 0),
                'Tổng tiền': float(v.total_amount or 0),
                'Kỳ khai thuế': f"{v.period_month or ''}/{v.period_year or ''}",
            })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet_name = 'VAT Đầu ra' if vat_type == 'output' else 'VAT Đầu vào'
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            _auto_fit_columns(writer.sheets[sheet_name])
        output.seek(0)
        return output

    @staticmethod
    def export_journal(entries):
        data = []
        for entry in entries:
            for line in entry.lines:
                data.append({
                    'Số bút toán': entry.code,
                    'Ngày': entry.date.strftime('%d/%m/%Y') if entry.date else '',
                    'Diễn giải': entry.description,
                    'Chứng từ gốc': entry.reference_code or '',
                    'Số TK': line.account.code if line.account else '',
                    'Tên TK': line.account.name if line.account else '',
                    'Diễn giải dòng': line.description or '',
                    'Nợ': float(line.debit or 0),
                    'Có': float(line.credit or 0),
                })
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Nhật ký chung', index=False)
            _auto_fit_columns(writer.sheets['Nhật ký chung'])
        output.seek(0)
        return output

    @staticmethod
    def export_health_check(checks, duplicate_rows=None, generated_at=None):
        rows = []
        for c in checks or []:
            rows.append({
                'Mã check': c.get('key', ''),
                'Nội dung': c.get('label', ''),
                'Số lỗi': int(c.get('count', 0) or 0),
                'Trạng thái': 'Có lỗi' if int(c.get('count', 0) or 0) > 0 else 'OK',
            })
        df = pd.DataFrame(rows)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet_name = 'Health Check'
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            ws = writer.sheets[sheet_name]
            _auto_fit_columns(ws)

            if duplicate_rows:
                dup_data = []
                for r in duplicate_rows:
                    dup_data.append({
                        'Reference Type': r.reference_type,
                        'Reference ID': r.reference_id,
                        'Số lượng': int(r.journal_count or 0),
                        'Journal Codes': r.journal_codes or '',
                    })
                df_dup = pd.DataFrame(dup_data)
                dup_sheet = 'Duplicate JE'
                df_dup.to_excel(writer, sheet_name=dup_sheet, index=False)
                _auto_fit_columns(writer.sheets[dup_sheet])
        output.seek(0)
        return output
