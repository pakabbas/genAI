from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


DiagramType = Literal["use_case", "erd", "swim_lane", "flowchart"]


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


class DiagramDocument(BaseModel):
    diagram_type: DiagramType
    title: str = "Untitled Diagram"
    nodes: list[DiagramNode] = Field(default_factory=list)
    edges: list[DiagramEdge] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class GenerateDiagramRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=8000)
    diagram_type: DiagramType = "use_case"
    existing: DiagramDocument | None = None


class GenerateDiagramResponse(BaseModel):
    diagram: DiagramDocument
    diagram_type: str
    diagram_type_label: str


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
