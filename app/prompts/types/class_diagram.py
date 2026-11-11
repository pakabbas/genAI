"""Class Diagram: generator rules and the editable-shape catalog defaults."""

from app.schemas.diagram import ToolboxItem

GUIDANCE = (
    "UML class diagram. Class/interface labels MUST use compartments separated by a line containing only --  e.g. 'Order\\n--\\n+id: UUID\\n+total: Money\\n--\\n+pay()'. association undirected; dependency dashed open; realization dashed hollow triangle; inheritance hollow triangle; composition filled diamond; aggregation open diamond. Put multiplicities in edge labels (e.g. 1..*).\n"
    "- Class/interface/enum labels use name, then '\\n--\\n', then attributes, then '\\n--\\n', then methods.\n"
    '- Keep package containers behind their contents, enclosing all children plus padding.'
)

TOOLBOX = [
    ToolboxItem(id="class", label="Class", kind="node", shape="class", default_width=180, default_height=120),
    ToolboxItem(id="interface", label="Interface", kind="node", shape="interface", default_width=180, default_height=100),
    ToolboxItem(id="enum", label="Enumeration", kind="node", shape="enum", default_width=160, default_height=90),
    ToolboxItem(id="package", label="Package", kind="node", shape="package", default_width=220, default_height=140),
    ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
    ToolboxItem(id="inheritance", label="Inheritance", kind="edge", shape="inheritance"),
    ToolboxItem(id="realization", label="Realization", kind="edge", shape="realization"),
    ToolboxItem(id="association", label="Association", kind="edge", shape="association"),
    ToolboxItem(id="composition", label="Composition", kind="edge", shape="composition"),
    ToolboxItem(id="aggregation", label="Aggregation", kind="edge", shape="aggregation"),
    ToolboxItem(id="dependency", label="Dependency", kind="edge", shape="dependency"),
]
