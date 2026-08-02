"""ensure unit conversion menu

Replaces ``_ensure_unit_conversion_menu()``. Inserts the
``SETTINGS_UNIT_CONVERSIONS`` menu under the settings root and grants
roles idempotently.

Revision ID: 0005unitconv
Revises: 0004usermenu
"""
from alembic import op
import sqlalchemy as sa

revision = '0005unitconv'
down_revision = '0004usermenu'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        INSERT INTO menus (code, name, parent_id, url, icon, order_no, module, roles, is_active)
        VALUES (
            'SETTINGS_UNIT_CONVERSIONS',
            'Quy đổi đơn vị',
            (SELECT id FROM menus WHERE module='settings' AND parent_id IS NULL ORDER BY order_no LIMIT 1),
            '/settings/unit-conversions',
            'fas fa-ruler-combined',
            97,
            'settings',
            '',
            true
        )
        ON CONFLICT (code) DO NOTHING
    """))
    for role in ('admin', 'accountant', 'warehouse'):
        op.execute(sa.text(
            "INSERT INTO menu_roles (menu_id, role) "
            "SELECT id, :role FROM menus WHERE code='SETTINGS_UNIT_CONVERSIONS' "
            "ON CONFLICT DO NOTHING"
        ).bindparams(role=role))


def downgrade():
    op.execute(sa.text("DELETE FROM menus WHERE code='SETTINGS_UNIT_CONVERSIONS'"))
