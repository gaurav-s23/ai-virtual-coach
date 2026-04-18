from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _database_url() -> str:
    """
    Resolve DATABASE_URL the same way as `backend/database.py`.

    Supports both Postgres and SQLite (including test overrides).
    """
    return os.getenv("DATABASE_URL") or "sqlite+pysqlite:///./app.db"


# Add your model's MetaData object here
# In Docker, WORKDIR is /app and `models.py` lives at /app/models.py.
# When running locally from repo root, `backend.models` is importable.
# Ensure both repo-root/backend paths are importable in all execution modes.
THIS_FILE = Path(__file__).resolve()
BACKEND_ROOT = THIS_FILE.parent.parent
REPO_ROOT = BACKEND_ROOT.parent
for p in (str(BACKEND_ROOT), str(REPO_ROOT), "/app", "/app/backend"):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from backend.models import Base  # type: ignore
except Exception:
    from models import Base  # type: ignore

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

