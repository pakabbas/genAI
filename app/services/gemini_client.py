"""Shared Gemini call helper with retries + optional fallback model."""

from __future__ import annotations

import logging
import time

from google import genai
from google.genai import types

from app.config import get_settings
from app.services import settings_service as cfg

logger = logging.getLogger(__name__)


def _client() -> genai.Client:
    api_key = get_settings()["gemini_api_key"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Set it in your .env file.")
    return genai.Client(api_key=api_key)


def generate_json(
    *,
    role: str,
    system_instruction: str,
    user_content: str,
    temperature: float,
    top_p: float,
    max_output_tokens: int,
) -> str:
    """Call Gemini for JSON. role selects primary model (analyst|planner|generator|qc)."""
    primary = cfg.resolve_model(role)
    fallback = cfg.fallback_model()
    retries = int(cfg.get_value("ai.max_retries"))
    timeout = float(cfg.get_value("ai.timeout_seconds"))

    models_to_try = [primary]
    if fallback and fallback != primary:
        models_to_try.append(fallback)

    last_err: Exception | None = None
    client = _client()

    for model_name in models_to_try:
        attempts = 1 + (retries if model_name == primary else 0)
        for attempt in range(attempts):
            try:
                # google-genai doesn't expose a simple timeout on all versions;
                # we bound wall time with a soft check around the call.
                started = time.monotonic()
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=temperature,
                        top_p=top_p,
                        max_output_tokens=max_output_tokens,
                        response_mime_type="application/json",
                    ),
                )
                if time.monotonic() - started > timeout:
                    logger.warning("Gemini call exceeded soft timeout (%.0fs)", timeout)
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
                if attempt + 1 < attempts:
                    time.sleep(0.4 * (attempt + 1))
                    continue
                break

    raise RuntimeError(f"Gemini call failed for {role}: {last_err}") from last_err
