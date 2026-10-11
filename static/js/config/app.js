const rootMeta = document.querySelector('meta[name="app-root"]');
const APP_ROOT = (rootMeta?.content || "").replace(/\/$/, "");
const withRoot = (path) => `${APP_ROOT}${path.startsWith("/") ? path : `/${path}`}`;

const els = {
  nav: document.getElementById("configNav"),
  panels: document.getElementById("configPanels"),
  promptsPanel: document.getElementById("promptsPanel"),
  status: document.getElementById("configStatus"),
  toast: document.getElementById("toastContainer"),
  promptKey: document.getElementById("promptKeySelect"),
  promptVersion: document.getElementById("promptVersionSelect"),
  promptBody: document.getElementById("promptBody"),
  promptChars: document.getElementById("promptCharCount"),
  promptVersionLabel: document.getElementById("promptVersionLabel"),
  promptSave: document.getElementById("promptSaveBtn"),
  promptActivate: document.getElementById("promptActivateBtn"),
  promptReset: document.getElementById("promptResetBtn"),
};

let state = { groups: [], status: {}, dirty: false, activeGroup: null, draft: {} };

function showToast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  els.toast.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

function formatDefault(val) {
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

function renderStatus() {
  const s = state.status || {};
  els.status.textContent = `v${s.version || "?"} · API ${s.api_key_status || "?"} · DB ${s.db_connected ? "on" : "off"}`;
}

function fieldControl(setting) {
  const key = setting.key;
  const val = state.draft[key] !== undefined ? state.draft[key] : setting.value;
  if (setting.readonly) {
    return `<input type="text" value="${escapeAttr(String(val))}" disabled />`;
  }
  if (setting.type === "boolean") {
    return `<label><input type="checkbox" data-key="${escapeAttr(key)}" ${val ? "checked" : ""}/> Enabled</label>`;
  }
  if (setting.allowed?.length) {
    return `<select data-key="${escapeAttr(key)}">${setting.allowed
      .map((a) => `<option value="${escapeAttr(String(a))}" ${String(a) === String(val) ? "selected" : ""}>${escapeHtml(String(a))}</option>`)
      .join("")}</select>`;
  }
  if (setting.type === "json") {
    return `<textarea data-key="${escapeAttr(key)}" data-json="1">${escapeHtml(JSON.stringify(val, null, 2))}</textarea>`;
  }
  if (setting.type === "integer" || setting.type === "number") {
    return `<input type="number" data-key="${escapeAttr(key)}" value="${escapeAttr(String(val))}" ${setting.min != null ? `min="${setting.min}"` : ""} ${setting.max != null ? `max="${setting.max}"` : ""} step="${setting.type === "integer" ? "1" : "any"}" />`;
  }
  return `<input type="text" data-key="${escapeAttr(key)}" value="${escapeAttr(String(val ?? ""))}" />`;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function escapeAttr(s) {
  return escapeHtml(s).replace(/"/g, "&quot;");
}

function renderNav() {
  const items = [
    ...state.groups.map((g) => ({ id: g.id, label: g.label })),
    { id: "prompts", label: "Agent Prompts" },
  ];
  els.nav.innerHTML = items
    .map(
      (item) =>
        `<button type="button" data-group="${item.id}" class="${state.activeGroup === item.id ? "is-active" : ""}">${escapeHtml(item.label)}</button>`,
    )
    .join("");
  els.nav.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (state.dirty && !confirm("Discard unsaved changes in this group?")) return;
      state.dirty = false;
      state.draft = {};
      showGroup(btn.dataset.group);
    });
  });
}

