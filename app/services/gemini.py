import re

from google import genai
from google.genai import types

from app.config import get_settings
from app.prompts import SYSTEM_INSTRUCTION, build_user_prompt

HTML_FENCE_PATTERN = re.compile(
    r"^```(?:html)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL | re.IGNORECASE,
)


def _strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    match = HTML_FENCE_PATTERN.match(stripped)
    if match:
        return match.group(1).strip()
    return stripped


def _ensure_html_document(text: str) -> str:
    cleaned = _strip_markdown_fences(text)
    lower = cleaned.lower()
    if "<!doctype html" in lower or "<html" in lower:
        return cleaned
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Generated Output</title>
  <style>
    body {{
      font-family: system-ui, sans-serif;
      line-height: 1.6;
      padding: 2rem;
      max-width: 960px;
      margin: 0 auto;
      color: #1a1a2e;
    }}
  </style>
</head>
<body>
{cleaned}
</body>
</html>"""


def generate_html(content_type: str, user_prompt: str) -> str:
    settings = get_settings()
    api_key = settings["gemini_api_key"]
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured. Set it in your .env file.")

    client = genai.Client(api_key=api_key)
    model = settings["gemini_model"]

    response = client.models.generate_content(
        model=model,
        contents=build_user_prompt(content_type, user_prompt),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.85,
            top_p=0.95,
            max_output_tokens=16384,
        ),
    )

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned an empty response. Please try again.")

    return _ensure_html_document(text)
