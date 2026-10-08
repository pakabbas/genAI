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
            "Checklist: every named lane present? every stated activity its own task? "
            "every if/or/accept-reject as gateway_xor with ≥2 labeled branches? start/end present?"
        ),
        "flowchart": (
            "Checklist: every stated step present? every conditional a decision with ≥2 "
            "labeled branches? start/end terminators present?"
        ),
        "sequence": (
            "Checklist: major participants present? messages use message/async_message/"
            "return_message? humans as actor where appropriate?"
        ),
        "erd": "Checklist: major entities present? relationships connect valid entity ids?",
        "class_diagram": "Checklist: major classes/interfaces present? associations valid?",
        "use_case": "Checklist: primary actors and major use cases present?",
        "network": "Checklist: major devices/sites present? data_store OK for databases?",
        "architecture": "Checklist: major services/APIs/stores present? service≠api shapes?",
    }.get(diagram_type, "Checklist: all major requested elements present?")

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
    return "\n".join(
        [
            base,
            "",
            "QC / COVERAGE REVISION REQUIRED — fix these blocking issues and return a COMPLETE diagram JSON:",
            issues,
            "",
            "Do not omit activities, lanes, decisions, or branches that appear in the brief/inventory.",
            "Do not invent unrelated flows (refunds, retries, etc.) unless they were requested.",
            "",
            "Previous attempt (improve, do not discard valid parts unless necessary):",
            previous_diagram.model_dump_json(by_alias=True, indent=2),
        ]
    )
