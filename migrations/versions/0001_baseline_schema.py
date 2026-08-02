"""baseline schema

Represents the existing production schema as of Phase 6. All schema objects
that were previously created by inline DDL in ``app/core/bootstrap`` are now
managed by the Alembic revisions below. This empty baseline is stamped as the
starting point so ``flask db upgrade`` can be replayed safely.

Revision ID: 0001baseline
Revises:
Create Date: 2026-07-15 23:05:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0001baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # No-op: existing production schema is the baseline.
    pass


def downgrade():
    pass
