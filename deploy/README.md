## Deployment (GCP 3 + GitHub Actions)

Production URL: **https://dd.spiralloopstechnologies.com/**

> **Migration note:** GenAI has moved from `https://leadpilotai.spiralloopstechnologies.com/genai/` to the new root URL above. See [`DECOMMISSION.md`](./DECOMMISSION.md) for steps to remove the old `/genai` path from the leadpilotai host after cutover.

The app runs as systemd service **`genai-leadpilot.service`** on port **8011**, proxied by nginx.

### Production server facts

| Item | Value |
|------|-------|
| Host | GCP instance `leadpacer-gcp3` (see `GCP_SSH_HOST` secret) |
| SSH user | See `GCP_SSH_USER` secret (has passwordless sudo) |
| App directory | `/var/www/html/leadpilotai/genai` |
| Service | `genai-leadpilot.service` (uvicorn on `127.0.0.1:8011`) |
| URL path | `/genai/` (lowercase) |

### GitHub repository secrets

Add these under **Settings → Secrets and variables → Actions** in the **GitHub repository**:

| Secret | Description |
|--------|-------------|
| `GCP_SSH_HOST` | Server IP address |
| `GCP_SSH_USER` | SSH username with passwordless sudo |
| `GCP_SSH_PRIVATE_KEY` | Full SSH private key (`-----BEGIN ... KEY-----` block) |

**SSH key format:** If your private key was pasted as a single line, the deploy workflow normalizes it automatically via `deploy/write_ssh_key.py`.

**Important notes:**
- The server `.env` already exists and is **never overwritten** by the deploy workflow.
- `GEMINI_API_KEY` is **not** required as a GitHub Actions secret (already configured on the server).
- Cursor Cloud agent secrets and GitHub Actions secrets are separate systems.

**Never commit SSH keys or API keys to the repository.**

### Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | PRs, pushes to `main` | Import check + script validation |
| `deploy.yml` | Push to `main`, manual dispatch | Production deploy |

### Deploy steps

1. Checkout repository
2. Setup SSH key
3. rsync application files to `/var/www/html/leadpilotai/genai/` (excluding `.git`, `.venv`, `.env`, `__pycache__`, etc.)
4. Install Python dependencies into server `.venv`
5. Set ownership to `pakabbas52:www-data` (SSH user : service group)
6. Restart `genai-leadpilot.service`
7. Verify health endpoint and homepage return HTTP 200

### File ownership

The app directory is owned by `pakabbas52:www-data`:

- **Owner (`pakabbas52`):** deploy SSH user — allows rsync to write files on subsequent deploys.
- **Group (`www-data`):** allows the systemd service (running as `www-data`) to read the app tree.
- **Directory setgid:** the app root has `g+rwxs` so new subdirectories inherit the `www-data` group.

The rsync step uses `--no-owner --no-group` to avoid permission errors when updating files.

### Legacy paths (removed)

The following old paths are no longer used:
- Old home directory app path (previously used on a different server)
- `/genAI/` uppercase URL path
- Port `8010`
- `genai.service` (old service name)
- `setup-server.sh` / `deploy.sh` scripts (nginx bootstrap)

### Local subpath testing

```bash
APP_ROOT_PATH=/genai uvicorn app.main:app --host 127.0.0.1 --port 8011
# Visit http://127.0.0.1:8011/ (app uses root_path for generated links)
```
