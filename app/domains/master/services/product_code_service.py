# -*- coding: utf-8 -*-
"""
product_code_service.py — Dịch vụ tạo mã hàng hóa

Tất cả logic tạo mã tự động nằm TẠI ĐÂY.
Các route chỉ cần gọi:
  from app.domains.master.services.product_code_service import (
      generate_product_code,
      get_or_create_product_by_name,
      next_sequential_code,
  )
"""

import re
import unicodedata
from app.database import db
from app.domains.master.models import Product, Unit


DEFAULT_CODE_PREFIX = "SP"

# ═══════════════════════════════════════════════════════════════
# TEXT UTILS
# ═══════════════════════════════════════════════════════════════


def normalize_text(text: str) -> str:
    if not text:
        return ''
    text = str(text).strip()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')

    text = text.replace('đ', 'd')
    text = text.replace('Đ', 'D')

    return text


def slug_code_from_name(name: str) -> str:
    """
    Ví dụ:
    Bìa Lỗ 500g -> BL500G
    Giấy Double A A4 70gsm -> GDAA470GSM
    Ống Nhựa PVC 90 -> ONPVC90
    """
    text = normalize_text(name)
    words = re.findall(r'[A-Za-z0-9]+', text)

    result = []

    for w in words:
        if not w:
            continue
        w_upper = w.upper()

        if (
            re.search(r'\d', w_upper)
            or len(w_upper) <= 2
            or w.upper() == w
        ):
            result.append(w_upper)
        else:
            result.append(w_upper[0])

    code = ''.join(result).strip()

    return code[:40] if code else DEFAULT_CODE_PREFIX


def generate_unique_code(
    base: str,
    max_length: int = 20
) -> str:
    base = (
        (base or DEFAULT_CODE_PREFIX)
        .strip()
        .upper()
    )

    base = re.sub(r'[^A-Z0-9]', '', base)

    if not base:
        base = DEFAULT_CODE_PREFIX

    base = base[:max_length]

    if not Product.query.filter_by(code=base).first():
        return base

    i = 1

    while True:
        suffix = f"{i:02d}"

        trimmed_base = base[:max_length - len(suffix)]

        new_code = f"{trimmed_base}{suffix}"

        if not Product.query.filter_by(code=new_code).first():
            return new_code

        i += 1


def generate_product_code(name: str = '', user_code: str = '') -> str:
    """
    Entry point chính để tạo mã hàng hóa.

    Logic:
        1. Nếu user nhập mã (user_code) → dùng mã đó, đảm bảo unique
        2. Nếu không nhập mã → tạo từ tên hàng, đảm bảo unique
        3. Nếu không có gì → dùng prefix mặc định 'SP'
    """
    if user_code and user_code.strip():
        return generate_unique_code(user_code.strip().upper())

    if name and name.strip():
        base = slug_code_from_name(name)
        return generate_unique_code(base)

    return generate_unique_code(DEFAULT_CODE_PREFIX)


def next_sequential_code(prefix: str = 'HH', width: int = 4) -> str:
    prefix = (prefix or 'HH').strip().upper()
    width = max(3, min(width, 8))

    candidates = Product.query.with_entities(Product.code).filter(
        Product.code.ilike(f'{prefix}%')
    ).all()

    max_num = 0
    pat = re.compile(rf'^{re.escape(prefix)}(\d+)$', re.IGNORECASE)
    for row in candidates:
        m = pat.match((row.code or '').strip())
        if m:
            try:
                max_num = max(max_num, int(m.group(1)))
            except Exception:
                continue

    return f"{prefix}{str(max_num + 1).zfill(width)}"


def find_product_by_name(name: str):
    if not name or not name.strip():
        return None

    target = normalize_text(name.strip())
    candidates = Product.query.filter_by(is_active=True).all()
    for p in candidates:
        if normalize_text(p.name) == target:
            return p
    return None


def get_or_create_product_by_name(name: str, created_by: int = None):
    n = (name or '').strip()
    if not n:
        return None

    extracted_code = None
    m = re.search(r'\b([A-Z0-9][A-Z0-9\-]{2,})$', n)
    if m:
        extracted_code = m.group(1).strip().upper()

    if extracted_code:
        p_by_code = Product.query.filter_by(code=extracted_code).first()
        if p_by_code:
            return p_by_code

    found = find_product_by_name(n)
    if found:
        return found

    if extracted_code:
        code = generate_unique_code(extracted_code)
    else:
        code = generate_product_code(name=n)

    unit_name = 'Cái'
    unit_id = None
    try:
        from app.domains.master.models import Unit
        unit = Unit.query.filter_by(name=unit_name).first()
        unit_id = unit.id if unit else None
    except Exception:
        pass

    p = Product(
        code=code,
        name=n,
        unit_id=unit_id,
        unit=unit_name,
        category_id=None,
        category='',
        purchase_price=0,
        sale_price=0,
        vat_rate=10,
        min_stock=0,
        allow_negative=True,
        is_active=True,
        created_by=created_by,
    )
    db.session.add(p)
    db.session.flush()
    return p
