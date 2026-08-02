"""ensure user_menu_overrides table

Replaces ``_ensure_user_menu_overrides_table()`` inline DDL.

Revision ID: 0004usermenu
Revises: 0003userperms
"""
from alembic import op
import sqlalchemy as sa

revision = '0004usermenu'
down_revision = '0003userperms'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS user_menu_overrides (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            menu_id INTEGER NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
            is_visible BOOLEAN NOT NULL,
            PRIMARY KEY (user_id, menu_id)
        )
    """))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS user_menu_overrides"))
