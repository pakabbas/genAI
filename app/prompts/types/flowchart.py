"""Flowchart: generator rules and the editable-shape catalog defaults."""

from app.schemas.diagram import ToolboxItem

GUIDANCE = (
    'Flowchart completeness rules (strict):\n'
    '- Start/end terminators required.\n'
    "- Every stated step = exactly ONE node with the brief's wording (do not merge distinct steps, do not split one stated step, never repeat a step).\n"
    '- Every conditional = decision diamond with ≥2 labeled branches (Yes/No, 2FA, retry, etc.); each answer label appears ONCE per decision.\n'
    "- Steps that run in parallel: a connector_node labelled 'Fork' fans out to them and a connector_node labelled 'Join' merges them (never two same-label edges from a decision).\n"
    '- Preserve prompt order; do not invent extra business rules.\n'
    '- Loop-backs / retries are edges back to the earlier node (the canvas routes them).\n'
    "- A branch that ends after an error/failure gets its OWN End terminator (e.g. 'End: Link expired') unless the brief names the same end.\n"
    "- Shapes: terminator = Start/End, process = action, decision = question, input = Input/Output (every 'Show …' message/screen and every user entry/selection).\n"
    '- Layout is automatic (top-to-bottom): coordinates are optional — do not spend output on x/y/width/height or waypoints.\n'
    '- Route loop-backs as orthogonal paths (large x/y offsets around nodes), not short diagonals through the middle.\n'
    '- Every decision needs Yes and No (or equivalent) labeled branches; failed paths reach an End.\n'
    "- For NEW diagrams only: x/y/width/height may be 0 (automatic layered layout). Edge order: list each decision's main/continuing branch first. In edit mode preserve existing geometry unless the user asks to change it."
)

TOOLBOX = [
    ToolboxItem(id="terminator", label="Start / End", kind="node", shape="terminator", default_width=120, default_height=48),
    ToolboxItem(id="process", label="Process", kind="node", shape="process", default_width=140, default_height=64),
    ToolboxItem(id="decision", label="Decision", kind="node", shape="decision", default_width=88, default_height=88),
    ToolboxItem(id="input", label="Input / Output", kind="node", shape="input", default_width=140, default_height=56),
    ToolboxItem(id="document", label="Document", kind="node", shape="document", default_width=120, default_height=72),
    ToolboxItem(id="data_store", label="Database", kind="node", shape="data_store", default_width=100, default_height=64),
    ToolboxItem(id="preparation", label="Preparation", kind="node", shape="preparation", default_width=140, default_height=56),
    ToolboxItem(id="display", label="Display", kind="node", shape="display", default_width=120, default_height=56),
    ToolboxItem(id="manual_input", label="Manual Operation", kind="node", shape="manual_input", default_width=120, default_height=56),
    ToolboxItem(id="delay", label="Delay", kind="node", shape="delay", default_width=56, default_height=56),
    ToolboxItem(id="off_page", label="Off-page", kind="node", shape="off_page", default_width=48, default_height=48),
    ToolboxItem(id="connector_node", label="Connector", kind="node", shape="connector_node", default_width=40, default_height=40),
    ToolboxItem(id="text_box", label="Comment", kind="node", shape="text_box", default_width=120, default_height=48),
    ToolboxItem(id="connector", label="Flow Line", kind="edge", shape="connector"),
]
