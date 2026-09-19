"""Two-agent diagram generation: Generator → QC Auditor (with optional one revision)."""

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
    QC_SYSTEM_INSTRUCTION,
    build_qc_audit_prompt,
    build_revision_prompt,
)
from app.schemas.diagram import DiagramDocument, DiagramType
from app.schemas.generation import AgentTraceEntry, GenerateDiagramResponse, QCAuditResult
from app.services.diagram_generator import _extract_json_object, _parse_diagram_json
from app.services.diagram_normalizer import normalize_diagram

TraceCallback = Callable[[AgentTraceEntry], None]

MAX_REVISION_ROUNDS = 1


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
) -> DiagramDocument:
    if revision_context:
        user_content = revision_context
    else:
        existing_json = existing.model_dump_json(by_alias=True) if existing else None
        user_content = build_diagram_user_prompt(diagram_type, user_prompt, existing_json)

    raw = _call_json_model(
        system_instruction=DIAGRAM_SYSTEM_INSTRUCTION,
        user_content=user_content,
        temperature=0.7,
    )
    return _parse_diagram_json(raw, diagram_type)


def _run_qc_audit(
    diagram_type: DiagramType,
    user_prompt: str,
    diagram: DiagramDocument,
) -> QCAuditResult:
    raw = _call_json_model(
        system_instruction=QC_SYSTEM_INSTRUCTION,
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


def generate_diagram_with_qc(
    diagram_type: DiagramType,
    user_prompt: str,
    existing: DiagramDocument | None = None,
    on_trace: TraceCallback | None = None,
) -> GenerateDiagramResponse:
    trace: list[AgentTraceEntry] = []
    step = 1
    revision_applied = False
    all_recommendations: list[str] = []

    _append_trace(
        trace,
        step=step,
        agent="system",
        phase="start",
        message="Starting two-agent generation pipeline (Generator → QC Auditor).",
        on_entry=on_trace,
    )
    step += 1

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

    diagram = _generate_diagram_document(diagram_type, user_prompt, existing)
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

    _append_trace(
        trace,
        step=step,
        agent="qc_auditor",
        phase="review",
        message="QC Auditor is reviewing for missing modules and structural errors…",
        on_entry=on_trace,
    )
    step += 1

    audit = _run_qc_audit(diagram_type, user_prompt, diagram)
    all_recommendations.extend(audit.recommendations)

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

    if audit.revision_required and audit.blocking_issues and MAX_REVISION_ROUNDS > 0:
        revision_applied = True
        _append_trace(
            trace,
            step=step,
            agent="system",
            phase="revision_handoff",
            message="Sending blocking issues back to the Generator for one revision pass.",
            detail="\n".join(f"• {issue}" for issue in audit.blocking_issues),
            on_entry=on_trace,
        )
        step += 1

        revision_prompt = build_revision_prompt(
            diagram_type,
            user_prompt,
            diagram,
            audit.blocking_issues,
        )
        _append_trace(
            trace,
            step=step,
            agent="generator",
            phase="revision",
            message="Generator is applying QC fixes…",
            on_entry=on_trace,
        )
        step += 1

        diagram = _generate_diagram_document(
            diagram_type,
            user_prompt,
            revision_context=revision_prompt,
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

        _append_trace(
            trace,
            step=step,
            agent="qc_auditor",
            phase="re_review",
            message="QC Auditor is re-checking the revised diagram…",
            on_entry=on_trace,
        )
        step += 1

        audit = _run_qc_audit(diagram_type, user_prompt, diagram)
        for rec in audit.recommendations:
            if rec not in all_recommendations:
                all_recommendations.append(rec)

        _append_trace(
            trace,
            step=step,
            agent="qc_auditor",
            phase="final_verdict",
            message=audit.summary or "Final review complete.",
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
