"""Architecture Diagram: generator rules and the editable-shape catalog defaults."""

from app.schemas.diagram import ToolboxItem

GUIDANCE = (
    'Software/system architecture. ONLY use toolbox ids: actor, service, api, package, cloud, data_store, note, text_box, dependency, data_flow. service and api are DISTINCT shapes (never both process). Map User→actor, microservice→service, API Gateway→api, Subsystem→package, External System→cloud, Database→data_store, Component→text_box. dependency=dashed open arrow; data_flow=solid filled arrow.\n'
    '- Keep package containers behind their contents, enclosing all children plus padding.'
)

TOOLBOX = [
    ToolboxItem(id="actor", label="User / Actor", kind="node", shape="actor", default_width=72, default_height=96),
    ToolboxItem(id="service", label="Service", kind="node", shape="service", default_width=160, default_height=72),
    ToolboxItem(id="api", label="API Gateway", kind="node", shape="api", default_width=160, default_height=72),
    ToolboxItem(id="package", label="Subsystem", kind="node", shape="package", default_width=240, default_height=160),
    ToolboxItem(id="cloud", label="External System", kind="node", shape="cloud", default_width=140, default_height=88),
    ToolboxItem(id="data_store", label="Database", kind="node", shape="data_store", default_width=100, default_height=64),
    ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
    ToolboxItem(id="text_box", label="Component", kind="node", shape="text_box", default_width=140, default_height=48),
    ToolboxItem(id="dependency", label="Dependency", kind="edge", shape="dependency"),
    ToolboxItem(id="data_flow", label="Data Flow", kind="edge", shape="data_flow"),
]
