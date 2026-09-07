"""Diagram types, toolbox definitions, and Gemini prompts for JSON diagram generation."""

import json

from app.schemas.diagram import DiagramType, ToolboxItem

DIAGRAM_TYPE_LABELS: dict[DiagramType, str] = {
    "use_case": "Use Case Diagram",
    "erd": "Entity Relationship (ERD)",
    "swim_lane": "Swim Lane / BPMN",
    "flowchart": "Flowchart",
    "sequence": "Sequence Diagram",
    "class_diagram": "Class Diagram",
    "network": "Network Diagram",
}

TOOLBOX: dict[DiagramType, list[ToolboxItem]] = {
    "use_case": [
        ToolboxItem(id="actor", label="Actor", kind="node", shape="actor", default_width=72, default_height=96),
        ToolboxItem(id="use_case", label="Use Case", kind="node", shape="use_case", default_width=140, default_height=56),
        ToolboxItem(id="system_boundary", label="System Boundary", kind="node", shape="system_boundary", default_width=360, default_height=280),
        ToolboxItem(id="package", label="Package", kind="node", shape="package", default_width=200, default_height=120),
        ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
        ToolboxItem(id="text_box", label="Text", kind="node", shape="text_box", default_width=120, default_height=48),
        ToolboxItem(id="association", label="Association", kind="edge", shape="association"),
        ToolboxItem(id="include", label="Include «include»", kind="edge", shape="include"),
        ToolboxItem(id="extend", label="Extend «extend»", kind="edge", shape="extend"),
        ToolboxItem(id="generalization", label="Generalization", kind="edge", shape="generalization"),
        ToolboxItem(id="dependency", label="Dependency", kind="edge", shape="dependency"),
    ],
    "erd": [
        ToolboxItem(id="entity", label="Entity", kind="node", shape="entity", default_width=160, default_height=80),
        ToolboxItem(id="weak_entity", label="Weak Entity", kind="node", shape="weak_entity", default_width=160, default_height=80),
        ToolboxItem(id="attribute", label="Attribute", kind="node", shape="attribute", default_width=120, default_height=48),
        ToolboxItem(id="relationship", label="Relationship", kind="node", shape="relationship", default_width=72, default_height=72),
        ToolboxItem(id="data_store", label="Data Store", kind="node", shape="data_store", default_width=100, default_height=64),
        ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
        ToolboxItem(id="one_to_many", label="One-to-Many", kind="edge", shape="one_to_many"),
        ToolboxItem(id="many_to_many", label="Many-to-Many", kind="edge", shape="many_to_many"),
        ToolboxItem(id="identifying", label="Identifying", kind="edge", shape="identifying"),
        ToolboxItem(id="association", label="Association", kind="edge", shape="association"),
    ],
    "swim_lane": [
        ToolboxItem(id="lane", label="Swim Lane", kind="node", shape="lane", default_width=920, default_height=150),
        ToolboxItem(id="start", label="Start Event", kind="node", shape="start", default_width=48, default_height=48),
        ToolboxItem(id="end", label="End Event", kind="node", shape="end", default_width=48, default_height=48),
        ToolboxItem(id="process", label="Task / Process", kind="node", shape="process", default_width=140, default_height=64),
        ToolboxItem(id="subprocess", label="Subprocess", kind="node", shape="subprocess", default_width=160, default_height=72),
        ToolboxItem(id="decision", label="Gateway", kind="node", shape="decision", default_width=88, default_height=88),
        ToolboxItem(id="document", label="Document", kind="node", shape="document", default_width=120, default_height=72),
        ToolboxItem(id="manual_input", label="Manual Input", kind="node", shape="manual_input", default_width=120, default_height=56),
        ToolboxItem(id="data_store", label="Data Store", kind="node", shape="data_store", default_width=100, default_height=64),
        ToolboxItem(id="delay", label="Delay", kind="node", shape="delay", default_width=56, default_height=56),
        ToolboxItem(id="text_box", label="Annotation", kind="node", shape="text_box", default_width=120, default_height=48),
        ToolboxItem(id="flow", label="Sequence Flow", kind="edge", shape="flow"),
        ToolboxItem(id="connector", label="Message Flow", kind="edge", shape="connector"),
    ],
    "flowchart": [
        ToolboxItem(id="terminator", label="Start / End", kind="node", shape="terminator", default_width=120, default_height=48),
        ToolboxItem(id="process", label="Process", kind="node", shape="process", default_width=140, default_height=64),
        ToolboxItem(id="decision", label="Decision", kind="node", shape="decision", default_width=88, default_height=88),
        ToolboxItem(id="input", label="Input / Output", kind="node", shape="input", default_width=140, default_height=56),
        ToolboxItem(id="document", label="Document", kind="node", shape="document", default_width=120, default_height=72),
        ToolboxItem(id="data_store", label="Database", kind="node", shape="data_store", default_width=100, default_height=64),
        ToolboxItem(id="preparation", label="Preparation", kind="node", shape="preparation", default_width=140, default_height=56),
        ToolboxItem(id="display", label="Display", kind="node", shape="display", default_width=120, default_height=56),
        ToolboxItem(id="manual_input", label="Manual Operation", kind="node", shape="manual_input", default_width=120, default_height=56),
        ToolboxItem(id="delay", label="Delay", kind="node", shape="delay", default_width=56, default_height=56),
        ToolboxItem(id="off_page", label="Off-page", kind="node", shape="off_page", default_width=48, default_height=48),
        ToolboxItem(id="connector_node", label="Connector", kind="node", shape="connector_node", default_width=40, default_height=40),
        ToolboxItem(id="text_box", label="Comment", kind="node", shape="text_box", default_width=120, default_height=48),
        ToolboxItem(id="connector", label="Flow Line", kind="edge", shape="connector"),
    ],
    "sequence": [
        ToolboxItem(id="actor", label="Actor", kind="node", shape="actor", default_width=72, default_height=96),
        ToolboxItem(id="lifeline", label="Lifeline", kind="node", shape="lifeline", default_width=80, default_height=320),
        ToolboxItem(id="object", label="Object", kind="node", shape="object", default_width=100, default_height=48),
        ToolboxItem(id="activation", label="Activation", kind="node", shape="activation", default_width=16, default_height=80),
        ToolboxItem(id="fragment", label="Fragment (alt/loop)", kind="node", shape="fragment", default_width=280, default_height=160),
        ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
        ToolboxItem(id="message", label="Sync Message", kind="edge", shape="message"),
        ToolboxItem(id="async_message", label="Async Message", kind="edge", shape="async_message"),
        ToolboxItem(id="return_message", label="Return", kind="edge", shape="return_message"),
    ],
    "class_diagram": [
        ToolboxItem(id="class", label="Class", kind="node", shape="class", default_width=180, default_height=120),
        ToolboxItem(id="interface", label="Interface", kind="node", shape="interface", default_width=180, default_height=100),
        ToolboxItem(id="enum", label="Enumeration", kind="node", shape="enum", default_width=160, default_height=90),
        ToolboxItem(id="package", label="Package", kind="node", shape="package", default_width=220, default_height=140),
        ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
        ToolboxItem(id="inheritance", label="Inheritance", kind="edge", shape="inheritance"),
        ToolboxItem(id="association", label="Association", kind="edge", shape="association"),
        ToolboxItem(id="composition", label="Composition", kind="edge", shape="composition"),
        ToolboxItem(id="aggregation", label="Aggregation", kind="edge", shape="aggregation"),
        ToolboxItem(id="dependency", label="Dependency", kind="edge", shape="dependency"),
    ],
    "network": [
        ToolboxItem(id="cloud", label="Cloud / Internet", kind="node", shape="cloud", default_width=140, default_height=88),
        ToolboxItem(id="router", label="Router", kind="node", shape="router", default_width=80, default_height=56),
        ToolboxItem(id="switch", label="Switch", kind="node", shape="switch", default_width=88, default_height=48),
        ToolboxItem(id="firewall", label="Firewall", kind="node", shape="firewall", default_width=72, default_height=72),
        ToolboxItem(id="server", label="Server", kind="node", shape="server", default_width=72, default_height=96),
        ToolboxItem(id="database", label="Database", kind="node", shape="data_store", default_width=100, default_height=64),
        ToolboxItem(id="client", label="Client", kind="node", shape="client", default_width=72, default_height=72),
        ToolboxItem(id="workstation", label="Workstation", kind="node", shape="workstation", default_width=80, default_height=64),
        ToolboxItem(id="text_box", label="Label", kind="node", shape="text_box", default_width=100, default_height=40),
        ToolboxItem(id="network_link", label="Ethernet Link", kind="edge", shape="network_link"),
        ToolboxItem(id="wireless", label="Wireless", kind="edge", shape="wireless"),
    ],
}

