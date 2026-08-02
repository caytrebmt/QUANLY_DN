"""add stocktaking tables

Creates ``stocktakings`` and ``stocktaking_items`` tables for
physical inventory count feature.

Revision ID: 0010stocktaking
Revises: 0009onlinecols
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = '0010stocktaking'
down_revision = '0009onlinecols'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(text("""
        CREATE TABLE IF NOT EXISTS stocktakings (
            id SERIAL PRIMARY KEY,
            warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
            count_date DATE NOT NULL DEFAULT CURRENT_DATE,
            status VARCHAR(20) DEFAULT 'draft',
            note TEXT NULL,
            created_by INTEGER NULL REFERENCES users(id),
            completed_by INTEGER NULL REFERENCES users(id),
            completed_at TIMESTAMP NULL,
            cancelled_by INTEGER NULL REFERENCES users(id),
            cancelled_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))

    op.execute(text("""
        CREATE TABLE IF NOT EXISTS stocktaking_items (
            id SERIAL PRIMARY KEY,
            stocktaking_id INTEGER NOT NULL REFERENCES stocktakings(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES products(id),
            book_quantity NUMERIC(18,3) DEFAULT 0,
            actual_quantity NUMERIC(18,3) NULL,
            difference NUMERIC(18,3) DEFAULT 0,
            note VARCHAR(200) NULL,
            is_adjusted BOOLEAN DEFAULT FALSE
        )
    """))

    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_stocktaking_items_session
        ON stocktaking_items (stocktaking_id)
    """))

    op.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_stocktakings_warehouse_date
        ON stocktakings (warehouse_id, count_date)
    """))


def downgrade():
    op.execute(text('DROP TABLE IF EXISTS stocktaking_items CASCADE'))
    op.execute(text('DROP TABLE IF EXISTS stocktakings CASCADE'))
