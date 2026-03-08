"""add section_heading to chunks

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-07

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("section_heading", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("chunks", "section_heading")
