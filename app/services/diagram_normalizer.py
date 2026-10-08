"""Normalize AI diagram output to toolbox-only editable shapes."""

from __future__ import annotations

import re

from app.prompts.diagrams import TOOLBOX
from app.schemas.diagram import DiagramDocument, DiagramEdge, DiagramNode, DiagramType

BACKGROUND_SHAPES = frozenset({"system_boundary", "lane", "package", "frame", "pool"})
CONTAINER_SHAPES = frozenset({"pool", "lane", "system_boundary", "package", "fragment"})

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
    "gateway": "gateway_xor",
    "gateway_xor": "gateway_xor",
    "xor": "gateway_xor",
    "exclusive_gateway": "gateway_xor",
    "gateway_and": "gateway_and",
    "and": "gateway_and",
    "parallel_gateway": "gateway_and",
    "pool": "pool",
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
    "load_balancer": "load_balancer",
    "loadbalancer": "load_balancer",
    "lb": "load_balancer",
    "haproxy": "load_balancer",
    "nlb": "load_balancer",
    "alb": "load_balancer",
    "service": "service",
    "microservice": "service",
    "api": "api",
    "api_gateway": "api",
    "apigateway": "api",
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
    "one": "one",
    "1": "one",
    "many": "many",
    "n": "many",
    "star": "many",
    "one_or_many": "one_or_many",
    "1n_plus": "one_or_many",
    "zero_or_one": "zero_or_one",
    "0_1": "zero_or_one",
    "zero_or_many": "zero_or_many",
    "0_n": "zero_or_many",
    "one_to_many": "one_to_many",
    "1n": "one_to_many",
    "many_to_many": "many_to_many",
    "nm": "many_to_many",
    "identifying": "identifying",
    "flow": "flow",
    "sequence_flow": "flow",
    "message_flow": "message_flow",
    "data_flow": "data_flow",
    "connector": "connector",
    "arrow": "connector",
    "message": "message",
    "sync": "message",
    "sync_message": "message",
    "call": "message",
    "async_message": "async_message",
    "async": "async_message",
    "asynchronous": "async_message",
    "return_message": "return_message",
    "return": "return_message",
    "reply": "return_message",
    "inheritance": "inheritance",
    "realization": "realization",
    "implements": "realization",
    "composition": "composition",
    "aggregation": "aggregation",
    "network_link": "network_link",
    "ethernet": "network_link",
    "wireless": "wireless",
}

FORBIDDEN_META_KEYS = frozenset({"src", "href", "url", "image", "svg", "html", "base64", "data"})

SEQUENCE_MESSAGE_TYPES = frozenset({"message", "async_message", "return_message"})
SEQUENCE_LIFELINE_TYPES = frozenset({"lifeline", "object", "actor"})
SEQUENCE_MESSAGE_START_Y = 88.0
SEQUENCE_MESSAGE_STEP = 52.0


_MSG_NUM_PREFIX = re.compile(r"^(\d+)\s*[.):\-]\s*(.*)$")


def _renumber_sequence_labels(edges: list[DiagramEdge]) -> list[DiagramEdge]:
    """Force 1..N message labels in stack order when AI skips numbers (e.g. 1,2,3,5)."""
    msg_edges = [e for e in edges if e.type in SEQUENCE_MESSAGE_TYPES]
    if not msg_edges:
        return edges
    if not any(_MSG_NUM_PREFIX.match((e.label or "").strip()) for e in msg_edges):
        return edges

    ordered = sorted(
        msg_edges,
        key=lambda e: (
            float((e.meta or {}).get("message_y") or 0),
            e.id,
        ),
    )
    id_to_num = {e.id: i + 1 for i, e in enumerate(ordered)}
    out: list[DiagramEdge] = []
    for edge in edges:
        num = id_to_num.get(edge.id)
        if num is None:
            out.append(edge)
            continue
        label = (edge.label or "").strip()
        match = _MSG_NUM_PREFIX.match(label)
        rest = match.group(2).strip() if match else label
        new_label = f"{num}. {rest}".strip() if rest else f"{num}."
        out.append(edge.model_copy(update={"label": new_label}))
    return out


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

    edges = _renumber_sequence_labels(edges)

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


