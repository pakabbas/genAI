"""Sequence Diagram: generator rules and the editable-shape catalog defaults."""

from app.schemas.diagram import ToolboxItem

GUIDANCE = (
    'UML sequence: lifelines top-to-bottom. Human participants (User, Customer, Actor, Person, Admin, etc.) MUST use node type actor (stick figure) — never lifeline or object for humans. Systems/services/APIs/DBs use type lifeline (or object). Message edges MUST use types message, async_message, or return_message only (never connector). Put optional meta.message_y for vertical order; the pipeline also stacks them.\n'
    '- Put message_y (number) on each message edge meta or field; use activation nodes when the brief asks.\n'
    '- Keep fragment containers behind their contents, enclosing all children plus padding.\n'
    '- When editing preserve activation boxes and message order unless the user asks to change them.'
)

TOOLBOX = [
    ToolboxItem(id="actor", label="Actor", kind="node", shape="actor", default_width=72, default_height=96),
    ToolboxItem(id="lifeline", label="Lifeline", kind="node", shape="lifeline", default_width=80, default_height=320),
    ToolboxItem(id="object", label="Object", kind="node", shape="object", default_width=100, default_height=48),
    ToolboxItem(id="activation", label="Activation", kind="node", shape="activation", default_width=16, default_height=80),
    ToolboxItem(id="fragment", label="Fragment (alt/loop)", kind="node", shape="fragment", default_width=280, default_height=160),
    ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
    ToolboxItem(id="message", label="Sync Message", kind="edge", shape="message"),
    ToolboxItem(id="async_message", label="Async Message", kind="edge", shape="async_message"),
    ToolboxItem(id="return_message", label="Return", kind="edge", shape="return_message"),
]
