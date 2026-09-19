"""QC auditor prompts — pragmatic review, not harsh perfectionism."""

import json

from app.prompts.diagrams import DIAGRAM_TYPE_LABELS, DIAGRAM_TYPE_GUIDANCE, toolbox_catalog
from app.schemas.diagram import DiagramDocument, DiagramType

QC_SYSTEM_INSTRUCTION = """You are a pragmatic diagram QC auditor for an AI diagram studio.

Your job is to REVIEW a generated diagram JSON — you do NOT edit or rewrite it.

APPROVE the diagram unless there is a clear blocking problem. Be lenient:
- Minor layout overlap, spacing, or missing optional labels → recommendations only, still APPROVE.
- Slightly simplified scope vs. a huge enterprise spec → APPROVE with recommendations.
- Naming typos or informal labels → recommendations only.

ONLY require revision (revision_required=true) when one or more BLOCKING issues exist:
1. Diagram is empty or essentially unusable (no meaningful nodes).
2. A major module, actor, entity, or process explicitly named in the user request is completely missing.
3. Structural errors: edges reference missing node ids, or nodes use types clearly outside the toolbox.
4. Diagram type is fundamentally wrong for the request (e.g. flowchart when user asked for ERD).

When revision_required=true, list concise blocking_issues the generator must fix.
Always include helpful recommendations (optional polish) — even when approved.

Respond ONLY with JSON:
{
  "approved": boolean,
  "revision_required": boolean,
  "blocking_issues": ["..."],
  "recommendations": ["..."],
  "summary": "One or two professional sentences for the user."
}

Rules:
- approved=true and revision_required=false when there are no blocking issues.
- If revision_required=true, approved must be false.
- Keep recommendations to at most 5 short bullets.
- Do not be harsh or pedantic."""


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
            "Generated diagram JSON to review:",
            diagram_json,
            "",
            "Audit this diagram. Require revision only for blocking issues listed in your instructions.",
        ]
    )


def build_revision_prompt(
    diagram_type: DiagramType,
    user_prompt: str,
    previous_diagram: DiagramDocument,
    blocking_issues: list[str],
) -> str:
    from app.prompts.diagrams import build_diagram_user_prompt

    base = build_diagram_user_prompt(diagram_type, user_prompt, None)
    issues = "\n".join(f"- {issue}" for issue in blocking_issues)
    return "\n".join(
        [
            base,
            "",
            "QC REVISION REQUIRED — fix ONLY these blocking issues and return a complete diagram JSON:",
            issues,
            "",
            "Previous attempt (improve, do not discard valid parts unless necessary):",
            previous_diagram.model_dump_json(by_alias=True, indent=2),
        ]
    )
