from __future__ import annotations

from typing import Dict, Iterable, Optional, Any

from app.domains.inventory.models import UnitConversion


def _fmt_qty(value: float, digits: int = 3) -> str:
    s = f"{float(value):,.{digits}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    if "," in s:
        s = s.rstrip("0").rstrip(",")
    return s


def build_conversion_map(product_ids: Iterable[int]) -> Dict[int, dict]:
    ids = [int(pid) for pid in product_ids if pid]
    if not ids:
        return {}

    rows = (
        UnitConversion.query
        .filter(UnitConversion.product_id.in_(ids))
        .all()
    )

    result: Dict[int, dict] = {}
    for row in rows:
        factor = float(row.conversion_factor or 0)
        if factor <= 0:
            continue

        ratio = factor if factor >= 1 else (1.0 / factor)
        current = result.get(row.product_id)
        # Prefer conversion with the strongest split ratio.
        if not current or ratio > float(current["ratio"]):
            if factor >= 1:
                # 1 from_unit = factor * to_unit(base)
                result[row.product_id] = {
                    "mode": "major_is_from",
                    "factor": factor,
                    "major_unit_name": row.from_unit.name if row.from_unit else "",
                    "minor_unit_name": row.to_unit.name if row.to_unit else "",
                    "ratio": ratio,
                }
            else:
                # 1 from_unit = factor * to_unit(base) with factor < 1
                # => 1 to_unit(base) = (1/factor) * from_unit
                result[row.product_id] = {
                    "mode": "major_is_base",
                    "factor": factor,
                    "major_unit_name": row.to_unit.name if row.to_unit else "",
                    "minor_unit_name": row.from_unit.name if row.from_unit else "",
                    "ratio": ratio,
                }
    return result


def format_multi_unit_qty(quantity_base: float, conv: Optional[dict], digits: int = 3) -> str:
    qty = float(quantity_base or 0)
    if abs(qty) < 1e-9:
        return "-"
    if not conv:
        return _fmt_qty(qty, digits)

    factor = float(conv.get("factor") or 0)
    mode = (conv.get("mode") or "").strip()
    major_unit = (conv.get("major_unit_name") or "").strip()
    minor_unit = (conv.get("minor_unit_name") or "").strip()

    if factor <= 0 or not major_unit or not minor_unit:
        return _fmt_qty(qty, digits)

    sign = "-" if qty < 0 else ""
    abs_qty = abs(qty)

    if mode == "major_is_from":
        # Base unit is minor, convert by division.
        major = int(abs_qty // factor)
        remainder = abs_qty - major * factor
        if abs(remainder) < 1e-9:
            remainder = 0.0
        minor_value = remainder
    elif mode == "major_is_base" and factor < 1:
        # Base unit is major, convert decimal part to minor.
        minors_per_major = 1.0 / factor
        major = int(abs_qty)
        remainder_base = abs_qty - major
        if abs(remainder_base) < 1e-9:
            remainder_base = 0.0
        minor_value = remainder_base * minors_per_major
        minor_value = round(minor_value, digits)
        # Handle carry due to rounding, e.g. 4.999 -> 5
        if minor_value >= minors_per_major - (10 ** (-digits)):
            major += 1
            minor_value = 0.0
    else:
        return _fmt_qty(qty, digits)

    parts = []
    if major > 0:
        parts.append(f"{major} {major_unit}")
    if minor_value > 0 or major == 0:
        parts.append(f"{_fmt_qty(minor_value, digits)} {minor_unit}")

    return f"{sign}{' '.join(parts)}"


def build_item_qty_display_map(items: Iterable[Any], digits: int = 3) -> Dict[int, str]:
    items_list = list(items or [])
    conv_map = build_conversion_map(
        [getattr(i, "product_id", None) for i in items_list]
    )
    result: Dict[int, str] = {}
    for item in items_list:
        item_id = getattr(item, "id", None)
        if item_id is None:
            continue
        qty = float(getattr(item, "quantity", 0) or 0)
        factor = float(getattr(item, "conversion_factor", 1) or 1)
        base_qty = qty * factor
        result[item_id] = format_multi_unit_qty(
            base_qty,
            conv_map.get(getattr(item, "product_id", None)),
            digits=digits,
        )
    return result
