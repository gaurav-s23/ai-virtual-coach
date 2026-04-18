"""modular_refactor_state_tables

Revision ID: 0002_modular_state
Revises: 0001_initial_schema
Create Date: 2026-04-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_modular_state"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    op.add_column("interviews", sa.Column("candidate_name", sa.String(length=120), nullable=True))
    op.add_column("interviews", sa.Column("status", sa.String(length=32), nullable=False, server_default="starting"))
    op.add_column("interviews", sa.Column("current_question", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("interviews", sa.Column("resume_context", sa.Text(), nullable=True))

    op.create_table(
        "global_mocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("questions", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_global_mocks_created_at", "global_mocks", ["created_at"], unique=False)
    op.create_index("ix_global_mocks_id", "global_mocks", ["id"], unique=False)

    op.create_table(
        "rag_status",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="processing"),
        sa.Column("message", sa.String(length=255), nullable=False, server_default="Resume embedding in progress"),
        sa.Column("chunks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_rag_status_id", "rag_status", ["id"], unique=False)
    op.create_index("ix_rag_status_user_id", "rag_status", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_rag_status_user_id", table_name="rag_status")
    op.drop_index("ix_rag_status_id", table_name="rag_status")
    op.drop_table("rag_status")

    op.drop_index("ix_global_mocks_id", table_name="global_mocks")
    op.drop_index("ix_global_mocks_created_at", table_name="global_mocks")
    op.drop_table("global_mocks")

    op.drop_column("interviews", "resume_context")
    op.drop_column("interviews", "current_question")
    op.drop_column("interviews", "status")
    op.drop_column("interviews", "candidate_name")
