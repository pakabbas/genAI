"""Requirements Analyst (Agent 0) — clarify briefly, then enhance the prompt."""

from app.prompts.diagrams import DIAGRAM_TYPE_GUIDANCE, DIAGRAM_TYPE_LABELS, toolbox_catalog
from app.schemas.diagram import DiagramType

REQUIREMENTS_SYSTEM_INSTRUCTION = """You are the Requirements Analyst for an AI diagram studio.

You are Agent 0 in a pipeline: Requirements Analyst → Diagram Generator → QC Auditor.

Your job:
1. Read the user's diagram request and chat history.
2. If the request is too vague to produce a consistent diagram, ask a SHORT clarifying question.
3. Otherwise (or after answers), produce a clear enhanced_prompt for the Diagram Generator.

CRITICAL rules — do NOT over-ask:
- Prefer reasonable assumptions over questions whenever possible.
- Ask ONLY when missing info would cause a wrong diagram type structure (e.g. unknown system domain, no actors/entities/steps at all).
- Ask at most 1–2 short questions in a single turn.
- Never ask more than necessary; never quiz the user.
- If the user already answered or said to proceed, set status to "ready".
- If force_ready is true, you MUST set status to "ready" and fill gaps with explicit assumptions.
- If the user asks for poems, jokes, stories, or other non-diagram content, set status to "rejected" and explain this studio only creates technical diagrams.

When status is "need_more_info":
- assistant_message should be a friendly, concise clarification (questions included).
- enhanced_prompt must be null.

When status is "ready":
- assistant_message briefly confirms what you will generate (1–2 sentences).
- enhanced_prompt must be a detailed, structured brief the generator can follow consistently.
- List key assumptions you made.

enhanced_prompt format (plain text, not JSON):
- Title suggestion
- Domain / system context
- Actors / roles OR entities OR lanes OR steps (as appropriate for the diagram type)
- Key flows / relationships / processes to include
- Scope boundaries (what to include / exclude)
- Explicit assumptions
- Desired level of detail (keep diagrams focused: typically 6–18 nodes)

Respond ONLY with JSON:
{
  "status": "need_more_info" | "ready" | "rejected",
  "assistant_message": "string shown in the chat UI",
  "enhanced_prompt": "string or null",
  "assumptions": ["..."],
  "questions_asked": ["..."]
}"""


def build_requirements_user_prompt(
    diagram_type: DiagramType,
    messages: list[dict[str, str]],
    *,
    force_ready: bool = False,
    prior_question_rounds: int = 0,
) -> str:
    label = DIAGRAM_TYPE_LABELS[diagram_type]
    guidance = DIAGRAM_TYPE_GUIDANCE[diagram_type]
    catalog = toolbox_catalog(diagram_type)

    history_lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        content = (msg.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")

    history = "\n\n".join(history_lines) if history_lines else "(empty)"

    force_note = (
        "FORCE READY: The user chose to proceed now. You MUST return status=\"ready\" "
        "with a solid enhanced_prompt, filling gaps via assumptions."
        if force_ready
        else "If the request is already clear enough, return status=\"ready\" without asking."
    )

    round_note = (
        f"Clarification rounds so far: {prior_question_rounds}. "
        "If prior_question_rounds >= 2, you MUST return status=\"ready\" "
        "(make assumptions instead of asking again)."
    )

    return f"""Diagram type selected: {label} ({diagram_type})

Type guidance:
{guidance}

Available toolbox shapes:
{catalog}

{force_note}
{round_note}

Conversation so far:
{history}

Decide whether you need more info or can enhance the prompt for generation.
Return JSON only."""
