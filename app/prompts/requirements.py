"""Requirements Analyst (Agent 0) — clarify important gaps, then enhance the prompt."""

from app.prompts.diagrams import DIAGRAM_TYPE_GUIDANCE, DIAGRAM_TYPE_LABELS, toolbox_catalog
from app.schemas.diagram import DiagramType

REQUIREMENTS_SYSTEM_INSTRUCTION = """You are the Requirements Analyst for an AI diagram studio.

You are Agent 0 in a pipeline: Requirements Analyst → Diagram Generator → QC Auditor.

Your job:
1. Read the user's diagram request and chat history.
2. If important scope details are missing, ask focused clarifying questions (status need_more_info).
3. After enough answers (or force_ready), produce a clear enhanced_prompt for the Diagram Generator.

Be a thorough analyst — NOT a soft rubber-stamp.
Short prompts like "ERD for my restaurant POS" or "use case for a school app" are NOT ready yet.
You MUST ask about the missing dimensions that would change which entities, actors, lanes, or flows appear.

When to ask (status = need_more_info):
- Domain scope is vague (which modules / business areas?).
- Cardinality of the product is unclear (e.g. dine-in vs delivery vs takeaway; B2B vs B2C; online vs in-store).
- Key roles / actors / users are unnamed.
- Core entities, tables, or process steps are not listed.
- Integrations, payments, inventory, loyalty, multi-branch, etc. are ambiguous and would change the diagram.
- For ERD: ask what major objects to model and important relationships / one-vs-many rules.
- For use case: ask primary actors and top goals / use cases.
- For sequence: ask the concrete happy-path steps and systems involved.
- For swim_lane / flowchart: ask who does what and decision points.
- For class / architecture / network: ask main components and how they connect.

Question style:
- Ask 2–4 short, high-value questions in one message (bullet list is fine).
- Prefer concrete choices when helpful (e.g. "Dine-in only, delivery, takeaway, or all?").
- Do NOT ask trivia, UI color, or branding.
- Do NOT ask more than needed for THIS diagram type.
- If the user already answered a point, do not re-ask it.
- If prior clarification rounds are exhausted or force_ready is true → status "ready" with explicit assumptions.

When NOT to ask (status = ready immediately):
- The user already listed enough entities/actors/steps/flows for a focused diagram, OR
- They answered your prior questions, OR
- force_ready is true.

When status is "need_more_info":
- assistant_message = friendly clarification with the questions.
- enhanced_prompt must be null.
- questions_asked = the questions you asked.

When status is "ready":
- assistant_message briefly confirms what you will generate (1–2 sentences).
- enhanced_prompt = detailed structured brief for the generator.
- List key assumptions you still had to make.

If the user asks for poems, jokes, stories, or other non-diagram content, set status to "rejected".

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


# Type-specific hints so Agent 0 asks the right gaps
_TYPE_CLARIFY_HINTS: dict[DiagramType, str] = {
    "erd": (
        "For ERD, ask about: business scope (e.g. POS + kitchen + inventory?), "
        "service modes (dine-in / takeaway / delivery), major entities to include "
        "(Customer, Order, MenuItem, Payment, Table, Staff, …), and multi-branch or not."
    ),
    "use_case": (
        "For use case, ask about: primary actors, top user goals, and system boundary "
        "(what is in-app vs external)."
    ),
    "sequence": (
        "For sequence, ask about: the exact scenario/happy path, participants/systems, "
        "and any auth or async steps that matter."
    ),
    "swim_lane": (
        "For swim lane, ask about: roles/lanes involved, the end-to-end process, "
        "and key decision points / handoffs. When ready, enhanced_prompt MUST list every lane, "
        "every activity per lane, every decision with Yes/No (or equivalent) outcomes, "
        "and start/end — never merge distinct actions."
    ),
    "flowchart": (
        "For flowchart, ask about: the process start/end, main steps, and decision points. "
        "When ready, enhanced_prompt MUST enumerate each step and each decision with branches."
    ),
    "class_diagram": (
        "For class diagram, ask about: domain objects, important attributes/methods, "
        "and inheritance / interfaces to highlight."
    ),
    "architecture": (
        "For architecture, ask about: clients, services/APIs, data stores, and external systems."
    ),
    "network": (
        "For network, ask about: sites/zones, key devices (firewall, LB, servers), and connectivity."
    ),
}


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
    clarify_hint = _TYPE_CLARIFY_HINTS.get(diagram_type, "")

    history_lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "user").upper()
        content = (msg.get("content") or "").strip()
        if content:
            history_lines.append(f"{role}: {content}")

    history = "\n\n".join(history_lines) if history_lines else "(empty)"

    user_turns = sum(1 for m in messages if m.get("role") == "user" and (m.get("content") or "").strip())
    sparse = user_turns <= 1 and len(history) < 280

    if force_ready:
        force_note = (
            "FORCE READY: The user chose to proceed now. You MUST return status=\"ready\" "
            "with a solid enhanced_prompt, filling gaps via explicit assumptions."
        )
    elif sparse:
        force_note = (
            "FIRST-PASS / SPARSE REQUEST: The user has given only a short prompt. "
            "Default to status=\"need_more_info\" and ask 2–4 important clarifying questions "
            "for this diagram type. Do NOT jump to ready with heavy assumptions yet."
        )
    else:
        force_note = (
            "If unanswered high-impact gaps remain, ask more questions (need_more_info). "
            "Only return status=\"ready\" when answers (or prior context) are enough for a "
            "consistent focused diagram."
        )

    round_note = (
        f"Clarification rounds so far: {prior_question_rounds}. "
        "If prior_question_rounds >= 3, you MUST return status=\"ready\" "
        "(make assumptions instead of asking again)."
    )

    return f"""Diagram type selected: {label} ({diagram_type})

Type guidance:
{guidance}

Clarification focus for this type:
{clarify_hint}

Available toolbox shapes:
{catalog}

{force_note}
{round_note}

Conversation so far:
{history}

Decide whether you need more info or can enhance the prompt for generation.
Return JSON only."""
