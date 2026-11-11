const rootMeta = document.querySelector('meta[name="app-root"]');
const APP_ROOT = (rootMeta?.content || "").replace(/\/$/, "");
const withRoot = (path) => `${APP_ROOT}${path.startsWith("/") ? path : `/${path}`}`;

const els = {
  nav: document.getElementById("configNav"),
  panels: document.getElementById("configPanels"),
  promptsPanel: document.getElementById("promptsPanel"),
  geminiKeyPanel: document.getElementById("geminiKeyPanel"),
  geminiKeyStatus: document.getElementById("geminiKeyStatus"),
  geminiKeyInput: document.getElementById("geminiKeyInput"),
  geminiKeyError: document.getElementById("geminiKeyError"),
  geminiKeySave: document.getElementById("geminiKeySaveBtn"),
  status: document.getElementById("configStatus"),
  toast: document.getElementById("toastContainer"),
  promptTabs: document.getElementById("promptTabs"),
  promptKeyField: document.getElementById("promptKeyField"),
  promptContextHelp: document.getElementById("promptContextHelp"),
  promptKey: document.getElementById("promptKeySelect"),
  promptVersion: document.getElementById("promptVersionSelect"),
  promptBody: document.getElementById("promptBody"),
  promptChars: document.getElementById("promptCharCount"),
  promptVersionLabel: document.getElementById("promptVersionLabel"),
  promptSave: document.getElementById("promptSaveBtn"),
  promptActivate: document.getElementById("promptActivateBtn"),
  promptReset: document.getElementById("promptResetBtn"),
};

let state = { groups: [], status: {}, dirty: false, promptDirty: false, activeGroup: null, draft: {}, promptKeys: [], promptContexts: [], promptTab: "shared" };
let promptLoadId = 0;
let loadedPromptKey = null;
let previewPromptVersion = "0";

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

function formatKeyStatus(info) {
  const src = info || state.status || {};
  if (src.api_key_configured || src.configured) {
    const last4 = src.api_key_last4 || src.last4;
    return last4 ? `configured · last 4: ${last4}` : "configured";
  }
  if (src.api_key_status === "set") return "configured";
  return "not configured";
}

function renderStatus() {
  const s = state.status || {};
  const text = `v${s.version || "?"} · API ${formatKeyStatus(s)} · DB ${s.db_connected ? "on" : "off"}`;
  els.status.textContent = text;
  els.status.title = text;
}

function renderGeminiKeyStatus(info) {
  if (!els.geminiKeyStatus) return;
  const src = info || {
    configured: state.status?.api_key_configured || state.status?.api_key_status === "set",
    last4: state.status?.api_key_last4,
  };
  const label = formatKeyStatus(src);
  els.geminiKeyStatus.innerHTML = `<div><strong>Current key:</strong> ${escapeHtml(label)}</div>`;
}

function setGeminiKeyError(msg) {
  if (!els.geminiKeyError) return;
  if (!msg) {
    els.geminiKeyError.hidden = true;
    els.geminiKeyError.textContent = "";
    return;
  }
  els.geminiKeyError.hidden = false;
  els.geminiKeyError.textContent = msg;
}

function detailMessage(data, fallback) {
  const d = data?.detail;
  if (typeof d === "string" && d.trim()) return d;
  if (Array.isArray(d)) {
    return d.map((item) => (typeof item === "string" ? item : item?.msg || JSON.stringify(item))).join("; ");
  }
  if (d && typeof d === "object" && d.message) return d.message;
  return fallback;
}

async function loadGeminiKeyStatus() {
  try {
    const res = await fetch(withRoot("/api/config/gemini-key"));
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(detailMessage(data, "Could not load key status"));
    if (state.status) {
      state.status.api_key_configured = Boolean(data.configured);
      state.status.api_key_last4 = data.last4 || null;
      state.status.api_key_status = data.configured ? "set" : "not set";
    }
    renderGeminiKeyStatus(data);
    renderStatus();
  } catch (err) {
    if (els.geminiKeyStatus) {
      els.geminiKeyStatus.textContent = "Could not load the current key status.";
    }
  }
}

