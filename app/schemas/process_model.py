"""Structured process inventory extracted from a user prompt before diagram generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProcessBranch(BaseModel):
    label: str = Field(..., description="Branch label such as Yes, No, Accepted, Declined")
    outcome: str = Field(..., description="What happens on this branch")
    next_element_id: str | None = Field(
        default=None,
        description="Id of the next element, or null if this branch ends the process",
    )
    ends_process: bool = False


class ProcessElement(BaseModel):
    id: str
    kind: Literal["start", "end", "activity", "decision", "parallel"]
    label: str
    lane: str | None = None
    branches: list[ProcessBranch] = Field(default_factory=list)


class ProcessFlow(BaseModel):
    from_id: str
    to_id: str
    label: str = ""


# 2.7.9: flowchart planners naturally emit I/O and parallel kinds. Map them onto the
# inventory kinds before validation (flowchart only — swim lane keeps the strict schema).
_FLOWCHART_KIND_MAP: dict[str, str] = {
    "input": "activity",
    "output": "activity",
    "io": "activity",
    "input_output": "activity",
    "display": "activity",
    "document": "activity",
    "process": "activity",
    "task": "activity",
    "action": "activity",
    "step": "activity",
    "subprocess": "activity",
    "manual_input": "activity",
    "data_store": "activity",
    "gateway": "decision",
    "xor": "decision",
    "condition": "decision",
    "fork": "parallel",
    "join": "parallel",
    "parallel": "parallel",
    "gateway_and": "parallel",
    "and": "parallel",
    "merge": "parallel",
    "terminator": "end",
    "stop": "end",
    "begin": "start",
}


def coerce_flowchart_kinds(data: object) -> object:
    """Return planner JSON with flowchart-specific kinds mapped to inventory kinds."""
    if not isinstance(data, dict):
        return data
    elements = data.get("elements")
    if not isinstance(elements, list):
        return data
    out = []
    for el in elements:
        if isinstance(el, dict):
            kind = str(el.get("kind") or "").strip().lower().replace("-", "_").replace(" ", "_")
            if kind not in {"start", "end", "activity", "decision"}:
                kind = _FLOWCHART_KIND_MAP.get(kind, "activity")
            el = {**el, "kind": kind}
        out.append(el)
    return {**data, "elements": out}


class ProcessModel(BaseModel):
    """Canonical inventory of lanes, activities, decisions, and flows derived from the prompt."""

    title: str = "Process"
    lanes: list[str] = Field(default_factory=list)
    elements: list[ProcessElement] = Field(default_factory=list)
    flows: list[ProcessFlow] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def activities(self) -> list[ProcessElement]:
        return [e for e in self.elements if e.kind == "activity"]

    def decisions(self) -> list[ProcessElement]:
        return [e for e in self.elements if e.kind == "decision"]

    def starts(self) -> list[ProcessElement]:
        return [e for e in self.elements if e.kind == "start"]

    def ends(self) -> list[ProcessElement]:
        return [e for e in self.elements if e.kind == "end"]
