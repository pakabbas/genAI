# GenAI Creator Studio

Python + FastAPI app — **AI-powered diagram designer** (use case, ERD, swim lane, flowchart) with an interactive SVG canvas, contextual toolbox, and Gemini generation.

## Cursor Cloud specific instructions

### Services

| Service | Command | URL |
|---------|---------|-----|
| Web app | `source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | http://localhost:8000 |

Only one service is required. Run it in tmux for long-lived sessions.

### First-time / dependency notes

- Requires **Python 3.12+** with `python3.12-venv` (Debian: `apt install python3.12-venv`).
- Create venv once: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Copy `.env.example` to `.env` and set `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey). Keys typically start with `AIza…`.
- Default model is `gemini-flash-lite-latest` (override with `GEMINI_MODEL` in `.env`).
- **Do not commit `.env`** — it is gitignored.

### Testing without a valid Gemini key

- Use **Load sample diagram** to verify toolbox, canvas (drag/zoom/connect), and export.
- `GET /api/health` should return `api_key_configured: true` when `.env` is set.
- `POST /api/generate-diagram` requires a valid Gemini API key for AI layout generation.

### Designer UI

- Left panel: diagram type + toolbox + canvas tools (select, pan, delete).
- Center: SVG designer canvas.
- Right panel: AI prompt, properties for selected node/edge.
- Frontend modules live under `static/js/designer/` (loaded as ES modules from `templates/index.html`).

### Starlette templating

Starlette ≥1.6 uses `TemplateResponse(request, "template.html", context={...})` — not the legacy `(name, {"request": ...})` signature.

### Production deployment (GCP)

- **Public URL:** https://leadpilotai.spiralloopstechnologies.com/genAI/
- **Server path:** `/home/muhamad_abbas/apps/genAI`
- **Service:** `genai.service` on `127.0.0.1:8010` (LeadPilot remains on `:8093`)
- **Nginx:** snippet at `/etc/nginx/snippets/genai-leadpilot-location.conf`, included from `leadpilotai.conf`
- **CI/CD:** `.github/workflows/deploy.yml` on push to `main` (requires GitHub secrets — see `deploy/README.md`)
- **Subpath:** set `APP_ROOT_PATH=/genAI` in production `.env`; frontend uses `meta[name=app-root]` for API/static URLs
