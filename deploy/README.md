## Deployment (GCP + GitHub Actions)

Production URL: **https://leadpilotai.spiralloopstechnologies.com/genAI/**

The app runs as a **separate systemd service** (`genai.service`) on port **8010**, proxied by nginx under `/genAI/` on the existing LeadPilot host (`34.41.10.28`). The root LeadPilot app on port **8093** is unchanged.

### GitHub repository secrets

Add these under **Settings → Secrets and variables → Actions** in the **GitHub repository** (not Cursor Cloud secrets):

| Secret | Value |
|--------|--------|
| `GCP_SSH_HOST` | `34.41.10.28` |
| `GCP_SSH_USER` | `muhamad_abbas` |
| `GCP_SSH_PRIVATE_KEY` | Full SSH private key (`-----BEGIN ... KEY-----` block) |
| `GEMINI_API_KEY` | Valid Google AI Studio API key |

**Important:** Cursor Cloud agent secrets and GitHub Actions secrets are separate. The deploy workflow reads only **GitHub repository secrets**. If deploy fails at "Validate GitHub Actions secrets", add the missing values in GitHub.

**Never commit SSH keys or API keys to the repository.**

### Workflows

- **`ci.yml`** — runs on PRs and pushes to `main` (import check + script validation)
- **`deploy.yml`** — deploys on push to `main` (or manual **workflow_dispatch**)

Deploy steps: rsync → `deploy/setup-server.sh` (nginx snippet + systemd, idempotent) → `deploy/deploy.sh` → public health check.

### Manual one-time server setup

```bash
ssh muhamad_abbas@34.41.10.28
cd ~/apps/genAI
chmod +x deploy/*.sh
./deploy/setup-server.sh
GEMINI_API_KEY=your_key ./deploy/deploy.sh
```

### Local subpath testing

```bash
APP_ROOT_PATH=/genAI uvicorn app.main:app --host 127.0.0.0 --port 8010
# Visit http://127.0.0.1:8010/ (app uses root_path for generated links)
```
