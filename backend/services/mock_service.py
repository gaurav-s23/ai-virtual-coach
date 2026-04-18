from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    from .. import models
    from .llm_service import generate_quiz
except ImportError:
    import models  # type: ignore
    from services.llm_service import generate_quiz  # type: ignore


def get_current_mock(db: Session) -> "models.GlobalMock | None":
    return db.query(models.GlobalMock).order_by(models.GlobalMock.created_at.desc()).first()


def replace_mock(db: Session, questions: list[dict]) -> "models.GlobalMock":
    with db.begin():
        try:
            db.execute(text("SELECT pg_advisory_xact_lock(987654321)"))
        except Exception:
            # Non-Postgres engines won't support advisory lock.
            pass
        db.query(models.GlobalMock).delete()
        row = models.GlobalMock(questions=questions)
        db.add(row)
    db.refresh(row)
    return row


async def generate_new_mock(db: Session, category: str, context: str = "") -> "models.GlobalMock":
    questions = await generate_quiz(context, category)
    return replace_mock(db, questions=questions)
