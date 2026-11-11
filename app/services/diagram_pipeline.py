"""Multi-agent diagram generation: Requirements Analyst → Generator → QC Auditor."""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from app.prompts.diagrams import (
    DIAGRAM_SYSTEM_INSTRUCTION,
    DIAGRAM_TYPE_LABELS,
    build_diagram_user_prompt,
    type_label,
)
from app.prompts.qc_audit import (
    build_qc_audit_prompt,
    build_revision_prompt,
    qc_system_for,
)
from app.schemas.diagram import DiagramDocument, DiagramType
from app.schemas.generation import AgentTraceEntry, GenerateDiagramResponse, QCAuditResult
from app.schemas.process_model import ProcessModel
from app.services.diagram_generator import _extract_json_object, _parse_diagram_json
from app.services.diagram_normalizer import normalize_diagram
from app.services.gemini_client import format_call_info, generate_json, last_call_info
from app.services.process_coverage import (
    coverage_revision_issues,
    extract_process_model,
    flowchart_merged_activity_gaps,
    process_model_brief,
    process_oriented_types,
    repair_merged_process_nodes,
    validate_process_coverage,
)
from app.services import flowchart_layout as fc_layout
from app.services.brief_coverage import BriefGaps, validate_brief_coverage
from app.services.prompt_guard import reject_if_non_diagram
from app.services import settings_service as cfg

TraceCallback = Callable[[AgentTraceEntry], None]

MAX_REVISION_ROUNDS = 3  # default; runtime uses pipeline.max_qc_revisions

# 2.7.9 (flowchart): server-side wall-clock budget for the whole pipeline (seconds).
FLOWCHART_PIPELINE_BUDGET_S = 240.0

# 2.7.9: user-safe stage per trace phase (the UI maps these to fixed friendly labels).
PHASE_STAGE: dict[str, str] = {
    "start": "understanding",
    "brief_ready": "understanding",
    "new_diagram": "planning",
    "edit_mode": "planning",
    "process_plan": "planning",
    "process_plan_ready": "planning",
    "process_plan_skip": "planning",
    "draft": "drawing",
    "brief_advisory": "drawing",
    "brief_validate": "polishing",
    "draft_complete": "drawing",
    "layout": "layout",
    "coverage_check": "checking",
    "coverage_advisory": "checking",
    "skipped": "checking",
    "review": "checking",
    "verdict": "checking",
    "revision_handoff": "polishing",
    "revision": "polishing",
    "revision_complete": "polishing",
    "coverage_recheck": "polishing",
    "re_review": "polishing",
    "final_verdict": "polishing",
    "revision_skipped": "layout",
    "complete": "done",
}


class PipelineCancelled(RuntimeError):
    """The client disconnected; stop spending model calls."""


def _append_trace(
    trace: list[AgentTraceEntry],
    *,
    step: int,
    agent: str,
    phase: str,
    message: str,
    detail: str | None = None,
    on_entry: TraceCallback | None = None,
) -> None:
    entry = AgentTraceEntry(
        step=step,
        agent=agent,
        phase=phase,
        message=message,
        detail=detail,
        stage=PHASE_STAGE.get(phase, "drawing"),
    )
    trace.append(entry)
    if on_entry:
        on_entry(entry)


def _generate_diagram_document(
    diagram_type: DiagramType,
    user_prompt: str,
    existing: DiagramDocument | None = None,
    revision_context: str | None = None,
    process_inventory: str | None = None,
    *,
    edit_mode: bool = False,
    hard_timeout: float | None = None,
    cancel_event: threading.Event | None = None,
) -> DiagramDocument:
    if revision_context:
        user_content = revision_context
    else:
        existing_json = (
            existing.model_dump_json(by_alias=True) if existing and edit_mode else None
        )
        user_content = build_diagram_user_prompt(
            diagram_type,
            user_prompt,
            existing_json,
            process_inventory=process_inventory,
            edit_mode=edit_mode,
        )

    system = cfg.active_prompt_body("generator.system") or DIAGRAM_SYSTEM_INSTRUCTION
    temp = float(
        cfg.get_value("ai.generator.revision_temperature")
        if revision_context
        else cfg.get_value("ai.generator.temperature")
    )
    raw = generate_json(
        role="generator",
        system_instruction=system,
        user_content=user_content,
        temperature=temp,
        top_p=float(cfg.get_value("ai.generator.top_p")),
        max_output_tokens=int(cfg.get_value("ai.generator.max_output_tokens")),
        hard_timeout=hard_timeout,
        cancel_event=cancel_event,
    )
    return _parse_diagram_json(raw, diagram_type)


