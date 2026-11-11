"""Entity Relationship (ERD): generator rules and the editable-shape catalog defaults."""

from app.schemas.diagram import ToolboxItem

GUIDANCE = (
    "ERD with table-style entities (label compartments: Name\\n--\\nPK id\\nattr\\nFK other_id). Optional Chen attribute ovals + relationship diamonds. Cardinality edges use crow's-foot types: one, many, one_or_many, zero_or_one, zero_or_many, one_to_one, one_to_many, many_to_many, identifying. Do NOT use data_store.\n"
    "- Use crow's-foot edge types for cardinality, never plain connector.\n"
    '- Connect attributes to entities and relationships to entities.'
)

TOOLBOX = [
    ToolboxItem(id="entity", label="Entity (table)", kind="node", shape="entity", default_width=180, default_height=110),
    ToolboxItem(id="weak_entity", label="Weak Entity", kind="node", shape="weak_entity", default_width=180, default_height=110),
    ToolboxItem(id="attribute", label="Attribute (oval)", kind="node", shape="attribute", default_width=120, default_height=48),
    ToolboxItem(id="relationship", label="Relationship ◆", kind="node", shape="relationship", default_width=72, default_height=72),
    ToolboxItem(id="note", label="Note", kind="node", shape="note", default_width=120, default_height=80),
    ToolboxItem(id="one", label="One (1)", kind="edge", shape="one"),
    ToolboxItem(id="many", label="Many (*)", kind="edge", shape="many"),
    ToolboxItem(id="one_or_many", label="One or Many (1..*)", kind="edge", shape="one_or_many"),
    ToolboxItem(id="zero_or_one", label="Zero or One (0..1)", kind="edge", shape="zero_or_one"),
    ToolboxItem(id="zero_or_many", label="Zero or Many (0..*)", kind="edge", shape="zero_or_many"),
    ToolboxItem(id="one_to_one", label="One-to-One", kind="edge", shape="one_to_one"),
    ToolboxItem(id="one_to_many", label="One-to-Many", kind="edge", shape="one_to_many"),
    ToolboxItem(id="many_to_many", label="Many-to-Many", kind="edge", shape="many_to_many"),
    ToolboxItem(id="identifying", label="Identifying", kind="edge", shape="identifying"),
]
