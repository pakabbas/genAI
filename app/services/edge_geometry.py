"""Border clipping helpers (mirrors canvas.js _borderPoint for unit tests)."""

from __future__ import annotations

import math
from typing import Any


def border_point(node: dict[str, Any], toward_x: float, toward_y: float) -> tuple[float, float]:
    w = float(node.get("width") or 80)
    h = float(node.get("height") or 40)
    cx = float(node["x"]) + w / 2
    cy = float(node["y"]) + h / 2
    dx = toward_x - cx
    dy = toward_y - cy
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return cx, cy
    ntype = str(node.get("type") or "")
    if ntype in {"decision", "relationship", "gateway_xor", "gateway_and"}:
        sx, sy = w / 2, h / 2
        t = 1 / (abs(dx) / sx + abs(dy) / sy)
        return cx + dx * t, cy + dy * t
    if ntype in {"use_case", "attribute", "terminator", "start", "end", "delay"}:
        rx, ry = w / 2, h / 2
        t = 1 / math.sqrt((dx * dx) / (rx * rx) + (dy * dy) / (ry * ry))
        return cx + dx * t, cy + dy * t
    hw, hh = w / 2, h / 2
    t = min(hw / abs(dx or 1e-9), hh / abs(dy or 1e-9))
    return cx + dx * t, cy + dy * t


def sequence_message_ends(from_node: dict[str, Any], to_node: dict[str, Any], y: float) -> dict[str, float]:
    """Lifeline-centre X (not header-box edges). Self-message is a small right-side loop."""
    def centre_x(node: dict[str, Any]) -> float:
        return float(node["x"]) + float(node.get("width") or 80) / 2

    if from_node.get("id") and from_node.get("id") == to_node.get("id"):
        cx = centre_x(from_node)
        return {"x1": cx, "y1": y, "x2": cx, "y2": y + 18, "self": True}
    return {
        "x1": centre_x(from_node),
        "y1": y,
        "x2": centre_x(to_node),
        "y2": y,
        "self": False,
    }


def label_anchor(route: list[dict[str, float]]) -> tuple[float, float]:
    """Midpoint of the longest segment, offset a few px off the line."""
    if not route:
        return 0.0, 0.0
    if len(route) == 1:
        return float(route[0]["x"]), float(route[0]["y"]) - 8
    best_i = 0
    best_len = -1.0
    for i in range(len(route) - 1):
        dx = route[i + 1]["x"] - route[i]["x"]
        dy = route[i + 1]["y"] - route[i]["y"]
        length = math.hypot(dx, dy)
        if length > best_len:
            best_len = length
            best_i = i
    a, b = route[best_i], route[best_i + 1]
    dx, dy = b["x"] - a["x"], b["y"] - a["y"]
    length = math.hypot(dx, dy) or 1.0
    x = (a["x"] + b["x"]) / 2 + (-dy / length) * 10
    y = (a["y"] + b["y"]) / 2 + (dx / length) * 10
    return x, y


def new_project_empty_diagram(diagram_type: str = "erd") -> dict[str, Any]:
    """Contract for Project > New (app.js newProject + clearCanvas skipConfirm)."""
    return {
        "diagram_type": diagram_type,
        "title": "Untitled Diagram",
        "nodes": [],
        "edges": [],
    }
