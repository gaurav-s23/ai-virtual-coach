from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Virtual Coach API")
    app_version: str = os.getenv("APP_VERSION", "3.0.0")
    frontend_url: str = os.getenv("FRONTEND_URL", "").strip()
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "12"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    llm_top_p: float = float(os.getenv("LLM_TOP_P", "0.9"))
    llm_retry_count: int = int(os.getenv("LLM_RETRY_COUNT", "2"))
    llm_cache_ttl_s: int = int(os.getenv("LLM_CACHE_TTL_SECONDS", "900"))
    admin_email: str = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password: str = os.getenv("ADMIN_PASSWORD", "").strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
