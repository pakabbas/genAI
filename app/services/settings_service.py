"""Runtime settings store: DB → env → code default, with short TTL cache."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.config import get_settings as get_env_settings
from app.db.connection import check_connection, get_connection
from app.services.settings_registry import (
    GROUP_META,
    PROMPT_KEYS,
    SETTINGS_REGISTRY,
)

logger = logging.getLogger(__name__)

_CACHE_TTL = 30.0
_SCHEMA_RETRY_SECONDS = 60.0
_cache: dict[str, Any] | None = None
_cache_at = 0.0
_schema_ready = False
_schema_failed_at = 0.0
_prompt_body_cache: dict[str, tuple[float, str]] = {}
_prompt_meta_cache: dict[str, tuple[float, dict[str, Any]]] = {}


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS genai_settings (
  `key` VARCHAR(128) NOT NULL PRIMARY KEY,
  `value` JSON NOT NULL,
  `type` VARCHAR(32) NOT NULL DEFAULT 'string',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS genai_prompts (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  prompt_key VARCHAR(128) NOT NULL,
  body MEDIUMTEXT NOT NULL,
  version INT NOT NULL DEFAULT 1,
  is_active TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_genai_prompts_key_version (prompt_key, version),
  INDEX idx_genai_prompts_active (prompt_key, is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


def ensure_schema() -> None:
    global _schema_ready, _schema_failed_at
    if _schema_ready:
        return
    if _schema_failed_at and (time.time() - _schema_failed_at) < _SCHEMA_RETRY_SECONDS:
        return
    if not check_connection():
        return
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for stmt in SCHEMA_SQL.strip().split(";"):
                    sql = stmt.strip()
                    if sql:
                        cur.execute(sql)
        _schema_ready = True
        _schema_failed_at = 0.0
    except Exception as exc:
        _schema_failed_at = time.time()
        logger.warning("genai settings schema ensure failed (retry in %ss): %s", int(_SCHEMA_RETRY_SECONDS), exc)


def invalidate_cache() -> None:
    global _cache, _cache_at, _prompt_body_cache, _prompt_meta_cache
    _cache = None
    _cache_at = 0.0
    _prompt_body_cache = {}
    _prompt_meta_cache = {}


def _load_db_map() -> dict[str, Any]:
    ensure_schema()
    if not check_connection():
        return {}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT `key`, `value` FROM genai_settings")
                rows = cur.fetchall() or []
        out: dict[str, Any] = {}
        for row in rows:
            key = row["key"]
            raw = row["value"]
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            if isinstance(raw, str):
                try:
                    out[key] = json.loads(raw)
                except json.JSONDecodeError:
                    out[key] = raw
            else:
                out[key] = raw
        return out
    except Exception as exc:
        logger.warning("load genai_settings failed: %s", exc)
        return {}


def _db_map_cached() -> dict[str, Any]:
    global _cache, _cache_at
    now = time.monotonic()
    if _cache is not None and (now - _cache_at) < _CACHE_TTL:
        return _cache
    _cache = _load_db_map()
    _cache_at = now
    return _cache


def _coerce(meta: dict[str, Any], value: Any) -> Any:
    t = meta["type"]
    key = meta["key"]
    if value is None:
        raise ValueError(f"{key} cannot be null.")
    try:
        if t == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                token = value.strip().lower()
                if token in {"1", "true", "yes", "on"}:
                    return True
                if token in {"0", "false", "no", "off"}:
                    return False
                raise ValueError(
                    f"{key} must be true/false/1/0/yes/no (got {value!r})."
                )
            if isinstance(value, int) and value in (0, 1):
                return bool(value)
            if isinstance(value, float) and value in (0.0, 1.0):
                return bool(int(value))
            raise ValueError(f"{key} must be a boolean.")
        if t == "integer":
            if isinstance(value, bool):
                raise ValueError(f"{key} must be an integer.")
            return int(value)
        if t == "number":
            if isinstance(value, bool):
                raise ValueError(f"{key} must be a number.")
            return float(value)
        if t == "json":
            if isinstance(value, str):
                return json.loads(value)
            if isinstance(value, (dict, list)):
                return value
            raise ValueError(f"{key} must be a JSON object or array.")
        return str(value)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(key):
            raise
        raise ValueError(f"{key} has an invalid {t} value.") from exc


def _validate(meta: dict[str, Any], value: Any) -> Any:
    if meta.get("readonly"):
        raise ValueError(f"{meta['key']} is read-only.")
    coerced = _coerce(meta, value)
    t = meta["type"]
    key = meta["key"]
    if t in {"integer", "number"}:
        if meta.get("min") is not None and coerced < meta["min"]:
            raise ValueError(f"{key} must be ≥ {meta['min']}.")
        if meta.get("max") is not None and coerced > meta["max"]:
            raise ValueError(f"{key} must be ≤ {meta['max']}.")
    if meta.get("allowed") is not None and coerced not in meta["allowed"]:
        raise ValueError(f"{key} must be one of {meta['allowed']}.")

    # Domain-specific validation
    if key == "guard.patterns":
        from app.services.prompt_guard import validate_guard_patterns

        coerced = validate_guard_patterns(coerced)
    elif key in {"guard.allowlist", "guard.short_creative_pattern"}:
        from app.services.prompt_guard import validate_guard_regex

        coerced = validate_guard_regex(key, coerced)
    return coerced


def get_value(key: str) -> Any:
    """Resolve: DB → env (for model keys) → code default."""
    meta = SETTINGS_REGISTRY.get(key)
    if not meta:
        raise KeyError(f"Unknown setting: {key}")

    db_map = _db_map_cached()
    if key in db_map:
        try:
            return _coerce(meta, db_map[key])
        except Exception:
            pass

    # Per-agent model falls back to GEMINI_MODEL env when unset in DB
    if key.startswith("ai.model.") and key != "ai.model.fallback":
        env_model = str(get_env_settings().get("gemini_model") or "").strip()
        if env_model:
            return env_model

    return meta["default"]


def get_many(keys: list[str] | None = None) -> dict[str, Any]:
    keys = keys or list(SETTINGS_REGISTRY.keys())
    return {k: get_value(k) for k in keys if k in SETTINGS_REGISTRY}


def get_public() -> dict[str, Any]:
    return {
        k: get_value(k)
        for k, meta in SETTINGS_REGISTRY.items()
        if meta.get("scope") == "public"
    }


def set_values(updates: dict[str, Any]) -> dict[str, Any]:
    if not updates:
        return get_grouped()
    ensure_schema()
    if not check_connection():
        raise RuntimeError("Database unavailable — cannot save settings.")

    validated: dict[str, Any] = {}
    for key, value in updates.items():
        meta = SETTINGS_REGISTRY.get(key)
        if not meta:
            raise KeyError(f"Unknown setting: {key}")
        validated[key] = _validate(meta, value)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                for key, value in validated.items():
                    meta = SETTINGS_REGISTRY[key]
                    # Store JSON text — works on MySQL and MariaDB (avoid CAST(... AS JSON)).
                    cur.execute(
                        """
                        INSERT INTO genai_settings (`key`, `value`, `type`)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                          `value` = VALUES(`value`),
                          `type` = VALUES(`type`)
                        """,
                        (key, json.dumps(value), meta["type"]),
                    )
    except Exception as exc:
        logger.exception("settings write failed")
        raise RuntimeError(f"Database write failed: {exc}") from exc
    invalidate_cache()
    return get_grouped()


def reset_keys(keys: list[str] | None = None, group: str | None = None) -> dict[str, Any]:
    ensure_schema()
    if not check_connection():
        raise RuntimeError("Database unavailable — cannot reset settings.")

    if group:
        keys = [k for k, m in SETTINGS_REGISTRY.items() if m["group"] == group and not m.get("readonly")]
    keys = keys or []
    unknown = [k for k in keys if k not in SETTINGS_REGISTRY]
    if unknown:
        raise KeyError(f"Unknown setting(s): {', '.join(unknown)}")

    if keys:
        with get_connection() as conn:
            with conn.cursor() as cur:
                placeholders = ",".join(["%s"] * len(keys))
                cur.execute(f"DELETE FROM genai_settings WHERE `key` IN ({placeholders})", keys)
    invalidate_cache()
    return get_grouped()


def get_grouped() -> dict[str, Any]:
    env = get_env_settings()
    groups: dict[str, Any] = {}
    for key, meta in SETTINGS_REGISTRY.items():
        g = meta["group"]
        if g not in groups:
            gm = GROUP_META.get(g, {"label": g, "order": 99})
            groups[g] = {
                "id": g,
                "label": gm["label"],
                "order": gm["order"],
                "settings": [],
            }
        current = get_value(key)
        groups[g]["settings"].append(
            {
                "key": key,
                "type": meta["type"],
                "label": meta["label"],
                "help": meta["help"],
                "scope": meta["scope"],
                "readonly": bool(meta.get("readonly")),
                "default": meta["default"],
                "value": current,
                "min": meta.get("min"),
                "max": meta.get("max"),
                "allowed": meta.get("allowed"),
            }
        )

    status = {
        "version": _app_version(),
        "api_key_status": "set" if env.get("gemini_api_key") else "not set",
        "db_connected": check_connection(),
        "env_model": env.get("gemini_model"),
        "models": {
            "analyst": get_value("ai.model.analyst"),
            "planner": get_value("ai.model.planner"),
            "generator": get_value("ai.model.generator"),
            "qc": get_value("ai.model.qc"),
            "fallback": get_value("ai.model.fallback"),
        },
        "provider": get_value("ai.provider"),
    }
    ordered = sorted(groups.values(), key=lambda g: g["order"])
    return {"groups": ordered, "status": status, "prompt_keys": PROMPT_KEYS}


def _app_version() -> str:
    from app.version import APP_VERSION

    return APP_VERSION


# --- Prompts -----------------------------------------------------------------


def _code_prompt_default(prompt_key: str) -> str:
    from app.prompts import diagrams as diagrams_mod
    from app.prompts import process_plan, requirements
    from app.prompts.qc import base as qc_base
    from app.prompts.qc import (
        architecture,
        class_diagram,
        erd,
        flowchart,
        network,
        sequence,
        swim_lane,
        use_case,
    )
    from app.prompts.qc_audit import build_revision_prompt

    qc_types = {
        "use_case": use_case.QC_SYSTEM,
        "erd": erd.QC_SYSTEM,
        "swim_lane": swim_lane.QC_SYSTEM,
        "flowchart": flowchart.QC_SYSTEM,
        "sequence": sequence.QC_SYSTEM,
        "class_diagram": class_diagram.QC_SYSTEM,
        "network": network.QC_SYSTEM,
        "architecture": architecture.QC_SYSTEM,
    }

    if prompt_key == "analyst.system":
        return requirements.REQUIREMENTS_SYSTEM_INSTRUCTION
    if prompt_key == "generator.system":
        return diagrams_mod.DIAGRAM_SYSTEM_INSTRUCTION
    if prompt_key == "planner.system":
        return process_plan.PROCESS_PLAN_SYSTEM
    if prompt_key == "qc.base.preamble":
        return qc_base.QC_COMMON_PREAMBLE
    if prompt_key == "qc.base.response_format":
        return qc_base.QC_RESPONSE_FORMAT
    if prompt_key == "qc.revision":
        # Header only — issue list is injected immediately after (v2.6.9 order).
        return (
            "QC / COVERAGE REVISION REQUIRED — fix these blocking issues and return a COMPLETE diagram JSON:\n"
            "\n"
            "Do not omit activities, lanes, decisions, or branches that appear in the brief/inventory.\n"
            "Do not invent unrelated flows (refunds, retries, etc.) unless they were requested.\n"
        )
    if prompt_key.startswith("generator.guidance."):
        dtype = prompt_key.split(".", 2)[2]
        return diagrams_mod.DIAGRAM_TYPE_GUIDANCE.get(dtype, "")
    if prompt_key.startswith("qc.type."):
        dtype = prompt_key.split(".", 2)[2]
        return qc_types.get(dtype, use_case.QC_SYSTEM)
    raise KeyError(f"Unknown prompt key: {prompt_key}")


def get_prompt(prompt_key: str) -> dict[str, Any]:
    if prompt_key not in PROMPT_KEYS:
        raise KeyError(f"Unknown prompt key: {prompt_key}")
    now = time.monotonic()
    cached = _prompt_meta_cache.get(prompt_key)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1]

    default_body = _code_prompt_default(prompt_key)
    ensure_schema()
    versions: list[dict[str, Any]] = []
    active_body = default_body
    active_version = 0
    if check_connection() and _schema_ready:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, version, is_active, created_at, CHAR_LENGTH(body) AS chars
                        FROM genai_prompts
                        WHERE prompt_key = %s
                        ORDER BY version DESC
                        """,
                        (prompt_key,),
                    )
                    rows = cur.fetchall() or []
                    for row in rows:
                        versions.append(
                            {
                                "id": row["id"],
                                "version": row["version"],
                                "is_active": bool(row["is_active"]),
                                "created_at": str(row["created_at"]),
                                "chars": row["chars"],
                            }
                        )
                    cur.execute(
                        """
                        SELECT body, version FROM genai_prompts
                        WHERE prompt_key = %s AND is_active = 1
                        ORDER BY version DESC LIMIT 1
                        """,
                        (prompt_key,),
                    )
                    active = cur.fetchone()
                    if active:
                        active_body = active["body"]
                        active_version = int(active["version"])
        except Exception as exc:
            logger.warning("get_prompt failed: %s", exc)

    result = {
        "prompt_key": prompt_key,
        "body": active_body,
        "version": active_version,
        "is_default": active_version == 0,
        "default_body": default_body,
        "versions": versions,
    }
    _prompt_meta_cache[prompt_key] = (now, result)
    _prompt_body_cache[prompt_key] = (now, active_body)
    return result


