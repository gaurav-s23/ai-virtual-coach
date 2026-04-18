"""cache_entries

Revision ID: 0003_cache_entries
Revises: 0002_modular_state
Create Date: 2026-04-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_cache_entries"
down_revision = "0002_modular_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cache_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=255), nullable=False, unique=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_cache_entries_id", "cache_entries", ["id"], unique=False)
    op.create_index("ix_cache_entries_key", "cache_entries", ["key"], unique=False)
    op.create_index("ix_cache_entries_expires_at", "cache_entries", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_cache_entries_expires_at", table_name="cache_entries")
    op.drop_index("ix_cache_entries_key", table_name="cache_entries")
    op.drop_index("ix_cache_entries_id", table_name="cache_entries")
    op.drop_table("cache_entries")
