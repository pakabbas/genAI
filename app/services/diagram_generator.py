import json
import re

from google import genai
from google.genai import types

from app.config import get_settings
from app.prompts.diagrams import (
    DIAGRAM_SYSTEM_INSTRUCTION,
    DIAGRAM_TYPE_LABELS,
    build_diagram_user_prompt,
)
from app.schemas.diagram import DiagramDocument, DiagramType

JSON_FENCE_PATTERN = re.compile(
    r"^```(?:json)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    match = JSON_FENCE_PATTERN.match(stripped)
    if match:
        return match.group(1).strip()
    return stripped


def _extract_json_object(text: str) -> str:
    cleaned = _strip_json_fences(text)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Gemini did not return a valid JSON diagram.")
    return cleaned[start : end + 1]


def generate_diagram(
    diagram_type: DiagramType,
    user_prompt: str,
    existing: DiagramDocument | None = None,
) -> DiagramDocument:
    settings = get_settings()
    api_key = settings["gemini_api_key"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Set it in your .env file.")

    existing_json = None
    if existing:
        existing_json = existing.model_dump_json(by_alias=True)

    client = genai.Client(api_key=api_key)
    model = settings["gemini_model"]

    response = client.models.generate_content(
        model=model,
        contents=build_diagram_user_prompt(diagram_type, user_prompt, existing_json),
        config=types.GenerateContentConfig(
            system_instruction=DIAGRAM_SYSTEM_INSTRUCTION,
            temperature=0.7,
            top_p=0.9,
            max_output_tokens=16384,
            response_mime_type="application/json",
        ),
    )

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response. Please try again.")

    raw_json = _extract_json_object(text)
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid diagram JSON from model: {exc}") from exc

    data["diagram_type"] = diagram_type
    if "title" not in data or not str(data.get("title", "")).strip():
        data["title"] = DIAGRAM_TYPE_LABELS[diagram_type]

    return DiagramDocument.model_validate(data)
