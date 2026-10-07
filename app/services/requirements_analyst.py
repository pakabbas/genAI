"""Requirements Analyst (Agent 0): chat clarification + prompt enhancement."""

from __future__ import annotations

import json

from google import genai
from google.genai import types

from app.config import get_settings
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
from app.services.prompt_guard import check_non_diagram_intent

MAX_CLARIFICATION_ROUNDS = 3


def _count_assistant_question_rounds(messages: list[ChatMessage]) -> int:
    """Count prior assistant turns that were asking for more info (heuristic)."""
    return sum(1 for m in messages if m.role == "assistant")


def run_requirements_turn(
    diagram_type: DiagramType,
    messages: list[ChatMessage],
    *,
    force_ready: bool = False,
) -> RequirementsChatResponse:
    settings = get_settings()
    api_key = settings["gemini_api_key"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Set it in your .env file.")

    prior_rounds = _count_assistant_question_rounds(messages)
    must_ready = force_ready or prior_rounds >= MAX_CLARIFICATION_ROUNDS

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

    user_content = build_requirements_user_prompt(
        diagram_type,
        payload,
        force_ready=must_ready,
        prior_question_rounds=prior_rounds,
    )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=str(settings["gemini_model"]),
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=REQUIREMENTS_SYSTEM_INSTRUCTION,
            temperature=0.35,
            top_p=0.9,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Requirements Analyst returned an empty response.")

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
