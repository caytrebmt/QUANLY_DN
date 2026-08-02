def format_currency(value):
    try:
        num = float(value or 0)
        if num == 0:
            return "-"
        return f"{num:,.0f}"
    except (ValueError, TypeError):
        return "-"


def format_number(value, decimals=3):
    try:
        num = float(value or 0)
        if num.is_integer():
            formatted = f"{int(num):,}"
        else:
            formatted = f"{num:,.{decimals}f}".rstrip("0").rstrip(".")
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "-"


def so_thanh_chu(so, don_vi='đồng'):
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
    chu = chu[0].upper() + chu[1:] if chu else 'Không'
    return f"{chu} {don_vi} chẵn"
