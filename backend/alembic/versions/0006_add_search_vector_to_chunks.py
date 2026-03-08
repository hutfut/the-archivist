"""add search_vector tsvector column to chunks

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chunks", sa.Column("search_vector", TSVECTOR, nullable=True))
    op.create_index(
        "ix_chunks_search_vector",
        "chunks",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_search_vector", table_name="chunks")
    op.drop_column("chunks", "search_vector")
