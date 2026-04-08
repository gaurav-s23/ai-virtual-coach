from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional


State = Literal["INTERVIEW", "DISCUSSION"]


def detect_discussion_intent(text: str) -> bool:
    t = (text or "").lower()
    triggers = [
        "what is",
        "explain",
        "clarify",
        "why",
        "how does",
        "help me",
        "can you",
        "?",
    ]
    return any(x in t for x in triggers)


def answer_too_short(answer: str) -> bool:
    a = (answer or "").strip()
    # Short answers are allowed sometimes; keep threshold conservative.
    return len(a) < 40


def steering_prompt(next_question: str) -> str:
    return (
        "When you are ready, let's return to the interview.\n\n"
        f"Next question: {next_question}"
    )

