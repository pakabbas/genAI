"""QC rules for Swim Lane / BPMN diagrams."""

from app.prompts.qc.base import compose_qc_system

QC_SYSTEM = compose_qc_system(
    type_focus=(
        "Swim lane / BPMN process diagrams with pool, lanes, start/end events, "
        "tasks (process), XOR/AND gateways, and sequence/message flows.\n"
        "Prompt completeness is CRITICAL for this type."
    ),
    vocabulary="lanes, tasks/activities, gateways, sequence flows, start/end events",
    blocking_rules="""
1. Diagram empty / unusable (no meaningful nodes).
2. A lane/role explicitly named in the request is missing.
3. An activity/action explicitly stated in the request is missing as its own task
   (do not accept two distinct actions illegally merged into one box).
4. A conditional in the request (if / or / accept-reject / success-failure / confirm-decline)
   is missing as gateway_xor (or equivalent), OR a gateway has fewer than two outgoing
   labeled branches, OR a stated branch outcome (e.g. notify + end) is missing.
5. Start or End event missing when the brief implies a process with start/end.
6. Edges reference missing node ids, or node/edge types outside the swim_lane toolbox.
7. Wrong diagram type for the request.
""",
)
