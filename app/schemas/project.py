from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.diagram import DiagramDocument, DiagramType


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    diagram_type: DiagramType = "use_case"
    title: str = Field(default="Untitled Diagram", max_length=255)
    diagram: DiagramDocument
    external_project_id: str | None = Field(default=None, max_length=255)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    diagram_type: DiagramType | None = None
    title: str | None = Field(default=None, max_length=255)
    diagram: DiagramDocument | None = None
    external_project_id: str | None = Field(default=None, max_length=255)


class ProjectSummary(BaseModel):
    id: str
    name: str
    diagram_type: DiagramType
    title: str
    external_project_id: str | None = None
    updated_at: datetime
    node_count: int = 0
    edge_count: int = 0


class ProjectDetail(ProjectSummary):
    description: str | None = None
    diagram: DiagramDocument
    created_at: datetime


class ProjectTransferRequest(BaseModel):
    target_project_id: str | None = Field(
        default=None,
        description="Another GenAI Studio project id to receive this diagram",
    )
    target_external_project_id: str | None = Field(
        default=None,
        description="Client canvas project id (updates matching saved project or returns payload only)",
    )
    replace: bool = Field(
        default=True,
        description="Replace target diagram content (default). If false, only logs transfer.",
    )


class CanvasExportV1(BaseModel):
    """Payload for external / client-owned canvas projects."""

    format: str = "genai-canvas-v1"
    project_id: str
    project_name: str
    external_project_id: str | None = None
    diagram_type: DiagramType
    title: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    exported_at: datetime
    source: str = "genai-diagram-studio"


class ProjectTransferResponse(BaseModel):
    status: str
    source_project_id: str
    target_project_id: str | None = None
    target_external_project_id: str | None = None
    canvas: CanvasExportV1
