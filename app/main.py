from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.prompts.diagrams import DIAGRAM_TYPE_LABELS, TOOLBOX
from app.schemas.diagram import (
    DiagramDocument,
    DiagramType,
    GenerateDiagramRequest,
    GenerateDiagramResponse,
    ToolboxResponse,
)
from app.services.diagram_generator import generate_diagram

BASE_DIR = Path(__file__).resolve().parent.parent
_settings = get_settings()
_root_path = str(_settings["app_root_path"])

app = FastAPI(
    title="GenAI Diagram Studio",
    description="AI-powered diagram designer — use case, ERD, swim lane, and flowcharts",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _template_context(extra: dict | None = None) -> dict:
    context = {"root_path": _root_path}
    if extra:
        context.update(extra)
    return context


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        context=_template_context({"diagram_types": DIAGRAM_TYPE_LABELS}),
    )


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "model": str(settings["gemini_model"]),
        "api_key_configured": bool(settings["gemini_api_key"]),
    }


@app.get("/api/toolbox/{diagram_type}", response_model=ToolboxResponse)
async def toolbox(diagram_type: DiagramType) -> ToolboxResponse:
    items = TOOLBOX.get(diagram_type)
    if not items:
        raise HTTPException(status_code=404, detail="Unknown diagram type.")
    return ToolboxResponse(
        diagram_type=diagram_type,
        label=DIAGRAM_TYPE_LABELS[diagram_type],
        items=items,
    )


@app.post("/api/generate-diagram", response_model=GenerateDiagramResponse)
async def generate_diagram_endpoint(
    request: GenerateDiagramRequest,
) -> GenerateDiagramResponse:
    try:
        diagram = generate_diagram(
            request.diagram_type,
            request.prompt,
            request.existing,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Generation failed: {exc}",
        ) from exc

    return GenerateDiagramResponse(
        diagram=diagram,
        diagram_type=request.diagram_type,
        diagram_type_label=DIAGRAM_TYPE_LABELS[request.diagram_type],
    )


@app.post("/api/validate-diagram")
async def validate_diagram(diagram: DiagramDocument) -> dict[str, str | int]:
    """Validate diagram JSON from the client (save/export round-trip)."""
    return {
        "status": "ok",
        "node_count": len(diagram.nodes),
        "edge_count": len(diagram.edges),
        "title": diagram.title,
    }
