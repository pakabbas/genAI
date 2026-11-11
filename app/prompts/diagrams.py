"""Diagram types, toolbox definitions, and Gemini prompts for JSON diagram generation."""

import json

from app.schemas.diagram import DiagramType, ToolboxItem
from app.prompts.base import DIAGRAM_SYSTEM_INSTRUCTION
from app.prompts.types import TYPE_CONTEXTS

DIAGRAM_TYPE_LABELS: dict[DiagramType, str] = {
    "flowchart": "Flowchart",
    "use_case": "Use Case Diagram",
    "erd": "Entity Relationship (ERD)",
    "swim_lane": "Swim Lane / BPMN",
    "sequence": "Sequence Diagram",
    "class_diagram": "Class Diagram",
    "network": "Network Diagram",
    "architecture": "Architecture Diagram",
}

# Compatibility aliases: each type owns its rules and shapes in types/<type>.py.
TOOLBOX: dict[DiagramType, list[ToolboxItem]] = {
    diagram_type: context.TOOLBOX for diagram_type, context in TYPE_CONTEXTS.items()
}
DIAGRAM_TYPE_GUIDANCE: dict[DiagramType, str] = {
    diagram_type: context.GUIDANCE for diagram_type, context in TYPE_CONTEXTS.items()
}


def type_labels() -> dict[str, str]:
    try:
        from app.services import settings_service as cfg

        labels = cfg.get_value("diagrams.type_labels")
        if isinstance(labels, dict) and labels:
            return {**DIAGRAM_TYPE_LABELS, **labels}
    except Exception:
        pass
    return dict(DIAGRAM_TYPE_LABELS)


def type_label(diagram_type: DiagramType | str) -> str:
    labels = type_labels()
    return str(labels.get(str(diagram_type), DIAGRAM_TYPE_LABELS.get(diagram_type, diagram_type)))


def effective_toolbox(diagram_type: DiagramType) -> list[ToolboxItem]:
    """TOOLBOX merged with toolbox.overrides (enabled + sizes)."""
    base = list(TOOLBOX.get(diagram_type) or [])
    try:
        from app.services import settings_service as cfg

        overrides = cfg.get_value("toolbox.overrides") or {}
    except Exception:
        overrides = {}

    out: list[ToolboxItem] = []
    for item in base:
        key = f"{diagram_type}.{item.id}"
        ov = overrides.get(key) if isinstance(overrides, dict) else None
        if isinstance(ov, dict) and ov.get("enabled") is False:
            continue
        width = item.default_width
        height = item.default_height
        if isinstance(ov, dict):
            if ov.get("default_width") is not None:
                width = int(ov["default_width"])
            if ov.get("default_height") is not None:
                height = int(ov["default_height"])
        out.append(
            ToolboxItem(
                id=item.id,
                label=item.label,
                kind=item.kind,
                shape=item.shape,
                default_width=width,
                default_height=height,
            )
        )
    return out


def toolbox_catalog(diagram_type: DiagramType) -> str:
    items = effective_toolbox(diagram_type)
    catalog = {
        "nodes": [
            {
                "type": item.id,
                "label": item.label,
                "default_width": item.default_width,
                "default_height": item.default_height,
            }
            for item in items
            if item.kind == "node"
        ],
        "edges": [{"type": item.id, "label": item.label} for item in items if item.kind == "edge"],
    }
    return json.dumps(catalog, indent=2)


def default_type_context(diagram_type: DiagramType) -> str:
    """Full editable context default, honoring legacy guidance and toolbox overrides.

    generator.context.<type> overrides the entire result. Existing guidance keys
    remain supported (and feed Analyst/QC through this context); they seed this default when no full
    context override is active. No other type's module enters the prompt.
    """
    guidance = DIAGRAM_TYPE_GUIDANCE[diagram_type]
    try:
        from app.services import settings_service as cfg

        guidance = cfg.active_prompt_body(f"generator.guidance.{diagram_type}") or guidance
    except Exception:
        pass
    return "\n".join([
        f"Diagram type: {type_label(diagram_type)}",
        f"Design guidance: {guidance}",
        "",
        "TOOLBOX CATALOG (you MUST only use these exact type values):",
        toolbox_catalog(diagram_type),
    ])


def effective_type_context(diagram_type: DiagramType) -> str:
    """Only the selected type's full context, or its file-backed default."""
    try:
        from app.services import settings_service as cfg

        context = cfg.active_prompt_body(f"generator.context.{diagram_type}")
        if context:
            return context
    except Exception:
        pass
    return default_type_context(diagram_type)


def build_diagram_user_prompt(
    diagram_type: DiagramType,
    user_prompt: str,
    existing_json: str | None = None,
    process_inventory: str | None = None,
    *,
    edit_mode: bool = False,
) -> str:
    # The pipeline sends the shared base as system_instruction. This user
    # message contains exactly one type context plus request/edit/inventory data.
    parts = [
        effective_type_context(diagram_type),
        "",
        f"User request:\n{user_prompt.strip()}",
    ]

    if process_inventory:
        parts.extend(
            [
                "",
                process_inventory,
                "",
                "Generate the diagram so EVERY inventory item is present as a toolbox node/edge.",
            ]
        )

    if existing_json and edit_mode:
        parts.extend(
            [
                "",
                "EXISTING DIAGRAM (EDIT MODE — surgical change only):",
                "- Keep EVERY existing node/edge id and label unless the user names that element.",
                "- Keep x, y, width, and height unless the user asks to move, resize, widen, align,",
                "  or otherwise change geometry — then apply those geometry changes.",
                "- Do NOT merge, rename, relocate, or delete unrelated shapes.",
                "- Only ADD or ALTER what the request asks for.",
                "- Preserve element order, internal structure, and branch labels.",
                existing_json,
            ]
        )
    else:
        parts.append("")
        parts.append(
            "Build a new diagram by placing toolbox nodes and connecting them with toolbox edges."
        )

    return "\n".join(parts)
