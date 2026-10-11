"""Registry of every configurable setting: defaults match v2.6.9 behaviour."""

from __future__ import annotations

from typing import Any

ALL_DIAGRAM_TYPES = [
    "use_case",
    "erd",
    "swim_lane",
    "flowchart",
    "sequence",
    "class_diagram",
    "network",
    "architecture",
]

DEFAULT_TYPE_LABELS = {
    "use_case": "Use Case Diagram",
    "erd": "Entity Relationship (ERD)",
    "swim_lane": "Swim Lane / BPMN",
    "flowchart": "Flowchart",
    "sequence": "Sequence Diagram",
    "class_diagram": "Class Diagram",
    "network": "Network Diagram",
    "architecture": "Architecture Diagram",
}

DEFAULT_GUARD_PATTERNS = [
    {
        "pattern": r"\b(write|compose|create|make)\s+(a|an|me\s+a|me)?\s*(poem|poetry|haiku|limerick|sonnet|verse)\b",
        "reason": "poem",
    },
    {
        "pattern": r"\b(poem|poetry|haiku|limerick|sonnet|ballad|ode|rhyme)\b",
        "reason": "poem",
    },
    {
        "pattern": r"\b(write|tell)\s+(me\s+)?(a|an)?\s*(joke|story|fairytale|fairy tale|song lyrics)\b",
        "reason": "creative writing",
    },
    {
        "pattern": r"\bignore (all )?(previous|prior) (instructions|prompts)\b",
        "reason": "prompt injection",
    },
]

DEFAULT_GUARD_ALLOWLIST = (
    r"\b(diagram|flowchart|erd|entity|use[- ]?case|sequence|class diagram|network|architecture|"
    r"swim[- ]?lane|bpmn|actor|database|api|system|process|component|topology|schema)\b"
)

DEFAULT_GUARD_SHORT_CREATIVE = (
    r"\b(rhyme|metaphor|love letter|essay|paragraph about|once upon a time)\b"
)

DEFAULT_REFUSAL = (
    "This studio only creates technical diagrams — not {reason}. "
    "Describe a system, process, data model, or architecture you want diagrammed."
)


def _s(
    key: str,
    *,
    type: str,
    default: Any,
    group: str,
    label: str,
    help: str,
    scope: str = "server",
    min: float | int | None = None,
    max: float | int | None = None,
    allowed: list[Any] | None = None,
    readonly: bool = False,
) -> dict[str, Any]:
    return {
        "key": key,
        "type": type,
        "default": default,
        "group": group,
        "label": label,
        "help": help,
        "scope": scope,
        "min": min,
        "max": max,
        "allowed": allowed,
        "readonly": readonly,
    }


