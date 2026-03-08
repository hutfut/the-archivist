"""convert all id columns from varchar to native uuid

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FK_SPECS = [
    ("chunks", "document_id", "fk_chunks_document_id", "documents", "id"),
    ("messages", "conversation_id", "fk_messages_conversation_id", "conversations", "id"),
]


def upgrade() -> None:
    for table, col, _fk_name, _ref_table, _ref_col in _FK_SPECS:
        op.drop_constraint(f"{table}_{col}_fkey", table, type_="foreignkey")

    for table in ("documents", "chunks", "conversations", "messages"):
        op.alter_column(
            table,
            "id",
            type_=UUID(as_uuid=True),
            postgresql_using="id::uuid",
        )

    op.alter_column(
        "chunks",
        "document_id",
        type_=UUID(as_uuid=True),
        postgresql_using="document_id::uuid",
    )

    op.alter_column(
        "messages",
        "conversation_id",
        type_=UUID(as_uuid=True),
        postgresql_using="conversation_id::uuid",
    )

    for table, col, fk_name, ref_table, ref_col in _FK_SPECS:
        op.create_foreign_key(
            fk_name,
            table,
            ref_table,
            [col],
            [ref_col],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table, _col, fk_name, _ref_table, _ref_col in _FK_SPECS:
        op.drop_constraint(fk_name, table, type_="foreignkey")

    op.alter_column(
        "messages",
        "conversation_id",
        type_=sa.String(),
        postgresql_using="conversation_id::text",
    )

    op.alter_column(
        "chunks",
        "document_id",
        type_=sa.String(),
        postgresql_using="document_id::text",
    )

    for table in ("documents", "chunks", "conversations", "messages"):
        op.alter_column(
            table,
            "id",
            type_=sa.String(),
            postgresql_using="id::text",
        )

    for table, col, _fk_name, ref_table, ref_col in _FK_SPECS:
        op.create_foreign_key(
            f"{table}_{col}_fkey",
            table,
            ref_table,
            [col],
            [ref_col],
            ondelete="CASCADE",
        )
