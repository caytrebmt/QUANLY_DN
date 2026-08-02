"""add tracking_token to online_orders

Allows guest order tracking via unguessable token instead of
sequential order code.

Revision ID: 0010tracking
Revises: 0009onlinecols
"""
from alembic import op
import sqlalchemy as sa

revision = '0010tracking'
down_revision = '0009onlinecols'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        ALTER TABLE online_orders
        ADD COLUMN IF NOT EXISTS tracking_token VARCHAR(64) NULL
    """))
    op.execute(sa.text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_online_orders_tracking_token "
        "ON online_orders (tracking_token)"
    ))
    op.execute(sa.text(
        "COMMENT ON COLUMN online_orders.tracking_token IS 'Token ngẫu nhiên để tra cứu đơn hàng cho khách vãng lai'"
    ))


def downgrade():
    op.execute(sa.text(
        "DROP INDEX IF EXISTS ix_online_orders_tracking_token"
    ))
    op.execute(sa.text(
        "ALTER TABLE online_orders DROP COLUMN IF EXISTS tracking_token"
    ))
