"""Prompts for extracting a structured process model from a user brief."""

from app.prompts.diagrams import DIAGRAM_TYPE_LABELS
from app.schemas.diagram import DiagramType

PROCESS_PLAN_SYSTEM = """You extract a COMPLETE structured process inventory from a diagram brief.

You do NOT draw the diagram. You inventory every explicit requirement so a later generator cannot omit them.

Rules:
1. Include EVERY lane/actor/role the user named.
2. Include EVERY activity/action the user stated — never merge two distinct actions into one.
3. Every conditional ("if", "or", "accept/reject", "success/failure", "confirm/decline", "Yes/No")
   MUST become a decision element with explicit branches.
4. Include start and end events. Failed/rejected branches that "end" need their own end elements
   (or clearly mark ends_process on the branch).
5. Include a notify / notify-customer activity ONLY when the brief affirmatively requests it.
   If the brief says no/not/without/exclude/don't/do not/skip notifications (or similar),
   do NOT invent a notify step. When a notify IS requested, it is a SEPARATE activity on each
   terminating branch that needs it — do not skip it.
6. Preserve the logical order from the prompt.
7. Do NOT invent refunds, retries, cancellations, timeouts, or extra business rules.
8. Do NOT drop a stated handoff or actor action. Do NOT merge pick-up with deliver (or any two
   distinct verbs) into one activity.
9. Lane names on activities/decisions must match the lane list exactly when the actor is clear.
10. Anything the brief excludes or says no/without/exclude MUST NOT appear in the inventory.

Respond ONLY with JSON:
{
  "title": "string",
  "lanes": ["Lane A", "Lane B"],
  "elements": [
    {"id":"s1","kind":"start","label":"Start","lane":"Lane A","branches":[]},
    {"id":"a1","kind":"activity","label":"Place Order & Pay","lane":"Lane A","branches":[]},
    {"id":"d1","kind":"decision","label":"Payment Successful?","lane":"Lane B",
     "branches":[
       {"label":"Yes","outcome":"continue","next_element_id":"a2","ends_process":false},
       {"label":"No","outcome":"end process","next_element_id":"e_fail","ends_process":true}
     ]},
    {"id":"e1","kind":"end","label":"End","lane":"Lane A","branches":[]}
  ],
  "flows": [
    {"from_id":"s1","to_id":"a1","label":""},
    {"from_id":"a1","to_id":"d1","label":""}
  ],
  "notes": ["optional short notes"]
}"""


def build_process_plan_prompt(diagram_type: DiagramType, user_prompt: str) -> str:
    label = DIAGRAM_TYPE_LABELS[diagram_type]
    return f"""Diagram type: {label}

Brief to inventory (extract EVERY stated requirement; invent nothing; honor exclusions):
{user_prompt.strip()}
"""