def _resolve_edge_type(raw: str, allowed: dict[str, str], diagram_type: DiagramType | None = None) -> str:
    key = _clean_key(raw)
    if diagram_type == "swim_lane" and key in {"connector", "messageflow", "message_flow"}:
        return allowed.get("message_flow", "message_flow")
    if diagram_type == "architecture" and key in {"connector", "arrow", "dataflow", "data_flow"}:
        return allowed.get("data_flow", "data_flow")
    if key in allowed:
        return allowed[key]
    if key in EDGE_ALIASES:
        mapped = EDGE_ALIASES[key]
        if mapped in allowed.values() or mapped in allowed:
            return allowed.get(mapped, mapped)
    if diagram_type == "sequence":
        # Never collapse sequence traffic onto a generic connector
        if "message" in allowed or "message" in allowed.values():
            return allowed.get("message", "message")
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
    if "message_y" in clean:
        try:
            clean["message_y"] = float(clean["message_y"])
        except (TypeError, ValueError):
            clean.pop("message_y", None)
    return clean


def _format_class_compartments(label: str, shape: str) -> str:
    """Ensure class/interface/enum labels use name / -- / attrs / -- / methods."""
    if shape not in {"class", "interface", "enum", "entity", "weak_entity"}:
        return label
    text = (label or "").replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n").strip()
    if not text:
        return "Interface" if shape == "interface" else "Class"
    if re.search(r"\n-{2,}\n", text) or "\n--\n" in text:
        return text

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    if len(lines) <= 1:
        chunks = [c.strip() for c in re.split(r"\s*\|\s*|\s*;\s*", text) if c.strip()]
        if len(chunks) <= 1:
            return text
        name, rest = chunks[0], chunks[1:]
    else:
        name, rest = lines[0], lines[1:]

    methods = [ln for ln in rest if "(" in ln or ln.startswith("+")]
    attrs = [ln for ln in rest if ln not in methods]
    parts = [name]
    if attrs:
        parts.append("--")
        parts.extend(attrs)
    if methods:
        parts.append("--")
        parts.extend(methods)
    elif not attrs and rest:
        parts.append("--")
        parts.extend(rest)
    return "\n".join(parts)


_HUMAN_PARTICIPANT = re.compile(
    r"^(user|actor|customer|person|human|visitor|guest|member|admin|employee|"
    r"student|patient|buyer|seller|operator|clerk|cashier|driver|rider|"
    r"end[\s_-]?user|enduser)s?\b",
    re.I,
)


def _is_human_sequence_label(label: str) -> bool:
    text = (label or "").strip()
    if not text:
        return False
    if _HUMAN_PARTICIPANT.match(text):
        return True
    # Exact short names often used for the left-most participant
    return text.lower() in {"user", "actor", "customer", "person", "admin"}


