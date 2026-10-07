"""Schemas for multi-agent diagram generation and QC audit trail."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.diagram import DiagramDocument, DiagramType


AgentName = Literal["requirements_analyst", "generator", "qc_auditor", "system"]


class AgentTraceEntry(BaseModel):
    step: int
    agent: AgentName
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


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)


class RequirementsChatRequest(BaseModel):
    diagram_type: DiagramType = "use_case"
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=40)
    force_ready: bool = False


class RequirementsChatResponse(BaseModel):
    status: Literal["need_more_info", "ready"]
    assistant_message: str
    enhanced_prompt: str | None = None
    assumptions: list[str] = Field(default_factory=list)
    questions_asked: list[str] = Field(default_factory=list)
    agent: Literal["requirements_analyst"] = "requirements_analyst"


class GenerateDiagramResponse(BaseModel):
    diagram: DiagramDocument
    diagram_type: str
    diagram_type_label: str
    qc_approved: bool = True
    revision_applied: bool = False
    recommendations: list[str] = Field(default_factory=list)
    enhanced_prompt: str | None = None
    trace: list[AgentTraceEntry] = Field(default_factory=list)
