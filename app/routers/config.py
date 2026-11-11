"""Configurations API — runtime settings + versioned prompts."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services import gemini_key as gemini_key_svc
from app.services import settings_service as cfg

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigResetBody(BaseModel):
    keys: list[str] | None = None
    group: str | None = None


class PromptSaveBody(BaseModel):
    body: str


class PromptActivateBody(BaseModel):
    version: int


class GeminiKeyBody(BaseModel):
    api_key: str = Field(..., min_length=1)


@router.get("/gemini-key")
async def get_gemini_key() -> dict:
    """Masked view of the configured Gemini key. Never returns the full secret."""
    return gemini_key_svc.mask_key()


@router.post("/gemini-key")
async def change_gemini_key(body: GeminiKeyBody) -> dict:
    """Test the new key with generateContent, then persist it only if the test passes."""
    key = (body.api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Enter a Gemini API key.")
    ok, message, model = gemini_key_svc.test_gemini_api_key(key)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    try:
        masked = gemini_key_svc.persist_verified_key(key)
    except OSError:
        raise HTTPException(
            status_code=503,
            detail="The key tested successfully but could not be saved to .env.",
        )
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="The key tested successfully but could not be saved.",
        )
    return {**masked, "ok": True, "model": model}


@router.get("")
async def get_config() -> dict:
    cfg.ensure_schema()
    return cfg.get_grouped()


@router.put("")
async def put_config(body: dict) -> dict:
    try:
        updates = body.get("updates") if isinstance(body.get("updates"), dict) else body
        if not isinstance(updates, dict):
            raise ValueError("Body must be a JSON object of setting keys.")
        # Strip wrapper keys if someone posts both
        updates = {k: v for k, v in updates.items() if k != "updates"}
        return cfg.set_values(updates)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid settings update: {exc}") from exc


@router.post("/reset")
async def reset_config(body: ConfigResetBody) -> dict:
    try:
        return cfg.reset_keys(keys=body.keys, group=body.group)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Reset failed: {exc}") from exc


@router.get("/public")
async def public_config() -> dict:
    cfg.ensure_schema()
    return cfg.get_public()


@router.get("/prompts")
async def list_prompts() -> dict:
    cfg.ensure_schema()
    return {"prompts": cfg.list_prompts()}


@router.get("/prompts/{prompt_key:path}")
async def get_prompt(prompt_key: str, version: int | None = None) -> dict:
    try:
        if version is not None:
            body = cfg.get_prompt_version_body(prompt_key, version)
            base = cfg.get_prompt(prompt_key)
            return {
                **base,
                "body": body,
                "preview_version": version,
                "is_preview": True,
            }
        return cfg.get_prompt(prompt_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/prompts/{prompt_key:path}")
async def put_prompt(prompt_key: str, body: PromptSaveBody) -> dict:
    try:
        return cfg.save_prompt(prompt_key, body.body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/prompts/{prompt_key:path}/reset")
async def reset_prompt(prompt_key: str) -> dict:
    try:
        return cfg.reset_prompt(prompt_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/prompts/{prompt_key:path}/activate")
async def activate_prompt(prompt_key: str, body: PromptActivateBody) -> dict:
    try:
        return cfg.activate_prompt_version(prompt_key, body.version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
