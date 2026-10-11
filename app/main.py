from pathlib import Path
from collections import defaultdict
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.db.connection import check_connection
from app.prompts.diagrams import effective_toolbox, type_label, type_labels
from app.routers.config import router as config_router
from app.schemas.diagram import (
    DiagramDocument,
    DiagramType,
    GenerateDiagramRequest,
    ToolboxResponse,
)
from app.schemas.generation import (
    GenerateDiagramResponse,
    RequirementsChatRequest,
    RequirementsChatResponse,
)
from app.schemas.project import (
    CanvasExportV1,
    ProjectCreate,
    ProjectDetail,
    ProjectSummary,
    ProjectTransferRequest,
    ProjectTransferResponse,
    ProjectUpdate,
)
from app.services.diagram_pipeline import generate_diagram_with_qc
from app.services.prompt_guard import PromptRejectedError
from app.services.requirements_analyst import run_requirements_turn
from app.services import project_repository as projects
from app.services import settings_service as cfg
from app.version import APP_VERSION

BASE_DIR = Path(__file__).resolve().parent.parent
_settings = get_settings()
_root_path = str(_settings["app_root_path"])

app = FastAPI(
    title="GenAI Diagram Studio",
    description="AI-powered diagram designer with project storage and canvas export API",
    version=APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
app.include_router(config_router)

_rate_buckets: dict[str, list[float]] = defaultdict(list)


@app.on_event("startup")
async def _startup() -> None:
    cfg.ensure_schema()


def _template_context(extra: dict | None = None) -> dict:
    context = {"root_path": _root_path, "app_version": APP_VERSION}
    if extra:
        context.update(extra)
    return context


def _db_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Database is not configured or unavailable. Set DB_* variables in .env.",
    )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(request: Request) -> None:
    limit = int(cfg.get_value("app.rate_limit_per_min") or 0)
    if limit <= 0:
        return
    ip = _client_ip(request)
    now = time.time()
    window = _rate_buckets[ip]
    _rate_buckets[ip] = [t for t in window if now - t < 60]
    if len(_rate_buckets[ip]) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    _rate_buckets[ip].append(now)


def _validate_chat_limits(body: RequirementsChatRequest) -> None:
    max_chars = int(cfg.get_value("limits.chat_message_chars"))
    max_msgs = int(cfg.get_value("limits.chat_max_messages"))
    if len(body.messages) > max_msgs:
        raise HTTPException(
            status_code=400,
            detail=f"Too many messages (max {max_msgs}).",
        )
    for msg in body.messages:
        if len(msg.content or "") > max_chars:
            raise HTTPException(
                status_code=400,
                detail=f"Message exceeds {max_chars} characters.",
            )


def _validate_generate_limits(body: GenerateDiagramRequest) -> None:
    max_prompt = int(cfg.get_value("limits.generate_prompt_chars"))
    max_orig = int(cfg.get_value("limits.original_prompt_chars"))
    if len(body.prompt or "") > max_prompt:
        raise HTTPException(status_code=400, detail=f"Prompt exceeds {max_prompt} characters.")
    if body.original_prompt and len(body.original_prompt) > max_orig:
        raise HTTPException(
            status_code=400,
            detail=f"Original prompt exceeds {max_orig} characters.",
        )
    enabled = cfg.get_value("diagrams.enabled_types") or []
    if enabled and body.diagram_type not in enabled:
        raise HTTPException(status_code=400, detail=f"Diagram type '{body.diagram_type}' is disabled.")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(BASE_DIR / "static/favicon.svg", media_type="image/svg+xml")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        context=_template_context({"diagram_types": type_labels()}),
    )


@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "config.html",
        context=_template_context(),
    )


@app.get("/demo", response_class=HTMLResponse)
async def api_demo_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "api-demo.html",
        context=_template_context(),
    )


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "status": "ok",
        "version": APP_VERSION,
        "model": str(cfg.resolve_model("generator")),
        "api_key_configured": bool(settings["gemini_api_key"]),
        "db_configured": bool(settings["db_password"]),
        "db_connected": check_connection(),
    }


@app.get("/api/toolbox/{diagram_type}", response_model=ToolboxResponse)
async def toolbox(diagram_type: DiagramType) -> ToolboxResponse:
    enabled = cfg.get_value("diagrams.enabled_types") or []
    if enabled and diagram_type not in enabled:
        raise HTTPException(status_code=404, detail="Diagram type disabled.")
    items = effective_toolbox(diagram_type)
    if not items:
        raise HTTPException(status_code=404, detail="Unknown diagram type.")
    return ToolboxResponse(
        diagram_type=diagram_type,
        label=type_label(diagram_type),
        items=items,
    )


