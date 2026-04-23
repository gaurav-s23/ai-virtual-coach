"""add_attendance_table

Revision ID: 0004_add_attendance_table
Revises: 0003_cache_entries
Create Date: 2026-04-24

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0004_add_attendance_table"
down_revision = "0003_cache_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    # Create attendance table with proper timezone support and additional fields
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("status", sa.String(32), server_default=sa.text("'present'"), nullable=False),  # present, absent, late
        sa.Column("session_type", sa.String(50), server_default=sa.text("'interview'"), nullable=False),  # interview, mock, english
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    
    # Create comprehensive indexes for performance
    op.create_index("ix_attendance_id", "attendance", ["id"], unique=False)
    op.create_index("ix_attendance_user_id_date", "attendance", ["user_id", "date"], unique=False)
    op.create_index("ix_attendance_user_id_status", "attendance", ["user_id", "status"], unique=False)
    op.create_index("ix_attendance_date", "attendance", ["date"], unique=False)
    op.create_index("ix_attendance_status", "attendance", ["status"], unique=False)
    op.create_index("ix_attendance_session_type", "attendance", ["session_type"], unique=False)
    
    # Create composite index for common queries
    op.create_index("ix_attendance_user_date_status", "attendance", ["user_id", "date", "status"], unique=False)


def downgrade() -> None:
    # Remove indexes first (in reverse order of creation)
    op.drop_index("ix_attendance_user_date_status", table_name="attendance")
    op.drop_index("ix_attendance_session_type", table_name="attendance")
    op.drop_index("ix_attendance_status", table_name="attendance")
    op.drop_index("ix_attendance_date", table_name="attendance")
    op.drop_index("ix_attendance_user_id_status", table_name="attendance")
    op.drop_index("ix_attendance_user_id_date", table_name="attendance")
    op.drop_index("ix_attendance_id", table_name="attendance")
    
    # Drop the table
    op.drop_table("attendance")
