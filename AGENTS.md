# GenAI Creator Studio

Python + FastAPI app that generates websites, PDF-style documents, use case diagrams, and custom HTML via **Gemini 2.5 Pro**, displayed on a live canvas.

## Cursor Cloud specific instructions

### Services

| Service | Command | URL |
|---------|---------|-----|
| Web app | `source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | http://localhost:8000 |

Only one service is required. Run it in tmux for long-lived sessions.

### First-time / dependency notes

- Requires **Python 3.12+** with `python3.12-venv` (Debian: `apt install python3.12-venv`).
- Create venv once: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.
- Copy `.env.example` to `.env` and set `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey). Keys typically start with `AIza…`. The placeholder key in user docs may be invalid.
- **Do not commit `.env`** — it is gitignored.

### Testing without a valid Gemini key

- Use **Preview example on canvas** in the UI to verify the canvas, toolbar (download/print/fullscreen), and responsive layout.
- `GET /api/health` should return `api_key_configured: true` when `.env` is set.
- `POST /api/generate` requires a valid Gemini API key for real AI output.

### Starlette templating

Starlette ≥1.6 uses `TemplateResponse(request, "template.html", context={...})` — not the legacy `(name, {"request": ...})` signature.

### Production deployment (GCP)

- **Public URL:** https://leadpilotai.spiralloopstechnologies.com/genAI/
- **Server path:** `/home/muhamad_abbas/apps/genAI`
- **Service:** `genai.service` on `127.0.0.1:8010` (LeadPilot remains on `:8093`)
- **Nginx:** snippet at `/etc/nginx/snippets/genai-leadpilot-location.conf`, included from `leadpilotai.conf`
- **CI/CD:** `.github/workflows/deploy.yml` on push to `main` (requires **GitHub repository** Actions secrets — see `deploy/README.md`; Cursor Cloud secrets are not used by GitHub Actions)
- **Subpath:** set `APP_ROOT_PATH=/genAI` in production `.env`; frontend uses `meta[name=app-root]` for API/static URLs
