"""ensure tt99 sidebar group

Replaces ``_ensure_tt99_sidebar_group()``. Creates the accounting
"Ban cáo" group plus its three children, grants admin/accountant roles,
and deactivates the legacy balance-sheet child. Idempotent.

Revision ID: 0006tt99group
Revises: 0005unitconv
"""
from alembic import op
import sqlalchemy as sa

revision = '0006tt99group'
down_revision = '0005unitconv'
branch_labels = None
depends_on = None

_ENTRIES = [
    ('ACCOUNTING_TT99_GROUP', 'Báo cáo', '/accounting/balance-sheet',
     'fas fa-file-invoice-dollar', 65),
    ('ACCOUNTING_TT99_INCOME_STATEMENT', 'Báo cáo KQKD',
     '/accounting/income-statement', 'fas fa-chart-line', 67),
    ('ACCOUNTING_TT99_GENERAL_LEDGER', 'Sổ cái (TK 156)',
     '/accounting/general-ledger/156', 'fas fa-book', 68),
    ('ACCOUNTING_TT99_DETAIL_LEDGER', 'Sổ chi tiết (TK 131)',
     '/accounting/detail-ledger/131', 'fas fa-list-alt', 69),
]


def upgrade():
    for code, name, url, icon, order_no in _ENTRIES:
        op.execute(sa.text(
            "INSERT INTO menus (code, name, parent_id, url, icon, order_no, module, roles, is_active) "
            "VALUES (:code, :name, "
            "(SELECT id FROM menus WHERE module='accounting' AND parent_id IS NULL ORDER BY order_no LIMIT 1), "
            ":url, :icon, :order_no, 'accounting', '', true) "
            "ON CONFLICT (code) DO NOTHING"
        ).bindparams(code=code, name=name, url=url, icon=icon, order_no=order_no))

    op.execute(sa.text(
        "UPDATE menus SET is_active=false WHERE code='ACCOUNTING_TT99_BALANCE_SHEET'"
    ))

    for code, _name, _url, _icon, _order in _ENTRIES:
        for role in ('admin', 'accountant'):
            op.execute(sa.text(
                "INSERT INTO menu_roles (menu_id, role) "
                "SELECT id, :role FROM menus WHERE code=:code "
                "ON CONFLICT DO NOTHING"
            ).bindparams(role=role, code=code))


def downgrade():
    for code, _name, _url, _icon, _order in _ENTRIES:
        op.execute(sa.text("DELETE FROM menus WHERE code=:code").bindparams(code=code))
