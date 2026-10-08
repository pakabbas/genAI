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
    "architecture": "Architecture Diagram",
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
        ToolboxItem(id="entity", label="Entity (table)", kind="node", shape="entity", default_width=180, default_height=110),
        ToolboxItem(id="weak_entity", label="Weak Entity", kind="node", shape="weak_entity", default_width=180, default_height=110),
        ToolboxItem(id="attribute", label="Attribute (oval)", kind="node", shape="attribute", default_width=120, default_height=48),
        ToolboxItem(id="relationship", label="Relationship ◆", kind="node", shape="relationship", default_width=72, default_height=72),
        ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
        ToolboxItem(id="one", label="One (1)", kind="edge", shape="one"),
        ToolboxItem(id="many", label="Many (*)", kind="edge", shape="many"),
        ToolboxItem(id="one_or_many", label="One or Many (1..*)", kind="edge", shape="one_or_many"),
        ToolboxItem(id="zero_or_one", label="Zero or One (0..1)", kind="edge", shape="zero_or_one"),
        ToolboxItem(id="zero_or_many", label="Zero or Many (0..*)", kind="edge", shape="zero_or_many"),
        ToolboxItem(id="one_to_many", label="One-to-Many", kind="edge", shape="one_to_many"),
        ToolboxItem(id="many_to_many", label="Many-to-Many", kind="edge", shape="many_to_many"),
        ToolboxItem(id="identifying", label="Identifying", kind="edge", shape="identifying"),
    ],
    "swim_lane": [
        ToolboxItem(id="pool", label="Pool", kind="node", shape="pool", default_width=1680, default_height=780),
        ToolboxItem(id="lane", label="Swim Lane", kind="node", shape="lane", default_width=1580, default_height=180),
        ToolboxItem(id="start", label="Start Event", kind="node", shape="start", default_width=48, default_height=48),
        ToolboxItem(id="end", label="End Event", kind="node", shape="end", default_width=48, default_height=48),
        ToolboxItem(id="process", label="Task / Process", kind="node", shape="process", default_width=140, default_height=64),
        ToolboxItem(id="subprocess", label="Subprocess", kind="node", shape="subprocess", default_width=160, default_height=72),
        ToolboxItem(id="gateway_xor", label="XOR Gateway", kind="node", shape="gateway_xor", default_width=72, default_height=72),
        ToolboxItem(id="gateway_and", label="AND Gateway", kind="node", shape="gateway_and", default_width=72, default_height=72),
        ToolboxItem(id="document", label="Document", kind="node", shape="document", default_width=120, default_height=72),
        ToolboxItem(id="data_store", label="Data Store", kind="node", shape="data_store", default_width=100, default_height=64),
        ToolboxItem(id="text_box", label="Annotation", kind="node", shape="text_box", default_width=120, default_height=48),
        ToolboxItem(id="flow", label="Sequence Flow", kind="edge", shape="flow"),
        ToolboxItem(id="message_flow", label="Message Flow", kind="edge", shape="message_flow"),
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
        ToolboxItem(id="realization", label="Realization", kind="edge", shape="realization"),
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
        ToolboxItem(id="load_balancer", label="Load Balancer", kind="node", shape="load_balancer", default_width=100, default_height=64),
        ToolboxItem(id="server", label="Server", kind="node", shape="server", default_width=72, default_height=96),
        # id and shape both data_store — label "Database" (avoids QC fighting database vs data_store)
        ToolboxItem(id="data_store", label="Database", kind="node", shape="data_store", default_width=100, default_height=64),
        ToolboxItem(id="client", label="Client", kind="node", shape="client", default_width=72, default_height=72),
        ToolboxItem(id="workstation", label="Workstation", kind="node", shape="workstation", default_width=80, default_height=64),
        ToolboxItem(id="text_box", label="Label", kind="node", shape="text_box", default_width=100, default_height=40),
        ToolboxItem(id="network_link", label="Ethernet Link", kind="edge", shape="network_link"),
        ToolboxItem(id="wireless", label="Wireless", kind="edge", shape="wireless"),
    ],
    "architecture": [
        ToolboxItem(id="actor", label="User / Actor", kind="node", shape="actor", default_width=72, default_height=96),
        ToolboxItem(id="service", label="Service", kind="node", shape="service", default_width=160, default_height=72),
        ToolboxItem(id="api", label="API Gateway", kind="node", shape="api", default_width=160, default_height=72),
        ToolboxItem(id="package", label="Subsystem", kind="node", shape="package", default_width=240, default_height=160),
        ToolboxItem(id="cloud", label="External System", kind="node", shape="cloud", default_width=140, default_height=88),
        ToolboxItem(id="data_store", label="Database", kind="node", shape="data_store", default_width=100, default_height=64),
        ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
        ToolboxItem(id="text_box", label="Component", kind="node", shape="text_box", default_width=140, default_height=48),
        ToolboxItem(id="dependency", label="Dependency", kind="edge", shape="dependency"),
        ToolboxItem(id="data_flow", label="Data Flow", kind="edge", shape="data_flow"),
    ],
}

