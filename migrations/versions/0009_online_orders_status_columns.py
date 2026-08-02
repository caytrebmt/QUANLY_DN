"""ensure online_orders status columns

Replaces ``_ensure_online_orders_status_columns()``. Adds the ERP
sync columns to ``online_orders`` idempotently.

Revision ID: 0009onlinecols
Revises: 0008ecommerce
"""
from alembic import op
import sqlalchemy as sa

revision = '0009onlinecols'
down_revision = '0008ecommerce'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        ALTER TABLE online_orders
        ADD COLUMN IF NOT EXISTS erp_status VARCHAR(20) NULL,
        ADD COLUMN IF NOT EXISTS erp_note TEXT NULL
    """))
    op.execute(sa.text(
        "COMMENT ON COLUMN online_orders.erp_status IS 'Trạng thái bản ghi xuất kho ERP'"
    ))
    op.execute(sa.text(
        "COMMENT ON COLUMN online_orders.erp_note IS 'Ghi chú cập nhật từ ERP'"
    ))


def downgrade():
    op.execute(sa.text(
        "ALTER TABLE online_orders DROP COLUMN IF EXISTS erp_status"
    ))
    op.execute(sa.text(
        "ALTER TABLE online_orders DROP COLUMN IF EXISTS erp_note"
    ))