SETTINGS_REGISTRY: dict[str, dict[str, Any]] = {
    # A. AI Models
    "ai.provider": _s(
        "ai.provider",
        type="string",
        default="gemini",
        group="ai_models",
        label="AI provider",
        help="Currently only Gemini is supported.",
        readonly=True,
    ),
    "ai.model.analyst": _s(
        "ai.model.analyst",
        type="string",
        default="gemini-flash-lite-latest",
        group="ai_models",
        label="Analyst model (Agent 0)",
        help="Model for Requirements Analyst. Falls back to GEMINI_MODEL env when empty.",
    ),
    "ai.model.planner": _s(
        "ai.model.planner",
        type="string",
        default="gemini-flash-lite-latest",
        group="ai_models",
        label="Planner model",
        help="Model for process inventory extraction.",
    ),
    "ai.model.generator": _s(
        "ai.model.generator",
        type="string",
        default="gemini-flash-lite-latest",
        group="ai_models",
        label="Generator model (Agent 1)",
        help="Model for diagram JSON generation.",
    ),
    "ai.model.qc": _s(
        "ai.model.qc",
        type="string",
        default="gemini-flash-lite-latest",
        group="ai_models",
        label="QC model (Agent 2)",
        help="Model for QC audit.",
    ),
    "ai.model.fallback": _s(
        "ai.model.fallback",
        type="string",
        default="",
        group="ai_models",
        label="Fallback model",
        help="Optional model used after retries are exhausted.",
    ),
    # B. Generation parameters
    "ai.analyst.temperature": _s(
        "ai.analyst.temperature", type="number", default=0.35, group="generation",
        label="Analyst temperature", help="Sampling temperature for Agent 0.", min=0, max=2,
    ),
    "ai.analyst.top_p": _s(
        "ai.analyst.top_p", type="number", default=0.9, group="generation",
        label="Analyst top_p", help="Nucleus sampling for Agent 0.", min=0, max=1,
    ),
    "ai.analyst.max_output_tokens": _s(
        "ai.analyst.max_output_tokens", type="integer", default=4096, group="generation",
        label="Analyst max tokens", help="Max output tokens for Agent 0.", min=256, max=65536,
    ),
    "ai.planner.temperature": _s(
        "ai.planner.temperature", type="number", default=0.2, group="generation",
        label="Planner temperature", help="Sampling temperature for process planner.", min=0, max=2,
    ),
    "ai.planner.top_p": _s(
        "ai.planner.top_p", type="number", default=0.8, group="generation",
        label="Planner top_p", help="Nucleus sampling for planner.", min=0, max=1,
    ),
    "ai.planner.max_output_tokens": _s(
        "ai.planner.max_output_tokens", type="integer", default=8192, group="generation",
        label="Planner max tokens", help="Max output tokens for planner.", min=256, max=65536,
    ),
    "ai.generator.temperature": _s(
        "ai.generator.temperature", type="number", default=0.55, group="generation",
        label="Generator temperature", help="Temperature for initial diagram generation.", min=0, max=2,
    ),
    "ai.generator.revision_temperature": _s(
        "ai.generator.revision_temperature", type="number", default=0.4, group="generation",
        label="Revision temperature", help="Temperature when revising after QC/coverage.", min=0, max=2,
    ),
    "ai.generator.top_p": _s(
        "ai.generator.top_p", type="number", default=0.9, group="generation",
        label="Generator top_p", help="Nucleus sampling for generator.", min=0, max=1,
    ),
    "ai.generator.max_output_tokens": _s(
        "ai.generator.max_output_tokens", type="integer", default=16384, group="generation",
        label="Generator max tokens", help="Max output tokens for generator.", min=256, max=65536,
    ),
    "ai.qc.temperature": _s(
        "ai.qc.temperature", type="number", default=0.2, group="generation",
        label="QC temperature", help="Sampling temperature for QC auditor.", min=0, max=2,
    ),
    "ai.qc.top_p": _s(
        "ai.qc.top_p", type="number", default=0.9, group="generation",
        label="QC top_p", help="Nucleus sampling for QC.", min=0, max=1,
    ),
    "ai.qc.max_output_tokens": _s(
        "ai.qc.max_output_tokens", type="integer", default=16384, group="generation",
        label="QC max tokens", help="Max output tokens for QC.", min=256, max=65536,
    ),
    "ai.timeout_seconds": _s(
        "ai.timeout_seconds", type="integer", default=120, group="generation",
        label="AI timeout (seconds)", help="Per-call timeout (keep below nginx 300s).", min=10, max=290,
    ),
    "ai.max_retries": _s(
        "ai.max_retries", type="integer", default=1, group="generation",
        label="AI max retries", help="Retries on transient errors before fallback model.", min=0, max=5,
    ),
    # C. Pipeline
    "pipeline.qc_enabled": _s(
        "pipeline.qc_enabled", type="boolean", default=True, group="pipeline",
        label="QC enabled", help="Run QC auditor after generation.",
    ),
    "pipeline.max_qc_revisions": _s(
        "pipeline.max_qc_revisions", type="integer", default=3, group="pipeline",
        label="Max QC revisions", help="Maximum generator revision rounds after QC/coverage.", min=0, max=10,
    ),
    "pipeline.max_clarify_rounds": _s(
        "pipeline.max_clarify_rounds", type="integer", default=3, group="pipeline",
        label="Max clarify rounds", help="Analyst clarification rounds before forcing ready.", min=0, max=10,
    ),
    "pipeline.clarify_mode": _s(
        "pipeline.clarify_mode", type="string", default="strict", group="pipeline",
        label="Clarify mode", help="strict = current behaviour; lenient asks less; off skips clarify.",
        allowed=["strict", "lenient", "off"],
    ),
    "pipeline.process_coverage_types": _s(
        "pipeline.process_coverage_types", type="json",
        default=["swim_lane", "flowchart"], group="pipeline",
        label="Process coverage types", help="Diagram types that run process inventory + coverage.",
    ),
    "pipeline.max_recommendations": _s(
        "pipeline.max_recommendations", type="integer", default=5, group="pipeline",
        label="Max recommendations", help="Cap for QC recommendations (prompt + API response).", min=1, max=20,
    ),
    # E. Input & Safety
    "limits.chat_message_chars": _s(
        "limits.chat_message_chars", type="integer", default=8000, group="limits",
        label="Chat message max chars", help="Max characters per chat message.", min=100, max=32000, scope="public",
    ),
    "limits.chat_max_messages": _s(
        "limits.chat_max_messages", type="integer", default=40, group="limits",
        label="Chat max messages", help="Max messages in a requirements chat request.", min=1, max=200,
    ),
    "limits.generate_prompt_chars": _s(
        "limits.generate_prompt_chars", type="integer", default=12000, group="limits",
        label="Generate prompt max chars", help="Max characters for generate-diagram prompt.", min=3, max=64000,
    ),
    "limits.original_prompt_chars": _s(
        "limits.original_prompt_chars", type="integer", default=8000, group="limits",
        label="Original prompt max chars", help="Max characters for original_prompt field.", min=3, max=32000,
    ),
    "guard.enabled": _s(
        "guard.enabled", type="boolean", default=True, group="limits",
        label="Prompt guard enabled", help="Reject poems / creative / injection prompts.",
    ),
    "guard.patterns": _s(
        "guard.patterns", type="json", default=DEFAULT_GUARD_PATTERNS, group="limits",
        label="Guard patterns", help="List of {pattern, reason} regex rules.",
    ),
    "guard.allowlist": _s(
        "guard.allowlist", type="string", default=DEFAULT_GUARD_ALLOWLIST, group="limits",
        label="Diagram allowlist regex", help="Vocabulary that marks a prompt as diagram-related.",
    ),
    "guard.short_creative_pattern": _s(
        "guard.short_creative_pattern", type="string", default=DEFAULT_GUARD_SHORT_CREATIVE, group="limits",
        label="Short creative regex", help="Extra refusal patterns for short non-diagram prompts.",
    ),
    "guard.short_prompt_chars": _s(
        "guard.short_prompt_chars", type="integer", default=160, group="limits",
        label="Short prompt threshold", help="Below this length, apply short creative checks.", min=20, max=2000,
    ),
    "guard.refusal_message": _s(
        "guard.refusal_message", type="string", default=DEFAULT_REFUSAL, group="limits",
        label="Refusal message", help="Use {reason} placeholder.",
    ),
    # F. Diagram types
    "diagrams.enabled_types": _s(
        "diagrams.enabled_types", type="json", default=ALL_DIAGRAM_TYPES, group="diagrams",
        label="Enabled diagram types", help="Types shown in the UI and accepted by the API.", scope="public",
    ),
    "diagrams.default_type": _s(
        "diagrams.default_type", type="string", default="use_case", group="diagrams",
        label="Default diagram type", help="Initial type on a fresh designer load.",
        allowed=ALL_DIAGRAM_TYPES, scope="public",
    ),
    "diagrams.type_labels": _s(
        "diagrams.type_labels", type="json", default=DEFAULT_TYPE_LABELS, group="diagrams",
        label="Type labels", help="Display labels keyed by diagram type.", scope="public",
    ),
    "toolbox.overrides": _s(
        "toolbox.overrides", type="json", default={}, group="diagrams",
        label="Toolbox overrides",
        help='Map of "type.shape" → {enabled, default_width, default_height}. Empty = code defaults.',
    ),
    # G. Canvas (public)
    "canvas.grid": _s(
        "canvas.grid", type="integer", default=20, group="canvas",
        label="Grid size", help="Snap grid in world units.", min=5, max=80, scope="public",
    ),
    "canvas.spawn_step_x": _s(
        "canvas.spawn_step_x", type="integer", default=40, group="canvas",
        label="Spawn step X", help="Collision nudge when dropping shapes.", min=10, max=200, scope="public",
    ),
    "canvas.spawn_step_y": _s(
        "canvas.spawn_step_y", type="integer", default=20, group="canvas",
        label="Spawn step Y", help="Collision nudge when dropping shapes.", min=10, max=200, scope="public",
    ),
    "canvas.zoom_min": _s(
        "canvas.zoom_min", type="number", default=0.25, group="canvas",
        label="Min zoom", help="Minimum canvas scale.", min=0.05, max=1, scope="public",
    ),
    "canvas.zoom_max": _s(
        "canvas.zoom_max", type="number", default=2.5, group="canvas",
        label="Max zoom", help="Maximum canvas scale.", min=1, max=8, scope="public",
    ),
    "canvas.zoom_step": _s(
        "canvas.zoom_step", type="number", default=0.1, group="canvas",
        label="Zoom step", help="Approximate zoom step factor (UI hint).", min=0.05, max=0.5, scope="public",
    ),
    "canvas.undo_depth": _s(
        "canvas.undo_depth", type="integer", default=48, group="canvas",
        label="Undo depth", help="Max undo history entries.", min=5, max=200, scope="public",
    ),
    "sequence.start_y": _s(
        "sequence.start_y", type="number", default=88, group="canvas",
        label="Sequence start Y", help="First message Y for sequence diagrams.", min=40, max=300, scope="public",
    ),
    "sequence.step": _s(
        "sequence.step", type="number", default=52, group="canvas",
        label="Sequence step", help="Vertical spacing between sequence messages.", min=24, max=120, scope="public",
    ),
    "sequence.lifeline_padding": _s(
        "sequence.lifeline_padding", type="number", default=100, group="canvas",
        label="Lifeline padding", help="Extra height below last message (server+client).", min=40, max=240, scope="public",
    ),
    "canvas.base_font": _s(
        "canvas.base_font", type="number", default=9.5, group="canvas",
        label="Base font size", help="Default shape label font size.", min=7, max=16, scope="public",
    ),
    "theme.accent": _s(
        "theme.accent", type="string", default="#2563eb", group="canvas",
        label="Accent color", help="Primary accent CSS color.", scope="public",
    ),
    "theme.canvas_bg": _s(
        "theme.canvas_bg", type="string", default="#fafbfd", group="canvas",
        label="Canvas background", help="Designer canvas background color.", scope="public",
    ),
    # H. App / UX
    "ux.welcome_tour_enabled": _s(
        "ux.welcome_tour_enabled", type="boolean", default=True, group="app",
        label="Welcome tour enabled", help="Show drill-down welcome modal (localStorage still respected).", scope="public",
    ),
    "ux.welcome_message": _s(
        "ux.welcome_message", type="string", default="", group="app",
        label="Welcome message", help="Optional banner text (empty = none).", scope="public",
    ),
    "ux.confirm_prompts": _s(
        "ux.confirm_prompts", type="boolean", default=True, group="app",
        label="Confirm prompts", help="Confirm before destructive canvas actions.", scope="public",
    ),
    "ux.leave_warning": _s(
        "ux.leave_warning", type="boolean", default=True, group="app",
        label="Leave warning", help="Warn on beforeunload when diagram is dirty.", scope="public",
    ),
    "export.svg_enabled": _s(
        "export.svg_enabled", type="boolean", default=True, group="app",
        label="SVG export", help="Show SVG export button.", scope="public",
    ),
    "export.json_enabled": _s(
        "export.json_enabled", type="boolean", default=True, group="app",
        label="JSON export", help="Show JSON export button.", scope="public",
    ),
    "projects.list_limit": _s(
        "projects.list_limit", type="integer", default=100, group="app",
        label="Projects list limit", help="Default/max projects returned by list API.", min=1, max=500,
    ),
    "projects.retention_days": _s(
        "projects.retention_days", type="integer", default=0, group="app",
        label="Project retention days", help="0 = keep forever (no purge job unless > 0).", min=0, max=3650,
    ),
    "app.log_level": _s(
        "app.log_level", type="string", default="INFO", group="app",
        label="Log level", help="Application log level.",
        allowed=["DEBUG", "INFO", "WARNING", "ERROR"],
    ),
    "app.rate_limit_per_min": _s(
        "app.rate_limit_per_min", type="integer", default=0, group="app",
        label="Rate limit / min", help="0 = off. Soft limit for AI endpoints per client IP.", min=0, max=600,
    ),
}

GROUP_META = {
    "ai_models": {"label": "AI Models", "order": 1},
    "generation": {"label": "Generation Parameters", "order": 2},
    "pipeline": {"label": "Pipeline", "order": 3},
    "prompts": {"label": "Agent Prompts", "order": 4},
    "limits": {"label": "Input & Safety", "order": 5},
    "diagrams": {"label": "Diagram Types & Toolbox", "order": 6},
    "canvas": {"label": "Canvas Defaults", "order": 7},
    "app": {"label": "App / Projects / UX", "order": 8},
}

# Prompt keys → code default loaders (lazy import in service)
PROMPT_KEYS = [
    "analyst.system",
    "generator.system",
    "planner.system",
    "qc.base.preamble",
    "qc.base.response_format",
    "qc.revision",
    *[f"generator.guidance.{t}" for t in ALL_DIAGRAM_TYPES],
    *[f"qc.type.{t}" for t in ALL_DIAGRAM_TYPES],
]
