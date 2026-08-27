# GenAI Creator Studio

A professional web app that uses **Google Gemini** to generate websites, print-ready documents, use case diagrams, and custom HTML creations — displayed live on an interactive canvas.

## Features

- **Content types:** Website, PDF document, Use Case diagram, Custom
- **Live canvas preview** with fullscreen, download, and print/save-as-PDF
- **Mobile-responsive** UI with collapsible creation panel
- **Gemini Flash Lite (latest)** — free-tier friendly, configurable via `GEMINI_MODEL`

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000).

## Production deployment

**URL:** https://leadpilotai.spiralloopstechnologies.com/genAI/

Deployed via GitHub Actions to GCP (`34.41.10.28`) as a separate service on port **8010**, proxied under `/genAI/` without affecting the LeadPilot app on port **8093**.

See [deploy/README.md](deploy/README.md) for GitHub secrets and workflow details.

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI Studio API key | *(required)* |
| `GEMINI_MODEL` | Gemini model id | `gemini-flash-lite-latest` |
| `APP_HOST` | Bind host | `0.0.0.0` |
| `APP_PORT` | Bind port | `8000` (local) / `8010` (production) |
| `APP_ROOT_PATH` | URL prefix when behind nginx | empty locally, `/genAI` in production |

## API

- `GET /api/health` — service status
- `POST /api/generate` — `{ "prompt": "...", "content_type": "website" }` → `{ "html": "..." }`
