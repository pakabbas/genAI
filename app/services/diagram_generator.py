"""JSON diagram parsing helpers (generation lives in diagram_pipeline)."""

import json
import re

from app.prompts.diagrams import DIAGRAM_TYPE_LABELS, type_label
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


def _parse_diagram_json(raw_text: str, diagram_type: DiagramType) -> DiagramDocument:
    raw_json = _extract_json_object(raw_text)
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid diagram JSON from model: {exc}") from exc

    data["diagram_type"] = diagram_type
    if "title" not in data or not str(data.get("title", "")).strip():
        try:
            data["title"] = type_label(diagram_type)
        except Exception:
            data["title"] = DIAGRAM_TYPE_LABELS[diagram_type]

    return DiagramDocument.model_validate(data)
