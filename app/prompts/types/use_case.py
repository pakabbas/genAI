"""Use Case Diagram: generator rules and the editable-shape catalog defaults."""

from app.schemas.diagram import ToolboxItem

GUIDANCE = (
    'UML use case: actors, ovals, system boundary. Edges: association (undirected), include/extend/dependency (dashed open arrow), generalization (hollow triangle).\n'
    '- Keep system_boundary and package containers behind their contents, enclosing all children plus padding.'
)

TOOLBOX = [
    ToolboxItem(id="actor", label="Actor", kind="node", shape="actor", default_width=72, default_height=96),
    ToolboxItem(id="use_case", label="Use Case", kind="node", shape="use_case", default_width=140, default_height=56),
    ToolboxItem(id="system_boundary", label="System Boundary", kind="node", shape="system_boundary", default_width=360, default_height=280),
    ToolboxItem(id="package", label="Package", kind="node", shape="package", default_width=200, default_height=120),
    ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
    ToolboxItem(id="text_box", label="Text", kind="node", shape="text_box", default_width=120, default_height=48),
    ToolboxItem(id="association", label="Association", kind="edge", shape="association"),
    ToolboxItem(id="include", label="Include «include»", kind="edge", shape="include"),
    ToolboxItem(id="extend", label="Extend «extend»", kind="edge", shape="extend"),
    ToolboxItem(id="generalization", label="Generalization", kind="edge", shape="generalization"),
    ToolboxItem(id="dependency", label="Dependency", kind="edge", shape="dependency"),
]
