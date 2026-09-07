from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.db.connection import check_connection
from app.prompts.diagrams import DIAGRAM_TYPE_LABELS, TOOLBOX
from app.schemas.diagram import (
    DiagramDocument,
    DiagramType,
    GenerateDiagramRequest,
    GenerateDiagramResponse,
    ToolboxResponse,
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
from app.services.diagram_generator import generate_diagram
from app.services import project_repository as projects

BASE_DIR = Path(__file__).resolve().parent.parent
_settings = get_settings()
_root_path = str(_settings["app_root_path"])

app = FastAPI(
    title="GenAI Diagram Studio",
    description="AI-powered diagram designer with project storage and canvas export API",
    version="2.1.0",
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def _template_context(extra: dict | None = None) -> dict:
    context = {"root_path": _root_path}
    if extra:
        context.update(extra)
    return context


def _db_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Database is not configured or unavailable. Set DB_* variables in .env.",
    )


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
        "db_configured": bool(settings["db_password"]),
        "db_connected": check_connection(),
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
    return {
        "status": "ok",
        "node_count": len(diagram.nodes),
        "edge_count": len(diagram.edges),
        "title": diagram.title,
    }


# --- Projects (MySQL) ---


@app.get("/api/projects", response_model=list[ProjectSummary])
async def list_projects(limit: int = 100) -> list[ProjectSummary]:
    if not check_connection():
        raise _db_unavailable()
    return projects.list_projects(limit=min(limit, 500))


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
    """Export diagram JSON for a client-owned canvas (LeadPilot / external project)."""
    if not check_connection():
        raise _db_unavailable()
    project = projects.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return projects.build_canvas_export(project)


@app.get("/api/canvas/external/{external_project_id}", response_model=CanvasExportV1)
async def export_canvas_by_external_id(external_project_id: str) -> CanvasExportV1:
    """Pull canvas JSON by the client's external project id."""
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
    """
    Copy diagram JSON to another saved project and/or client canvas project.
    Returns genai-canvas-v1 payload for ingestion by an external canvas.
    """
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