async function saveGeminiKey() {
  const key = (els.geminiKeyInput?.value || "").trim();
  setGeminiKeyError("");
  if (!key) {
    setGeminiKeyError("Enter a Gemini API key.");
    showToast("Enter a Gemini API key.", "error");
    return;
  }
  if (els.geminiKeySave) {
    els.geminiKeySave.disabled = true;
    els.geminiKeySave.textContent = "Testing key…";
  }
  try {
    const res = await fetch(withRoot("/api/config/gemini-key"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: key }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = detailMessage(data, "The key test failed. Nothing was saved.");
      setGeminiKeyError(msg);
      showToast(msg, "error");
      return;
    }
    if (els.geminiKeyInput) els.geminiKeyInput.value = "";
    if (state.status) {
      state.status.api_key_configured = Boolean(data.configured);
      state.status.api_key_last4 = data.last4 || null;
      state.status.api_key_status = data.configured ? "set" : "not set";
    }
    renderGeminiKeyStatus(data);
    renderStatus();
    showToast("Key tested and saved.", "success");
  } catch (err) {
    const msg = err?.message || "The key test failed. Nothing was saved.";
    setGeminiKeyError(msg);
    showToast(msg, "error");
  } finally {
    if (els.geminiKeySave) {
      els.geminiKeySave.disabled = false;
      els.geminiKeySave.textContent = "Test and save";
    }
  }
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
    { id: "gemini_key", label: "Gemini API key" },
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
      if ((state.dirty || state.promptDirty) && !confirm("Discard unsaved changes in this group?")) return;
      state.dirty = false;
      state.promptDirty = false;
      state.draft = {};
      showGroup(btn.dataset.group);
    });
  });
}

