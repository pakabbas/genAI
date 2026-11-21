"""Fail-safe generation usage logs for the admin/config panel.

Logging must never raise into the generation path. If MySQL is down or insert
fails, generation continues as usual.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from app.db.connection import check_connection, get_connection
from app.services import gemini_key as gemini_key_svc

logger = logging.getLogger(__name__)

_SCHEMA_RETRY_SECONDS = 60.0
_schema_ready = False
_schema_failed_at = 0.0

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS genai_generation_logs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  diagram_type VARCHAR(32) NOT NULL DEFAULT '',
  edit_mode TINYINT(1) NOT NULL DEFAULT 0,
  status VARCHAR(16) NOT NULL DEFAULT 'ok',
  error_message VARCHAR(512) NULL,
  api_key_last4 VARCHAR(8) NULL,
  models_used VARCHAR(512) NULL,
  call_count INT NOT NULL DEFAULT 0,
  prompt_tokens INT NULL,
  thoughts_tokens INT NULL,
  output_tokens INT NULL,
  total_tokens INT NULL,
  duration_ms INT NULL,
  calls_json JSON NULL,
  INDEX idx_genai_gen_logs_created (created_at),
  INDEX idx_genai_gen_logs_key (api_key_last4),
  INDEX idx_genai_gen_logs_type (diagram_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


def ensure_schema() -> bool:
    """Create the usage log table if missing. Returns True when ready."""
    global _schema_ready, _schema_failed_at
    if _schema_ready:
        return True
    if _schema_failed_at and (time.time() - _schema_failed_at) < _SCHEMA_RETRY_SECONDS:
        return False
    if not check_connection():
        return False
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
        _schema_ready = True
        _schema_failed_at = 0.0
        return True
    except Exception as exc:
        _schema_failed_at = time.time()
        logger.warning(
            "genai_generation_logs schema ensure failed (retry in %ss): %s",
            int(_SCHEMA_RETRY_SECONDS),
            exc,
        )
        return False


def _sum_int(calls: list[dict[str, Any]], key: str) -> int | None:
    total = 0
    seen = False
    for call in calls:
        val = call.get(key)
        if val is None:
            continue
        try:
            total += int(val)
            seen = True
        except (TypeError, ValueError):
            continue
    return total if seen else None


def _models_summary(calls: list[dict[str, Any]]) -> str:
    seen: list[str] = []
    for call in calls:
        model = str(call.get("model") or "").strip()
        role = str(call.get("role") or "").strip()
        label = f"{role}:{model}" if role and model else (model or role)
        if label and label not in seen:
            seen.append(label)
    return ", ".join(seen)[:500]


def record_generation(
    *,
    diagram_type: str,
    edit_mode: bool = False,
    status: str = "ok",
    error_message: str | None = None,
    calls: list[dict[str, Any]] | None = None,
    duration_seconds: float | None = None,
) -> None:
    """Persist one generation usage row. Never raises."""
    try:
        if not ensure_schema():
            return
        call_list = list(calls or [])
        key_info = gemini_key_svc.mask_key()
        prompt_tokens = _sum_int(call_list, "prompt_tokens")
        thoughts_tokens = _sum_int(call_list, "thoughts_tokens")
        output_tokens = _sum_int(call_list, "output_tokens")
        total_tokens = _sum_int(call_list, "total_tokens")
        if total_tokens is None:
            parts = [prompt_tokens, thoughts_tokens, output_tokens]
            if any(p is not None for p in parts):
                total_tokens = sum(p or 0 for p in parts)
        duration_ms = None
        if duration_seconds is not None:
            try:
                duration_ms = int(max(0.0, float(duration_seconds)) * 1000)
            except (TypeError, ValueError):
                duration_ms = None
        err = (error_message or "").strip()[:512] or None
        payload = json.dumps(call_list, default=str) if call_list else None
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO genai_generation_logs
                      (diagram_type, edit_mode, status, error_message, api_key_last4,
                       models_used, call_count, prompt_tokens, thoughts_tokens,
                       output_tokens, total_tokens, duration_ms, calls_json)
                    VALUES
                      (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(diagram_type or "")[:32],
                        1 if edit_mode else 0,
                        str(status or "ok")[:16],
                        err,
                        key_info.get("last4"),
                        _models_summary(call_list) or None,
                        len(call_list),
                        prompt_tokens,
                        thoughts_tokens,
                        output_tokens,
                        total_tokens,
                        duration_ms,
                        payload,
                    ),
                )
    except Exception as exc:
        logger.warning("generation usage log failed (ignored): %s", exc)


def list_logs(*, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """Return recent usage logs for the admin panel."""
    limit = max(1, min(int(limit or 100), 500))
    offset = max(0, int(offset or 0))
    if not ensure_schema():
        return {"items": [], "total": 0, "db_connected": False}
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS n FROM genai_generation_logs")
                total_row = cur.fetchone() or {}
                total = int(total_row.get("n") or 0)
                cur.execute(
                    """
                    SELECT id, created_at, diagram_type, edit_mode, status, error_message,
                           api_key_last4, models_used, call_count, prompt_tokens,
                           thoughts_tokens, output_tokens, total_tokens, duration_ms
                    FROM genai_generation_logs
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall() or []
        items = []
        for row in rows:
            created = row.get("created_at")
            if isinstance(created, datetime):
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                created_iso = created.isoformat()
            else:
                created_iso = str(created) if created else None
            items.append(
                {
                    "id": row.get("id"),
                    "created_at": created_iso,
                    "diagram_type": row.get("diagram_type") or "",
                    "edit_mode": bool(row.get("edit_mode")),
                    "status": row.get("status") or "ok",
                    "error_message": row.get("error_message"),
                    "api_key_last4": row.get("api_key_last4"),
                    "models_used": row.get("models_used"),
                    "call_count": int(row.get("call_count") or 0),
                    "prompt_tokens": row.get("prompt_tokens"),
                    "thoughts_tokens": row.get("thoughts_tokens"),
                    "output_tokens": row.get("output_tokens"),
                    "total_tokens": row.get("total_tokens"),
                    "duration_ms": row.get("duration_ms"),
                }
            )
        return {"items": items, "total": total, "db_connected": True}
    except Exception as exc:
        logger.warning("list generation usage logs failed: %s", exc)
        return {"items": [], "total": 0, "db_connected": False, "error": str(exc)}