DIAGRAM_TYPE_GUIDANCE: dict[DiagramType, str] = {
    "use_case": "UML use case: actors, ovals, system boundary, association/include/extend.",
    "erd": "Chen ERD: entities, attributes, relationship diamonds, cardinality on edges.",
    "swim_lane": "BPMN-style swim lanes with tasks, gateways, start/end events, sequence flows.",
    "flowchart": "Standard flowchart symbols: terminators, processes, decisions, I/O, database.",
    "sequence": "UML sequence: lifelines top-to-bottom, sync/async/return messages between lifelines.",
    "class_diagram": "UML class diagram: classes, interfaces, packages, inheritance and associations.",
    "network": "Network topology: cloud, routers, switches, servers, clients, links.",
}

DIAGRAM_SYSTEM_INSTRUCTION = """You assemble diagrams from a fixed TOOLBOX of editable shapes — like Lucidchart or Visio building blocks.

CRITICAL:
- NEVER output images, SVG strings, HTML, base64, screenshots, or embedded graphics.
- ONLY use node "type" and edge "type" values from the TOOLBOX CATALOG provided in the user message.
- Each node is an independent editable part with id, type, label, x, y, width, height.
- Do NOT create a single node representing the whole diagram.

JSON schema:
{
  "diagram_type": "<type>",
  "title": "string",
  "nodes": [{"id":"n1","type":"<toolbox_node_id>","label":"text","x":0,"y":0,"width":120,"height":60,"meta":{}}],
  "edges": [{"id":"e1","from":"n1","to":"n2","label":"","type":"<toolbox_edge_id>","meta":{}}]
}

Layout rules:
1. Use unique ids (n1, n2, e1…).
2. Spread nodes on a ~1000×700 canvas; avoid heavy overlap.
3. Edges must reference existing node ids.
4. Put containers (system_boundary, lane, package, fragment) behind content with larger width/height.
5. Labels concise and professional."""


def toolbox_catalog(diagram_type: DiagramType) -> str:
    items = TOOLBOX[diagram_type]
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


def build_diagram_user_prompt(
    diagram_type: DiagramType,
    user_prompt: str,
    existing_json: str | None = None,
) -> str:
    label = DIAGRAM_TYPE_LABELS[diagram_type]
    guidance = DIAGRAM_TYPE_GUIDANCE[diagram_type]
    catalog = toolbox_catalog(diagram_type)

    parts = [
        f"Diagram type: {label}",
        f"Design guidance: {guidance}",
        "",
        "TOOLBOX CATALOG (you MUST only use these exact type values):",
        catalog,
        "",
        f"User request:\n{user_prompt.strip()}",
    ]

    if existing_json:
        parts.extend(
            [
                "",
                "Extend this existing diagram using ONLY toolbox types (keep ids when possible):",
                existing_json,
            ]
        )
    else:
        parts.append("")
        parts.append(
            "Build a new diagram by placing toolbox nodes and connecting them with toolbox edges."
        )

    return "\n".join(parts)
