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
    kind: Literal["start", "end", "activity", "decision"]
    label: str
    lane: str | None = None
    branches: list[ProcessBranch] = Field(default_factory=list)


class ProcessFlow(BaseModel):
    from_id: str
    to_id: str
    label: str = ""


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
