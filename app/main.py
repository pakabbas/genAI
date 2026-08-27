from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.config import get_settings
from app.prompts import CONTENT_TYPE_LABELS
from app.services.gemini import generate_html

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="GenAI Creator Studio",
    description="Create websites, documents, and diagrams with Gemini",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=8000)
    content_type: str = Field(default="website")


class GenerateResponse(BaseModel):
    html: str
    content_type: str
    content_type_label: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        context={"content_types": CONTENT_TYPE_LABELS},
    )


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "model": str(settings["gemini_model"]),
        "api_key_configured": bool(settings["gemini_api_key"]),
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    if request.content_type not in CONTENT_TYPE_LABELS:
        raise HTTPException(status_code=400, detail="Invalid content type.")

    try:
        html = generate_html(request.content_type, request.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Generation failed: {exc}",
        ) from exc

    return GenerateResponse(
        html=html,
        content_type=request.content_type,
        content_type_label=CONTENT_TYPE_LABELS[request.content_type],
    )
