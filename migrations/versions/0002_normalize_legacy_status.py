"""normalize legacy status values

Data migration: normalise free-text status values stored in legacy rows of
``stock_ins``, ``stock_outs`` and ``debts`` into the canonical enum-like codes
used by the application. Kept as an Alembic data migration (no raw SQL in app
code). Idempotent: only rows that differ from the canonical value are updated.

Revision ID: 0002normalize
Revises: 0001baseline
"""
from alembic import op
from sqlalchemy import text, inspect

revision = '0002normalize'
down_revision = '0001baseline'
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_context().bind
    if bind is None:
        return False
    return inspect(bind).has_table(table_name)


def _stock_ins_sql():
    return text(
        "UPDATE stock_ins SET status = "
        "CASE "
        "WHEN status IS NULL OR btrim(status) = '' THEN 'draft' "
        "WHEN lower(status) IN ('draft', 'nháp', 'nhap moi') THEN 'draft' "
        "WHEN lower(status) IN ('confirmed', 'xác nhận', 'xac nhan', 'đã xác nhận', 'da xac nhan', 'nhập', 'nhap') THEN 'confirmed' "
        "WHEN lower(status) IN ('cancelled', 'cancel', 'đã hủy', 'da huy', 'hủy', 'huy') THEN 'cancelled' "
        "ELSE lower(status) END "
        "WHERE status IS NULL OR status <> "
        "CASE "
        "WHEN status IS NULL OR btrim(status) = '' THEN 'draft' "
        "WHEN lower(status) IN ('draft', 'nháp', 'nhap moi') THEN 'draft' "
        "WHEN lower(status) IN ('confirmed', 'xác nhận', 'xac nhan', 'đã xác nhận', 'da xac nhan', 'nhập', 'nhap') THEN 'confirmed' "
        "WHEN lower(status) IN ('cancelled', 'cancel', 'đã hủy', 'da huy', 'hủy', 'huy') THEN 'cancelled' "
        "ELSE lower(status) END"
    )


def _stock_outs_sql():
    return text(
        "UPDATE stock_outs SET status = "
        "CASE "
        "WHEN status IS NULL OR btrim(status) = '' THEN 'draft' "
        "WHEN lower(status) IN ('draft', 'nháp', 'nhap moi') THEN 'draft' "
        "WHEN lower(status) IN ('confirmed', 'xác nhận', 'xac nhan', 'đã xác nhận', 'da xac nhan', 'xuất', 'xuat') THEN 'confirmed' "
        "WHEN lower(status) IN ('cancelled', 'cancel', 'đã hủy', 'da huy', 'hủy', 'huy') THEN 'cancelled' "
        "ELSE lower(status) END "
        "WHERE status IS NULL OR status <> "
        "CASE "
        "WHEN status IS NULL OR btrim(status) = '' THEN 'draft' "
        "WHEN lower(status) IN ('draft', 'nháp', 'nhap moi') THEN 'draft' "
        "WHEN lower(status) IN ('confirmed', 'xác nhận', 'xac nhan', 'đã xác nhận', 'da xac nhan', 'xuất', 'xuat') THEN 'confirmed' "
        "WHEN lower(status) IN ('cancelled', 'cancel', 'đã hủy', 'da huy', 'hủy', 'huy') THEN 'cancelled' "
        "ELSE lower(status) END"
    )


def _debts_sql():
    return text(
        "UPDATE debts SET status = "
        "CASE "
        "WHEN status IS NULL OR btrim(status) = '' THEN 'open' "
        "WHEN lower(status) IN ('open', 'phải thu', 'phai thu', 'phải trả', 'phai tra', 'mở', 'mo') THEN 'open' "
        "WHEN lower(status) IN ('một phần', 'mot phan', 'partial') THEN 'partial' "
        "WHEN lower(status) IN ('đã thanh toán', 'da thanh toan', 'paid') THEN 'paid' "
        "WHEN lower(status) IN ('quá hạn', 'qua han', 'overdue') THEN 'overdue' "
        "ELSE lower(status) END "
        "WHERE status IS NULL OR status <> "
        "CASE "
        "WHEN status IS NULL OR btrim(status) = '' THEN 'open' "
        "WHEN lower(status) IN ('open', 'phải thu', 'phai thu', 'phải trả', 'phai tra', 'mở', 'mo') THEN 'open' "
        "WHEN lower(status) IN ('một phần', 'mot phan', 'partial') THEN 'partial' "
        "WHEN lower(status) IN ('đã thanh toán', 'da thanh toan', 'paid') THEN 'paid' "
        "WHEN lower(status) IN ('quá hạn', 'qua han', 'overdue') THEN 'overdue' "
        "ELSE lower(status) END"
    )


def upgrade():
    if _table_exists('stock_ins'):
        op.execute(_stock_ins_sql())
    if _table_exists('stock_outs'):
        op.execute(_stock_outs_sql())
    if _table_exists('debts'):
        op.execute(_debts_sql())


def downgrade():
    pass
