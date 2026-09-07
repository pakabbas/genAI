"""Diagram types, toolbox definitions, and Gemini prompts for JSON diagram generation."""

from app.schemas.diagram import DiagramType, ToolboxItem

DIAGRAM_TYPE_LABELS: dict[DiagramType, str] = {
    "use_case": "Use Case Diagram",
    "erd": "Entity Relationship (ERD)",
    "swim_lane": "Swim Lane",
    "flowchart": "Flowchart",
}

TOOLBOX: dict[DiagramType, list[ToolboxItem]] = {
    "use_case": [
        ToolboxItem(
            id="actor",
            label="Actor",
            kind="node",
            shape="actor",
            default_width=72,
            default_height=96,
        ),
        ToolboxItem(
            id="use_case",
            label="Use Case",
            kind="node",
            shape="use_case",
            default_width=140,
            default_height=56,
        ),
        ToolboxItem(
            id="system_boundary",
            label="System Boundary",
            kind="node",
            shape="system_boundary",
            default_width=320,
            default_height=240,
        ),
        ToolboxItem(
            id="note",
            label="Note",
            kind="node",
            shape="note",
            default_width=120,
            default_height=80,
        ),
        ToolboxItem(
            id="association",
            label="Association",
            kind="edge",
            shape="association",
        ),
        ToolboxItem(
            id="include",
            label="Include",
            kind="edge",
            shape="include",
        ),
        ToolboxItem(
            id="extend",
            label="Extend",
            kind="edge",
            shape="extend",
        ),
    ],
    "erd": [
        ToolboxItem(
            id="entity",
            label="Entity",
            kind="node",
            shape="entity",
            default_width=160,
            default_height=80,
        ),
        ToolboxItem(
            id="attribute",
            label="Attribute",
            kind="node",
            shape="attribute",
            default_width=120,
            default_height=48,
        ),
        ToolboxItem(
            id="relationship",
            label="Relationship",
            kind="node",
            shape="relationship",
            default_width=72,
            default_height=72,
        ),
        ToolboxItem(
            id="weak_entity",
            label="Weak Entity",
            kind="node",
            shape="weak_entity",
            default_width=160,
            default_height=80,
        ),
        ToolboxItem(
            id="one_to_many",
            label="One-to-Many",
            kind="edge",
            shape="one_to_many",
        ),
        ToolboxItem(
            id="many_to_many",
            label="Many-to-Many",
            kind="edge",
            shape="many_to_many",
        ),
        ToolboxItem(
            id="identifying",
            label="Identifying",
            kind="edge",
            shape="identifying",
        ),
    ],
    "swim_lane": [
        ToolboxItem(
            id="lane",
            label="Swim Lane",
            kind="node",
            shape="lane",
            default_width=900,
            default_height=160,
        ),
        ToolboxItem(
            id="process",
            label="Process",
            kind="node",
            shape="process",
            default_width=140,
            default_height=64,
        ),
        ToolboxItem(
            id="start",
            label="Start",
            kind="node",
            shape="start",
            default_width=48,
            default_height=48,
        ),
        ToolboxItem(
            id="end",
            label="End",
            kind="node",
            shape="end",
            default_width=48,
            default_height=48,
        ),
        ToolboxItem(
            id="decision",
            label="Decision",
            kind="node",
            shape="decision",
            default_width=88,
            default_height=88,
        ),
        ToolboxItem(
            id="document",
            label="Document",
            kind="node",
            shape="document",
            default_width=120,
            default_height=72,
        ),
        ToolboxItem(
            id="flow",
            label="Flow",
            kind="edge",
            shape="flow",
        ),
    ],
    "flowchart": [
        ToolboxItem(
            id="start",
            label="Start/End",
            kind="node",
            shape="terminator",
            default_width=120,
            default_height=48,
        ),
        ToolboxItem(
            id="process",
            label="Process",
            kind="node",
            shape="process",
            default_width=140,
            default_height=64,
        ),
        ToolboxItem(
            id="decision",
            label="Decision",
            kind="node",
            shape="decision",
            default_width=88,
            default_height=88,
        ),
        ToolboxItem(
            id="input",
            label="Input/Output",
            kind="node",
            shape="parallelogram",
            default_width=140,
            default_height=56,
        ),
        ToolboxItem(
            id="connector",
            label="Connector",
            kind="edge",
            shape="connector",
        ),
    ],
}