@app.post("/api/requirements-chat", response_model=RequirementsChatResponse)
async def requirements_chat_endpoint(
    request: Request,
    body: RequirementsChatRequest,
) -> RequirementsChatResponse:
    _check_rate_limit(request)
    _validate_chat_limits(body)
    try:
        return run_requirements_turn(
            body.diagram_type,
            body.messages,
            force_ready=body.force_ready,
        )
    except PromptRejectedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Requirements chat failed: {exc}",
        ) from exc


@app.post("/api/generate-diagram", response_model=GenerateDiagramResponse)
async def generate_diagram_endpoint(
    request: Request,
    body: GenerateDiagramRequest,
) -> GenerateDiagramResponse:
    _check_rate_limit(request)
    _validate_generate_limits(body)
    try:
        result = generate_diagram_with_qc(
            body.diagram_type,
            body.prompt,
            body.existing,
            prompt_enhanced=body.prompt_enhanced,
            original_prompt=body.original_prompt,
            edit_mode=body.edit_mode,
        )
    except PromptRejectedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        msg = str(exc)
        if "only creates technical diagrams" in msg:
            raise HTTPException(status_code=400, detail=msg) from exc
        raise HTTPException(status_code=503, detail=msg) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Generation failed: {exc}",
        ) from exc

    return result


@app.post("/api/validate-diagram")
async def validate_diagram(diagram: DiagramDocument) -> dict[str, str | int]:
    return {
        "status": "ok",
        "node_count": len(diagram.nodes),
        "edge_count": len(diagram.edges),
        "title": diagram.title,
    }


@app.get("/api/projects", response_model=list[ProjectSummary])
async def list_projects(limit: int | None = None) -> list[ProjectSummary]:
    if not check_connection():
        raise _db_unavailable()
    default_limit = int(cfg.get_value("projects.list_limit"))
    use_limit = min(limit if limit is not None else default_limit, 500)
    return projects.list_projects(limit=use_limit)


@app.post("/api/projects", response_model=ProjectDetail, status_code=201)
async def create_project(body: ProjectCreate) -> ProjectDetail:
    if not check_connection():
        raise _db_unavailable()
    return projects.create_project(body)


@app.get("/api/projects/{project_id}", response_model=ProjectDetail)
async def get_project(project_id: str) -> ProjectDetail:
    if not check_connection():
        raise _db_unavailable()
    project = projects.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@app.put("/api/projects/{project_id}", response_model=ProjectDetail)
async def update_project(project_id: str, body: ProjectUpdate) -> ProjectDetail:
    if not check_connection():
        raise _db_unavailable()
    project = projects.update_project(project_id, body)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str) -> dict[str, str]:
    if not check_connection():
        raise _db_unavailable()
    if not projects.delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"status": "deleted", "id": project_id}


@app.get("/api/projects/{project_id}/export", response_model=CanvasExportV1)
async def export_project_canvas(project_id: str) -> CanvasExportV1:
    if not check_connection():
        raise _db_unavailable()
    project = projects.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return projects.build_canvas_export(project)


@app.get("/api/canvas/external/{external_project_id}", response_model=CanvasExportV1)
async def export_canvas_by_external_id(external_project_id: str) -> CanvasExportV1:
    if not check_connection():
        raise _db_unavailable()
    project = projects.get_project_by_external(external_project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail="No diagram linked to this external project id.",
        )
    return projects.build_canvas_export(project)


@app.post("/api/projects/{project_id}/transfer", response_model=ProjectTransferResponse)
async def transfer_project(
    project_id: str,
    body: ProjectTransferRequest,
) -> ProjectTransferResponse:
    if not check_connection():
        raise _db_unavailable()
    if not body.target_project_id and not body.target_external_project_id:
        raise HTTPException(
            status_code=400,
            detail="Provide target_project_id and/or target_external_project_id.",
        )

    source = projects.get_project(project_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source project not found.")

    export = projects.build_canvas_export(source)
    target_id: str | None = None
    target_external = body.target_external_project_id

    if body.target_project_id:
        target, export = projects.transfer_to_project(
            source,
            body.target_project_id,
            replace=body.replace,
        )
        if not target:
            raise HTTPException(status_code=404, detail="Target project not found.")
        target_id = target.id

    if body.target_external_project_id:
        target, export = projects.transfer_to_external(
            source,
            body.target_external_project_id,
            replace=body.replace,
        )
        if target:
            target_id = target.id

    return ProjectTransferResponse(
        status="transferred",
        source_project_id=project_id,
        target_project_id=target_id,
        target_external_project_id=target_external,
        canvas=export,
    )
