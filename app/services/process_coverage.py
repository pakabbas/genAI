"""Process inventory extraction and diagram coverage validation (prompt completeness)."""

from __future__ import annotations

import json
import re
from difflib import SequenceMatcher

from google.genai import types

from app.prompts.process_plan import PROCESS_PLAN_SYSTEM, build_process_plan_prompt
from app.schemas.diagram import DiagramDocument, DiagramType
from app.schemas.process_model import ProcessBranch, ProcessElement, ProcessModel
from app.services.diagram_generator import _extract_json_object

PROCESS_ORIENTED_TYPES: set[str] = {"swim_lane", "flowchart"}

# Heuristic decision cues in the user brief (generic — not domain-specific).
_DECISION_CUES: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    # regex, decision label, preferred lane hint (may be ""), branches
    (
        r"accept\s*/\s*reject|accept(?:s|ed)?\s+or\s+reject|restaurant\s+accept",
        "Accept Order?",
        "Restaurant",
        [("Yes", "accepted"), ("No", "rejected — notify and end")],
    ),
    (
        r"success\s*/\s*failure|confirm(?:s|ed)?\s+or\s+decline|payment\s+(?:success|fail|declin)|"
        r"if\s+declined|if\s+confirmed",
        "Payment Successful?",
        "Payment Gateway",
        [("Yes", "confirmed"), ("No", "declined — notify and end")],
    ),
    (
        r"approve\s*/\s*deny|approved\s+or\s+denied|if\s+approved|if\s+denied",
        "Approved?",
        "",
        [("Yes", "approved"), ("No", "denied")],
    ),
]

_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "for",
    "is",
    "be",
    "with",
    "in",
    "on",
    "at",
    "by",
    "from",
    "as",
    "into",
}


