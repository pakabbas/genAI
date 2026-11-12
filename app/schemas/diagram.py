from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


DiagramType = Literal[
    "flowchart",
    "use_case",
    "erd",
    "swim_lane",
    "sequence",
    "class_diagram",
    "network",
    "architecture",
]


class DiagramNode(BaseModel):
    id: str
    type: str
    label: str = ""
    x: float = 0
    y: float = 0
    width: float = 120
    height: float = 60
    meta: dict[str, Any] = Field(default_factory=dict)


class DiagramEdge(BaseModel):
    id: str
    from_node: str = Field(alias="from", serialization_alias="from")
    to_node: str = Field(alias="to", serialization_alias="to")
    label: str = ""
    type: str = "connector"
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class DrillDown(BaseModel):
    """Named, colored group of shapes/lines on the same canvas (USP)."""

    id: str
    name: str = ""
    color: str = "#2563eb"
    category: str = ""
    description: str = ""
    node_ids: list[str] = Field(default_factory=list, alias="nodeIds")
    edge_ids: list[str] = Field(default_factory=list, alias="edgeIds")

    model_config = ConfigDict(populate_by_name=True)


class DiagramDocument(BaseModel):
    diagram_type: DiagramType
    title: str = "Untitled Diagram"
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)
    drilldowns: list[DrillDown] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class GenerateDiagramRequest(BaseModel):
    # Ceiling matches settings_registry max; runtime enforces limits.* via /api handlers.
    prompt: str = Field(..., min_length=3, max_length=64000)
    diagram_type: DiagramType = "flowchart"
    existing: DiagramDocument | None = None
    # When true with `existing`, Generator must modify the canvas (not recreate).
    edit_mode: bool = False
    # When true, `prompt` is the Requirements Analyst enhanced brief.
    prompt_enhanced: bool = False
    original_prompt: str | None = Field(default=None, max_length=32000)
    # Edit mode: the user's latest chat message (the requested change). Optional.
    edit_request: str | None = Field(default=None, max_length=8000)


class ToolboxItem(BaseModel):
    id: str
    label: str
    kind: Literal["node", "edge"]
    shape: str
    icon: str = ""
    default_width: float = 120
    default_height: float = 60


class ToolboxResponse(BaseModel):
    diagram_type: DiagramType
    label: str
    items: list[ToolboxItem]