def get_prompt_version_body(prompt_key: str, version: int) -> str:
    """Return body for a specific stored version, or code default when version=0."""
    if prompt_key not in PROMPT_KEYS:
        raise KeyError(f"Unknown prompt key: {prompt_key}")
    if version <= 0:
        return _code_prompt_default(prompt_key)
    ensure_schema()
    if not check_connection():
        raise RuntimeError("Database unavailable.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT body FROM genai_prompts WHERE prompt_key = %s AND version = %s",
                (prompt_key, version),
            )
            row = cur.fetchone()
            if not row:
                raise KeyError("Version not found.")
            return row["body"]


def list_prompts() -> list[dict[str, Any]]:
    out = []
    for key in PROMPT_KEYS:
        info = get_prompt(key)
        out.append(
            {
                "prompt_key": key,
                "version": info["version"],
                "is_default": info["is_default"],
                "chars": len(info["body"]),
            }
        )
    return out


def save_prompt(prompt_key: str, body: str) -> dict[str, Any]:
    if prompt_key not in PROMPT_KEYS:
        raise KeyError(f"Unknown prompt key: {prompt_key}")
    body = (body or "").strip()
    if len(body) < 20:
        raise ValueError("Prompt body is too short.")
    ensure_schema()
    if not check_connection():
        raise RuntimeError("Database unavailable — cannot save prompts.")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(version), 0) AS v FROM genai_prompts WHERE prompt_key = %s",
                    (prompt_key,),
                )
                next_v = int((cur.fetchone() or {}).get("v") or 0) + 1
                cur.execute(
                    "UPDATE genai_prompts SET is_active = 0 WHERE prompt_key = %s",
                    (prompt_key,),
                )
                cur.execute(
                    """
                    INSERT INTO genai_prompts (prompt_key, body, version, is_active)
                    VALUES (%s, %s, %s, 1)
                    """,
                    (prompt_key, body, next_v),
                )
    except Exception as exc:
        raise RuntimeError(f"Database write failed: {exc}") from exc
    invalidate_cache()
    return get_prompt(prompt_key)