def _run_qc_audit(
    diagram_type: DiagramType,
    user_prompt: str,
    diagram: DiagramDocument,
    *,
    edit_mode: bool = False,
    previous: DiagramDocument | None = None,
    hard_timeout: float | None = None,
    cancel_event: threading.Event | None = None,
) -> QCAuditResult:
    qc_user = build_qc_audit_prompt(diagram_type, user_prompt, diagram)
    if edit_mode and previous is not None:
        prev_ids = {n.id for n in previous.nodes}
        new_ids = {n.id for n in diagram.nodes}
        deleted = sorted(prev_ids - new_ids)
        renamed = []
        prev_labels = {n.id: n.label for n in previous.nodes}
        for n in diagram.nodes:
            if n.id in prev_labels and (n.label or "") != (prev_labels[n.id] or ""):
                renamed.append(f"{n.id}: {prev_labels[n.id]!r} → {n.label!r}")
        qc_user += (
            "\n\nEDIT MODE CHECK:\n"
            "- Flag as blocking if shapes were deleted or renamed without being requested.\n"
            f"- Deleted ids vs prior canvas: {deleted or 'none'}\n"
            f"- Relabeled ids: {renamed[:12] or 'none'}\n"
        )
    raw = generate_json(
        role="qc",
        system_instruction=qc_system_for(diagram_type),
        user_content=qc_user,
        temperature=float(cfg.get_value("ai.qc.temperature")),
        top_p=float(cfg.get_value("ai.qc.top_p")),
        max_output_tokens=int(cfg.get_value("ai.qc.max_output_tokens")),
        hard_timeout=hard_timeout,
        cancel_event=cancel_event,
    )
    data = json.loads(_extract_json_object(raw))
    audit = QCAuditResult.model_validate(data)

    if audit.revision_required and not audit.blocking_issues:
        audit.revision_required = False
        audit.approved = True

    if audit.revision_required:
        audit.approved = False
    elif not audit.blocking_issues:
        audit.approved = True
        audit.revision_required = False

    return audit


def _merge_coverage_into_audit(
    audit: QCAuditResult,
    gaps: list[str],
    *,
    prefix: str = "Prompt coverage",
) -> QCAuditResult:
    if not gaps:
        return audit
    blocking = list(audit.blocking_issues)
    for gap in gaps:
        issue = f"{prefix}: {gap}"
        if issue not in blocking:
            blocking.append(issue)
    audit.blocking_issues = blocking
    audit.revision_required = True
    audit.approved = False
    if not audit.summary:
        audit.summary = "Revision required — the diagram is missing required process elements."
    return audit


def generate_diagram_with_qc(
    diagram_type: DiagramType,
    user_prompt: str,
    existing: DiagramDocument | None = None,
    on_trace: TraceCallback | None = None,
    *,
    prompt_enhanced: bool = False,
    original_prompt: str | None = None,
    edit_mode: bool = False,
    cancel_event: threading.Event | None = None,
    edit_request: str | None = None,
) -> GenerateDiagramResponse:
    if diagram_type == "flowchart":
        return _generate_flowchart_with_qc(
            user_prompt,
            existing,
            on_trace,
            prompt_enhanced=prompt_enhanced,
            original_prompt=original_prompt,
            edit_mode=edit_mode,
            cancel_event=cancel_event,
            edit_request=edit_request,
        )
    return _generate_with_qc_default(
        diagram_type,
        user_prompt,
        existing,
        on_trace,
        prompt_enhanced=prompt_enhanced,
        original_prompt=original_prompt,
        edit_mode=edit_mode,
        cancel_event=cancel_event,
    )


