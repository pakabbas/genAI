"""QC auditor prompt builders — type-specific system instructions live under app/prompts/qc/."""

from app.prompts.diagrams import DIAGRAM_TYPE_GUIDANCE, DIAGRAM_TYPE_LABELS, toolbox_catalog
from app.prompts.qc import QC_SYSTEM_INSTRUCTION, qc_system_for
from app.schemas.diagram import DiagramDocument, DiagramType

__all__ = [
    "QC_SYSTEM_INSTRUCTION",
    "qc_system_for",
    "build_qc_audit_prompt",
    "build_revision_prompt",
]


def build_qc_audit_prompt(
    diagram_type: DiagramType,
    user_prompt: str,
    diagram: DiagramDocument,
) -> str:
    try:
        from app.prompts.diagrams import type_label
        from app.services import settings_service as cfg

        label = type_label(diagram_type)
        guidance = (
            cfg.active_prompt_body(f"generator.guidance.{diagram_type}")
            or DIAGRAM_TYPE_GUIDANCE[diagram_type]
        )
    except Exception:
        label = DIAGRAM_TYPE_LABELS[diagram_type]
        guidance = DIAGRAM_TYPE_GUIDANCE[diagram_type]
    catalog = toolbox_catalog(diagram_type)
    diagram_json = diagram.model_dump_json(by_alias=True, indent=2)

    node_ids = {n.id for n in diagram.nodes}
    dangling = [
        e.id
        for e in diagram.edges
        if e.from_node not in node_ids or e.to_node not in node_ids
    ]

    stats = (
        f"Nodes: {len(diagram.nodes)}, Edges: {len(diagram.edges)}, "
        f"Title: {diagram.title!r}"
    )
    if dangling:
        stats += f"\nDangling edge ids (pre-check): {', '.join(dangling)}"

    type_checklist = {
        "swim_lane": (
            "Checklist (tick each): every named lane? every stated activity its own task? "
            "every if/or/accept-reject as gateway_xor with ≥2 labeled branches? start/end?"
        ),
        "flowchart": (
            "Checklist (tick each): every stated step? every conditional a decision with ≥2 "
            "labeled branches (incl. No/2FA/retry)? start/end? loop-backs routed around nodes?"
        ),
        "sequence": (
            "Checklist (tick each): each participant? message count/order/types "
            "(message/async_message/return_message)? activation boxes if requested? "
            "humans as actor?"
        ),
        "erd": (
            "Checklist (tick each): major entities? relationships on valid ids? "
            "cardinality edge types (one/many/one_to_many) when brief asks?"
        ),
        "class_diagram": "Checklist (tick each): major classes/interfaces? associations valid?",
        "use_case": "Checklist (tick each): primary actors and major use cases?",
        "network": "Checklist (tick each): major devices/sites? data_store for databases?",
        "architecture": "Checklist (tick each): major services/APIs/stores? service≠api shapes?",
    }.get(diagram_type, "Checklist (tick each): all major requested elements present?")

    return "\n".join(
        [
            f"Diagram type: {label}",
            f"Design guidance: {guidance}",
            "",
            "TOOLBOX CATALOG (valid node/edge types):",
            catalog,
            "",
            f"User request:\n{user_prompt.strip()}",
            "",
            stats,
            "",
            "REQUIREMENT-BY-REQUIREMENT AUDIT:",
            "List each concrete requirement from the user request, mark PASS or FAIL,",
            "and set revision_required if any FAIL.",
            type_checklist,
            "",
            "Generated diagram JSON to review:",
            diagram_json,
            "",
            "Audit this diagram using your type-specific blocking rules.",
        ]
    )


def build_revision_prompt(
    diagram_type: DiagramType,
    user_prompt: str,
    previous_diagram: DiagramDocument,
    blocking_issues: list[str],
    process_inventory: str | None = None,
) -> str:
    from app.prompts.diagrams import build_diagram_user_prompt

    base = build_diagram_user_prompt(
        diagram_type,
        user_prompt,
        None,
        process_inventory=process_inventory,
    )
    issues = "\n".join(f"- {issue}" for issue in blocking_issues)
    try:
        from app.services import settings_service as cfg

        revision_header = cfg.active_prompt_body("qc.revision").strip()
    except Exception:
        revision_header = (
            "QC / COVERAGE REVISION REQUIRED — fix these blocking issues and return a COMPLETE diagram JSON:"
        )
    # v2.6.9 order: header → issue list → do-not-omit notes (never bury issues under notes).
    header_line = revision_header.split("\n")[0].strip() or (
        "QC / COVERAGE REVISION REQUIRED — fix these blocking issues and return a COMPLETE diagram JSON:"
    )
    trailing_notes = [
        line
        for line in revision_header.split("\n")[1:]
        if line.strip() and not line.strip().startswith("-")
    ]
    if not trailing_notes:
        trailing_notes = [
            "Do not omit activities, lanes, decisions, or branches that appear in the brief/inventory.",
            "Do not invent unrelated flows (refunds, retries, etc.) unless they were requested.",
        ]
    return "\n".join(
        [
            base,
            "",
            header_line,
            issues,
            "",
            *trailing_notes,
            "",
            "Previous attempt (improve, do not discard valid parts unless necessary):",
            previous_diagram.model_dump_json(by_alias=True, indent=2),
        ]
    )