function showGroup(groupId) {
  state.activeGroup = groupId;
  renderNav();
  const isPrompts = groupId === "prompts";
  els.promptsPanel.hidden = !isPrompts;
  els.panels.hidden = isPrompts;
  if (isPrompts) {
    loadPromptList();
    return;
  }
  const group = state.groups.find((g) => g.id === groupId);
  if (!group) return;

  const statusBlock =
    groupId === "ai_models"
      ? `<div class="status-ro">
          <div><strong>API key:</strong> ${escapeHtml(state.status.api_key_status || "unknown")} (env only — never editable here)</div>
          <div><strong>Env model:</strong> <code>${escapeHtml(String(state.status.env_model || ""))}</code></div>
          <div><strong>DB:</strong> ${state.status.db_connected ? "connected" : "offline"}</div>
        </div>`
      : "";

  els.panels.innerHTML = `
    <div class="config-card" data-group="${group.id}">
      <h2>${escapeHtml(group.label)}</h2>
      <p class="config-help">Changes apply at runtime (cached ~30s). Defaults match v2.6.9 behaviour.</p>
      ${statusBlock}
      ${group.settings
        .map(
          (s) => `
        <div class="config-field" data-field="${escapeAttr(s.key)}">
          <div class="config-field-head">
            <label>${escapeHtml(s.label)}</label>
            <span class="default-hint">default: ${escapeHtml(formatDefault(s.default))}</span>
          </div>
          <p class="help">${escapeHtml(s.help)}</p>
          ${fieldControl(s)}
          <div class="error" hidden></div>
          ${s.readonly ? "" : `<button type="button" class="btn btn-ghost btn-sm field-reset" data-reset-key="${escapeAttr(s.key)}">Reset field</button>`}
        </div>`,
        )
        .join("")}
      <div class="config-actions">
        <button type="button" class="btn btn-primary" id="saveGroupBtn">Save group</button>
        <button type="button" class="btn btn-secondary" id="resetGroupBtn">Reset group</button>
      </div>
    </div>`;

  els.panels.querySelectorAll("[data-key]").forEach((input) => {
    const handler = () => {
      state.dirty = true;
      const key = input.dataset.key;
      if (input.type === "checkbox") state.draft[key] = input.checked;
      else if (input.dataset.json) {
        try {
          state.draft[key] = JSON.parse(input.value);
          input.closest(".config-field").querySelector(".error").hidden = true;
        } catch {
          input.closest(".config-field").querySelector(".error").hidden = false;
          input.closest(".config-field").querySelector(".error").textContent = "Invalid JSON";
        }
      } else if (input.type === "number") {
        state.draft[key] = input.value.includes(".") ? Number(input.value) : parseInt(input.value, 10);
      } else state.draft[key] = input.value;
    };
    input.addEventListener("input", handler);
    input.addEventListener("change", handler);
  });

  els.panels.querySelectorAll(".field-reset").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await resetKeys([btn.dataset.resetKey]);
    });
  });
  document.getElementById("saveGroupBtn")?.addEventListener("click", saveDraft);
  document.getElementById("resetGroupBtn")?.addEventListener("click", async () => {
    if (!confirm(`Reset all settings in “${group.label}” to defaults?`)) return;
    await resetGroup(group.id);
  });
}

async function loadConfig() {
  const res = await fetch(withRoot("/api/config"));
  if (!res.ok) throw new Error("Failed to load config");
  const data = await res.json();
  state.groups = data.groups || [];
  state.status = data.status || {};
  renderStatus();
  if (!state.activeGroup) state.activeGroup = state.groups[0]?.id || "prompts";
  renderNav();
  showGroup(state.activeGroup);
  // Populate prompt keys from API list
  const keys = data.prompt_keys || [];
  els.promptKey.innerHTML = keys.map((k) => `<option value="${escapeAttr(k)}">${escapeHtml(k)}</option>`).join("");
}

async function saveDraft() {
  if (!Object.keys(state.draft).length) {
    showToast("No changes to save.", "info");
    return;
  }
  const res = await fetch(withRoot("/api/config"), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state.draft),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    showToast(data.detail || "Save failed", "error");
    return;
  }
  state.groups = data.groups || state.groups;
  state.status = data.status || state.status;
  state.draft = {};
  state.dirty = false;
  renderStatus();
  showGroup(state.activeGroup);
  showToast("Settings saved.", "success");
}