DIAGRAM_TYPE_GUIDANCE: dict[DiagramType, str] = {
    "use_case": (
        "UML use case: actors, ovals, system boundary. "
        "Edges: association (undirected), include/extend/dependency (dashed open arrow), "
        "generalization (hollow triangle)."
    ),
    "erd": (
        "ERD with table-style entities (label compartments: Name\\n--\\nPK id\\nattr\\nFK other_id). "
        "Optional Chen attribute ovals + relationship diamonds. "
        "Cardinality edges use crow's-foot types: one, many, one_or_many, zero_or_one, zero_or_many, "
        "one_to_many, many_to_many, identifying. Do NOT use data_store."
    ),
    "swim_lane": (
        "BPMN completeness rules (strict):\n"
        "- Create one pool and one lane node per named role/actor. Lane labels must match the brief.\n"
        "- Place start + end event circles. Failed/rejected paths that end the process need End events too.\n"
        "- Every stated action = its own process task (never merge 'pick up' + 'deliver' into one box).\n"
        "- Every if/or/accept-reject/success-failure = gateway_xor with ≥2 labeled outgoing flows "
        "(Yes/No or Accepted/Rejected). Do not replace a decision with a plain task.\n"
        "- Keep activities in the correct lane for the actor who performs them.\n"
        "- Sequence flow = flow (solid filled arrow); message flow = message_flow (dashed open arrow).\n"
        "- Layout (generous spacing — avoid cramped diagrams):\n"
        "  · Pool ≈ 1600–2000 wide; each lane ≥ 170 tall with 24px vertical padding inside.\n"
        "  · Place tasks left→right with ≥ 80px horizontal gap between shapes.\n"
        "  · Leave ≥ 120px free margin on the right of the rightmost task (room for future shapes).\n"
        "  · World coords may span x:40–2100 and y:40–1400; pan/zoom is fine — do NOT pack tightly."
    ),
    "flowchart": (
        "Flowchart completeness rules (strict):\n"
        "- Start/end terminators required.\n"
        "- Every stated step = its own process (do not merge distinct steps).\n"
        "- Every conditional = decision diamond with ≥2 labeled branches.\n"
        "- Preserve prompt order; do not invent extra business rules.\n"
        "- Layout: ≥ 70px gaps between shapes; may use x:40–1600, y:40–1200 — do not cram."
    ),
    "sequence": (
        "UML sequence: lifelines top-to-bottom. "
        "Human participants (User, Customer, Actor, Person, Admin, etc.) MUST use node type "
        "actor (stick figure) — never lifeline or object for humans. "
        "Systems/services/APIs/DBs use type lifeline (or object). "
        "Message edges MUST use types message, async_message, or return_message only (never connector). "
        "Put optional meta.message_y for vertical order; the pipeline also stacks them."
    ),
    "class_diagram": (
        "UML class diagram. Class/interface labels MUST use compartments separated by "
        "a line containing only --  e.g. 'Order\\n--\\n+id: UUID\\n+total: Money\\n--\\n+pay()'. "
        "association undirected; dependency dashed open; realization dashed hollow triangle; "
        "inheritance hollow triangle; composition filled diamond; aggregation open diamond. "
        "Put multiplicities in edge labels (e.g. 1..*)."
    ),
    "network": (
        "Network topology: cloud, routers, switches, load_balancer, servers, clients, links. "
        "Use node type data_store for databases. Use load_balancer (not router) for LB/HAProxy/NLB. "
        "Ethernet network_link has no arrowhead."
    ),
    "architecture": (
        "Software/system architecture. ONLY use toolbox ids: actor, service, api, package, "
        "cloud, data_store, note, text_box, dependency, data_flow. "
        "service and api are DISTINCT shapes (never both process). "
        "Map User→actor, microservice→service, API Gateway→api, Subsystem→package, "
        "External System→cloud, Database→data_store, Component→text_box. "
        "dependency=dashed open arrow; data_flow=solid filled arrow."
    ),
}

DIAGRAM_SYSTEM_INSTRUCTION = """You assemble diagrams from a fixed TOOLBOX of editable shapes — like Lucidchart or Visio building blocks.

CRITICAL:
- NEVER output images, SVG strings, HTML, base64, screenshots, or embedded graphics.
- ONLY use node "type" and edge "type" values from the TOOLBOX CATALOG provided in the user message.
- Each node is an independent editable part with id, type, label, x, y, width, height.
- Do NOT create a single node representing the whole diagram.
- Completeness over brevity: if the brief (or PROCESS INVENTORY) lists N activities/decisions/lanes,
  the JSON must contain all of them. Never silently drop branches or merge distinct actions.

JSON schema:
{
  "diagram_type": "<type>",
  "title": "string",
  "nodes": [{"id":"n1","type":"<toolbox_node_id>","label":"text","x":0,"y":0,"width":120,"height":60,"meta":{}}],
  "edges": [{"id":"e1","from":"n1","to":"n2","label":"","type":"<toolbox_edge_id>","meta":{}}]
}

Layout rules:
1. Use unique ids (n1, n2, e1…).
2. Prefer a SPACIOUS layout. Typical world bounds: x 40–2000, y 40–1400.
   The viewer pans/zooms — NEVER compress a complex diagram into a tiny 800×600 box.
3. Keep ≥ 70–100px clear space between neighboring shapes; leave empty margin for future edits.
4. Include every major entity/activity/decision the user asked for — do not stop after partial output.
5. Edges must reference existing node ids; connect attributes to entities and relationships to entities.
6. Put containers (system_boundary, lane, package, fragment, pool) behind content with larger width/height
   that fully enclose their children plus padding.
7. Labels concise and professional, but keep the meaning of each required step.
8. For class/interface/enum labels use name then '\\n--\\n' then attributes then '\\n--\\n' then methods.
9. For sequence diagrams only use edge types message / async_message / return_message.
10. For swim_lane / flowchart: decision gateways need ≥2 labeled outgoing edges; failed paths reach an End."""


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
    process_inventory: str | None = None,
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

    if process_inventory:
        parts.extend(
            [
                "",
                process_inventory,
                "",
                "Generate the diagram so EVERY inventory item is present as a toolbox node/edge.",
            ]
        )

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
