"""Requirements Analyst (Agent 0): chat clarification + prompt enhancement."""

from __future__ import annotations

import json

from app.prompts.requirements import (
    REQUIREMENTS_SYSTEM_INSTRUCTION,
    build_requirements_user_prompt,
)
from app.schemas.diagram import DiagramType
from app.schemas.generation import (
    ChatMessage,
    RequirementsChatResponse,
)
from app.services.diagram_generator import _extract_json_object
from app.services.gemini_client import generate_json
from app.services.prompt_guard import check_non_diagram_intent
from app.services import settings_service as cfg


def _count_assistant_question_rounds(messages: list[ChatMessage]) -> int:
    """Count prior assistant turns that were asking for more info (heuristic)."""
    return sum(1 for m in messages if m.role == "assistant")


def run_requirements_turn(
    diagram_type: DiagramType,
    messages: list[ChatMessage],
    *,
    force_ready: bool = False,
) -> RequirementsChatResponse:
    max_clarify = int(cfg.get_value("pipeline.max_clarify_rounds"))
    clarify_mode = str(cfg.get_value("pipeline.clarify_mode"))

    prior_rounds = _count_assistant_question_rounds(messages)
    must_ready = (
        force_ready
        or clarify_mode == "off"
        or prior_rounds >= max_clarify
    )

    payload = [
        {"role": m.role, "content": m.content.strip()}
        for m in messages
        if m.content.strip()
    ]
    if not payload:
        raise ValueError("Send at least one message describing your diagram.")

    user_text = "\n".join(m["content"] for m in payload if m["role"] == "user")
    refusal = check_non_diagram_intent(user_text)
    if refusal:
        return RequirementsChatResponse(
            status="rejected",
            assistant_message=refusal,
            enhanced_prompt=None,
            assumptions=[],
            questions_asked=[],
        )

    if clarify_mode == "off":
        must_ready = True

    user_content = build_requirements_user_prompt(
        diagram_type,
        payload,
        force_ready=must_ready,
        prior_question_rounds=prior_rounds,
        max_clarify_rounds=max_clarify,
        clarify_mode=clarify_mode,
    )

    system = cfg.active_prompt_body("analyst.system") or REQUIREMENTS_SYSTEM_INSTRUCTION
    text = generate_json(
        role="analyst",
        system_instruction=system,
        user_content=user_content,
        temperature=float(cfg.get_value("ai.analyst.temperature")),
        top_p=float(cfg.get_value("ai.analyst.top_p")),
        max_output_tokens=int(cfg.get_value("ai.analyst.max_output_tokens")),
    )

    data = json.loads(_extract_json_object(text))
    result = RequirementsChatResponse.model_validate(data)

    if must_ready:
        result.status = "ready"

    if result.status == "ready":
        if not (result.enhanced_prompt or "").strip():
            # Fallback: stitch conversation into a usable brief
            user_bits = [m.content.strip() for m in messages if m.role == "user"]
            result.enhanced_prompt = (
                "Diagram brief derived from user conversation:\n\n"
                + "\n\n".join(user_bits)
            )
        result.enhanced_prompt = result.enhanced_prompt.strip()
        if not result.assistant_message.strip():
            result.assistant_message = (
                "Brief is ready. I enhanced your requirements for consistent generation. "
                "Click Generate when you want the diagram."
            )
    else:
        result.enhanced_prompt = None
        if not result.assistant_message.strip():
            result.assistant_message = (
                "Could you share a bit more detail so I can shape a clear diagram brief?"
            )

    return result
