"""Shared Gemini call helper with retries + optional fallback model."""

from __future__ import annotations

import contextvars
import logging
import threading
import time
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.services import settings_service as cfg

logger = logging.getLogger(__name__)

# Gemini 3 Flash supports low/medium/high only (not "minimal").
_THINKING_BY_ROLE = {
    "analyst": "low",
    "planner": "low",
    "generator": "medium",
    "qc": "low",
}


# 2.7.9: per-thread info about the last call (latency, model, thinking tokens) for the trace.
_last_call = threading.local()

# Per-generation accumulator (propagates to planner worker via copy_context).
_usage_session: contextvars.ContextVar[list[dict[str, Any]] | None] = contextvars.ContextVar(
    "gemini_usage_session", default=None
)


def begin_usage_session() -> list[dict[str, Any]]:
    """Start collecting token usage for the current generation. Returns the shared list."""
    calls: list[dict[str, Any]] = []
    _usage_session.set(calls)
    return calls


def clear_usage_session() -> None:
    _usage_session.set(None)


def current_usage_calls() -> list[dict[str, Any]]:
    return list(_usage_session.get() or [])


def _record_usage_call(info: dict[str, Any]) -> None:
    bucket = _usage_session.get()
    if bucket is None:
        return
    try:
        bucket.append(dict(info))
    except Exception:
        pass


def last_call_info() -> dict:
    """Return usage/latency dict for this thread's last call."""
    return dict(getattr(_last_call, "info", None) or {})


def format_call_info(info: dict | None = None) -> str:
    info = info if info is not None else last_call_info()
    if not info:
        return ""
    return (
        f"took {info.get('seconds', 0):.1f}s, model {info.get('model')}, "
        f"prompt_tokens {info.get('prompt_tokens')}, "
        f"thoughts_tokens {info.get('thoughts_tokens')}, output_tokens {info.get('output_tokens')}"
    )


def reset_client() -> None:
    """Clear any cached client so the next call picks up the current env key."""
    # Clients are created per call today; this hook exists so a key rotation
    # takes effect immediately if caching is added later.
    return None


def _client() -> genai.Client:
    api_key = get_settings()["gemini_api_key"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Set it in your .env file.")
    return genai.Client(api_key=api_key)


def _thinking_config(model_name: str, role: str) -> types.ThinkingConfig | None:
    name = (model_name or "").lower()
    # 2.7.9: every gemini-* model except the 1.x/2.x families accepts thinking_level
    # (gemini-4-argon included). If the API rejects it we retry once without it.
    if not name.startswith("gemini") or any(tag in name for tag in ("gemini-1", "gemini-2")):
        return None
    level = _THINKING_BY_ROLE.get(role, "low")
    try:
        return types.ThinkingConfig(thinking_level=level)
    except Exception:
        return None


def generate_json(
    *,
    role: str,
    system_instruction: str,
    user_content: str,
    temperature: float,
    top_p: float,
    max_output_tokens: int,
    hard_timeout: float | None = None,
    cancel_event: threading.Event | None = None,
) -> str:
    """Call Gemini for JSON. role selects primary model (analyst|planner|generator|qc).

    hard_timeout (2.7.9, opt-in): a real HTTP timeout in seconds for this call.
    cancel_event (2.7.9, opt-in): skip further attempts once the client has gone away.
    """
    _last_call.info = {}
    primary = cfg.resolve_model(role)
    fallback = cfg.fallback_model()
    retries = int(cfg.get_value("ai.max_retries"))
    timeout = float(cfg.get_value("ai.timeout_seconds"))

    models_to_try = [primary]
    if fallback and fallback != primary:
        models_to_try.append(fallback)

    last_err: Exception | None = None
    client = _client()

    no_thinking: set[str] = set()
    for model_name in models_to_try:
        attempts = 1 + (retries if model_name == primary else 0)
        attempt = 0
        while attempt < attempts:
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError("Generation cancelled (client disconnected).")
            try:
                started = time.monotonic()
                thinking = None if model_name in no_thinking else _thinking_config(model_name, role)
                config_kwargs: dict = {
                    "system_instruction": system_instruction,
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_output_tokens": max_output_tokens,
                    "response_mime_type": "application/json",
                }
                if thinking is not None:
                    config_kwargs["thinking_config"] = thinking
                if hard_timeout:
                    try:
                        config_kwargs["http_options"] = types.HttpOptions(
                            timeout=int(max(5.0, float(hard_timeout)) * 1000)
                        )
                    except Exception:
                        pass
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
                if time.monotonic() - started > timeout:
                    logger.warning("Gemini call exceeded soft timeout (%.0fs)", timeout)
                # Log finish / thinking usage when available (helps diagnose truncated JSON).
                try:
                    cand = (response.candidates or [None])[0]
                    finish = getattr(cand, "finish_reason", None) if cand else None
                    usage = getattr(response, "usage_metadata", None)
                    thoughts = getattr(usage, "thoughts_token_count", None) if usage else None
                    prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
                    output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
                    total_tokens = getattr(usage, "total_token_count", None) if usage else None
                    cached_tokens = (
                        getattr(usage, "cached_content_token_count", None) if usage else None
                    )
                    call_info = {
                        "seconds": time.monotonic() - started,
                        "model": model_name,
                        "role": role,
                        "prompt_tokens": prompt_tokens,
                        "thoughts_tokens": thoughts,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "cached_tokens": cached_tokens,
                        "thinking_level": getattr(thinking, "thinking_level", None) if thinking else None,
                        "finish_reason": str(finish) if finish is not None else None,
                    }
                    _last_call.info = call_info
                    _record_usage_call(call_info)
                    logger.info(
                        "Gemini %s model=%s finish=%s prompt=%s thoughts=%s output=%s",
                        role,
                        model_name,
                        finish,
                        prompt_tokens,
                        thoughts,
                        output_tokens,
                    )
                except Exception:
                    pass
                text = (response.text or "").strip()
                if not text:
                    raise RuntimeError("Gemini returned an empty response. Please try again.")
                return text
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "Gemini %s via %s attempt %s failed: %s",
                    role,
                    model_name,
                    attempt + 1,
                    exc,
                )
                text_err = str(exc).lower()
                if thinking is not None and "thinking" in text_err and model_name not in no_thinking:
                    # Model rejected thinking_level — retry the same attempt without it.
                    no_thinking.add(model_name)
                    continue
                attempt += 1
                if attempt < attempts:
                    time.sleep(0.4 * attempt)
                    continue
                break

    raise RuntimeError(f"Gemini call failed for {role}: {last_err}") from last_err
