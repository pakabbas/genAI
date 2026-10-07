"""Normalize AI diagram output to toolbox-only editable shapes."""

from __future__ import annotations

import re

from app.prompts.diagrams import TOOLBOX
from app.schemas.diagram import DiagramDocument, DiagramEdge, DiagramNode, DiagramType

BACKGROUND_SHAPES = frozenset({"system_boundary", "lane", "package", "frame"})

NODE_ALIASES: dict[str, str] = {
    "actor": "actor",
    "user": "actor",
    "person": "actor",
    "stickfigure": "actor",
    "usecase": "use_case",
    "use_case": "use_case",
    "use case": "use_case",
    "system": "system_boundary",
    "systemboundary": "system_boundary",
    "system_boundary": "system_boundary",
    "boundary": "system_boundary",
    "note": "note",
    "comment": "note",
    "entity": "entity",
    "table": "entity",
    "weakentity": "weak_entity",
    "weak_entity": "weak_entity",
    "attribute": "attribute",
    "field": "attribute",
    "column": "attribute",
    "relationship": "relationship",
    "relation": "relationship",
    "lane": "lane",
    "swimlane": "lane",
    "swim_lane": "lane",
    "process": "process",
    "task": "process",
    "activity": "process",
    "action": "process",
    "start": "start",
    "end": "end",
    "terminator": "terminator",
    "decision": "decision",
    "gateway": "decision",
    "document": "document",
    "input": "input",
    "output": "input",
    "parallelogram": "parallelogram",
    "datastore": "data_store",
    "data_store": "data_store",
    "database": "data_store",
    "db": "data_store",
    "delay": "delay",
    "subprocess": "subprocess",
    "manual": "manual_input",
    "manual_input": "manual_input",
    "preparation": "preparation",
    "display": "display",
    "connector": "connector_node",
    "offpage": "off_page",
    "off_page": "off_page",
    "lifeline": "lifeline",
    "object": "object",
    "activation": "activation",
    "fragment": "fragment",
    "class": "class",
    "interface": "interface",
    "enum": "enum",
    "package": "package",
    "server": "server",
    "router": "router",
    "firewall": "firewall",
    "cloud": "cloud",
    "client": "client",
    "workstation": "workstation",
    "switch": "switch",
    "service": "process",
    "microservice": "process",
    "api": "process",
    "api_gateway": "process",
    "component": "text_box",
    "text": "text_box",
    "textbox": "text_box",
    "text_box": "text_box",
    "group": "text_box",
    "rectangle": "process",
    "box": "process",
    "oval": "use_case",
    "ellipse": "use_case",
    "diamond": "decision",
    "image": "text_box",
    "svg": "text_box",
    "diagram": "text_box",
}

EDGE_ALIASES: dict[str, str] = {
    "association": "association",
    "link": "association",
    "include": "include",
    "extend": "extend",
    "generalization": "generalization",
    "dependency": "dependency",
    "one_to_many": "one_to_many",
    "1n": "one_to_many",
    "many_to_many": "many_to_many",
    "nm": "many_to_many",
    "identifying": "identifying",
    "flow": "flow",
    "connector": "connector",
    "arrow": "connector",
    "message": "message",
    "async_message": "async_message",
    "return_message": "return_message",
    "inheritance": "inheritance",
    "composition": "composition",
    "aggregation": "aggregation",
    "network_link": "network_link",
    "wireless": "wireless",
}

FORBIDDEN_META_KEYS = frozenset({"src", "href", "url", "image", "svg", "html", "base64", "data"})

SEQUENCE_MESSAGE_TYPES = frozenset({"message", "async_message", "return_message"})
SEQUENCE_LIFELINE_TYPES = frozenset({"lifeline", "object", "actor"})
SEQUENCE_MESSAGE_START_Y = 88.0
SEQUENCE_MESSAGE_STEP = 52.0


def _layout_sequence_messages(document: DiagramDocument) -> DiagramDocument:
    """Assign horizontal message Y positions so sequence edges do not overlap."""
    if not any(e.type in SEQUENCE_MESSAGE_TYPES for e in document.edges):
        return document

    nodes = list(document.nodes)
    edges: list[DiagramEdge] = []
    max_y = SEQUENCE_MESSAGE_START_Y
    message_index = 0

    for edge in document.edges:
        if edge.type not in SEQUENCE_MESSAGE_TYPES:
            edges.append(edge)
            continue
        y = SEQUENCE_MESSAGE_START_Y + message_index * SEQUENCE_MESSAGE_STEP
        message_index += 1
        max_y = max(max_y, y + 24)
        meta = dict(edge.meta or {})
        meta["message_y"] = y
        edges.append(edge.model_copy(update={"meta": meta}))

    updated_nodes: list[DiagramNode] = []
    min_height = max_y + 80
    for node in nodes:
        if node.type in SEQUENCE_LIFELINE_TYPES and node.height < min_height:
            updated_nodes.append(node.model_copy(update={"height": float(min_height)}))
        elif node.type == "activation":
            updated_nodes.append(node)
        else:
            updated_nodes.append(node)

    return document.model_copy(update={"nodes": updated_nodes, "edges": edges})


