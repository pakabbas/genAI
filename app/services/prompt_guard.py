"""Reject non-diagram prompts (poems, creative writing, off-topic) before generation."""

from __future__ import annotations

import re

from app.services import settings_service as cfg
from app.services.settings_registry import (
    DEFAULT_GUARD_ALLOWLIST,
    DEFAULT_GUARD_PATTERNS,
    DEFAULT_GUARD_SHORT_CREATIVE,
    DEFAULT_REFUSAL,
)


class PromptRejectedError(ValueError):
    """Raised when the user asks for non-diagram content. Map to HTTP 400."""


def validate_guard_patterns(patterns: object) -> list[dict]:
    """Validate guard.patterns for settings writes. Raises ValueError on bad input."""
    if not isinstance(patterns, list):
        raise ValueError("guard.patterns must be a JSON array of {pattern, reason} objects.")
    out: list[dict] = []
    for i, item in enumerate(patterns):
        if not isinstance(item, dict):
            raise ValueError(f"guard.patterns[{i}] must be an object.")
        pattern = str(item.get("pattern") or "").strip()
        reason = str(item.get("reason") or "").strip() or "unsupported content"
        if not pattern:
            raise ValueError(f"guard.patterns[{i}].pattern is required.")
        try:
            re.compile(pattern, re.I)
        except re.error as exc:
            raise ValueError(f"guard.patterns[{i}].pattern is invalid: {exc}") from exc
        out.append({"pattern": pattern, "reason": reason})
    return out


def validate_guard_regex(key: str, value: object) -> str:
    text = str(value or "")
    try:
        re.compile(text, re.I)
    except re.error as exc:
        raise ValueError(f"{key} is not a valid regex: {exc}") from exc
    return text


def refusal_message(reason: str) -> str:
    try:
        template = str(cfg.get_value("guard.refusal_message") or DEFAULT_REFUSAL)
    except Exception:
        template = DEFAULT_REFUSAL
    try:
        return template.format(reason=reason)
    except Exception:
        return (
            f"This studio only creates technical diagrams — not {reason}. "
            "Describe a system, process, data model, or architecture you want diagrammed."
        )


def _safe_patterns() -> list[tuple[re.Pattern[str], str]]:
    try:
        raw = cfg.get_value("guard.patterns") or DEFAULT_GUARD_PATTERNS
    except Exception:
        raw = DEFAULT_GUARD_PATTERNS
    compiled: list[tuple[re.Pattern[str], str]] = []
    if not isinstance(raw, list):
        raw = DEFAULT_GUARD_PATTERNS
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            pattern = re.compile(str(item.get("pattern") or ""), re.I)
            reason = str(item.get("reason") or "unsupported content")
        except re.error:
            continue
        if pattern.pattern:
            compiled.append((pattern, reason))
    if not compiled:
        for item in DEFAULT_GUARD_PATTERNS:
            compiled.append((re.compile(item["pattern"], re.I), item["reason"]))
    return compiled


def _safe_allowlist() -> re.Pattern[str]:
    try:
        text = str(cfg.get_value("guard.allowlist") or DEFAULT_GUARD_ALLOWLIST)
        return re.compile(text, re.I)
    except Exception:
        return re.compile(DEFAULT_GUARD_ALLOWLIST, re.I)


def _safe_short_creative() -> str:
    try:
        return str(cfg.get_value("guard.short_creative_pattern") or DEFAULT_GUARD_SHORT_CREATIVE)
    except Exception:
        return DEFAULT_GUARD_SHORT_CREATIVE


def check_non_diagram_intent(*texts: str | None) -> str | None:
    """Return a user-facing refusal string, or None if prompts look diagram-related."""
    try:
        enabled = cfg.get_value("guard.enabled")
    except Exception:
        enabled = True
    if not enabled:
        return None

    combined = "\n".join((t or "").strip() for t in texts if (t or "").strip())
    cleaned = combined.strip()
    if len(cleaned) < 3:
        return None

    for pattern, reason in _safe_patterns():
        if pattern.search(cleaned):
            return refusal_message(reason)

    try:
        short_limit = int(cfg.get_value("guard.short_prompt_chars"))
    except Exception:
        short_limit = 160

    allowlist = _safe_allowlist()
    short_creative = _safe_short_creative()
    if len(cleaned) < short_limit and not allowlist.search(cleaned):
        try:
            if short_creative and re.search(short_creative, cleaned, re.I):
                return refusal_message("creative writing")
        except re.error:
            if re.search(DEFAULT_GUARD_SHORT_CREATIVE, cleaned, re.I):
                return refusal_message("creative writing")

    return None


def reject_if_non_diagram(*texts: str | None) -> None:
    """Raise PromptRejectedError when intent is not a diagram request."""
    msg = check_non_diagram_intent(*texts)
    if msg:
        raise PromptRejectedError(msg)