function showGroup(groupId) {
  state.activeGroup = groupId;
  renderNav();
  const isPrompts = groupId === "prompts";
  const isGeminiKey = groupId === "gemini_key";
  if (els.promptsPanel) els.promptsPanel.hidden = !isPrompts;
  if (els.geminiKeyPanel) els.geminiKeyPanel.hidden = !isGeminiKey;
  els.panels.hidden = isPrompts || isGeminiKey;
  if (isPrompts) {
    loadPromptList();
    return;
  }
  if (isGeminiKey) {
    loadGeminiKeyStatus();
    return;
  }
  const group = state.groups.find((g) => g.id === groupId);
  if (!group) return;

  const statusBlock =
    groupId === "ai_models"
      ? `<div class="status-ro">
          <div><strong>API key:</strong> ${escapeHtml(formatKeyStatus(state.status))} (change it under Gemini API key)</div>
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
  renderGeminiKeyStatus();
  if (!state.activeGroup) state.activeGroup = "gemini_key";
  state.promptKeys = data.prompt_keys || [];
  state.promptContexts = data.prompt_contexts || [];
  renderNav();
  showGroup(state.activeGroup);
}

// 2.7.6: read every field at save time instead of relying only on input/change
// events (autofill, paste-and-click, and some browsers don't always fire them).
function collectDraft() {
  const group = state.groups.find((g) => g.id === state.activeGroup);
  if (!group) return;
  const byKey = Object.fromEntries(group.settings.map((s) => [s.key, s]));
  els.panels.querySelectorAll("[data-key]").forEach((input) => {
    const key = input.dataset.key;
    const setting = byKey[key];
    if (!setting || setting.readonly) return;
    let val;
    if (input.type === "checkbox") val = input.checked;
    else if (input.dataset.json) {
      try { val = JSON.parse(input.value); } catch { return; }
    } else if (input.type === "number") {
      if (input.value === "") return;
      val = setting.type === "integer" ? parseInt(input.value, 10) : Number(input.value);
    } else val = input.value.trim();
    if (JSON.stringify(val) !== JSON.stringify(setting.value)) state.draft[key] = val;
    else delete state.draft[key];
  });
}

async function saveDraft() {
  collectDraft();
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

function promptTabItems() {
  return [
    { id: "shared", label: "Shared Base", keys: ["generator.system"] },
    ...state.promptContexts.map((c) => ({ id: c.diagram_type, label: c.label, keys: [c.prompt_key] })),
    { id: "other", label: "Other Agent Prompts", keys: state.promptKeys.filter((key) => key !== "generator.system" && !key.startsWith("generator.context.")) },
  ];
}

async function loadPromptList() {
  const tabs = promptTabItems();
  const tab = tabs.find((item) => item.id === state.promptTab) || tabs[0];
  state.promptTab = tab.id;
  const previousKey = els.promptKey.value;
  els.promptTabs.innerHTML = tabs.map((item) =>
    `<button type="button" role="tab" id="prompt-tab-${escapeAttr(item.id)}" aria-controls="promptBody" aria-selected="${item.id === tab.id}" data-prompt-tab="${escapeAttr(item.id)}">${escapeHtml(item.label)}</button>`
  ).join("");
  els.promptTabs.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.promptTab === state.promptTab && loadedPromptKey) return;
      if (state.promptDirty && !confirm("Discard unsaved prompt changes?")) return;
      state.promptDirty = false;
      state.promptTab = button.dataset.promptTab;
      loadPromptList();
    });
  });
  els.promptKey.innerHTML = tab.keys.map((key) => `<option value="${escapeAttr(key)}">${escapeHtml(key)}</option>`).join("");
  if (tab.keys.includes(previousKey)) els.promptKey.value = previousKey;
  els.promptKeyField.hidden = tab.keys.length === 1;
  els.promptBody.setAttribute("aria-labelledby", `prompt-tab-${tab.id}`);
  els.promptContextHelp.textContent = tab.id === "shared"
    ? "Shared, type-neutral JSON schema, completeness, edit stability and layout rules. Always included."
    : tab.id === "other"
      ? "Analyst, planner, QC and legacy guidance prompts. Legacy guidance seeds each type's default context; a saved full context takes precedence."
      : `${tab.label}: this context alone is combined with Shared Base. Key: ${tab.keys[0]}`;
  await loadPrompt(els.promptKey.value);
}

function setPromptLoading(loading) {
  els.promptBody.disabled = loading;
  els.promptVersion.disabled = loading;
  els.promptSave.disabled = loading;
  els.promptActivate.disabled = loading;
  els.promptReset.disabled = loading;
}

async function loadPrompt(key, version = null) {
  if (!key || key !== els.promptKey.value) return;
  const loadId = ++promptLoadId;
  loadedPromptKey = null;
  setPromptLoading(true);
  els.promptBody.value = "";
  els.promptChars.textContent = "0 chars";
  els.promptVersionLabel.textContent = "Loading…";
  try {
    const query = version === null ? "" : `?version=${version}`;
    const res = await fetch(withRoot(`/api/config/prompts/${encodeURIComponent(key)}${query}`));
    const data = await res.json();
    if (loadId !== promptLoadId || key !== els.promptKey.value) return;
    if (!res.ok) throw new Error(data.detail || "Failed to load prompt");
    state.promptDirty = false;
    loadedPromptKey = key;
    els.promptBody.value = data.body || "";
    els.promptChars.textContent = `${(data.body || "").length} chars`;
    els.promptVersionLabel.textContent = version !== null
      ? (version === 0 ? "preview: code default" : `preview: v${version}`)
      : (data.is_default ? "using code default" : `active v${data.version}`);
    const versions = data.versions || [];
    els.promptVersion.innerHTML = `<option value="0">Code default</option>` +
      versions.map((v) => `<option value="${v.version}">v${v.version} (${v.chars} chars)</option>`).join("");
    previewPromptVersion = String(version ?? data.version ?? 0);
    els.promptVersion.value = previewPromptVersion;
    setPromptLoading(false);
  } catch (err) {
    if (loadId !== promptLoadId || key !== els.promptKey.value) return;
    els.promptVersionLabel.textContent = "Prompt load failed — select the tab again to retry.";
    showToast(err.message || "Failed to load prompt", "error");
  }
}

els.promptKey?.addEventListener("change", () => {
  if (state.promptDirty && !confirm("Discard unsaved prompt changes?")) {
    els.promptKey.value = loadedPromptKey;
    return;
  }
  state.promptDirty = false;
  loadPrompt(els.promptKey.value);
});

els.promptBody?.addEventListener("input", () => {
  state.promptDirty = true;
  els.promptChars.textContent = `${els.promptBody.value.length} chars`;
});
els.promptSave?.addEventListener("click", async () => {
  const key = els.promptKey.value;
  if (!loadedPromptKey || loadedPromptKey !== key) return;
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
  if (!loadedPromptKey || loadedPromptKey !== key) return;
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
  if (!loadedPromptKey || loadedPromptKey !== key) return;
  if (!confirm("Deactivate overrides and use the code default?")) return;
  await fetch(withRoot(`/api/config/prompts/${encodeURIComponent(key)}/reset`), { method: "POST" });
  showToast("Prompt reset to default.", "success");
  await loadPrompt(key);
});
els.promptVersion?.addEventListener("change", () => {
  if (state.promptDirty && !confirm("Discard unsaved prompt changes?")) {
    els.promptVersion.value = previewPromptVersion;
    return;
  }
  state.promptDirty = false;
  loadPrompt(els.promptKey.value, parseInt(els.promptVersion.value, 10) || 0);
});

window.addEventListener("beforeunload", (e) => {
  if (state.dirty || state.promptDirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});

els.geminiKeySave?.addEventListener("click", saveGeminiKey);
els.geminiKeyInput?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    saveGeminiKey();
  }
});

loadConfig().catch((err) => {
  els.status.textContent = "Config load failed";
  showToast(err.message, "error");
});
