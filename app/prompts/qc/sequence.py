"""QC rules for Sequence diagrams."""

from app.prompts.qc.base import compose_qc_system

QC_SYSTEM = compose_qc_system(
    type_focus=(
        "UML sequence: actors/lifelines and ordered messages.\n"
        "Human participants should be actor shapes; systems use lifeline/object.\n"
        "Message edges must be message / async_message / return_message."
    ),
    vocabulary="actors, lifelines, messages (never say entity boxes)",
    blocking_rules="""
1. Diagram empty / unusable.
2. A major participant or message exchange explicitly named in the request is missing.
3. Edges use invalid types (must be message / async_message / return_message — not connector).
4. Edges reference missing node ids, or node types outside the sequence toolbox.
5. Wrong diagram type for the request.
""",
)
