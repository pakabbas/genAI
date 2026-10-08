"""QC rules for Class diagrams."""

from app.prompts.qc.base import compose_qc_system

QC_SYSTEM = compose_qc_system(
    type_focus=(
        "UML class diagram: classes/interfaces/enums with compartment labels, "
        "and association / inheritance / composition / aggregation / dependency edges."
    ),
    vocabulary="classes, interfaces, associations, inheritance",
    blocking_rules="""
1. Diagram empty / unusable.
2. A major class/interface explicitly named in the request is missing.
3. Edges reference missing node ids, or types outside the class_diagram toolbox.
4. Wrong diagram type for the request.
5. Missing optional methods/attributes → recommendation only, not blocking.
""",
)
