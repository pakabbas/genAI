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
   (or clearly mark ends_process on the branch) plus any notify/notify-customer activity stated.
5. If the brief says the customer (or another actor) is notified on decline/reject, that notify
   action is a SEPARATE activity on EACH such terminating branch — do not skip it.
6. Preserve the logical order from the prompt.
7. Do NOT invent refunds, retries, cancellations, timeouts, or extra business rules.
8. Do NOT drop a stated handoff or actor action. Do NOT merge pick-up with deliver (or any two
   distinct verbs) into one activity.
9. Lane names on activities/decisions must match the lane list exactly when the actor is clear.

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
       {"label":"No","outcome":"notify customer and end","next_element_id":"a_notify","ends_process":false}
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

Extract the full process inventory from this brief. Be exhaustive for activities and decisions.

User brief:
{user_prompt.strip()}
"""