async function resetKeys(keys) {
  const res = await fetch(withRoot("/api/config/reset"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keys }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    showToast(data.detail || "Reset failed", "error");
    return;
  }
  state.groups = data.groups || state.groups;
  state.status = data.status || state.status;
  state.draft = {};
  state.dirty = false;
  showGroup(state.activeGroup);
  showToast("Reset to default.", "success");
}

async function resetGroup(group) {
  const res = await fetch(withRoot("/api/config/reset"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ group }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    showToast(data.detail || "Reset failed", "error");
    return;
  }
  state.groups = data.groups || state.groups;
  state.status = data.status || state.status;
  state.draft = {};
  state.dirty = false;
  showGroup(state.activeGroup);
  showToast("Group reset.", "success");
}

async function loadPromptList() {
  await loadPrompt(els.promptKey.value || els.promptKey.options[0]?.value);
}

async function loadPrompt(key) {
  if (!key) return;
  const res = await fetch(withRoot(`/api/config/prompts/${encodeURIComponent(key)}`));
  const data = await res.json();
  if (!res.ok) {
    showToast(data.detail || "Failed to load prompt", "error");
    return;
  }
  els.promptBody.value = data.body || "";
  els.promptChars.textContent = `${(data.body || "").length} chars`;
  els.promptVersionLabel.textContent = data.is_default ? "using code default" : `active v${data.version}`;
  const versions = data.versions || [];
  els.promptVersion.innerHTML =
    `<option value="0">Code default</option>` +
    versions.map((v) => `<option value="${v.version}" ${v.is_active ? "selected" : ""}>v${v.version} (${v.chars} chars)</option>`).join("");
}

els.promptKey?.addEventListener("change", () => loadPrompt(els.promptKey.value));
els.promptBody?.addEventListener("input", () => {
  els.promptChars.textContent = `${els.promptBody.value.length} chars`;
});
els.promptSave?.addEventListener("click", async () => {
  const key = els.promptKey.value;
  const res = await fetch(withRoot(`/api/config/prompts/${encodeURIComponent(key)}`), {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ body: els.promptBody.value }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    showToast(data.detail || "Save failed", "error");
    return;
  }
  showToast(`Saved prompt v${data.version}`, "success");
  await loadPrompt(key);
});
els.promptActivate?.addEventListener("click", async () => {
  const key = els.promptKey.value;
  const version = parseInt(els.promptVersion.value, 10);
  if (!version) {
    await fetch(withRoot(`/api/config/prompts/${encodeURIComponent(key)}/reset`), { method: "POST" });
    showToast("Using code default.", "success");
    await loadPrompt(key);
    return;
  }
  const res = await fetch(withRoot(`/api/config/prompts/${encodeURIComponent(key)}/activate`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ version }),
  });
  if (!res.ok) {
    showToast("Activate failed", "error");
    return;
  }
  showToast(`Activated v${version}`, "success");
  await loadPrompt(key);
});
els.promptReset?.addEventListener("click", async () => {
  const key = els.promptKey.value;
  if (!confirm("Deactivate overrides and use the code default?")) return;
  await fetch(withRoot(`/api/config/prompts/${encodeURIComponent(key)}/reset`), { method: "POST" });
  showToast("Prompt reset to default.", "success");
  await loadPrompt(key);
});
els.promptVersion?.addEventListener("change", async () => {
  const key = els.promptKey.value;
  const version = parseInt(els.promptVersion.value, 10);
  if (!version) {
    const res = await fetch(withRoot(`/api/config/prompts/${encodeURIComponent(key)}`));
    const data = await res.json();
    els.promptBody.value = data.default_body || "";
    els.promptChars.textContent = `${els.promptBody.value.length} chars`;
    return;
  }
  // Reload active; version preview uses activate for apply — show active body
  await loadPrompt(key);
});

window.addEventListener("beforeunload", (e) => {
  if (state.dirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});

loadConfig().catch((err) => {
  els.status.textContent = "Config load failed";
  showToast(err.message, "error");
});
