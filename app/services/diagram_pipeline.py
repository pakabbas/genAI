"""Multi-agent diagram generation: Requirements Analyst → Generator → QC Auditor."""

from __future__ import annotations

import json
from typing import Callable

from google import genai
from google.genai import types

from app.config import get_settings
from app.prompts.diagrams import (
    DIAGRAM_SYSTEM_INSTRUCTION,
    DIAGRAM_TYPE_LABELS,
    build_diagram_user_prompt,
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
from app.services.process_coverage import (
    PROCESS_ORIENTED_TYPES,
    coverage_revision_issues,
    extract_process_model,
    process_model_brief,
    validate_process_coverage,
)
from app.services.prompt_guard import reject_if_non_diagram

TraceCallback = Callable[[AgentTraceEntry], None]

MAX_REVISION_ROUNDS = 2


def _client_and_model():
    settings = get_settings()
    api_key = settings["gemini_api_key"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Set it in your .env file.")
    return genai.Client(api_key=api_key), settings["gemini_model"]


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
    entry = AgentTraceEntry(step=step, agent=agent, phase=phase, message=message, detail=detail)
    trace.append(entry)
    if on_entry:
        on_entry(entry)


def _call_json_model(
    *,
    system_instruction: str,
    user_content: str,
    temperature: float = 0.5,
) -> str:
    client, model = _client_and_model()
    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            top_p=0.9,
            max_output_tokens=16384,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response. Please try again.")
    return text


def _generate_diagram_document(
    diagram_type: DiagramType,
    user_prompt: str,
    existing: DiagramDocument | None = None,
    revision_context: str | None = None,
    process_inventory: str | None = None,
) -> DiagramDocument:
    if revision_context:
        user_content = revision_context
    else:
        existing_json = existing.model_dump_json(by_alias=True) if existing else None
        user_content = build_diagram_user_prompt(
            diagram_type,
            user_prompt,
            existing_json,
            process_inventory=process_inventory,
        )

    raw = _call_json_model(
        system_instruction=DIAGRAM_SYSTEM_INSTRUCTION,
        user_content=user_content,
        temperature=0.55,
    )
    return _parse_diagram_json(raw, diagram_type)


def _run_qc_audit(
    diagram_type: DiagramType,
    user_prompt: str,
    diagram: DiagramDocument,
) -> QCAuditResult:
    raw = _call_json_model(
        system_instruction=qc_system_for(diagram_type),
        user_content=build_qc_audit_prompt(diagram_type, user_prompt, diagram),
        temperature=0.2,
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
) -> QCAuditResult:
    if not gaps:
        return audit
    blocking = list(audit.blocking_issues)
    for gap in gaps:
        issue = f"Prompt coverage: {gap}"
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
) -> GenerateDiagramResponse:
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

    # Process-oriented types: derive structured inventory before drawing
    if diagram_type in PROCESS_ORIENTED_TYPES:
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
        message="Generator is composing the diagram from toolbox shapes…",
        detail=f"Diagram type: {DIAGRAM_TYPE_LABELS[diagram_type]}",
        on_entry=on_trace,
    )
    step += 1

    diagram = _generate_diagram_document(
        diagram_type,
        generation_prompt,
        existing,
        process_inventory=process_inventory,
    )
    diagram = normalize_diagram(diagram_type, diagram)

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
            process_model, diagram, diagram_type=diagram_type
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

    _append_trace(
        trace,
        step=step,
        agent="qc_auditor",
        phase="review",
        message="QC Auditor is reviewing for missing modules and structural errors…",
        on_entry=on_trace,
    )
    step += 1

    audit = _run_qc_audit(diagram_type, qc_prompt, diagram)
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
    while audit.revision_required and audit.blocking_issues and rounds < MAX_REVISION_ROUNDS:
        rounds += 1
        revision_applied = True
        _append_trace(
            trace,
            step=step,
            agent="system",
            phase="revision_handoff",
            message=f"Sending blocking issues back to the Generator (revision {rounds}/{MAX_REVISION_ROUNDS}).",
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
                process_model, diagram, diagram_type=diagram_type
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

        audit = _run_qc_audit(diagram_type, qc_prompt, diagram)
        audit = _merge_coverage_into_audit(audit, coverage_gaps)
        # Prefer the latest QC recommendations (drop stale notes from prior drafts).
        all_recommendations = list(audit.recommendations)

        _append_trace(
            trace,
            step=step,
            agent="qc_auditor",
            phase="final_verdict" if rounds >= MAX_REVISION_ROUNDS or not audit.revision_required else "verdict",
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
        diagram_type_label=DIAGRAM_TYPE_LABELS[diagram_type],
        qc_approved=qc_approved,
        revision_applied=revision_applied,
        recommendations=all_recommendations[:8],
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
