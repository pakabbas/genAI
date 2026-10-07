# Decommission: Old /genai path on leadpilotai host

This runbook documents how to remove the GenAI `/genai` (and `/genAI`) path from the `leadpilotai.spiralloopstechnologies.com` host after cutover to the new `dd.spiralloopstechnologies.com` deployment.

## Host Inventory

| Item | Value |
|------|-------|
| Shared IP | `34.136.90.173` (hosts both LeadPilot and GenAI) |
| DNS A records | `leadpilotai.spiralloopstechnologies.com` → 34.136.90.173 |
| VM | GCP instance `leadpacer-gcp3` |
| Other services on this VM | **LeadPilot** on port 8093 — **DO NOT REMOVE** |

## What served the old /genai path

| Component | Location | Purpose |
|-----------|----------|---------|
| App directory | `/var/www/html/leadpilotai/genai` | GenAI Python app files |
| Systemd service | `genai-leadpilot.service` | uvicorn on `127.0.0.1:8011` |
| Nginx snippet | `/etc/nginx/snippets/genai-leadpilot-location.conf` | Proxies `/genAI/` → `:8011` |
| Nginx include | In `/etc/nginx/sites-enabled/leadpilotai.conf` | `include snippets/genai-leadpilot-location.conf;` |

## Pre-cutover checklist

- [ ] Confirm `https://dd.spiralloopstechnologies.com/api/health` returns 200
- [ ] Confirm `https://dd.spiralloopstechnologies.com/` loads the GenAI UI
- [ ] Notify users of URL change if applicable
- [ ] Update any external links/bookmarks pointing to old URL

## Decommission steps (run on leadpacer-gcp3 VM)

**⚠️ Do NOT delete the VM — it hosts LeadPilot and other services.**

### Step 1: Stop and disable the GenAI service

```bash
sudo systemctl stop genai-leadpilot.service
sudo systemctl disable genai-leadpilot.service
```

### Step 2: Remove the nginx /genAI location

Option A — Comment out the include (preserves rollback ability):

```bash
sudo sed -i 's|^\(\s*include snippets/genai-leadpilot-location.conf;\)|# DECOMMISSIONED: \1|' \
  /etc/nginx/sites-enabled/leadpilotai.conf
```

Option B — Delete the include line entirely:

```bash
sudo sed -i '/include snippets\/genai-leadpilot-location.conf;/d' \
  /etc/nginx/sites-enabled/leadpilotai.conf
```

### Step 3: Validate and reload nginx

```bash
sudo nginx -t && sudo systemctl reload nginx
```

### Step 4: Verify /genai returns 404

```bash
curl -sS -o /dev/null -w "%{http_code}\n" \
  "https://leadpilotai.spiralloopstechnologies.com/genai/"
# Expected: 404
```

### Step 5 (optional): Archive or remove app files

If you want to keep the files for reference:

```bash
sudo mv /var/www/html/leadpilotai/genai /var/www/html/leadpilotai/genai.decommissioned
```

Or remove entirely:

```bash
sudo rm -rf /var/www/html/leadpilotai/genai
```

### Step 6 (optional): Remove systemd unit file

```bash
sudo rm /etc/systemd/system/genai-leadpilot.service
sudo systemctl daemon-reload
```

### Step 7 (optional): Remove nginx snippet

```bash
sudo rm /etc/nginx/snippets/genai-leadpilot-location.conf
```

## Rollback (if needed before full decommission)

To restore service temporarily:

```bash
# Restore nginx include if commented out
sudo sed -i 's|^# DECOMMISSIONED: \(\s*include snippets/genai-leadpilot-location.conf;\)|\1|' \
  /etc/nginx/sites-enabled/leadpilotai.conf

# Start service
sudo systemctl start genai-leadpilot.service

# Reload nginx
sudo nginx -t && sudo systemctl reload nginx
```

## Post-cutover state

After completing these steps:

| URL | Expected |
|-----|----------|
| `https://dd.spiralloopstechnologies.com/` | ✅ GenAI UI |
| `https://dd.spiralloopstechnologies.com/api/health` | ✅ 200 OK |
| `https://leadpilotai.spiralloopstechnologies.com/genai/` | ❌ 404 Not Found |
| `https://leadpilotai.spiralloopstechnologies.com/genAI/` | ❌ 404 Not Found |
| `https://leadpilotai.spiralloopstechnologies.com/` | ✅ LeadPilot (unchanged) |

## Notes

- The MySQL database (`leadpilot.genai_projects`, `leadpilot.genai_project_transfers`) is shared and should be retained — it may be used by the new deployment at `dd.spiralloopstechnologies.com`.
- The Gemini API key in the old `.env` can be revoked after confirming the new deployment has its own key configured.
- DNS for `leadpilotai.spiralloopstechnologies.com` is unaffected — LeadPilot continues to serve at the root.
