"""Swim Lane / BPMN: generator rules and the editable-shape catalog defaults."""

from app.schemas.diagram import ToolboxItem

GUIDANCE = (
    'BPMN completeness rules (strict):\n'
    '- Create one pool and one lane node per named role/actor. Lane labels must match the brief.\n'
    '- Place start + end event circles. Failed/rejected paths that end the process need End events too.\n'
    "- Every stated action = its own process task (never merge 'pick up' + 'deliver' into one box).\n"
    '- Every if/or/accept-reject/success-failure = gateway_xor with ≥2 labeled outgoing flows (Yes/No or Accepted/Rejected). Do not replace a decision with a plain task.\n'
    '- Keep activities in the correct lane for the actor who performs them.\n'
    '- Sequence flow = flow (solid filled arrow); message flow = message_flow (dashed open arrow).\n'
    '- Layout (generous spacing — avoid cramped diagrams):\n'
    '  · Pool ≈ 1600–2000 wide; each lane ≥ 170 tall with 24px vertical padding inside.\n'
    '  · Place tasks left→right with ≥ 80px horizontal gap between shapes.\n'
    '  · Leave ≥ 120px free margin on the right of the rightmost task (room for future shapes).\n'
    '  · World coords may span x:40–2100 and y:40–1400; pan/zoom is fine — do NOT pack tightly.\n'
    '- Decision gateways need at least two labeled outgoing edges; failed paths reach an End.\n'
    '- Keep pool and lane containers behind their contents, enclosing all children plus padding.'
)

TOOLBOX = [
    ToolboxItem(id="pool", label="Pool", kind="node", shape="pool", default_width=1680, default_height=780),
    ToolboxItem(id="lane", label="Swim Lane", kind="node", shape="lane", default_width=1580, default_height=180),
    ToolboxItem(id="start", label="Start Event", kind="node", shape="start", default_width=48, default_height=48),
    ToolboxItem(id="end", label="End Event", kind="node", shape="end", default_width=48, default_height=48),
    ToolboxItem(id="process", label="Task / Process", kind="node", shape="process", default_width=140, default_height=64),
    ToolboxItem(id="subprocess", label="Subprocess", kind="node", shape="subprocess", default_width=160, default_height=72),
    ToolboxItem(id="gateway_xor", label="XOR Gateway", kind="node", shape="gateway_xor", default_width=72, default_height=72),
    ToolboxItem(id="gateway_and", label="AND Gateway", kind="node", shape="gateway_and", default_width=72, default_height=72),
    ToolboxItem(id="document", label="Document", kind="node", shape="document", default_width=120, default_height=72),
    ToolboxItem(id="data_store", label="Data Store", kind="node", shape="data_store", default_width=100, default_height=64),
    ToolboxItem(id="text_box", label="Annotation", kind="node", shape="text_box", default_width=120, default_height=48),
    ToolboxItem(id="flow", label="Sequence Flow", kind="edge", shape="flow"),
    ToolboxItem(id="message_flow", label="Message Flow", kind="edge", shape="message_flow"),
]