def activate_prompt_version(prompt_key: str, version: int) -> dict[str, Any]:
    if prompt_key not in PROMPT_KEYS:
        raise KeyError(f"Unknown prompt key: {prompt_key}")
    ensure_schema()
    if not check_connection():
        raise RuntimeError("Database unavailable.")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM genai_prompts WHERE prompt_key = %s AND version = %s",
                (prompt_key, version),
            )
            if not cur.fetchone():
                raise KeyError("Version not found.")
            cur.execute(
                "UPDATE genai_prompts SET is_active = 0 WHERE prompt_key = %s",
                (prompt_key,),
            )
            cur.execute(
                "UPDATE genai_prompts SET is_active = 1 WHERE prompt_key = %s AND version = %s",
                (prompt_key, version),
            )
    invalidate_cache()
    return get_prompt(prompt_key)


def reset_prompt(prompt_key: str) -> dict[str, Any]:
    if prompt_key not in PROMPT_KEYS:
        raise KeyError(f"Unknown prompt key: {prompt_key}")
    ensure_schema()
    if check_connection():
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE genai_prompts SET is_active = 0 WHERE prompt_key = %s",
                    (prompt_key,),
                )
    invalidate_cache()
    return get_prompt(prompt_key)


def active_prompt_body(prompt_key: str) -> str:
    now = time.monotonic()
    cached = _prompt_body_cache.get(prompt_key)
    if cached and (now - cached[0]) < _CACHE_TTL:
        return cached[1]
    body = get_prompt(prompt_key)["body"]
    _prompt_body_cache[prompt_key] = (now, body)
    return body


# --- Helpers used by pipeline / toolbox --------------------------------------


def resolve_model(role: str) -> str:
    """role: analyst | planner | generator | qc"""
    key = f"ai.model.{role}"
    value = str(get_value(key) if key in SETTINGS_REGISTRY else "").strip()
    if value:
        return value
    return str(get_env_settings().get("gemini_model") or "gemini-3.1-pro-preview")


def fallback_model() -> str:
    return str(get_value("ai.model.fallback") or "").strip()
