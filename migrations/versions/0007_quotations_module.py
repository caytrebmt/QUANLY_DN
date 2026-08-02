"""ensure quotations module

Replaces ``_ensure_quotations_module()``. Creates the ``quotations`` and
``quotation_items`` tables and the ``SALES_QUOTATIONS`` menu.

Revision ID: 0007quotations
Revises: 0006tt99group
"""
from alembic import op
import sqlalchemy as sa

revision = '0007quotations'
down_revision = '0006tt99group'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS quotations (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            date DATE NOT NULL,
            valid_until DATE NULL,
            customer_id INTEGER NULL REFERENCES customers(id),
            recipient_name VARCHAR(200) NULL,
            recipient_address VARCHAR(300) NULL,
            recipient_phone VARCHAR(50) NULL,
            recipient_email VARCHAR(120) NULL,
            subtotal NUMERIC(18,2) DEFAULT 0,
            discount_amount NUMERIC(18,2) DEFAULT 0,
            vat_amount NUMERIC(18,2) DEFAULT 0,
            total_amount NUMERIC(18,2) DEFAULT 0,
            vat_mode VARCHAR(20) DEFAULT 'grouped',
            vat_rate_grouped NUMERIC(5,2) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'draft',
            note TEXT NULL,
            terms TEXT NULL,
            stock_out_id INTEGER NULL REFERENCES stock_outs(id),
            created_by INTEGER NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS quotation_items (
            id SERIAL PRIMARY KEY,
            quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id),
            unit_id INTEGER NULL REFERENCES units(id),
            conversion_factor NUMERIC(12,4) DEFAULT 1,
            quantity NUMERIC(18,3) NOT NULL,
            unit_price NUMERIC(18,2) NOT NULL,
            vat_rate NUMERIC(5,2) DEFAULT 10,
            vat_amount NUMERIC(18,2) DEFAULT 0,
            amount NUMERIC(18,2) DEFAULT 0,
            total_amount NUMERIC(18,2) DEFAULT 0,
            note VARCHAR(200) NULL
        )
    """))
    op.execute(sa.text("""
        INSERT INTO menus (code, name, parent_id, url, icon, order_no, module, roles, is_active)
        VALUES (
            'SALES_QUOTATIONS',
            'Bảng báo giá',
            COALESCE(
                (SELECT id FROM menus WHERE module='stock_out' AND parent_id IS NULL ORDER BY order_no LIMIT 1),
                (SELECT id FROM menus WHERE name ILIKE '%Ban hang%' AND parent_id IS NULL ORDER BY order_no LIMIT 1)
            ),
            '/quotations',
            'fas fa-file-signature',
            54,
            'quotations',
            '',
            true
        )
        ON CONFLICT (code) DO NOTHING
    """))
    for role in ('admin', 'accountant', 'warehouse'):
        op.execute(sa.text(
            "INSERT INTO menu_roles (menu_id, role) "
            "SELECT id, :role FROM menus WHERE code='SALES_QUOTATIONS' "
            "ON CONFLICT DO NOTHING"
        ).bindparams(role=role))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS quotation_items"))
    op.execute(sa.text("DROP TABLE IF EXISTS quotations"))
    op.execute(sa.text("DELETE FROM menus WHERE code='SALES_QUOTATIONS'"))
