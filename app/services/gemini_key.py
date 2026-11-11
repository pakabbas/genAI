"""Change the Gemini API key: mask, test with generateContent, persist to .env."""

from __future__ import annotations

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types

from app.config import get_settings
from app.services import settings_service as cfg

logger = logging.getLogger(__name__)

ENV_VAR = "GEMINI_API_KEY"
_KEY_RE = re.compile(r"(?:AIza[0-9A-Za-z_\-]{8,}|GEMINI_API_KEY\s*[=:]\s*\S+)", re.I)
_LINE_RE = re.compile(r"^(\s*(?:export\s+)?)GEMINI_API_KEY\s*=", re.I)


def project_root() -> Path:
    here = Path(__file__).resolve()
    root = here.parents[2]
    if (root / ".env").is_file():
        return root
    cwd = Path.cwd()
    if (cwd / ".env").is_file():
        return cwd
    return root


def env_file_path() -> Path:
    return project_root() / ".env"


def old_key_log_path() -> Path:
    home_log = Path.home() / "gemini_old_key.log"
    try:
        home_log.parent.mkdir(parents=True, exist_ok=True)
        # Prefer the service user's home, as documented.
        if home_log.exists() or os.access(home_log.parent, os.W_OK):
            return home_log
    except OSError:
        pass
    return project_root() / "gemini_old_key.log"


def current_key() -> str:
    return str(get_settings().get("gemini_api_key") or "").strip()


def mask_key(key: str | None = None) -> dict:
    """Public view of the key: configured flag + last 4, never the full secret."""
    value = current_key() if key is None else str(key or "").strip()
    if not value:
        return {"configured": False, "last4": None}
    last4 = value[-4:] if len(value) >= 8 else None
    return {"configured": True, "last4": last4}


def redact(text: str, extra: str = "") -> str:
    out = str(text or "")
    if extra:
        out = out.replace(extra, "[redacted]")
    return _KEY_RE.sub("[redacted]", out)


def _env_quote(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_.\-/]+", value):
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _google_error_message(exc: Exception, new_key: str) -> str:
    code = getattr(exc, "status_code", None)
    if code is None:
        code = getattr(exc, "code", None)
    resp = getattr(exc, "response", None) or getattr(exc, "_response", None)
    if code is None and resp is not None:
        code = getattr(resp, "status_code", None)
    msg = getattr(exc, "message", None) or str(exc)
    # Prefer structured details when present.
    details = getattr(exc, "details", None) or getattr(exc, "status", None)
    if details and not isinstance(details, (int, float)):
        extra = redact(str(details), new_key)
        body = redact(str(msg), new_key)
        if extra and extra not in body:
            body = f"{body} ({extra})"
    else:
        body = redact(str(msg), new_key)
    body = re.sub(r"\s+", " ", body).strip()
    if code and str(code) not in body:
        return f"{code}: {body}"
    return body or "Gemini rejected the key."


def test_gemini_api_key(api_key: str) -> tuple[bool, str, str]:
    """Run a short generateContent call. models.list is not sufficient.

    Returns (ok, message, model_used). On failure, message is the Google error.
    """
    key = (api_key or "").strip()
    if not key:
        return False, "Enter a Gemini API key.", ""

    primary = str(cfg.resolve_model("generator") or "").strip()
    fallback = str(cfg.fallback_model() or "").strip()
    models: list[str] = []
    for name in (primary, fallback):
        if name and name not in models:
            models.append(name)
    if not models:
        models.append(str(get_settings().get("gemini_model") or "gemini-3.1-pro-preview"))

    client = genai.Client(api_key=key)
    last_err = "Gemini rejected the key."
    last_model = models[0]
    for model_name in models:
        last_model = model_name
        try:
            # Short, cheap probe — must be generateContent, not models.list.
            client.models.generate_content(
                model=model_name,
                contents="Reply with the single word OK.",
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=16,
                    http_options=types.HttpOptions(timeout=25_000),
                ),
            )
            return True, "ok", model_name
        except TypeError:
            # Older SDK may not accept http_options on GenerateContentConfig.
            try:
                client.models.generate_content(
                    model=model_name,
                    contents="Reply with the single word OK.",
                    config=types.GenerateContentConfig(
                        temperature=0,
                        max_output_tokens=16,
                    ),
                )
                return True, "ok", model_name
            except Exception as exc:
                last_err = _google_error_message(exc, key)
                logger.warning("Gemini key test failed via %s: %s", model_name, redact(str(exc), key))
        except Exception as exc:
            last_err = _google_error_message(exc, key)
            logger.warning("Gemini key test failed via %s: %s", model_name, redact(str(exc), key))
    return False, last_err, last_model


def _append_old_key_log(old_key: str) -> None:
    path = old_key_log_path()
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    payload = old_key if old_key else "(none)"
    line = f"{stamp}\t{payload}\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _write_env_key(path: Path, value: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines(keepends=True)
    replaced = False
    out: list[str] = []
    for line in lines:
        if _LINE_RE.match(line) and not line.lstrip().startswith("#"):
            prefix = _LINE_RE.match(line).group(1) or ""
            ending = "\n" if line.endswith("\n") else ""
            out.append(f"{prefix}{ENV_VAR}={_env_quote(value)}{ending or chr(10)}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        if out and not str(out[-1]).endswith("\n"):
            out.append("\n")
        out.append(f"{ENV_VAR}={_env_quote(value)}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("".join(out))
        try:
            os.chmod(tmp_name, 0o600)
        except OSError:
            pass
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def persist_verified_key(new_key: str) -> dict:
    """Write the already-tested key to .env, archive the old key, reload in-process."""
    value = (new_key or "").strip()
    if not value:
        raise ValueError("Enter a Gemini API key.")
    old = current_key()
    _append_old_key_log(old)
    _write_env_key(env_file_path(), value)
    os.environ[ENV_VAR] = value
    # No cached Gemini client today; new Client() calls read get_settings() / os.environ.
    reload_gemini_runtime()
    return mask_key(value)


def reload_gemini_runtime() -> None:
    """Drop any in-process Gemini client state so the next call uses the new key."""
    try:
        from app.services import gemini_client

        if hasattr(gemini_client, "reset_client"):
            gemini_client.reset_client()
    except Exception:
        logger.warning("Could not reset in-process Gemini client; env is updated.")
