# GenAI Creator Studio

A professional web app that uses **Google Gemini 2.5 Pro** to generate websites, print-ready documents, use case diagrams, and custom HTML creations — displayed live on an interactive canvas.

## Features

- **Content types:** Website, PDF document, Use Case diagram, Custom
- **Live canvas preview** with fullscreen, download, and print/save-as-PDF
- **Mobile-responsive** UI with collapsible creation panel
- **Gemini 2.5 Pro** for highest-quality HTML output

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

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI Studio API key | *(required)* |
| `GEMINI_MODEL` | Gemini model id | `gemini-2.5-pro` |
| `APP_HOST` | Bind host | `0.0.0.0` |
| `APP_PORT` | Bind port | `8000` |

## API

- `GET /api/health` — service status
- `POST /api/generate` — `{ "prompt": "...", "content_type": "website" }` → `{ "html": "..." }`
