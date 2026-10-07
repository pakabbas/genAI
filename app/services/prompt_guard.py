"""Reject non-diagram prompts (poems, creative writing, off-topic) before generation."""

from __future__ import annotations

import re


class PromptRejectedError(ValueError):
    """Raised when the user asks for non-diagram content. Map to HTTP 400."""


_NON_DIAGRAM_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"\b(write|compose|create|make)\s+(a|an|me\s+a|me)?\s*(poem|poetry|haiku|limerick|sonnet|verse)\b",
            re.I,
        ),
        "poem",
    ),
    (
        re.compile(
            r"\b(poem|poetry|haiku|limerick|sonnet|ballad|ode|rhyme)\b",
            re.I,
        ),
        "poem",
    ),
    (
        re.compile(
            r"\b(write|tell)\s+(me\s+)?(a|an)?\s*(joke|story|fairytale|fairy tale|song lyrics)\b",
            re.I,
        ),
        "creative writing",
    ),
    (
        re.compile(r"\bignore (all )?(previous|prior) (instructions|prompts)\b", re.I),
        "prompt injection",
    ),
]

_DIAGRAM_HINTS = re.compile(
    r"\b(diagram|flowchart|erd|entity|use[- ]?case|sequence|class diagram|network|architecture|"
    r"swim[- ]?lane|bpmn|actor|database|api|system|process|component|topology|schema)\b",
    re.I,
)


def refusal_message(reason: str) -> str:
    return (
        f"This studio only creates technical diagrams — not {reason}. "
        "Describe a system, process, data model, or architecture you want diagrammed."
    )


def check_non_diagram_intent(*texts: str | None) -> str | None:
    """Return a user-facing refusal string, or None if prompts look diagram-related."""
    combined = "\n".join((t or "").strip() for t in texts if (t or "").strip())
    cleaned = combined.strip()
    if len(cleaned) < 3:
        return None

    for pattern, reason in _NON_DIAGRAM_PATTERNS:
        if pattern.search(cleaned):
            return refusal_message(reason)

    # Short creative-only prompts with no diagram vocabulary
    if len(cleaned) < 160 and not _DIAGRAM_HINTS.search(cleaned):
        if re.search(
            r"\b(rhyme|metaphor|love letter|essay|paragraph about|once upon a time)\b",
            cleaned,
            re.I,
        ):
            return refusal_message("creative writing")

    return None


def reject_if_non_diagram(*texts: str | None) -> None:
    """Raise PromptRejectedError when intent is not a diagram request."""
    msg = check_non_diagram_intent(*texts)
    if msg:
        raise PromptRejectedError(msg)
