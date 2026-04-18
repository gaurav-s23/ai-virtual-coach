from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Iterable, Optional

import litellm

logger = logging.getLogger("ai_virtual_coach.llm")


def _parse_model_list(raw: str) -> list[str]:
    items = [x.strip() for x in (raw or "").split(",") if x.strip()]
    return items


def default_fallback_models() -> list[str]:
    """
    A sane default hierarchy:
    - Gemini Pro (quality)
    - Gemini Flash (reliability/cost)
    - Local Ollama (no external dependency)
    """
    return ["gemini/gemini-2.5-flash", "gemini/gemini-2.5-pro"]


def get_fallback_models(env_var: str = "LLM_FALLBACK_MODELS") -> list[str]:
    return _parse_model_list(os.getenv(env_var, "")) or default_fallback_models()


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    provider: Optional[str] = None
    raw: Optional[dict[str, Any]] = None


def _messages(prompt: str, system: str | None) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.append({"role": "user", "content": prompt})
    return msgs


async def complete_with_fallback(
    *,
    prompt: str,
    system: str | None = None,
    models: Optional[Iterable[str]] = None,
    timeout_s: float = 15.0,
    temperature: float = 0.7,
    top_p: float = 0.95,
    request_id: Optional[str] = None,
) -> Optional[LLMResult]:
    """
    Self-healing text completion:
    tries models in order and returns the first successful response.

    Never raises (returns None on total failure).
    """
    model_list = list(models) if models is not None else get_fallback_models()
    if not model_list:
        logger.error("llm_no_models_configured request_id=%s", request_id)
        return None

    last_error: Optional[BaseException] = None
    msgs = _messages(prompt, system)

    for idx, model in enumerate(model_list):
        try:
            logger.info(
                "llm_attempt request_id=%s model=%s attempt=%s/%s",
                request_id,
                model,
                idx + 1,
                len(model_list),
            )

            # litellm.acompletion can raise various provider-specific exceptions.
            # Wrap with an overall asyncio timeout so upstream hangs don't wedge the API.
            resp = await asyncio.wait_for(
                litellm.acompletion(
                    model=model,
                    messages=msgs,
                    temperature=temperature,
                    top_p=top_p,
                ),
                timeout=timeout_s,
            )

            # Normalize response across providers.
            text = ""
            try:
                text = (resp.choices[0].message.content or "").strip()  # type: ignore[attr-defined]
            except Exception:
                # Best-effort fallback: dump response for debugging
                text = str(resp)

            provider = getattr(resp, "provider", None)
            logger.info(
                "llm_success request_id=%s model=%s provider=%s",
                request_id,
                model,
                provider,
            )
            return LLMResult(
                text=text,
                model=model,
                provider=provider,
                raw=json.loads(resp.model_dump_json()) if hasattr(resp, "model_dump_json") else None,  # type: ignore[union-attr]
            )
        except asyncio.TimeoutError as e:
            last_error = e
            logger.warning(
                "llm_timeout request_id=%s model=%s timeout_s=%s",
                request_id,
                model,
                timeout_s,
            )
        except Exception as e:
            last_error = e
            logger.warning(
                "llm_error request_id=%s model=%s error=%s",
                request_id,
                model,
                repr(e),
            )

    logger.error(
        "llm_all_models_failed request_id=%s models=%s last_error=%s",
        request_id,
        ",".join(model_list),
        repr(last_error),
    )
    return None