def normalize_diagram(diagram_type: DiagramType, document: DiagramDocument) -> DiagramDocument:
    """Coerce AI output to toolbox shape ids with safe sizes and valid edges."""
    allowed_nodes, allowed_edges, sizes = _toolbox_maps(diagram_type)
    default_node = "process" if "process" in allowed_nodes else next(iter(allowed_nodes))
    actor_allowed = "actor" in allowed_nodes

    nodes: list[DiagramNode] = []
    seen_ids: set[str] = set()

    for index, node in enumerate(document.nodes):
        node_id = node.id.strip() if node.id else f"n{index + 1}"
        if node_id in seen_ids:
            node_id = f"n{index + 1}"
        seen_ids.add(node_id)

        shape = _resolve_node_type(node.type, allowed_nodes, default_node)
        label = (node.label or "").strip()
        raw_type = _clean_key(node.type or "")

        # Sequence: never draw humans as lifeline/object boxes — keep type actor
        if (
            diagram_type == "sequence"
            and actor_allowed
            and shape in {"lifeline", "object"}
            and _is_human_sequence_label(label)
        ):
            shape = allowed_nodes.get("actor", "actor")

        # Architecture: service/api are distinct — never collapse both to process boxes
        if diagram_type == "architecture":
            allowed_shapes = set(allowed_nodes.values())
            process_like = raw_type in {
                "api",
                "apigateway",
                "api_gateway",
                "service",
                "microservice",
                "process",
                "task",
                "activity",
                "box",
                "rectangle",
            }
            if raw_type in {"api", "apigateway", "api_gateway"} or (
                process_like and re.search(r"\b(api|gateway)\b", label, re.I)
            ):
                shape = allowed_nodes.get("api", "api")
            elif process_like:
                shape = allowed_nodes.get("service", "service")
            elif shape not in allowed_shapes and "service" in allowed_nodes:
                shape = allowed_nodes["service"]

        # Swim lane: plain decision diamonds become XOR gateways
        if diagram_type == "swim_lane" and (
            raw_type in {"decision", "gateway", "xor", "exclusive_gateway"} or shape == "decision"
        ):
            shape = allowed_nodes.get("gateway_xor", "gateway_xor")
        if diagram_type == "swim_lane" and raw_type in {"and", "gateway_and", "parallel_gateway"}:
            shape = allowed_nodes.get("gateway_and", "gateway_and")

        width, height = sizes.get(shape, (node.width, node.height))
        if shape in CONTAINER_SHAPES:
            # Pools/lanes/boundaries must be allowed to grow large for spacious layouts
            node_width = float(node.width) if node.width > 0 else float(width)
            node_height = float(node.height) if node.height > 0 else float(height)
            node_width = max(float(width) * 0.8, min(node_width, 4200.0))
            node_height = max(float(height) * 0.8, min(node_height, 3200.0))
        elif node.width <= 0 or node.height <= 0:
            node_width, node_height = width, height
        else:
            node_width = max(width * 0.75, min(node.width, width * 2.5))
            node_height = max(height * 0.75, min(node.height, height * 2.5))

        # Actor stick figure is ~72 wide; keep that even if model sent a wide lifeline box
        if shape == "actor":
            aw, ah = sizes.get("actor", (72.0, 96.0))
            node_width = float(aw)
            # Keep tall height from model/layout for message span; visual legs stay fixed
            node_height = max(float(ah), float(node_height))

        if not label and shape == "text_box":
            label = "Label"
        label = _format_class_compartments(label, shape)

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
                    "type": _resolve_edge_type(edge.type, allowed_edges, diagram_type),
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
    if diagram_type == "swim_lane":
        result = _layout_swim_lane(result)
    elif diagram_type == "flowchart":
        result = _layout_flowchart_space(result)
    return result