def _client_and_model():
    from google import genai

    from app.config import get_settings

    settings = get_settings()
    api_key = settings["gemini_api_key"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Set it in your .env file.")
    return genai.Client(api_key=api_key), settings["gemini_model"]


def extract_process_model(diagram_type: DiagramType, user_prompt: str) -> ProcessModel:
    """Ask Gemini for a structured process inventory derived from the brief."""
    client, model_name = _client_and_model()
    response = client.models.generate_content(
        model=model_name,
        contents=build_process_plan_prompt(diagram_type, user_prompt),
        config=types.GenerateContentConfig(
            system_instruction=PROCESS_PLAN_SYSTEM,
            temperature=0.2,
            top_p=0.8,
            max_output_tokens=8192,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Process planner returned an empty response.")
    data = json.loads(_extract_json_object(text))
    model_obj = ProcessModel.model_validate(data)
    if not model_obj.elements:
        raise RuntimeError("Process planner returned no elements.")
    return enrich_process_model_from_prompt(model_obj, user_prompt)


def enrich_process_model_from_prompt(model: ProcessModel, user_prompt: str) -> ProcessModel:
    """
    Patch LLM inventory with decision/notify cues detected directly in the brief.
    Prevents under-extraction (e.g. only one of two required XOR gateways).
    """
    prompt = user_prompt or ""
    existing_decision_labels = [e.label for e in model.decisions()]
    next_idx = len(model.elements) + 1

    for pattern, label, lane_hint, branches in _DECISION_CUES:
        if not re.search(pattern, prompt, flags=re.I):
            continue
        if any(_label_match(label, existing, min_ratio=0.45) for existing in existing_decision_labels):
            continue
        # Also skip if any existing decision already covers key tokens
        key = _tokens(label)
        if any(key and key <= _tokens(existing) for existing in existing_decision_labels):
            continue

        lane = lane_hint
        if lane and model.lanes and not any(_label_match(lane, ln, min_ratio=0.5) for ln in model.lanes):
            # Prefer a lane from the model that shares tokens with the hint
            for ln in model.lanes:
                if _tokens(lane_hint) & _tokens(ln):
                    lane = ln
                    break

        did = f"d_auto_{next_idx}"
        next_idx += 1
        model.elements.append(
            ProcessElement(
                id=did,
                kind="decision",
                label=label,
                lane=lane or None,
                branches=[
                    ProcessBranch(label=bl, outcome=out, ends_process=("end" in out.lower()))
                    for bl, out in branches
                ],
            )
        )
        existing_decision_labels.append(label)

    # Notify-on-failure cues: ensure at least one notify activity when prompt says so
    if re.search(r"notif(?:y|ied|ication)", prompt, flags=re.I):
        activity_labels = [e.label for e in model.activities()]
        if not any("notif" in _norm(lbl) for lbl in activity_labels):
            lane = None
            for ln in model.lanes:
                if _label_match("Customer", ln, min_ratio=0.5):
                    lane = ln
                    break
            model.elements.append(
                ProcessElement(
                    id=f"a_auto_notify_{next_idx}",
                    kind="activity",
                    label="Notify Customer",
                    lane=lane,
                )
            )

    return model


def prompt_decision_gaps(user_prompt: str, diagram: DiagramDocument) -> list[str]:
    """Extra coverage against the raw prompt when the inventory under-counted decisions."""
    gaps: list[str] = []
    decision_labels = _decision_labels(diagram) + [
        (n.label or "") for n in diagram.nodes if n.type in {"decision", "gateway_xor", "gateway"}
    ]
    for pattern, label, _lane, _branches in _DECISION_CUES:
        if not re.search(pattern, user_prompt or "", flags=re.I):
            continue
        if not any(_label_match(label, cand, min_ratio=0.4) for cand in decision_labels if cand):
            # Broader fallback: any gateway whose label shares significant tokens
            key = {t for t in _tokens(label) if len(t) > 3}
            if key and any(key <= _tokens(cand) for cand in decision_labels if cand):
                continue
            gaps.append(f"Missing decision gateway required by prompt: '{label}'")
    return gaps


def process_model_brief(model: ProcessModel) -> str:
    """Human-readable inventory injected into the generator prompt."""
    lines = [
        "MANDATORY PROCESS INVENTORY (every item MUST appear in the diagram — do not merge or omit):",
        f"Title: {model.title}",
        f"Lanes (exact): {', '.join(model.lanes) if model.lanes else '(none listed)'}",
        "",
        "Elements:",
    ]
    for el in model.elements:
        lane = f" @ {el.lane}" if el.lane else ""
        lines.append(f"- [{el.id}] {el.kind.upper()}: {el.label}{lane}")
        for br in el.branches:
            nxt = br.next_element_id or ("END" if br.ends_process else "?")
            lines.append(f"    · branch '{br.label}' → {nxt} ({br.outcome})")
    if model.flows:
        lines.append("")
        lines.append("Sequence flows:")
        for flow in model.flows:
            lbl = f" [{flow.label}]" if flow.label else ""
            lines.append(f"- {flow.from_id} → {flow.to_id}{lbl}")
    lines.append("")
    lines.append(
        "Rules: one diagram node per activity/decision above; decision branches must be "
        "separate labeled edges; do not invent extra business rules."
    )
    return "\n".join(lines)


def _norm(text: str) -> str:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # light synonym collapse (generic, not domain-specific)
    text = text.replace("pick up", "pickup").replace("check out", "checkout")
    return text


def _tokens(text: str) -> set[str]:
    return {t for t in _norm(text).split() if t and t not in _STOP and len(t) > 1}


def _label_match(required: str, candidate: str, *, min_ratio: float = 0.58) -> bool:
    rn = _norm(required)
    cn = _norm(candidate)
    if not rn or not cn:
        return False
    if rn == cn or rn in cn or cn in rn:
        return True
    req_toks = _tokens(required)
    cand_toks = _tokens(candidate)
    if not req_toks:
        return True
    # Prefer requiring most significant tokens (length > 3) to avoid false merges
    significant = {t for t in req_toks if len(t) > 3} or req_toks
    if significant and significant <= cand_toks:
        return True
    overlap = len(req_toks & cand_toks) / max(len(req_toks), 1)
    if overlap >= min_ratio and len(req_toks & cand_toks) >= max(1, min(2, len(req_toks))):
        return True
    return SequenceMatcher(None, rn, cn).ratio() >= 0.78


def _node_labels(diagram: DiagramDocument) -> list[str]:
    return [(n.label or "").strip() for n in diagram.nodes if (n.label or "").strip()]


def _lane_labels(diagram: DiagramDocument) -> list[str]:
    return [
        (n.label or "").strip()
        for n in diagram.nodes
        if n.type in {"lane", "pool"} and (n.label or "").strip()
    ]


def _activity_labels(diagram: DiagramDocument) -> list[str]:
    activity_types = {
        "process",
        "subprocess",
        "task",
        "document",
        "input",
        "manual_input",
        "preparation",
        "display",
        "text_box",
    }
    return [
        (n.label or "").strip()
        for n in diagram.nodes
        if n.type in activity_types and (n.label or "").strip()
    ]


def _decision_labels(diagram: DiagramDocument) -> list[str]:
    return [
        (n.label or "").strip()
        for n in diagram.nodes
        if n.type in {"decision", "gateway_xor", "gateway_and", "gateway"} and (n.label or "").strip()
    ]


def _edge_labels(diagram: DiagramDocument) -> list[str]:
    return [(e.label or "").strip() for e in diagram.edges if (e.label or "").strip()]


def _has_start(diagram: DiagramDocument) -> bool:
    return any(n.type in {"start", "terminator"} for n in diagram.nodes)


def _has_end(diagram: DiagramDocument) -> bool:
    return any(n.type in {"end", "terminator"} for n in diagram.nodes)


def _decision_outdegree(diagram: DiagramDocument) -> dict[str, int]:
    counts: dict[str, int] = {}
    decision_ids = {
        n.id for n in diagram.nodes if n.type in {"decision", "gateway_xor", "gateway_and", "gateway"}
    }
    for edge in diagram.edges:
        if edge.from_node in decision_ids:
            counts[edge.from_node] = counts.get(edge.from_node, 0) + 1
    return counts


def validate_process_coverage(
    process_model: ProcessModel,
    diagram: DiagramDocument,
    *,
    diagram_type: DiagramType,
    user_prompt: str | None = None,
) -> list[str]:
    """
    Return blocking gap messages when the diagram omits inventory items.
    Generic — works for any process brief, not a single example domain.
    """
    gaps: list[str] = []
    if user_prompt:
        gaps.extend(prompt_decision_gaps(user_prompt, diagram))

    if diagram_type == "swim_lane" and process_model.lanes:
        lane_labels = _lane_labels(diagram)
        for lane in process_model.lanes:
            if not any(_label_match(lane, cand, min_ratio=0.5) for cand in lane_labels):
                gaps.append(f"Missing swim lane: '{lane}'")

    if process_model.starts() and not _has_start(diagram):
        gaps.append("Missing Start event")
    if process_model.ends() and not _has_end(diagram):
        gaps.append("Missing End event")

    activity_labels = _activity_labels(diagram)
    all_labels = _node_labels(diagram)
    for el in process_model.activities():
        pool = activity_labels or all_labels
        if not any(_label_match(el.label, cand) for cand in pool):
            where = f" (lane: {el.lane})" if el.lane else ""
            gaps.append(f"Missing activity{where}: '{el.label}'")

    decision_labels = _decision_labels(diagram)
    for el in process_model.decisions():
        if not any(_label_match(el.label, cand, min_ratio=0.5) for cand in decision_labels + all_labels):
            where = f" (lane: {el.lane})" if el.lane else ""
            gaps.append(f"Missing decision gateway{where}: '{el.label}'")

    edge_labels = _edge_labels(diagram)
    for el in process_model.decisions():
        for br in el.branches:
            if not br.label.strip():
                continue
            if not any(_label_match(br.label, cand, min_ratio=0.45) for cand in edge_labels):
                gaps.append(
                    f"Missing decision branch edge labeled '{br.label}' "
                    f"for decision '{el.label}'"
                )

    # Each decision should have at least 2 outgoing edges
    outdeg = _decision_outdegree(diagram)
    decision_nodes = [
        n for n in diagram.nodes if n.type in {"decision", "gateway_xor", "gateway_and", "gateway"}
    ]
    expected_decisions = len(process_model.decisions())
    if expected_decisions and len(decision_nodes) < expected_decisions:
        gaps.append(
            f"Expected at least {expected_decisions} decision gateway(s), "
            f"found {len(decision_nodes)}"
        )
    for node in decision_nodes:
        if outdeg.get(node.id, 0) < 2:
            gaps.append(
                f"Decision '{node.label or node.id}' must have at least two outgoing branches"
            )

    # De-dupe while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for g in gaps:
        if g not in seen:
            seen.add(g)
            unique.append(g)
    return unique


def coverage_revision_issues(gaps: list[str]) -> list[str]:
    return [
        "PROMPT COVERAGE GAP — add the missing element without inventing unrelated flows:",
        *[f"• {g}" for g in gaps],
    ]
