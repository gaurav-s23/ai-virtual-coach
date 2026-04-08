"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-04-08

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind is not None else ""

    json_type = postgresql.JSONB() if dialect == "postgresql" else sa.JSON()

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("target_role", sa.String(length=100), nullable=True),
        sa.Column("readiness_score", sa.Integer(), nullable=True),
        sa.Column("streak_count", sa.Integer(), nullable=True),
        sa.Column("total_interviews", sa.Integer(), nullable=True),
        sa.Column("total_mocks", sa.Integer(), nullable=True),
        sa.Column("total_english_sessions", sa.Integer(), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_refresh_tokens_id", "refresh_tokens", ["id"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_user_id_created_at", "refresh_tokens", ["user_id", "created_at"], unique=False)

    op.create_table(
        "interviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("brutal_feedback", sa.Text(), nullable=True),
        sa.Column("transcript", json_type, nullable=True),
        sa.Column("had_pivot", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_interviews_id", "interviews", ["id"], unique=False)
    op.create_index("ix_interviews_session_id", "interviews", ["session_id"], unique=True)
    op.create_index("ix_interviews_user_id_created_at", "interviews", ["user_id", "created_at"], unique=False)

    op.create_table(
        "mock_tests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("total_questions", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_mock_tests_id", "mock_tests", ["id"], unique=False)
    op.create_index("ix_mock_tests_user_id_created_at", "mock_tests", ["user_id", "created_at"], unique=False)

    op.create_table(
        "english_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("grammar_score", sa.Integer(), nullable=True),
        sa.Column("vocab_score", sa.Integer(), nullable=True),
        sa.Column("fluency_score", sa.Integer(), nullable=True),
        sa.Column("rating", sa.String(length=10), nullable=True),
        sa.Column("critique", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_english_sessions_id", "english_sessions", ["id"], unique=False)
    op.create_index("ix_english_sessions_user_id_created_at", "english_sessions", ["user_id", "created_at"], unique=False)

    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
    )
    op.create_index("ix_attendance_id", "attendance", ["id"], unique=False)
    op.create_index("ix_attendance_user_id_date", "attendance", ["user_id", "date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_attendance_user_id_date", table_name="attendance")
    op.drop_index("ix_attendance_id", table_name="attendance")
    op.drop_table("attendance")

    op.drop_index("ix_english_sessions_user_id_created_at", table_name="english_sessions")
    op.drop_index("ix_english_sessions_id", table_name="english_sessions")
    op.drop_table("english_sessions")

    op.drop_index("ix_mock_tests_user_id_created_at", table_name="mock_tests")
    op.drop_index("ix_mock_tests_id", table_name="mock_tests")
    op.drop_table("mock_tests")

    op.drop_index("ix_interviews_user_id_created_at", table_name="interviews")
    op.drop_index("ix_interviews_session_id", table_name="interviews")
    op.drop_index("ix_interviews_id", table_name="interviews")
    op.drop_table("interviews")

    op.drop_index("ix_refresh_tokens_user_id_created_at", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