DIAGRAM_TYPE_GUIDANCE: dict[DiagramType, str] = {
    "use_case": (
        "UML use case diagram: actors outside system boundary, use cases as ovals inside "
        "a dashed system boundary rectangle. Use association edges between actors and use cases. "
        "Use include/extend edges between use cases where appropriate. Place nodes with clear spacing."
    ),
    "erd": (
        "Chen-style or crow's-foot ERD: entities as rectangles, attributes as ovals connected "
        "to entities, relationships as diamonds between entities. Label cardinality on edges "
        "(1, N, M). Include primary keys in entity labels when relevant."
    ),
    "swim_lane": (
        "Cross-functional swim lane diagram: horizontal lanes labeled by role/department. "
        "Processes as rounded rectangles within lanes. Start/end circles, decision diamonds. "
        "Flow arrows showing handoffs between lanes."
    ),
    "flowchart": (
        "Standard flowchart: terminators for start/end, rectangles for processes, diamonds for "
        "decisions, parallelograms for I/O. Logical top-to-bottom or left-to-right flow with "
        "labeled decision branches."
    ),
}

DIAGRAM_SYSTEM_INSTRUCTION = """You are an expert systems analyst and diagram designer. You output ONLY valid JSON representing a diagram document — no markdown, no code fences, no commentary.

JSON schema:
{
  "diagram_type": "use_case" | "erd" | "swim_lane" | "flowchart",
  "title": "string",
  "nodes": [
    {
      "id": "unique_string",
      "type": "shape id from toolbox (e.g. actor, use_case, entity, lane, process)",
      "label": "display text",
      "x": number (pixels, 0-1200),
      "y": number (pixels, 0-800),
      "width": number,
      "height": number,
      "meta": {}
    }
  ],
  "edges": [
    {
      "id": "unique_string",
      "from": "source node id",
      "to": "target node id",
      "label": "optional label",
      "type": "edge type (association, include, flow, one_to_many, etc.)",
      "meta": {}
    }
  ]
}

Rules:
1. Return ONLY the JSON object. No text before or after.
2. Use unique ids like "n1", "n2", "e1".
3. Position nodes so they do not heavily overlap; use the full canvas (roughly 900x600).
4. Every edge must reference existing node ids.
5. Include enough nodes and edges to match the user's request professionally.
6. Labels must be concise and meaningful.
7. For swim_lane diagrams, create lane nodes first (large horizontal bands), then place processes inside lane y-ranges.
8. For use_case diagrams, system_boundary should wrap related use cases visually."""


def build_diagram_user_prompt(
    diagram_type: DiagramType,
    user_prompt: str,
    existing_json: str | None = None,
) -> str:
    label = DIAGRAM_TYPE_LABELS[diagram_type]
    guidance = DIAGRAM_TYPE_GUIDANCE[diagram_type]
    allowed_shapes = ", ".join(item.id for item in TOOLBOX[diagram_type])

    parts = [
        f"Diagram type: {label}",
        f"Design guidance: {guidance}",
        f"Allowed node/edge types: {allowed_shapes}",
        "",
        f"User request:\n{user_prompt.strip()}",
    ]

    if existing_json:
        parts.extend(
            [
                "",
                "Extend or refine this existing diagram JSON (preserve ids where possible, "
                "adjust layout as needed):",
                existing_json,
            ]
        )
    else:
        parts.append("")
        parts.append("Create a complete new diagram JSON for this request.")

    return "\n".join(parts)
