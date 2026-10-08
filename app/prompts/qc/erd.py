"""QC rules for Entity-Relationship diagrams."""

from app.prompts.qc.base import compose_qc_system

QC_SYSTEM = compose_qc_system(
    type_focus=(
        "ERD with table-style entities, optional Chen attributes/relationship diamonds, "
        "and crow's-foot cardinality edges."
    ),
    vocabulary="entities, relationships, attributes, cardinality",
    blocking_rules="""
1. Diagram empty / unusable.
2. A major entity explicitly named in the request is completely missing.
3. Edges reference missing node ids, or types outside the ERD toolbox.
4. Wrong diagram type for the request (e.g. flowchart when user asked for ERD).
5. Do NOT block solely for missing optional attribute ovals when table compartments exist.
""",
)
