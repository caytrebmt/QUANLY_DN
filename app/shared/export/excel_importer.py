import pandas as pd
from app.database import db


class ExcelImporter:
    @staticmethod
    def import_products(file_data):
        from app.domains.master.models import Product
        df = pd.read_excel(file_data, sheet_name=0)
        required_cols = ['Mã hàng', 'Tên hàng', 'Đơn vị']
        errors = []
        imported = 0
        updated = 0

        for col in required_cols:
            if col not in df.columns:
                return 0, 0, [f"Thiếu cột bắt buộc: {col}"]

        for idx, row in df.iterrows():
            try:
                code = str(row.get('Mã hàng', '')).strip()
                name = str(row.get('Tên hàng', '')).strip()
                unit = str(row.get('Đơn vị', 'Cái')).strip()
                if not code or not name:
                    continue

                p = Product.query.filter_by(code=code).first()
                if p:
                    p.name = name
                    p.unit = unit
                    p.category = str(row.get('Nhóm hàng', '') or '').strip()
                    p.purchase_price = float(row.get('Giá mua', 0) or 0)
                    p.sale_price = float(row.get('Giá bán', 0) or 0)
                    p.vat_rate = float(row.get('Thuế VAT (%)', 10) or 10)
                    updated += 1
                else:
                    p = Product(
                        code=code,
                        name=name,
                        unit=unit,
                        category=str(row.get('Nhóm hàng', '') or '').strip(),
                        purchase_price=float(row.get('Giá mua', 0) or 0),
                        sale_price=float(row.get('Giá bán', 0) or 0),
                        vat_rate=float(row.get('Thuế VAT (%)', 10) or 10),
                    )
                    db.session.add(p)
                    imported += 1
            except Exception as e:
                errors.append(f"Dòng {idx + 2}: {str(e)}")

        db.session.commit()
        return imported, updated, errors

    @staticmethod
    def import_customers(file_data):
        from app.domains.master.models import Customer
        df = pd.read_excel(file_data, sheet_name=0)
        errors = []
        imported = 0
        updated = 0

        for idx, row in df.iterrows():
            try:
                code = str(row.get('Mã KH', '')).strip()
                name = str(row.get('Tên khách hàng', '')).strip()
                if not code or not name:
                    continue

                c = Customer.query.filter_by(code=code).first()
                if c:
                    c.name = name
                    c.phone = str(row.get('Điện thoại', '') or '').strip()
                    c.email = str(row.get('Email', '') or '').strip()
                    c.address = str(row.get('Địa chỉ', '') or '').strip()
                    c.tax_code = str(row.get('Mã số thuế', '') or '').strip()
                    updated += 1
                else:
                    c = Customer(
                        code=code,
                        name=name,
                        phone=str(row.get('Điện thoại', '') or '').strip(),
                        email=str(row.get('Email', '') or '').strip(),
                        address=str(row.get('Địa chỉ', '') or '').strip(),
                        tax_code=str(row.get('Mã số thuế', '') or '').strip(),
                    )
                    db.session.add(c)
                    imported += 1
            except Exception as e:
                errors.append(f"Dòng {idx + 2}: {str(e)}")

        db.session.commit()
        return imported, updated, errors

    @staticmethod
    def import_suppliers(file_data):
        from app.domains.master.models import Supplier
        df = pd.read_excel(file_data, sheet_name=0)
        errors = []
        imported = 0
        updated = 0

        for idx, row in df.iterrows():
            try:
                code = str(row.get('Mã NCC', '')).strip()
                name = str(row.get('Tên nhà cung cấp', '')).strip()
                if not code or not name:
                    continue

                s = Supplier.query.filter_by(code=code).first()
                if s:
                    s.name = name
                    s.phone = str(row.get('Điện thoại', '') or '').strip()
                    s.email = str(row.get('Email', '') or '').strip()
                    s.address = str(row.get('Địa chỉ', '') or '').strip()
                    s.tax_code = str(row.get('Mã số thuế', '') or '').strip()
                    updated += 1
                else:
                    s = Supplier(
                        code=code,
                        name=name,
                        phone=str(row.get('Điện thoại', '') or '').strip(),
                        email=str(row.get('Email', '') or '').strip(),
                        address=str(row.get('Địa chỉ', '') or '').strip(),
                        tax_code=str(row.get('Mã số thuế', '') or '').strip(),
                    )
                    db.session.add(s)
                    imported += 1
            except Exception as e:
                errors.append(f"Dòng {idx + 2}: {str(e)}")

        db.session.commit()
        return imported, updated, errors
