def pytest_configure() -> None:
    """Set test-safe defaults for environment variables."""
    import os

    os.environ.setdefault("RATELIMIT_ENABLED", "false")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    # Use a shared in-memory SQLite DB for tests.
    os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///file::memory:?cache=shared")


def pytest_sessionstart() -> None:
    """Apply Alembic migrations to the test database."""
    try:
        from alembic import command
        from alembic.config import Config
    except Exception:
        # If dependencies aren't installed in the current environment,
        # skip migration orchestration (CI/Docker should install requirements).
        return
    import os

    cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
    command.upgrade(cfg, "head")


def pytest_sessionfinish(session, exitstatus) -> None:  # type: ignore[no-untyped-def]
    """Rollback Alembic migrations from the test database."""
    try:
        from alembic import command
        from alembic.config import Config
    except Exception:
        return
    import os

    cfg = Config(os.path.join(os.path.dirname(__file__), "alembic.ini"))
    command.downgrade(cfg, "base")

