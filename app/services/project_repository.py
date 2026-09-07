import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.connection import get_connection
from app.schemas.diagram import DiagramDocument
from app.schemas.project import (
    CanvasExportV1,
    ProjectCreate,
    ProjectDetail,
    ProjectSummary,
    ProjectUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _diagram_counts(diagram_json: dict[str, Any]) -> tuple[int, int]:
    nodes = diagram_json.get("nodes") or []
    edges = diagram_json.get("edges") or []
    return len(nodes), len(edges)


def _row_to_summary(row: dict[str, Any]) -> ProjectSummary:
    diagram_json = row["diagram_json"]
    if isinstance(diagram_json, str):
        diagram_json = json.loads(diagram_json)
    node_count, edge_count = _diagram_counts(diagram_json)
    return ProjectSummary(
        id=row["id"],
        name=row["name"],
        diagram_type=row["diagram_type"],
        title=row["title"],
        external_project_id=row.get("external_project_id"),
        updated_at=row["updated_at"],
        node_count=node_count,
        edge_count=edge_count,
    )


def _row_to_detail(row: dict[str, Any]) -> ProjectDetail:
    diagram_json = row["diagram_json"]
    if isinstance(diagram_json, str):
        diagram_json = json.loads(diagram_json)
    node_count, edge_count = _diagram_counts(diagram_json)
    return ProjectDetail(
        id=row["id"],
        name=row["name"],
        description=row.get("description"),
        diagram_type=row["diagram_type"],
        title=row["title"],
        external_project_id=row.get("external_project_id"),
        diagram=DiagramDocument.model_validate(diagram_json),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        node_count=node_count,
        edge_count=edge_count,
    )


def list_projects(limit: int = 100) -> list[ProjectSummary]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, diagram_type, title, external_project_id,
                       diagram_json, updated_at
                FROM genai_projects
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    return [_row_to_summary(row) for row in rows]


def get_project(project_id: str) -> ProjectDetail | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM genai_projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
    return _row_to_detail(row) if row else None


def get_project_by_external(external_project_id: str) -> ProjectDetail | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM genai_projects WHERE external_project_id = %s LIMIT 1",
                (external_project_id,),
            )
            row = cur.fetchone()
    return _row_to_detail(row) if row else None


def create_project(data: ProjectCreate) -> ProjectDetail:
    project_id = str(uuid.uuid4())
    diagram_json = data.diagram.model_dump(by_alias=True)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO genai_projects
                  (id, name, description, diagram_type, title, diagram_json, external_project_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    project_id,
                    data.name,
                    data.description,
                    data.diagram_type,
                    data.title,
                    json.dumps(diagram_json),
                    data.external_project_id,
                ),
            )
    project = get_project(project_id)
    if not project:
        raise RuntimeError("Failed to create project.")
    return project


def update_project(project_id: str, data: ProjectUpdate) -> ProjectDetail | None:
    existing = get_project(project_id)
    if not existing:
        return None

    name = data.name if data.name is not None else existing.name
    description = data.description if data.description is not None else existing.description
    diagram_type = data.diagram_type if data.diagram_type is not None else existing.diagram_type
    title = data.title if data.title is not None else existing.title
    diagram = data.diagram if data.diagram is not None else existing.diagram
    external_project_id = (
        data.external_project_id
        if data.external_project_id is not None
        else existing.external_project_id
    )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE genai_projects
                SET name = %s, description = %s, diagram_type = %s, title = %s,
                    diagram_json = %s, external_project_id = %s
                WHERE id = %s
                """,
                (
                    name,
                    description,
                    diagram_type,
                    title,
                    json.dumps(diagram.model_dump(by_alias=True)),
                    external_project_id,
                    project_id,
                ),
            )
    return get_project(project_id)


def delete_project(project_id: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM genai_projects WHERE id = %s", (project_id,))
            return cur.rowcount > 0


def build_canvas_export(project: ProjectDetail) -> CanvasExportV1:
    diagram = project.diagram.model_dump(by_alias=True)
    return CanvasExportV1(
        project_id=project.id,
        project_name=project.name,
        external_project_id=project.external_project_id,
        diagram_type=project.diagram_type,
        title=project.title,
        nodes=diagram.get("nodes", []),
        edges=diagram.get("edges", []),
        exported_at=_utcnow(),
    )


def log_transfer(
    source_project_id: str,
    target_project_id: str,
    payload: CanvasExportV1,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO genai_project_transfers
                  (source_project_id, target_project_id, export_payload)
                VALUES (%s, %s, %s)
                """,
                (
                    source_project_id,
                    target_project_id,
                    json.dumps(payload.model_dump(mode="json")),
                ),
            )


def transfer_to_project(
    source: ProjectDetail,
    target_project_id: str,
    *,
    replace: bool = True,
) -> tuple[ProjectDetail | None, CanvasExportV1]:
    export = build_canvas_export(source)
    target = get_project(target_project_id)
    if not target:
        return None, export

    if replace:
        updated = update_project(
            target_project_id,
            ProjectUpdate(
                diagram_type=source.diagram_type,
                title=source.title,
                diagram=source.diagram,
            ),
        )
        target = updated or target

    log_transfer(source.id, target_project_id, export)
    return target, export


def transfer_to_external(
    source: ProjectDetail,
    target_external_project_id: str,
    *,
    replace: bool = True,
) -> tuple[ProjectDetail | None, CanvasExportV1]:
    export = build_canvas_export(source)
    export.external_project_id = target_external_project_id
    target = get_project_by_external(target_external_project_id)

    if target and replace:
        updated = update_project(
            target.id,
            ProjectUpdate(
                diagram_type=source.diagram_type,
                title=source.title,
                diagram=source.diagram,
                external_project_id=target_external_project_id,
            ),
        )
        target = updated or target
        log_transfer(source.id, target.id, export)
    elif target:
        log_transfer(source.id, target.id, export)

    return target, export
