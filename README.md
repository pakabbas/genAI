# GenAI Diagram Studio

An AI-powered diagram designer — like Lucidchart or Visio with Gemini. Create **use case diagrams**, **ERDs**, **swim lane** flows, and **flowcharts** on an interactive canvas. Add, move, connect, and delete nodes; let AI generate an editable starting layout.

## Features

- **Diagram types:** Use case, ERD, swim lane, flowchart
- **Designer canvas:** drag nodes, connect edges, pan/zoom, delete selection
- **Contextual toolbox:** shapes and connectors change per diagram type
- **AI generate:** Gemini returns editable JSON diagrams (not static HTML)
- **Export:** SVG and JSON

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

## API

- `GET /api/health` — service status
- `GET /api/toolbox/{diagram_type}` — toolbox items for `use_case`, `erd`, `swim_lane`, `flowchart`
- `POST /api/generate-diagram` — `{ "prompt": "...", "diagram_type": "use_case", "existing": null }` → diagram JSON
- `POST /api/validate-diagram` — validate diagram JSON from the client
