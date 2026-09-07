# GenAI Diagram Studio

An AI-powered diagram designer — like Lucidchart or Visio with Gemini. Create **use case diagrams**, **ERDs**, **swim lane** flows, and **flowcharts** on an interactive canvas. Add, move, connect, and delete nodes; let AI generate an editable starting layout.

## Features

- **Diagram types:** Use case, ERD, swim lane, flowchart
- **Designer canvas:** drag nodes, connect edges, pan/zoom, delete selection
- **Contextual toolbox:** shapes and connectors change per diagram type
- **AI generate:** Gemini returns editable JSON diagrams (not static HTML)
- **Export:** SVG, JSON, and **genai-canvas-v1** for external canvases
- **Projects:** save/load diagrams in MySQL; transfer JSON to other projects

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GEMINI_API_KEY from https://aistudio.google.com/apikey
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

Use **Load sample diagram** to explore without an API key. **Generate with AI** requires a valid `GEMINI_API_KEY`.

## Production deployment

**URL:** https://leadpilotai.spiralloopstechnologies.com/genAI/

See [deploy/README.md](deploy/README.md) for GitHub secrets and workflow details.

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI Studio API key | *(required for AI)* |
| `GEMINI_MODEL` | Gemini model id | `gemini-flash-lite-latest` |
| `APP_HOST` | Bind host | `0.0.0.0` |
| `APP_PORT` | Bind port | `8000` (local) / `8010` (production) |
| `APP_ROOT_PATH` | URL prefix when behind nginx | empty locally, `/genAI` in production |
| `DB_HOST` | MySQL host | `127.0.0.1` on GCP |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | MySQL database | `leadpilot` (tables `genai_*`) |
| `DB_USER` | MySQL user | `leadpilot` |
| `DB_PASSWORD` | MySQL password | from `/opt/leadpilot/config/mysqldb.txt` on server |

## API

### Diagrams

- `GET /api/health` — service status (`db_connected`, `api_key_configured`)
- `GET /api/toolbox/{diagram_type}` — toolbox items
- `POST /api/generate-diagram` — AI diagram JSON
- `POST /api/validate-diagram` — validate diagram JSON

### Projects (MySQL)

- `GET /api/projects` — list saved projects
- `POST /api/projects` — create `{ name, diagram_type, title, diagram, external_project_id? }`
- `GET /api/projects/{id}` — load project + diagram
- `PUT /api/projects/{id}` — update
- `DELETE /api/projects/{id}` — delete

### Client canvas integration

Export format **`genai-canvas-v1`** for LeadPilot / external canvas:

- `GET /api/projects/{id}/export` — JSON payload with `nodes` and `edges`
- `GET /api/canvas/external/{external_project_id}` — fetch by client project id
- `POST /api/projects/{id}/transfer` — `{ "target_project_id": "...", "target_external_project_id": "...", "replace": true }`

Schema: `deploy/mysql_schema.sql`
