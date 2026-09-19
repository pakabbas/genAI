"""Schemas for multi-agent diagram generation and QC audit trail."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.diagram import DiagramDocument


class AgentTraceEntry(BaseModel):
    step: int
    agent: Literal["generator", "qc_auditor", "system"]
    phase: str
    message: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QCAuditResult(BaseModel):
    approved: bool
    revision_required: bool = False
    blocking_issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str = ""


class GenerateDiagramResponse(BaseModel):
    diagram: DiagramDocument
    diagram_type: str
    diagram_type_label: str
    qc_approved: bool = True
    revision_applied: bool = False
    recommendations: list[str] = Field(default_factory=list)
    trace: list[AgentTraceEntry] = Field(default_factory=list)
