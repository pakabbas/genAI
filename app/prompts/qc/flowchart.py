"""QC rules for Flowchart diagrams."""

from app.prompts.qc.base import compose_qc_system

QC_SYSTEM = compose_qc_system(
    type_focus=(
        "Standard flowcharts: terminators, processes, decisions, I/O, documents, connectors.\n"
        "Prompt completeness for steps and decisions is CRITICAL."
    ),
    vocabulary="steps/processes, decisions, branches, start/end terminators",
    blocking_rules="""
1. Diagram empty / unusable.
2. A major process step explicitly named in the request is missing
   (do not accept distinct steps merged into one process box).
3. A conditional in the request is missing as a decision diamond, OR a decision has
   fewer than two outgoing labeled branches, OR a stated branch outcome is missing
   (e.g. 2FA Yes/No, retry loops).
4. Long diagonal loop-backs that cut through the diagram instead of routing around —
   flag as blocking when readability collapses.
5. Start/end terminator missing when the brief describes a bounded process.
6. Edges reference missing node ids, or types outside the flowchart toolbox.
7. Wrong diagram type for the request.
""",
)
