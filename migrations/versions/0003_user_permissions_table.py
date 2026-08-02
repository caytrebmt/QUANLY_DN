"""ensure user_permissions table

Replaces ``_ensure_user_permissions_table()`` inline DDL.

Revision ID: 0003userperms
Revises: 0002normalize
"""
from alembic import op
import sqlalchemy as sa

revision = '0003userperms'
down_revision = '0002normalize'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS user_permissions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            module VARCHAR(50) NOT NULL,
            can_view BOOLEAN DEFAULT FALSE,
            can_add BOOLEAN DEFAULT FALSE,
            can_edit BOOLEAN DEFAULT FALSE,
            can_delete BOOLEAN DEFAULT FALSE,
            CONSTRAINT uq_user_module UNIQUE (user_id, module)
        )
    """))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS user_permissions"))
