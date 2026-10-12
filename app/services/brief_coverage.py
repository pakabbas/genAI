"""Lightweight brief→diagram validation for Generator re-ask (Agent 1)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.diagram import DiagramDocument, DiagramType

# Only phrases that clearly point at the canvas (domain verbs like rename/move alone are NOT edits).
_EDIT_HINT = re.compile(
    r"(?:"
    r"\bon\s+this\s+diagram\b|"
    r"\bthe\s+current\s+diagram\b|"
    r"\bthis\s+canvas\b|"
    r"\bedit\s+(the\s+|this\s+|current\s+)?diagram\b|"
    r"\badd\s+.+\s+to\s+the\s+existing\b|"
    r"\bmake\s+these\s+(boxes|shapes|nodes)\b"
    r")",
    re.I,
)

_STOP_PARTICIPANTS = {
    "the", "a", "an", "user", "system", "then", "when", "after", "before",
    "finally", "next", "first", "second", "third", "participants", "participant",
    "sequence", "diagram", "message", "return", "async", "sync", "actor",
    "lifeline", "service", "client", "server", "request", "response",
}


@dataclass(frozen=True)
class BriefGaps:
    """advisory = trace-only; blocking = high-confidence (re-ask / QC)."""

    advisory: list[str]
    blocking: list[str]

    def all(self) -> list[str]:
        return [*self.blocking, *self.advisory]


def looks_like_edit_request(prompt: str, has_existing: bool) -> bool:
    if not has_existing or not (prompt or "").strip():
        return False
    return bool(_EDIT_HINT.search(prompt))


def validate_brief_coverage(
    diagram_type: DiagramType | str,
    brief: str,
    diagram: DiagramDocument,
) -> BriefGaps:
    """Heuristic gaps. Prefer advisory; only high-confidence items are blocking."""
    text = (brief or "").strip()
    if len(text) < 12:
        return BriefGaps([], [])
    dtype = str(diagram_type)
    labels = " ".join((n.label or "") for n in diagram.nodes).lower()
    edge_labels = " ".join((e.label or "") for e in diagram.edges).lower()

    if dtype == "sequence":
        return _sequence_gaps(text, diagram, labels)
    if dtype == "flowchart":
        return _flowchart_gaps(text, diagram, labels, edge_labels)
    if dtype == "erd":
        return _erd_gaps(text, diagram, labels)
    advisory = _named_token_gaps(text, labels, min_len=4, limit=6)
    return BriefGaps(advisory=advisory, blocking=[])


def _sequence_gaps(text: str, diagram: DiagramDocument, labels: str) -> BriefGaps:
    advisory: list[str] = []
    blocking: list[str] = []

    # Only explicit participant lists: "Participants: A, B" / "actors: …" / bullet lists after that heading
    for name in _explicit_participant_names(text):
        if name.lower() in _STOP_PARTICIPANTS:
            continue
        if not any(name.lower() in (n.label or "").lower() for n in diagram.nodes):
            advisory.append(f"Possible missing participant from brief list: {name}")

    msg_count = len(diagram.edges)
    asked_msgs = re.findall(r"\b(\d+)\s*(messages?|calls?)\b", text, re.I)
    for num_s, _ in asked_msgs:
        need = int(num_s)
        if need >= 3 and msg_count < need:
            blocking.append(f"Brief asks for ~{need} messages/calls but diagram has {msg_count}.")

    if re.search(r"\bactivation\s+box", text, re.I) or re.search(
        r"\bwith\s+activations?\b", text, re.I
    ):
        if not any(n.type == "activation" for n in diagram.nodes):
            blocking.append("Brief requests activation boxes but none are present.")

    types = {e.type for e in diagram.edges}
    if (
        re.search(r"\basync(?:hronous)?\s+messages?\b", text, re.I)
        and not re.search(r"(?i)\b(no|not|without|don't|do not)\b[^\n.]{0,24}\basync", text)
        and "async_message" not in types
    ):
        blocking.append("Brief mentions async messages but no async_message edges.")
    if (
        re.search(r"\b(?:dashed\s+)?return\s+messages?\b", text, re.I)
        and not re.search(
            r"(?i)\b(no|not|without|don't|do not)\b[^\n.]{0,28}\breturn\s+messages?\b",
            text,
        )
        and "return_message" not in types
    ):
        blocking.append("Brief mentions return messages but no return_message edges.")

    return BriefGaps(advisory=advisory[:8], blocking=blocking[:8])


def _explicit_participant_names(text: str) -> list[str]:
    names: list[str] = []
    # Quoted names near participant wording
    for m in re.finditer(
        r"(?i)(?:participants?|actors?|lifelines?)\s*[:=]\s*([^\n.]+)",
        text,
    ):
        chunk = m.group(1)
        for part in re.split(r"[,;/]| and ", chunk):
            part = part.strip().strip("\"'")
            if 2 <= len(part) <= 40:
                names.append(part)
    for m in re.finditer(r'"([^"]{2,40})"', text):
        # Only if the quote sits near participant language
        start = max(0, m.start() - 40)
        window = text[start : m.end() + 40]
        if re.search(r"(?i)participant|actor|lifeline", window):
            names.append(m.group(1).strip())
    # Dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        key = n.lower()
        if key not in seen:
            seen.add(key)
            out.append(n)
    return out


def _flowchart_gaps(
    text: str, diagram: DiagramDocument, labels: str, edge_labels: str
) -> BriefGaps:
    advisory: list[str] = []
    blocking: list[str] = []
    decisions = [n for n in diagram.nodes if n.type == "decision"]
    for n in decisions:
        outs = [e for e in diagram.edges if e.from_node == n.id]
        if len(outs) < 2:
            blocking.append(f"Decision {n.label!r} needs ≥2 outgoing labeled branches.")
        elif sum(1 for e in outs if (e.label or "").strip()) < 2:
            blocking.append(f"Decision {n.label!r} branches need labels (e.g. Yes/No).")

    # Whole-word "No" branch — never match substring of "not"/"another"
    if decisions and re.search(r"(?i)\b(yes\s*/\s*no|yes\s+or\s+no|\bno\s+branch)\b", text):
        if not any(re.search(r"(?i)^\s*no\s*$", (e.label or "").strip()) for e in diagram.edges):
            if not any(re.search(r"(?i)\bno\b", (e.label or "")) for e in diagram.edges):
                advisory.append("Brief implies a No branch that may be missing on a decision.")

    advisory.extend(_named_token_gaps(text, labels, min_len=5, limit=4))
    return BriefGaps(advisory=advisory[:8], blocking=blocking[:8])


def _erd_gaps(text: str, diagram: DiagramDocument, labels: str) -> BriefGaps:
    advisory: list[str] = []
    blocking: list[str] = []
    entities = [n for n in diagram.nodes if n.type in {"entity", "weak_entity"}]
    if re.search(r"(?i)\b(one[- ]to[- ]many|many[- ]to[- ]many|cardinality|1\.\.\*)\b", text):
        card_types = {
            "one", "many", "one_or_many", "zero_or_one", "zero_or_many",
            "one_to_many", "one_to_one", "many_to_many", "identifying",
        }
        if not any(e.type in card_types for e in diagram.edges):
            blocking.append("Brief requests cardinalities but no crow's-foot edge types are used.")
    if len(entities) < 2 and re.search(r"(?i)\b(entities|tables)\b", text):
        advisory.append("ERD may need more entity tables for the brief.")
    advisory.extend(_named_token_gaps(text, labels, min_len=4, limit=4))
    return BriefGaps(advisory=advisory[:8], blocking=blocking[:8])


def _named_token_gaps(text: str, labels: str, *, min_len: int, limit: int) -> list[str]:
    gaps: list[str] = []
    for name in re.findall(r'"([^"]{2,40})"', text):
        if len(name) >= min_len and name.lower() not in labels:
            gaps.append(f"Missing quoted element from brief: {name}")
        if len(gaps) >= limit:
            break
    return gaps
