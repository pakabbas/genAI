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
