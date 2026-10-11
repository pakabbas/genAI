"""Lightweight brief→diagram validation for Generator re-ask (Agent 1)."""

from __future__ import annotations

import re

from app.schemas.diagram import DiagramDocument, DiagramType

_EDIT_HINT = re.compile(
    r"\b(make|wider|narrower|taller|shorter|resize|relabel|rename|move|shift|"
    r"add (a |an |the )?(branch|edge|arrow|box|node|lane|message)|"
    r"change (the )?(label|color|size|width|height)|"
    r"only (change|update|fix|edit)|don'?t recreate|modify|patch|tweak)\b",
    re.I,
)


def looks_like_edit_request(prompt: str, has_existing: bool) -> bool:
    if not has_existing or not (prompt or "").strip():
        return False
    return bool(_EDIT_HINT.search(prompt))


def validate_brief_coverage(
    diagram_type: DiagramType | str,
    brief: str,
    diagram: DiagramDocument,
) -> list[str]:
    """Return human-readable gaps (empty = OK). Heuristic, not LLM."""
    text = (brief or "").strip()
    if len(text) < 12:
        return []
    dtype = str(diagram_type)
    labels = " ".join((n.label or "") for n in diagram.nodes).lower()
    edge_labels = " ".join((e.label or "") for e in diagram.edges).lower()
    gaps: list[str] = []

    if dtype == "sequence":
        gaps.extend(_sequence_gaps(text, diagram, labels))
    elif dtype == "flowchart":
        gaps.extend(_flowchart_gaps(text, diagram, labels, edge_labels))
    elif dtype == "erd":
        gaps.extend(_erd_gaps(text, diagram, labels))
    elif dtype in {"swim_lane", "architecture", "use_case", "class_diagram", "network"}:
        gaps.extend(_named_token_gaps(text, labels, min_len=4, limit=6))

    return gaps[:12]


def _sequence_gaps(text: str, diagram: DiagramDocument, labels: str) -> list[str]:
    gaps: list[str] = []
    # Quoted or Title-Case participant-like tokens
    candidates = re.findall(r'"([^"]{2,40})"', text)
    candidates += re.findall(
        r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,2})\b", text
    )
    skip = {
        "The", "A", "An", "User", "System", "Then", "When", "After", "Before",
        "Sequence", "Diagram", "Message", "Return", "Async", "Sync",
    }
    seen: set[str] = set()
    for name in candidates:
        key = name.strip()
        if len(key) < 3 or key in skip or key.lower() in seen:
            continue
        seen.add(key.lower())
        if key.lower() not in labels and not any(
            key.lower() in (n.label or "").lower() for n in diagram.nodes
        ):
            # Only flag if brief presents it as a participant
            if re.search(
                rf"\b(participant|actor|lifeline|service|api|client|server|gateway)\b.*\b{re.escape(key)}\b"
                rf"|\b{re.escape(key)}\b.*\b(participant|actor|lifeline|calls?|sends?|receives?)\b",
                text,
                re.I,
            ):
                gaps.append(f"Missing participant mentioned in brief: {key}")

    msg_count = len(diagram.edges)
    asked_msgs = re.findall(
        r"\b(\d+)\s*(messages?|calls?|steps?)\b", text, re.I
    )
    for num_s, _ in asked_msgs:
        need = int(num_s)
        if need >= 3 and msg_count < need:
            gaps.append(f"Brief asks for ~{need} messages/calls but diagram has {msg_count}.")

    if re.search(r"\bactivation\b", text, re.I):
        if not any(n.type == "activation" for n in diagram.nodes):
            gaps.append("Brief requests activation boxes but none are present.")

    if re.search(r"\b(dashed return|return message|async)\b", text, re.I):
        types = {e.type for e in diagram.edges}
        if re.search(r"\basync\b", text, re.I) and "async_message" not in types:
            gaps.append("Brief mentions async messages but no async_message edges.")
        if re.search(r"\breturn\b", text, re.I) and "return_message" not in types:
            gaps.append("Brief mentions return messages but no return_message edges.")

    return gaps


def _flowchart_gaps(
    text: str, diagram: DiagramDocument, labels: str, edge_labels: str
) -> list[str]:
    gaps: list[str] = []
    decisions = [n for n in diagram.nodes if n.type == "decision"]
    for n in decisions:
        outs = [e for e in diagram.edges if e.from_node == n.id]
        if len(outs) < 2:
            gaps.append(f"Decision {n.label!r} needs ≥2 outgoing labeled branches.")
        elif sum(1 for e in outs if (e.label or "").strip()) < 2:
            gaps.append(f"Decision {n.label!r} branches need labels (e.g. Yes/No).")

    if re.search(r"\b(yes|no|true|false|2fa|mfa|retry)\b", text, re.I):
        if "no" in text.lower() and "no" not in edge_labels and "n" not in edge_labels.split():
            # soft: only if a decision exists
            if decisions and not any(
                re.search(r"\bno\b", (e.label or ""), re.I) for e in diagram.edges
            ):
                gaps.append("Brief implies a No/alternate branch that is missing on a decision.")

    gaps.extend(_named_token_gaps(text, labels, min_len=5, limit=5))
    return gaps


def _erd_gaps(text: str, diagram: DiagramDocument, labels: str) -> list[str]:
    gaps: list[str] = []
    entities = [n for n in diagram.nodes if n.type in {"entity", "weak_entity"}]
    if re.search(r"\b(one[- ]to[- ]many|many[- ]to[- ]many|cardinality|1\.\.\*)\b", text, re.I):
        card_types = {
            "one", "many", "one_or_many", "zero_or_one", "zero_or_many",
            "one_to_many", "many_to_many", "identifying",
        }
        if not any(e.type in card_types for e in diagram.edges):
            gaps.append("Brief requests cardinalities but no crow's-foot edge types are used.")
    if len(entities) < 2 and re.search(r"\b(entities|tables|relationship)\b", text, re.I):
        gaps.append("ERD should include multiple entity tables for the brief.")
    gaps.extend(_named_token_gaps(text, labels, min_len=4, limit=5))
    return gaps


def _named_token_gaps(text: str, labels: str, *, min_len: int, limit: int) -> list[str]:
    gaps: list[str] = []
    # Prefer quoted names
    for name in re.findall(r'"([^"]{2,40})"', text):
        if len(name) >= min_len and name.lower() not in labels:
            gaps.append(f"Missing element mentioned in brief: {name}")
        if len(gaps) >= limit:
            break
    return gaps
