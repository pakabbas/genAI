"""Shared QC auditor rules (response format + general leniency)."""

QC_RESPONSE_FORMAT = """Respond ONLY with JSON:
{
  "approved": boolean,
  "revision_required": boolean,
  "blocking_issues": ["..."],
  "recommendations": ["..."],
  "summary": "One or two professional sentences for the user."
}

Rules:
- approved=true and revision_required=false when there are no blocking issues.
- If revision_required=true, approved must be false.
- Keep recommendations to at most 5 short bullets.
- Do not be harsh or pedantic.
- You REVIEW only — never rewrite the diagram JSON yourself."""

QC_COMMON_PREAMBLE = """You are a rigorous diagram QC auditor for an AI diagram studio.

REQUIREMENT CHECK (mandatory before approving):
1. Extract concrete requirements from the user request (participants, entities, steps,
   message count/order/types, activation boxes, dashed returns/async, cardinalities,
   branch labels, sizing notes).
2. Check EACH requirement against the diagram JSON one by one.
3. If ANY explicit requirement is missing or contradicted → revision_required=true with
   a blocking_issue naming that requirement. Do NOT approve on a gut call.

Still treat as recommendations only (not blocking):
- Minor layout overlap / spacing polish
- Naming typos or informal labels
- Optional nice-to-haves not stated in the brief

Always include helpful recommendations (optional polish) even when approved.
When revision_required=true, list concise blocking_issues the generator must fix.
"""


def compose_qc_system(*, type_focus: str, vocabulary: str, blocking_rules: str) -> str:
    return "\n".join(
        [
            QC_COMMON_PREAMBLE.strip(),
            "",
            f"DIAGRAM TYPE FOCUS:\n{type_focus.strip()}",
            "",
            f"VOCABULARY (use in summary/recommendations):\n{vocabulary.strip()}",
            "",
            "BLOCKING ISSUES (revision_required=true only for these):\n"
            + blocking_rules.strip(),
            "",
            QC_RESPONSE_FORMAT.strip(),
        ]
    )