def _toolbox_maps(diagram_type: DiagramType) -> tuple[dict[str, str], dict[str, str], dict[str, tuple[float, float]]]:
    items = TOOLBOX[diagram_type]
    node_types: dict[str, str] = {}
    edge_types: dict[str, str] = {}
    sizes: dict[str, tuple[float, float]] = {}
    for item in items:
        if item.kind == "node":
            node_types[item.id] = item.shape
            sizes[item.shape] = (item.default_width, item.default_height)
        else:
            edge_types[item.id] = item.shape
    return node_types, edge_types, sizes


def _clean_key(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "", value.strip().lower().replace("-", "_"))


def _resolve_node_type(raw: str, allowed: dict[str, str], fallback: str = "process") -> str:
    key = _clean_key(raw)
    if key in allowed:
        return allowed[key]
    if key in NODE_ALIASES:
        mapped = NODE_ALIASES[key]
        if mapped in allowed.values() or mapped in allowed:
            return allowed.get(mapped, mapped)
    for token in re.split(r"[\s_]+", key):
        if token in NODE_ALIASES:
            mapped = NODE_ALIASES[token]
            if mapped in allowed.values() or mapped in allowed:
                return allowed.get(mapped, mapped)
    return allowed.get(fallback, fallback if fallback in allowed.values() else next(iter(allowed.values())))


def _resolve_edge_type(raw: str, allowed: dict[str, str]) -> str:
    key = _clean_key(raw)
    if key in allowed:
        return allowed[key]
    if key in EDGE_ALIASES:
        mapped = EDGE_ALIASES[key]
        if mapped in allowed.values() or mapped in allowed:
            return allowed.get(mapped, mapped)
    default = "connector" if "connector" in allowed else "association" if "association" in allowed else "flow"
    return allowed.get(default, default)


def _sanitize_meta(meta: dict) -> dict:
    clean: dict = {}
    for key, value in (meta or {}).items():
        if key.lower() in FORBIDDEN_META_KEYS:
            continue
        if isinstance(value, str) and ("<svg" in value.lower() or "data:image" in value.lower()):
            continue
        clean[key] = value
    return clean


def normalize_diagram(diagram_type: DiagramType, document: DiagramDocument) -> DiagramDocument:
    """Coerce AI output to toolbox shape ids with safe sizes and valid edges."""
    allowed_nodes, allowed_edges, sizes = _toolbox_maps(diagram_type)
    default_node = "process" if "process" in allowed_nodes else next(iter(allowed_nodes))

    nodes: list[DiagramNode] = []
    seen_ids: set[str] = set()

    for index, node in enumerate(document.nodes):
        node_id = node.id.strip() if node.id else f"n{index + 1}"
        if node_id in seen_ids:
            node_id = f"n{index + 1}"
        seen_ids.add(node_id)

        shape = _resolve_node_type(node.type, allowed_nodes, default_node)
        width, height = sizes.get(shape, (node.width, node.height))
        if node.width <= 0 or node.height <= 0:
            node_width, node_height = width, height
        else:
            node_width = max(width * 0.75, min(node.width, width * 2))
            node_height = max(height * 0.75, min(node.height, height * 2))

        label = (node.label or "").strip()
        if not label and shape == "text_box":
            label = "Label"

        nodes.append(
            DiagramNode(
                id=node_id,
                type=shape,
                label=label,
                x=float(node.x),
                y=float(node.y),
                width=float(node_width),
                height=float(node_height),
                meta=_sanitize_meta(node.meta),
            )
        )

    id_map = {n.id for n in nodes}
    edges: list[DiagramEdge] = []
    for index, edge in enumerate(document.edges):
        src = edge.from_node
        dst = edge.to_node
        if src not in id_map or dst not in id_map or src == dst:
            continue
        edge_id = edge.id.strip() if edge.id else f"e{index + 1}"
        edges.append(
            DiagramEdge(
                id=edge_id,
                **{
                    "from": src,
                    "to": dst,
                    "label": (edge.label or "").strip(),
                    "type": _resolve_edge_type(edge.type, allowed_edges),
                    "meta": _sanitize_meta(edge.meta),
                },
            )
        )

    # Background containers first for stable client z-order
    nodes.sort(key=lambda n: (0 if n.type in BACKGROUND_SHAPES else 1, n.y, n.x))

    title = (document.title or "").strip() or "Untitled Diagram"
    result = DiagramDocument(
        diagram_type=diagram_type,
        title=title,
        nodes=nodes,
        edges=edges,
    )
    if diagram_type == "sequence":
        result = _layout_sequence_messages(result)
    return result