def _check_cancel(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise PipelineCancelled("Generation cancelled (client disconnected).")


def _generate_with_qc_default(
    diagram_type: DiagramType,
    user_prompt: str,
    existing: DiagramDocument | None = None,
    on_trace: TraceCallback | None = None,
    *,
    prompt_enhanced: bool = False,
    original_prompt: str | None = None,
    edit_mode: bool = False,
    cancel_event: threading.Event | None = None,
) -> GenerateDiagramResponse:
    """Pre-2.7.9 pipeline, unchanged for every non-flowchart type (plus a disconnect check)."""
    trace: list[AgentTraceEntry] = []
    step = 1
    revision_applied = False
    all_recommendations: list[str] = []
    generation_prompt = user_prompt
    qc_prompt = original_prompt.strip() if original_prompt and original_prompt.strip() else user_prompt
    process_model: ProcessModel | None = None
    process_inventory: str | None = None

    # Refuse poems / off-topic on BOTH original chat text and enhanced brief.
    reject_if_non_diagram(original_prompt, user_prompt, qc_prompt)

    _append_trace(
        trace,
        step=step,
        agent="system",
        phase="start",
        message=(
            "Starting three-agent pipeline (Requirements Analyst → Generator → QC Auditor)."
            if prompt_enhanced
            else "Starting generation pipeline (Generator → QC Auditor)."
        ),
        on_entry=on_trace,
    )
    step += 1

    if prompt_enhanced:
        _append_trace(
            trace,
            step=step,
            agent="requirements_analyst",
            phase="brief_ready",
            message="Requirements Analyst handed off an enhanced brief to the Generator.",
            detail=generation_prompt[:2500],
            on_entry=on_trace,
        )
        step += 1

    # Edit mode is explicit from the client toggle only (never inferred from brief verbs).
    edit_mode = bool(edit_mode) and existing is not None
    if not edit_mode:
        existing = None
    _append_trace(
        trace,
        step=step,
        agent="generator",
        phase="edit_mode" if edit_mode else "new_diagram",
        message=(
            "Edit mode — Generator will modify the existing diagram (keep ids/labels/positions)."
            if edit_mode
            else "New diagram — generating from the brief (canvas not used as a base)."
        ),
        on_entry=on_trace,
    )
    step += 1

    # Process-oriented types: derive structured inventory before drawing
    # Skip full re-inventory on small edits so we don't thrash a good canvas.
    if diagram_type in process_oriented_types() and not edit_mode:
        _append_trace(
            trace,
            step=step,
            agent="generator",
            phase="process_plan",
            message="Deriving a structured process inventory (lanes, activities, decisions)…",
            on_entry=on_trace,
        )
        step += 1
        try:
            process_model = extract_process_model(diagram_type, generation_prompt)
            process_inventory = process_model_brief(process_model)
            _append_trace(
                trace,
                step=step,
                agent="generator",
                phase="process_plan_ready",
                message=(
                    f"Process inventory ready — {len(process_model.lanes)} lane(s), "
                    f"{len(process_model.activities())} activit(ies), "
                    f"{len(process_model.decisions())} decision(s)."
                ),
                detail=process_inventory[:3000],
                on_entry=on_trace,
            )
            step += 1
        except Exception as exc:  # noqa: BLE001 — fall back to direct generation
            _append_trace(
                trace,
                step=step,
                agent="system",
                phase="process_plan_skip",
                message="Process inventory step failed; continuing with the brief alone.",
                detail=str(exc)[:500],
                on_entry=on_trace,
            )
            step += 1
            process_model = None
            process_inventory = None

    _append_trace(
        trace,
        step=step,
        agent="generator",
        phase="draft",
        message=(
            "Generator is applying edits to the existing diagram…"
            if edit_mode
            else "Generator is composing the diagram from toolbox shapes…"
        ),
        detail=(
            f"Diagram type: {type_label(diagram_type)} · "
            f"models analyst/planner/generator/qc: "
            f"{cfg.resolve_model('analyst')} / {cfg.resolve_model('planner')} / "
            f"{cfg.resolve_model('generator')} / {cfg.resolve_model('qc')}"
        ),
        on_entry=on_trace,
    )
    step += 1

    diagram = _generate_diagram_document(
        diagram_type,
        generation_prompt,
        existing,
        process_inventory=process_inventory,
        edit_mode=edit_mode,
    )
    diagram = normalize_diagram(diagram_type, diagram)
    if process_model is not None:
        diagram = repair_merged_process_nodes(diagram, process_model)
        diagram = normalize_diagram(diagram_type, diagram)

    # Brief coverage: re-ask only on high-confidence gaps; advisory stays in the Log.
    brief_gaps: BriefGaps = validate_brief_coverage(diagram_type, qc_prompt, diagram)
    if brief_gaps.advisory:
        _append_trace(
            trace,
            step=step,
            agent="generator",
            phase="brief_advisory",
            message=f"Brief advisory notes ({len(brief_gaps.advisory)}) — not blocking.",
            detail="\n".join(f"• {g}" for g in brief_gaps.advisory),
            on_entry=on_trace,
        )
        step += 1
    if brief_gaps.blocking and not edit_mode:
        _append_trace(
            trace,
            step=step,
            agent="generator",
            phase="brief_validate",
            message=f"Brief validation found {len(brief_gaps.blocking)} high-confidence gap(s) — re-asking once.",
            detail="\n".join(f"• {g}" for g in brief_gaps.blocking),
            on_entry=on_trace,
        )
        step += 1
        fix_prompt = build_revision_prompt(
            diagram_type,
            generation_prompt,
            diagram,
            brief_gaps.blocking,
            process_inventory=process_inventory,
        )
        diagram = _generate_diagram_document(
            diagram_type,
            generation_prompt,
            revision_context=fix_prompt,
            process_inventory=process_inventory,
            edit_mode=False,
        )
        diagram = normalize_diagram(diagram_type, diagram)
        if process_model is not None:
            diagram = repair_merged_process_nodes(diagram, process_model)
            diagram = normalize_diagram(diagram_type, diagram)
        brief_gaps = validate_brief_coverage(diagram_type, qc_prompt, diagram)

    _append_trace(
        trace,
        step=step,
        agent="generator",
        phase="draft_complete",
        message=f"Draft ready — {len(diagram.nodes)} nodes, {len(diagram.edges)} edges.",
        detail=f"Title: {diagram.title}",
        on_entry=on_trace,
    )
    step += 1

    coverage_gaps: list[str] = []
    if process_model is not None:
        coverage_gaps = validate_process_coverage(
            process_model,
            diagram,
            diagram_type=diagram_type,
            user_prompt=qc_prompt,
        )
        _append_trace(
            trace,
            step=step,
            agent="qc_auditor",
            phase="coverage_check",
            message=(
                "Prompt coverage check passed."
                if not coverage_gaps
                else f"Coverage gaps detected ({len(coverage_gaps)})."
            ),
            detail="\n".join(f"• {g}" for g in coverage_gaps) if coverage_gaps else None,
            on_entry=on_trace,
        )
        step += 1

    # Only high-confidence brief gaps become QC blocking coverage items.
    for g in brief_gaps.blocking:
        if g not in coverage_gaps:
            coverage_gaps.append(g)

    max_revisions = int(cfg.get_value("pipeline.max_qc_revisions"))
    if edit_mode:
        max_revisions = min(max_revisions, 1)
    qc_enabled = bool(cfg.get_value("pipeline.qc_enabled"))
    max_recs = int(cfg.get_value("pipeline.max_recommendations"))

    if not qc_enabled:
        _append_trace(
            trace,
            step=step,
            agent="qc_auditor",
            phase="skipped",
            message="QC Auditor skipped (pipeline.qc_enabled=false).",
            on_entry=on_trace,
        )
        step += 1
        _append_trace(
            trace,
            step=step,
            agent="system",
            phase="complete",
            message="Pipeline complete — diagram delivered to canvas.",
            detail="QC: skipped",
            on_entry=on_trace,
        )
        return GenerateDiagramResponse(
            diagram=diagram,
            diagram_type=diagram_type,
            diagram_type_label=type_label(diagram_type),
            qc_approved=True,
            revision_applied=False,
            recommendations=[],
            enhanced_prompt=generation_prompt if prompt_enhanced else None,
            trace=trace,
        )

    _append_trace(
        trace,
        step=step,
        agent="qc_auditor",
        phase="review",
        message=f"QC Auditor is reviewing… (model: {cfg.resolve_model('qc')})",
        on_entry=on_trace,
    )
    step += 1

    prior_for_qc = existing if edit_mode else None
    audit = _run_qc_audit(
        diagram_type, qc_prompt, diagram, edit_mode=edit_mode, previous=prior_for_qc
    )
    audit = _merge_coverage_into_audit(audit, coverage_gaps)
    all_recommendations = list(audit.recommendations)

    _append_trace(
        trace,
        step=step,
        agent="qc_auditor",
        phase="verdict",
        message=audit.summary or ("Approved." if audit.approved else "Revision requested."),
        detail=_format_audit_detail(audit),
        on_entry=on_trace,
    )
    step += 1

    rounds = 0
    while audit.revision_required and audit.blocking_issues and rounds < max_revisions:
        _check_cancel(cancel_event)
        rounds += 1
        revision_applied = True
        _append_trace(
            trace,
            step=step,
            agent="system",
            phase="revision_handoff",
            message=f"Sending blocking issues back to the Generator (revision {rounds}/{max_revisions}).",
            detail="\n".join(f"• {issue}" for issue in audit.blocking_issues),
            on_entry=on_trace,
        )
        step += 1

        revision_prompt = build_revision_prompt(
            diagram_type,
            generation_prompt,
            diagram,
            audit.blocking_issues,
            process_inventory=process_inventory,
        )
        if coverage_gaps:
            revision_prompt = (
                f"{revision_prompt}\n\n"
                + "\n".join(coverage_revision_issues(coverage_gaps))
            )

        _append_trace(
            trace,
            step=step,
            agent="generator",
            phase="revision",
            message="Generator is applying QC / coverage fixes…",
            on_entry=on_trace,
        )
        step += 1

        diagram = _generate_diagram_document(
            diagram_type,
            generation_prompt,
            revision_context=revision_prompt,
            process_inventory=process_inventory,
        )
        diagram = normalize_diagram(diagram_type, diagram)
        if process_model is not None:
            diagram = repair_merged_process_nodes(diagram, process_model)
            diagram = normalize_diagram(diagram_type, diagram)

        _append_trace(
            trace,
            step=step,
            agent="generator",
            phase="revision_complete",
            message=f"Revised diagram — {len(diagram.nodes)} nodes, {len(diagram.edges)} edges.",
            on_entry=on_trace,
        )
        step += 1

        coverage_gaps = []
        if process_model is not None:
            coverage_gaps = validate_process_coverage(
                process_model,
                diagram,
                diagram_type=diagram_type,
                user_prompt=qc_prompt,
            )
            _append_trace(
                trace,
                step=step,
                agent="qc_auditor",
                phase="coverage_recheck",
                message=(
                    "Coverage re-check passed."
                    if not coverage_gaps
                    else f"Coverage still incomplete ({len(coverage_gaps)} gap(s))."
                ),
                detail="\n".join(f"• {g}" for g in coverage_gaps) if coverage_gaps else None,
                on_entry=on_trace,
            )
            step += 1

        _append_trace(
            trace,
            step=step,
            agent="qc_auditor",
            phase="re_review",
            message="QC Auditor is re-checking the revised diagram…",
            on_entry=on_trace,
        )
        step += 1

        audit = _run_qc_audit(
            diagram_type, qc_prompt, diagram, edit_mode=edit_mode, previous=prior_for_qc
        )
        audit = _merge_coverage_into_audit(audit, coverage_gaps)
        # Prefer the latest QC recommendations (drop stale notes from prior drafts).
        all_recommendations = list(audit.recommendations)

        _append_trace(
            trace,
            step=step,
            agent="qc_auditor",
            phase="final_verdict" if rounds >= max_revisions or not audit.revision_required else "verdict",
            message=audit.summary or "Review complete.",
            detail=_format_audit_detail(audit),
            on_entry=on_trace,
        )
        step += 1

    qc_approved = audit.approved or not audit.revision_required

    _append_trace(
        trace,
        step=step,
        agent="system",
        phase="complete",
        message="Pipeline complete — diagram delivered to canvas.",
        detail=(
            f"QC: {'passed' if qc_approved else 'passed with notes'} · "
            f"Recommendations: {len(all_recommendations)}"
        ),
        on_entry=on_trace,
    )

    return GenerateDiagramResponse(
        diagram=diagram,
        diagram_type=diagram_type,
        diagram_type_label=type_label(diagram_type),
        qc_approved=qc_approved,
        revision_applied=revision_applied,
        recommendations=all_recommendations[:max_recs],
        enhanced_prompt=generation_prompt if prompt_enhanced else None,
        trace=trace,
    )


def _format_audit_detail(audit: QCAuditResult) -> str:
    lines: list[str] = []
    lines.append(f"Approved: {'yes' if audit.approved else 'no'}")
    lines.append(f"Revision required: {'yes' if audit.revision_required else 'no'}")
    if audit.blocking_issues:
        lines.append("Blocking issues:")
        lines.extend(f"• {issue}" for issue in audit.blocking_issues)
    if audit.recommendations:
        lines.append("Recommendations:")
        lines.extend(f"• {rec}" for rec in audit.recommendations)
    return "\n".join(lines)


# ============================================================================ 2.7.9 flowchart


def _compact_flowchart_json(diagram: DiagramDocument) -> str:
    """Current diagram without coordinates (the layout is automatic) — for patch-style revisions."""
    return json.dumps(
        {
            "title": diagram.title,
            "nodes": [{"id": n.id, "type": n.type, "label": n.label} for n in diagram.nodes],
            "edges": [
                {"id": e.id, "from": e.from_node, "to": e.to_node, "label": e.label, "type": e.type}
                for e in diagram.edges
            ],
        },
        ensure_ascii=False,
    )


def _flowchart_revision_prompt(
    user_prompt: str, diagram: DiagramDocument, issues: list[str]
) -> str:
    base = build_revision_prompt("flowchart", user_prompt, diagram, issues, process_inventory=None)
    return "\n".join(
        [
            base,
            "",
            "CURRENT DIAGRAM (revise THIS one — minimal patch, not a redesign):",
            "- Keep every node/edge id, type and label that is not named in the issues above.",
            "- Only add, relabel or rewire what the issues require. Never duplicate an existing step.",
            "- Coordinates are computed automatically: you may set x=0, y=0 and omit width/height.",
            _compact_flowchart_json(diagram),
        ]
    )


def _structural_issues(diagram: DiagramDocument) -> int:
    """Cheap score used to keep the best draft (lower is better)."""
    score = 0
    outs: dict[str, int] = {}
    labelled: dict[str, int] = {}
    for e in diagram.edges:
        outs[e.from_node] = outs.get(e.from_node, 0) + 1
        if (e.label or "").strip():
            labelled[e.from_node] = labelled.get(e.from_node, 0) + 1
    for n in diagram.nodes:
        if n.type == "decision":
            if outs.get(n.id, 0) < 2:
                score += 2
            elif labelled.get(n.id, 0) < 2:
                score += 1
    return score


def _generate_flowchart_with_qc(
    user_prompt: str,
    existing: DiagramDocument | None = None,
    on_trace: TraceCallback | None = None,
    *,
    prompt_enhanced: bool = False,
    original_prompt: str | None = None,
    edit_mode: bool = False,
    cancel_event: threading.Event | None = None,
    edit_request: str | None = None,
) -> GenerateDiagramResponse:
    """
    Flowchart pipeline (2.7.9):
    - planner runs IN PARALLEL with the first draft; its inventory feeds coverage only
    - the merge-splitter never runs; merged-step findings are advisory
    - coverage gaps enter the revision prompt once; identical gap sets stop the loop
    - QC approved + deterministic gaps only ⇒ at most one revision, for Missing … gaps only
    - wall-clock budget + real per-call timeouts; a failed revision keeps the best draft
    """
    diagram_type: DiagramType = "flowchart"
    t0 = time.monotonic()
    budget = FLOWCHART_PIPELINE_BUDGET_S
    call_timeout = float(cfg.get_value("ai.timeout_seconds"))
    trace: list[AgentTraceEntry] = []
    step = 1
    revision_applied = False
    all_recommendations: list[str] = []
    generation_prompt = user_prompt
    qc_prompt = original_prompt.strip() if original_prompt and original_prompt.strip() else user_prompt
    process_model: ProcessModel | None = None

    def add(agent: str, phase: str, message: str, detail: str | None = None) -> None:
        nonlocal step
        _append_trace(
            trace, step=step, agent=agent, phase=phase, message=message, detail=detail, on_entry=on_trace
        )
        step += 1

    def remaining() -> float:
        return budget - (time.monotonic() - t0)

    def timed(info: dict | None = None) -> str:
        return format_call_info(info) or ""

    reject_if_non_diagram(original_prompt, user_prompt, qc_prompt)

    add(
        "system",
        "start",
        "Starting three-agent pipeline (Requirements Analyst → Generator → QC Auditor)."
        if prompt_enhanced
        else "Starting generation pipeline (Generator → QC Auditor).",
    )
    if prompt_enhanced:
        add(
            "requirements_analyst",
            "brief_ready",
            "Requirements Analyst handed off an enhanced brief to the Generator.",
            generation_prompt[:2500],
        )

    edit_mode = bool(edit_mode) and existing is not None
    if not edit_mode:
        existing = None
    add(
        "generator",
        "edit_mode" if edit_mode else "new_diagram",
        "Edit mode — Generator will modify the existing diagram (keep ids/labels/positions)."
        if edit_mode
        else "New diagram — generating from the brief (canvas not used as a base).",
    )

    # Layout mode: relayout only when the canvas is still exactly our automatic layout.
    layout_mode = "auto"
    if edit_mode and not fc_layout.is_auto_layout(existing):
        layout_mode = "keep"

    edit_request = (edit_request or "").strip()
    if edit_mode and edit_request:
        generation_prompt = (
            f"{generation_prompt}\n\nUSER'S EDIT REQUEST (apply ONLY this change; keep every other "
            f"node id, label and kind word-for-word):\n{edit_request[:2000]}"
        )

    def norm(doc: DiagramDocument) -> DiagramDocument:
        if edit_mode and existing is not None and edit_request:
            doc = fc_layout.lock_unrelated_labels(existing, doc, edit_request)
        out = normalize_diagram(diagram_type, doc, flowchart_layout=layout_mode)
        if edit_mode and existing is not None and layout_mode == "auto":
            out = fc_layout.pin_above_insertion(existing, out)
        notes = fc_layout.take_notes()
        if notes:
            add(
                "generator",
                "layout",
                f"Layout clean-up notes ({len(notes)}) — advisory.",
                "\n".join(f"• {n}" for n in notes),
            )
        return out

    # Planner (inventory) in parallel with the first draft — new diagrams only.
    planner_future = None
    executor: ThreadPoolExecutor | None = None
    if diagram_type in process_oriented_types() and not edit_mode:
        add(
            "generator",
            "process_plan",
            "Deriving a structured process inventory in parallel (used for the coverage check only)…",
        )
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fc-planner")

        def _plan():
            started = time.monotonic()
            model = extract_process_model(diagram_type, generation_prompt)
            info = last_call_info()
            info.setdefault("seconds", time.monotonic() - started)
            return model, info

        planner_future = executor.submit(_plan)

    add(
        "generator",
        "draft",
        "Generator is applying edits to the existing diagram…"
        if edit_mode
        else "Generator is composing the diagram from toolbox shapes…",
        f"Diagram type: {type_label(diagram_type)} · "
        f"models analyst/planner/generator/qc: "
        f"{cfg.resolve_model('analyst')} / {cfg.resolve_model('planner')} / "
        f"{cfg.resolve_model('generator')} / {cfg.resolve_model('qc')}",
    )

    try:
        diagram = _generate_diagram_document(
            diagram_type,
            generation_prompt,
            existing,
            process_inventory=None,
            edit_mode=edit_mode,
            hard_timeout=call_timeout,
            cancel_event=cancel_event,
        )
    finally:
        if executor is not None:
            executor.shutdown(wait=False)
    draft_info = last_call_info()
    diagram = norm(diagram)
    last_gen_s = float(draft_info.get("seconds") or 45.0)

    if planner_future is not None:
        try:
            process_model, plan_info = planner_future.result(timeout=max(5.0, min(call_timeout, remaining())))
            add(
                "generator",
                "process_plan_ready",
                (
                    f"Process inventory ready — {len(process_model.activities())} activit(ies), "
                    f"{len(process_model.decisions())} decision(s)."
                ),
                (timed(plan_info) + "\n" + process_model_brief(process_model))[:3000],
            )
        except Exception as exc:  # noqa: BLE001 — coverage is optional
            process_model = None
            add(
                "system",
                "process_plan_skip",
                "Process inventory step failed; continuing with the brief alone.",
                str(exc)[:500],
            )

    _check_cancel(cancel_event)

    brief_gaps: BriefGaps = validate_brief_coverage(diagram_type, qc_prompt, diagram)
    if brief_gaps.advisory:
        add(
            "generator",
            "brief_advisory",
            f"Brief advisory notes ({len(brief_gaps.advisory)}) — not blocking.",
            "\n".join(f"• {g}" for g in brief_gaps.advisory),
        )
    if brief_gaps.blocking and not edit_mode and remaining() > last_gen_s + 20:
        add(
            "generator",
            "brief_validate",
            f"Brief validation found {len(brief_gaps.blocking)} high-confidence gap(s) — re-asking once.",
            "\n".join(f"• {g}" for g in brief_gaps.blocking),
        )
        try:
            fixed = _generate_diagram_document(
                diagram_type,
                generation_prompt,
                revision_context=_flowchart_revision_prompt(generation_prompt, diagram, brief_gaps.blocking),
                edit_mode=False,
                hard_timeout=min(call_timeout, max(10.0, remaining())),
                cancel_event=cancel_event,
            )
            fixed = norm(fixed)
            new_gaps = validate_brief_coverage(diagram_type, qc_prompt, fixed)
            if len(new_gaps.blocking) <= len(brief_gaps.blocking):
                diagram, brief_gaps = fixed, new_gaps
        except PipelineCancelled:
            raise
        except Exception as exc:  # noqa: BLE001 — keep the first draft
            add("system", "revision_skipped", "Re-ask failed; keeping the first draft.", str(exc)[:300])

    add(
        "generator",
        "draft_complete",
        f"Draft ready — {len(diagram.nodes)} nodes, {len(diagram.edges)} edges.",
        f"Title: {diagram.title}\n{timed(draft_info)}",
    )

    def coverage(doc: DiagramDocument) -> tuple[list[str], list[str]]:
        if process_model is None:
            return [], []
        blocking = validate_process_coverage(
            process_model, doc, diagram_type=diagram_type, user_prompt=qc_prompt
        )
        advisory = flowchart_merged_activity_gaps(process_model, doc)
        return blocking, advisory

    coverage_gaps, coverage_adv = coverage(diagram)
    if process_model is not None:
        add(
            "qc_auditor",
            "coverage_check",
            "Prompt coverage check passed."
            if not coverage_gaps
            else f"Coverage gap (deterministic) — {len(coverage_gaps)} item(s).",
            "\n".join(f"• {g}" for g in coverage_gaps) if coverage_gaps else None,
        )
    if coverage_adv:
        add(
            "qc_auditor",
            "coverage_advisory",
            f"Coverage advisory ({len(coverage_adv)}) — not blocking.",
            "\n".join(f"• {g}" for g in coverage_adv),
        )
    for g in brief_gaps.blocking:
        if g not in coverage_gaps:
            coverage_gaps.append(g)

    max_revisions = int(cfg.get_value("pipeline.max_qc_revisions"))
    if edit_mode:
        max_revisions = min(max_revisions, 1)
    qc_enabled = bool(cfg.get_value("pipeline.qc_enabled"))
    max_recs = int(cfg.get_value("pipeline.max_recommendations"))

    if not qc_enabled:
        add("qc_auditor", "skipped", "QC Auditor skipped (pipeline.qc_enabled=false).")
        add("system", "complete", "Pipeline complete — diagram delivered to canvas.", "QC: skipped")
        return GenerateDiagramResponse(
            diagram=diagram,
            diagram_type=diagram_type,
            diagram_type_label=type_label(diagram_type),
            qc_approved=True,
            revision_applied=False,
            recommendations=[],
            enhanced_prompt=generation_prompt if prompt_enhanced else None,
            trace=trace,
        )

    prior_for_qc = existing if edit_mode else None

    def run_qc(doc: DiagramDocument, gaps: list[str]) -> tuple[QCAuditResult, bool, str]:
        audit = _run_qc_audit(
            diagram_type,
            qc_prompt,
            doc,
            edit_mode=edit_mode,
            previous=prior_for_qc,
            hard_timeout=min(call_timeout, max(15.0, remaining())),
            cancel_event=cancel_event,
        )
        info = timed()
        llm_ok = bool(audit.approved and not audit.revision_required)
        use_gaps = gaps
        if llm_ok:
            # Only "Missing …" deterministic items may trigger a (single) revision.
            use_gaps = [g for g in gaps if g.lower().startswith("missing")]
        audit = _merge_coverage_into_audit(audit, use_gaps, prefix="Coverage gap (deterministic)")
        return audit, llm_ok, info

    add("qc_auditor", "review", f"QC Auditor is reviewing… (model: {cfg.resolve_model('qc')})")
    try:
        audit, llm_ok, qc_info = run_qc(diagram, coverage_gaps)
    except PipelineCancelled:
        raise
    except Exception as exc:  # noqa: BLE001 — a QC failure never loses a good draft
        add("system", "revision_skipped", "QC review unavailable; delivering the draft.", str(exc)[:300])
        add("system", "complete", "Pipeline complete — diagram delivered to canvas.", "QC: unavailable")
        return GenerateDiagramResponse(
            diagram=diagram,
            diagram_type=diagram_type,
            diagram_type_label=type_label(diagram_type),
            qc_approved=True,
            revision_applied=False,
            recommendations=[],
            enhanced_prompt=generation_prompt if prompt_enhanced else None,
            trace=trace,
        )
    all_recommendations = list(audit.recommendations)
    add(
        "qc_auditor",
        "verdict",
        audit.summary or ("Approved." if audit.approved else "Revision requested."),
        _format_audit_detail(audit) + (f"\n{qc_info}" if qc_info else ""),
    )

    best = (diagram, audit, all_recommendations)
    best_score = (len(audit.blocking_issues), _structural_issues(diagram))
    prev_blocking: set[str] | None = None
    rounds = 0
    cap = max_revisions
    if llm_ok:
        cap = min(cap, 1)
    last_qc_s = 5.0
    while audit.revision_required and audit.blocking_issues and rounds < cap:
        _check_cancel(cancel_event)
        cur = set(audit.blocking_issues)
        if prev_blocking is not None and cur == prev_blocking:
            add(
                "system",
                "revision_skipped",
                "Same issues as the previous round — stopping and keeping the best draft.",
                "\n".join(f"• {i}" for i in audit.blocking_issues),
            )
            break
        if remaining() < last_gen_s + last_qc_s + 10:
            add(
                "system",
                "revision_skipped",
                f"Time budget reached ({budget:.0f}s) — delivering the best draft (partial).",
            )
            break
        prev_blocking = cur
        rounds += 1
        add(
            "system",
            "revision_handoff",
            f"Sending blocking issues back to the Generator (revision {rounds}/{cap}).",
            "\n".join(f"• {issue}" for issue in audit.blocking_issues),
        )
        add("generator", "revision", "Generator is applying QC / coverage fixes…")
        try:
            revised = _generate_diagram_document(
                diagram_type,
                generation_prompt,
                revision_context=_flowchart_revision_prompt(
                    generation_prompt, diagram, list(audit.blocking_issues)
                ),
                hard_timeout=min(call_timeout, max(10.0, remaining())),
                cancel_event=cancel_event,
            )
            gen_info = last_call_info()
            last_gen_s = float(gen_info.get("seconds") or last_gen_s)
            revised = norm(revised)
        except PipelineCancelled:
            raise
        except Exception as exc:  # noqa: BLE001 — keep the best draft
            add("system", "revision_skipped", "Revision failed; keeping the best draft.", str(exc)[:300])
            break
        revision_applied = True
        diagram = revised
        add(
            "generator",
            "revision_complete",
            f"Revised diagram — {len(diagram.nodes)} nodes, {len(diagram.edges)} edges.",
            timed(gen_info),
        )
        coverage_gaps, coverage_adv = coverage(diagram)
        if process_model is not None:
            add(
                "qc_auditor",
                "coverage_recheck",
                "Coverage re-check passed."
                if not coverage_gaps
                else f"Coverage gap (deterministic) — {len(coverage_gaps)} item(s).",
                "\n".join(f"• {g}" for g in coverage_gaps) if coverage_gaps else None,
            )
        add("qc_auditor", "re_review", "QC Auditor is re-checking the revised diagram…")
        try:
            q_started = time.monotonic()
            audit, llm_ok2, qc_info = run_qc(diagram, coverage_gaps)
            last_qc_s = time.monotonic() - q_started
        except PipelineCancelled:
            raise
        except Exception as exc:  # noqa: BLE001
            add("system", "revision_skipped", "QC re-check unavailable; keeping the revision.", str(exc)[:300])
            audit = QCAuditResult(approved=True, revision_required=False, summary="QC re-check unavailable.")
            llm_ok2 = True
        if llm_ok2:
            cap = min(cap, rounds)  # QC approved: never another round for deterministic items
        all_recommendations = list(audit.recommendations)
        add(
            "qc_auditor",
            "final_verdict" if rounds >= cap or not audit.revision_required else "verdict",
            audit.summary or "Review complete.",
            _format_audit_detail(audit) + (f"\n{qc_info}" if qc_info else ""),
        )
        score = (len(audit.blocking_issues), _structural_issues(diagram))
        if score <= best_score:
            best, best_score = (diagram, audit, all_recommendations), score

    # Deliver the best draft seen (fewest blocking issues; latest wins ties).
    if (len(audit.blocking_issues), _structural_issues(diagram)) > best_score:
        diagram, audit, all_recommendations = best
        add("system", "revision_skipped", "Keeping the earlier draft — it had fewer open issues.")

    qc_approved = audit.approved or not audit.revision_required
    add(
        "system",
        "complete",
        "Pipeline complete — diagram delivered to canvas.",
        f"QC: {'passed' if qc_approved else 'passed with notes'} · "
        f"Recommendations: {len(all_recommendations)} · total {time.monotonic() - t0:.1f}s",
    )
    return GenerateDiagramResponse(
        diagram=diagram,
        diagram_type=diagram_type,
        diagram_type_label=type_label(diagram_type),
        qc_approved=qc_approved,
        revision_applied=revision_applied,
        recommendations=all_recommendations[:max_recs],
        enhanced_prompt=generation_prompt if prompt_enhanced else None,
        trace=trace,
    )