def _layout_swim_lane(document: DiagramDocument) -> DiagramDocument:
    """
    Expand cramped swimlane diagrams: stack lanes with headroom, spread tasks
    left→right with gaps, grow pool/lanes, and leave right-side margin for edits.
    """
    nodes = [n.model_copy(deep=True) for n in document.nodes]
    if not nodes:
        return document

    pools = [n for n in nodes if n.type == "pool"]
    lanes = sorted([n for n in nodes if n.type == "lane"], key=lambda n: n.y)
    content = [n for n in nodes if n.type not in {"pool", "lane"}]
    if not lanes:
        return document

    min_lane_h = 180.0
    lane_pad_x = 48.0  # left label band + padding
    lane_pad_y = 28.0
    gap_x = 90.0
    gap_y_between_lanes = 16.0
    right_margin = 160.0  # free space for future shapes
    pool_pad = 28.0
    origin_x = 40.0
    origin_y = 40.0

    # Assign each content node to the nearest lane by vertical center
    def lane_for(node: DiagramNode) -> DiagramNode:
        cy = node.y + node.height / 2
        best = lanes[0]
        best_dist = abs((best.y + best.height / 2) - cy)
        for lane in lanes[1:]:
            dist = abs((lane.y + lane.height / 2) - cy)
            if dist < best_dist:
                best = lane
                best_dist = dist
        return best

    by_lane: dict[str, list[DiagramNode]] = {lane.id: [] for lane in lanes}
    for node in content:
        by_lane[lane_for(node).id].append(node)

    # Horizontal spread + vertical centering within each lane band (computed next)
    # First pass: determine required width from densest lane
    required_inner_w = 400.0
    for lane in lanes:
        members = sorted(by_lane[lane.id], key=lambda n: (n.x, n.id))
        if not members:
            continue
        span = sum(m.width for m in members) + gap_x * max(0, len(members) - 1)
        required_inner_w = max(required_inner_w, span)

    lane_w = max(1580.0, lane_pad_x + required_inner_w + right_margin)
    # Cap insane widths but allow large processes
    lane_w = min(lane_w, 3600.0)

    cursor_y = origin_y + (pool_pad if pools else 0.0)
    for lane in lanes:
        members = sorted(by_lane[lane.id], key=lambda n: (n.x, n.id))
        content_h = max((m.height for m in members), default=64.0)
        lane_h = max(min_lane_h, content_h + lane_pad_y * 2 + 24.0)

        lane.x = origin_x + (pool_pad if pools else 0.0)
        lane.y = cursor_y
        lane.width = lane_w
        lane.height = lane_h

        # Place members left→right with gaps, vertically centered in lane
        x = lane.x + lane_pad_x
        mid_y = lane.y + lane_h / 2
        for member in members:
            member.x = x
            member.y = mid_y - member.height / 2
            x += member.width + gap_x

        cursor_y += lane_h + gap_y_between_lanes

    # Grow / reposition pool to enclose all lanes with padding + extra room
    if pools:
        pool = pools[0]
        top = min(l.y for l in lanes) - pool_pad
        left = min(l.x for l in lanes) - pool_pad
        bottom = max(l.y + l.height for l in lanes) + pool_pad
        right = max(l.x + l.width for l in lanes) + pool_pad
        pool.x = max(20.0, left)
        pool.y = max(20.0, top)
        pool.width = max(1680.0, right - pool.x)
        pool.height = max(780.0, bottom - pool.y)

    # Reassemble preserving background-first sort
    rebuilt = [n for n in nodes if n.type == "pool"] + lanes + content
    rebuilt.sort(key=lambda n: (0 if n.type in BACKGROUND_SHAPES else 1, n.y, n.x))
    return DiagramDocument(
        diagram_type=document.diagram_type,
        title=document.title,
        nodes=rebuilt,
        edges=document.edges,
    )


def _layout_flowchart_space(document: DiagramDocument) -> DiagramDocument:
    """Light de-crowd for flowcharts: push overlapping nodes apart on a grid."""
    nodes = [n.model_copy(deep=True) for n in document.nodes]
    if len(nodes) < 2:
        return document

    min_gap = 70.0
    # Sort and nudge overlaps iteratively
    for _ in range(4):
        moved = False
        ordered = sorted(nodes, key=lambda n: (n.y, n.x))
        for i, a in enumerate(ordered):
            for b in ordered[i + 1 :]:
                if b.y > a.y + a.height + min_gap:
                    break
                overlap_x = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
                overlap_y = min(a.y + a.height, b.y + b.height) - max(a.y, b.y)
                if overlap_x > 0 and overlap_y > 0:
                    # Push b right or down, whichever needs less travel
                    push_right = overlap_x + min_gap
                    push_down = overlap_y + min_gap
                    if push_right <= push_down:
                        b.x += push_right
                    else:
                        b.y += push_down
                    moved = True
        if not moved:
            break

    nodes.sort(key=lambda n: (0 if n.type in BACKGROUND_SHAPES else 1, n.y, n.x))
    return DiagramDocument(
        diagram_type=document.diagram_type,
        title=document.title,
        nodes=nodes,
        edges=document.edges,
    )
