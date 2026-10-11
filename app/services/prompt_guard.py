"""Reject non-diagram prompts (poems, creative writing, off-topic) before generation."""

from __future__ import annotations

import re

from app.services import settings_service as cfg


class PromptRejectedError(ValueError):
    """Raised when the user asks for non-diagram content. Map to HTTP 400."""


def refusal_message(reason: str) -> str:
    template = str(cfg.get_value("guard.refusal_message"))
    try:
        return template.format(reason=reason)
    except Exception:
        return (
            f"This studio only creates technical diagrams — not {reason}. "
            "Describe a system, process, data model, or architecture you want diagrammed."
        )


def check_non_diagram_intent(*texts: str | None) -> str | None:
    """Return a user-facing refusal string, or None if prompts look diagram-related."""
    if not cfg.get_value("guard.enabled"):
        return None

    combined = "\n".join((t or "").strip() for t in texts if (t or "").strip())
    cleaned = combined.strip()
    if len(cleaned) < 3:
        return None

    patterns = cfg.get_value("guard.patterns") or []
    for item in patterns:
        try:
            pattern = re.compile(str(item.get("pattern", "")), re.I)
            reason = str(item.get("reason") or "unsupported content")
        except re.error:
            continue
        if pattern.pattern and pattern.search(cleaned):
            return refusal_message(reason)

    allowlist = re.compile(str(cfg.get_value("guard.allowlist") or ""), re.I)
    short_limit = int(cfg.get_value("guard.short_prompt_chars"))
    short_creative = str(cfg.get_value("guard.short_creative_pattern") or "")

    if len(cleaned) < short_limit and not allowlist.search(cleaned):
        if short_creative and re.search(short_creative, cleaned, re.I):
            return refusal_message("creative writing")

    return None


def reject_if_non_diagram(*texts: str | None) -> None:
    """Raise PromptRejectedError when intent is not a diagram request."""
    msg = check_non_diagram_intent(*texts)
    if msg:
        raise PromptRejectedError(msg)
