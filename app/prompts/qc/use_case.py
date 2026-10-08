"""QC rules for Use Case diagrams."""

from app.prompts.qc.base import compose_qc_system

QC_SYSTEM = compose_qc_system(
    type_focus=(
        "UML use case: actors, use-case ovals, optional system boundary, "
        "association / include / extend / generalization edges."
    ),
    vocabulary="actors, use cases, system boundary, associations",
    blocking_rules="""
1. Diagram empty / unusable.
2. A primary actor or major use case explicitly named in the request is missing.
3. Edges reference missing node ids, or types outside the use_case toolbox.
4. Wrong diagram type for the request.
""",
)
