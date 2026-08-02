from decimal import Decimal
from flask_babel import gettext as _
from flask import session
from datetime import datetime, date

# def number(value, digits=0):
#     if value is None:
#         return ""
#     format_str = "{:,.%df}" % digits
#     return format_str.format(value).replace(",", ".")


def number(value, decimals=3):
    try:
        num = Decimal(str(value))

        if num == num.to_integral():
            formatted = f"{int(num):,}"
        else:
            formatted = f"{num:,.{decimals}f}".rstrip("0").rstrip(".")

        return (
            formatted
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

    except Exception:
        return "-"


# def currency(value):
#     if value is None:
#         return ""
#     return "{:,.0f}".format(value).replace(",", ".") + " đ"

def currency(value):
    try:
        num = float(value or 0)

        # Ẩn số 0
        if num == 0:
            return "-"

        return "{:,.0f}".format(num).replace(",", ".") #+ " đ"

    except (ValueError, TypeError):
        return "-"


def currency_text(value):
    try:
        n = int(round(float(value or 0)))
    except Exception:
        return ""
    if n == 0:
        return "Không đồng"
    units = ["", " nghìn", " triệu", " tỷ", " nghìn tỷ", " triệu tỷ"]
    parts = []
    idx = 0
    while n > 0 and idx < len(units):
        chunk = n % 1000
        if chunk:
            parts.append(f"{chunk}{units[idx]}")
        n //= 1000
        idx += 1
    return " ".join(reversed(parts)) + " đồng"


def percent(value, digits=0):
    if value is None:
        return ""
    return f"{value:.{digits}f}%"


def qty_vn(value, digits=3):
    if value is None:
        return ""
    try:
        n = float(value)
    except Exception:
        return str(value)
    s = f"{n:,.{digits}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    if "," in s:
        s = s.rstrip("0").rstrip(",")
    return s


def dateformat(value, fmt='%d/%m/%Y'):
    if not value:
        return ''
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    return str(value)

def so_thanh_chu(so, don_vi='đồng'):
    """
    Chuyển số nguyên thành chữ tiếng Việt.
    Ví dụ: 18_000_000 → "Mười tám triệu đồng chẵn"
            1_250_500 → "Một triệu hai trăm năm mươi nghìn năm trăm đồng chẵn"
    """
    try:
        so = int(round(float(so or 0)))
    except Exception:
        return "Không đồng"

    if so == 0:
        return f"Không {don_vi} chẵn"
    if so < 0:
        return "Âm " + so_thanh_chu(-so, don_vi)

    _chu_so = ['không', 'một', 'hai', 'ba',
               'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín']

    def _doc_ba_chu_so(n, la_dau=False):
        """Đọc nhóm 3 chữ số (0–999)."""
        if n == 0:
            return ''
        tram = n // 100
        chuc = (n % 100) // 10
        dv = n % 10
        result = []

        if tram > 0:
            result.append(_chu_so[tram] + ' trăm')
        elif not la_dau:
            result.append('không trăm')

        if chuc == 0:
            if dv > 0:
                # Nhóm đầu tiên không cần "lẻ"
                if tram == 0 and la_dau:
                    result.append(_chu_so[dv])
                else:
                    result.append('lẻ ' + _chu_so[dv])
        elif chuc == 1:
            result.append('mười')
            if dv == 5:
                result.append('lăm')
            elif dv > 0:
                result.append(_chu_so[dv])
        else:
            result.append(_chu_so[chuc] + ' mươi')
            if dv == 1:
                result.append('mốt')
            elif dv == 5:
                result.append('lăm')
            elif dv > 0:
                result.append(_chu_so[dv])

        return ' '.join(result)

    # Phân tách theo nhóm tỷ / triệu / nghìn / đơn vị
    TY = 1_000_000_000
    TRIEU = 1_000_000
    NGHIN = 1_000

    parts = []

    if so >= TY:
        ty = so // TY
        parts.append(_doc_ba_chu_so(ty, la_dau=True) + ' tỷ')
        so %= TY

    if so >= TRIEU:
        trieu = so // TRIEU
        parts.append(_doc_ba_chu_so(
            trieu, la_dau=(len(parts) == 0)) + ' triệu')
        so %= TRIEU

    if so >= NGHIN:
        nghin = so // NGHIN
        parts.append(_doc_ba_chu_so(
            nghin, la_dau=(len(parts) == 0)) + ' nghìn')
        so %= NGHIN

    if so > 0:
        parts.append(_doc_ba_chu_so(so, la_dau=(len(parts) == 0)))

    chu = ' '.join(parts).strip()
    # Viết hoa chữ cái đầu
    chu = chu[0].upper() + chu[1:] if chu else 'Không'
    return f"{chu} {don_vi} chẵn."


def status_label(code):
    code = (code or '').strip().lower()
    lang = session.get('lang', 'vi') if session else 'vi'
    vi_mapping = {
        'draft': 'Nháp',
        'confirmed': 'Đã xác nhận',
        'cancelled': 'Đã hủy',
        'sent': 'Đã gửi',
        'accepted': 'Đã chấp nhận',
        'converted': 'Đã chuyển phiếu xuất',
        'open': 'Chưa thanh toán',
        'partial': 'Thanh toán một phần',
        'paid': 'Đã thanh toán',
    }
    en_mapping = {
        'draft': _('Draft'),
        'confirmed': _('Confirmed'),
        'cancelled': _('Cancelled'),
        'sent': _('Sent'),
        'accepted': _('Accepted'),
        'converted': _('Converted'),
        'open': _('Open'),
        'partial': _('Partial'),
        'paid': _('Paid'),
    }
    return vi_mapping.get(code, code) if lang == 'vi' else en_mapping.get(code, code)


def register_filters(app):
    app.jinja_env.filters.update({
        'number': number,
        'currency': currency,
        'currency_text': currency_text,
        'so_thanh_chu': so_thanh_chu,
        'status_label': status_label,
        'percent': percent,
        'qty_vn': qty_vn,
        'dateformat': dateformat
    })
