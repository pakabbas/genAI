import { DIAGRAM_TYPE_LABELS, SAMPLE_DIAGRAMS } from "./diagram-types.js";
import { DiagramCanvas } from "./canvas.js";
import { normalizeDiagram } from "./normalize.js";

(() => {
  const APP_ROOT = document.querySelector('meta[name="app-root"]')?.content || "";

  function withRoot(path) {
    return `${APP_ROOT}${path}`;
  }

  const state = {
    diagramType: "use_case",
    toolbox: [],
    lastPrompt: "",
    isGenerating: false,
    isDirty: false,
    currentProjectId: null,
    externalProjectId: null,
    dbConnected: false,
  };

  const els = {
    apiStatus: document.getElementById("apiStatus"),
    diagramTypeSelect: document.getElementById("diagramTypeSelect"),
    diagramTypeSelectLeft: document.getElementById("diagramTypeSelectLeft"),
    activeTypeLabel: document.getElementById("activeTypeLabel"),
    toolboxNodes: document.getElementById("toolboxNodes"),
    toolboxEdges: document.getElementById("toolboxEdges"),
    toolboxHint: document.getElementById("toolboxHint"),
    canvasHost: document.getElementById("canvasHost"),
    diagramTitle: document.getElementById("diagramTitle"),
    promptInput: document.getElementById("promptInput"),
    charCount: document.getElementById("charCount"),
    generateBtn: document.getElementById("generateBtn"),
    sampleBtn: document.getElementById("sampleBtn"),
    clearBtn: document.getElementById("clearBtn"),
    deleteBtn: document.getElementById("deleteBtn"),
    duplicateBtn: document.getElementById("duplicateBtn"),
    selectTool: document.getElementById("selectTool"),
    panTool: document.getElementById("panTool"),
    connectHint: document.getElementById("connectHint"),
    propsEmpty: document.getElementById("propsEmpty"),
    propsForm: document.getElementById("propsForm"),
    propLabel: document.getElementById("propLabel"),
    propType: document.getElementById("propType"),
    zoomInBtn: document.getElementById("zoomInBtn"),
    zoomOutBtn: document.getElementById("zoomOutBtn"),
    fitBtn: document.getElementById("fitBtn"),
    exportSvgBtn: document.getElementById("exportSvgBtn"),
    exportJsonBtn: document.getElementById("exportJsonBtn"),
    canvasBadge: document.getElementById("canvasBadge"),
    canvasLoading: document.getElementById("canvasLoading"),
    toastContainer: document.getElementById("toastContainer"),
    leftPanel: document.getElementById("leftPanel"),
    rightPanel: document.getElementById("rightPanel"),
    panelToggleLeft: document.getElementById("panelToggleLeft"),
    panelToggleRight: document.getElementById("panelToggleRight"),
    tabAi: document.getElementById("tabAi"),
    tabProject: document.getElementById("tabProject"),
    panelAi: document.getElementById("panelAi"),
    panelProject: document.getElementById("panelProject"),
    projectSelect: document.getElementById("projectSelect"),
    projectNameInput: document.getElementById("projectNameInput"),
    newProjectBtn: document.getElementById("newProjectBtn"),
    saveProjectBtn: document.getElementById("saveProjectBtn"),
    deleteProjectBtn: document.getElementById("deleteProjectBtn"),
    transferTargetSelect: document.getElementById("transferTargetSelect"),
    transferProjectBtn: document.getElementById("transferProjectBtn"),
    copyCanvasExportBtn: document.getElementById("copyCanvasExportBtn"),
    projectStatus: document.getElementById("projectStatus"),
  };

  const canvas = new DiagramCanvas(els.canvasHost, {
    onChange: () => {
      state.isDirty = true;
      els.canvasBadge.textContent = "Edited";
      els.canvasBadge.classList.add("is-live");
      if (els.diagramTitle.value !== canvas.diagram.title) {
        els.diagramTitle.value = canvas.diagram.title;
      }
    },
    onSelectionChange: (selection) => {
      updatePropertiesPanel(selection);
    },
  });

  function switchSidebarTab(tab) {
    const isAi = tab === "ai";
    els.tabAi?.classList.toggle("is-active", isAi);
    els.tabProject?.classList.toggle("is-active", !isAi);
    els.tabAi?.setAttribute("aria-selected", isAi ? "true" : "false");
    els.tabProject?.setAttribute("aria-selected", !isAi ? "true" : "false");
    els.panelAi?.classList.toggle("is-active", isAi);
    els.panelProject?.classList.toggle("is-active", !isAi);
    if (els.panelAi) els.panelAi.hidden = !isAi;
    if (els.panelProject) els.panelProject.hidden = isAi;
  }

  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast${type === "error" ? " is-error" : type === "success" ? " is-success" : ""}`;
    toast.textContent = message;
    els.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4200);
  }

  function setGenerating(isGenerating) {
    state.isGenerating = isGenerating;
    els.generateBtn.disabled = isGenerating;
    els.generateBtn.classList.toggle("is-loading", isGenerating);
    els.generateBtn.querySelector(".btn-spinner").hidden = !isGenerating;
    els.canvasLoading.hidden = !isGenerating;
    els.canvasBadge.classList.toggle("is-loading", isGenerating);
  }

  function updateCharCount() {
    els.charCount.textContent = `${els.promptInput.value.length} / 8000`;
  }

  function applyDiagramToCanvas(diagram, badge = "Ready") {
    const normalized = normalizeDiagram(diagram, state.toolbox);
    canvas.loadNormalizedDiagram(normalized);
    els.diagramTitle.value = normalized.title;
    state.isDirty = false;
    canvas.scheduleFitToContent();
    els.canvasBadge.textContent = badge;
    els.canvasBadge.classList.add("is-live");
  }

  function selectDiagramType(type, { clearCanvasOnChange = false } = {}) {
    if (state.diagramType === type && !clearCanvasOnChange) {
      return;
    }
    state.diagramType = type;
    if (els.diagramTypeSelect) els.diagramTypeSelect.value = type;
    if (els.diagramTypeSelectLeft) els.diagramTypeSelectLeft.value = type;
    if (els.activeTypeLabel) {
      els.activeTypeLabel.textContent = DIAGRAM_TYPE_LABELS[type] || type;
    }
    canvas.setDiagramType(type);
    loadToolbox(type).then(() => {
      if (clearCanvasOnChange) {
        clearCanvas();
      }
    });
  }

  async function loadToolbox(type) {
    try {
      const res = await fetch(withRoot(`/api/toolbox/${type}`));
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to load toolbox");
      state.toolbox = data.items;
      renderToolbox(data.items);
      els.toolboxHint.textContent = data.label;
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  function renderToolbox(items) {
    els.toolboxNodes.innerHTML = "";
    els.toolboxEdges.innerHTML = "";
    for (const item of items) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `toolbox-item toolbox-${item.kind}`;
      btn.dataset.shape = item.shape;
      btn.title = item.label;
      btn.innerHTML = `
        <span class="toolbox-glyph" aria-hidden="true">${glyphFor(item)}</span>
        <span class="toolbox-label">${item.label}</span>
      `;
      btn.addEventListener("click", () => onToolboxClick(item));
      if (item.kind === "node") els.toolboxNodes.appendChild(btn);
      else els.toolboxEdges.appendChild(btn);
    }
  }

  function glyphFor(item) {
    const map = {
      actor: "Actor",
      use_case: "UC",
      entity: "Ent",
      process: "Proc",
      lane: "Lane",
      class: "Class",
      cloud: "Cloud",
    };
    if (item.kind === "edge") return "→";
    return map[item.shape] || item.label.slice(0, 4);
  }

  function onToolboxClick(item) {
    if (item.kind === "node") {
      canvas.setMode("select");
      setActiveTool("select");
      const center = canvas.viewport.getBoundingClientRect();
      const world = canvas._screenToWorld(center.left + center.width / 2, center.top + center.height / 2);
      canvas.addNode(item.shape, "", world.x - item.default_width / 2, world.y - item.default_height / 2);
      showToast(`Added ${item.label}`, "success");
    } else {
      canvas.setMode("connect", item.shape);
      setActiveTool("connect");
      els.connectHint.hidden = false;
      els.connectHint.textContent = `Connect: click source, then target (${item.label})`;
    }
  }

  function setActiveTool(tool) {
    els.selectTool.classList.toggle("is-active", tool === "select");
    els.panTool.classList.toggle("is-active", tool === "pan");
    if (tool === "select") {
      canvas.setMode("select");
      els.connectHint.hidden = true;
    } else if (tool === "pan") {
      canvas.setMode("pan");
      els.connectHint.hidden = true;
    }
  }

  function updatePropertiesPanel(selection) {
    const item = selection.nodes[0] || selection.edges[0];
    if (!item) {
      els.propsEmpty.hidden = false;
      els.propsForm.hidden = true;
      return;
    }
    els.propsEmpty.hidden = true;
    els.propsForm.hidden = false;
    els.propLabel.value = item.label || "";
    els.propType.textContent = item.type;
  }

  function duplicateSelection() {
    const sel = canvas.getSelection();
    if (!sel.nodes.length) {
      showToast("Select a shape to duplicate.", "error");
      return;
    }
    for (const node of sel.nodes) {
      canvas.addNode(node.type, node.label, node.x + 24, node.y + 24);
    }
    showToast("Duplicated selection.", "success");
  }

  async function checkHealth() {
    try {
      const res = await fetch(withRoot("/api/health"));
      const data = await res.json();
      state.dbConnected = Boolean(data.db_connected);
      if (data.api_key_configured) {
        els.apiStatus.classList.add("is-ready");
        const dbLabel = data.db_connected ? " · DB" : "";
        els.apiStatus.innerHTML = `<span class="status-dot"></span> Gemini ready${dbLabel}`;
      } else {
        els.apiStatus.classList.add("is-error");
        els.apiStatus.innerHTML = '<span class="status-dot"></span> API key missing';
        showToast("Set GEMINI_API_KEY in .env to enable AI generation.", "error");
      }
      if (!data.db_connected) {
        setProjectStatus("Database offline — save disabled");
      } else {
        await refreshProjectList();
      }
    } catch {
      els.apiStatus.classList.add("is-error");
      els.apiStatus.innerHTML = '<span class="status-dot"></span> Offline';
    }
  }

  function setProjectStatus(text) {
    if (els.projectStatus) els.projectStatus.textContent = text;
  }

  function buildDiagramPayload() {
    const diagram = canvas.getDiagram();
    diagram.diagram_type = state.diagramType;
    diagram.title = els.diagramTitle.value.trim() || diagram.title;
    return normalizeDiagram(diagram, state.toolbox);
  }

  async function refreshProjectList() {
    if (!state.dbConnected || !els.projectSelect) return;
    try {
      const res = await fetch(withRoot("/api/projects"));
      const items = await res.json();
      if (!res.ok) throw new Error(items.detail || "Could not load projects.");

      const current = state.currentProjectId;
      els.projectSelect.innerHTML = '<option value="">— New unsaved project —</option>';
      els.transferTargetSelect.innerHTML = '<option value="">Select target…</option>';

      for (const p of items) {
        const label = `${p.name} (${p.node_count} shapes)`;
        const opt = document.createElement("option");
        opt.value = p.id;
        opt.textContent = label;
        els.projectSelect.appendChild(opt);

        if (p.id !== current) {
          const tOpt = document.createElement("option");
          tOpt.value = p.id;
          tOpt.textContent = label;
          els.transferTargetSelect.appendChild(tOpt);
        }
      }

      if (current) els.projectSelect.value = current;
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function loadProject(projectId) {
    if (!projectId) return;
    try {
      const res = await fetch(withRoot(`/api/projects/${projectId}`));
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Load failed.");

      state.currentProjectId = data.id;
      state.externalProjectId = data.external_project_id || null;
      els.projectNameInput.value = data.name;
      els.diagramTitle.value = data.title;
      selectDiagramType(data.diagram_type);
      applyDiagramToCanvas(data.diagram, "Loaded");
      state.isDirty = false;
      setProjectStatus(`Saved · ${data.id.slice(0, 8)}…`);
      await refreshProjectList();
      showToast(`Opened project “${data.name}”.`, "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  function newProject() {
    state.currentProjectId = null;
    state.externalProjectId = null;
    els.projectNameInput.value = "Untitled Project";
    els.projectSelect.value = "";
    clearCanvas();
    setProjectStatus("Not saved yet");
    showToast("New project — edit and click Save.", "success");
  }

  async function saveProject() {
    if (!state.dbConnected) {
      showToast("Database not connected.", "error");
      return;
    }

    const name = els.projectNameInput.value.trim() || "Untitled Project";
    const diagram = buildDiagramPayload();
    const body = {
      name,
      diagram_type: state.diagramType,
      title: diagram.title,
      diagram: {
        diagram_type: state.diagramType,
        title: diagram.title,
        nodes: diagram.nodes,
        edges: diagram.edges,
      },
      external_project_id: state.externalProjectId,
    };

    try {
      let res;
      if (state.currentProjectId) {
        res = await fetch(withRoot(`/api/projects/${state.currentProjectId}`), {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } else {
        res = await fetch(withRoot("/api/projects"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      }
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Save failed.");

      state.currentProjectId = data.id;
      state.externalProjectId = data.external_project_id || null;
      state.isDirty = false;
      setProjectStatus(`Saved · ${data.id.slice(0, 8)}…`);
      await refreshProjectList();
      els.projectSelect.value = data.id;
      showToast("Project saved.", "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function deleteCurrentProject() {
    if (!state.currentProjectId) {
      showToast("No saved project selected.", "error");
      return;
    }
    if (!confirm("Delete this project from the database?")) return;

    try {
      const res = await fetch(withRoot(`/api/projects/${state.currentProjectId}`), { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Delete failed.");
      newProject();
      await refreshProjectList();
      showToast("Project deleted.", "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function transferProject() {
    if (!state.currentProjectId) {
      showToast("Save the project first before transferring.", "error");
      return;
    }
    const targetId = els.transferTargetSelect.value;
    if (!targetId) {
      showToast("Select a target project.", "error");
      return;
    }

    const payload = { replace: true, target_project_id: targetId };
    if (state.externalProjectId) {
      payload.target_external_project_id = state.externalProjectId;
    }

    try {
      const res = await fetch(withRoot(`/api/projects/${state.currentProjectId}/transfer`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Transfer failed.");
      await refreshProjectList();
      showToast("Diagram JSON sent — use export API or client canvas to render.", "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function copyCanvasExport() {
    const projectId = state.currentProjectId;
    if (!projectId) {
      showToast("Save the project first to get a canvas export id.", "error");
      return;
    }
    try {
      const res = await fetch(withRoot(`/api/projects/${projectId}/export`));
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Export failed.");
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      showToast("Canvas export JSON copied (genai-canvas-v1).", "success");
    } catch (err) {
      showToast(err.message || "Copy failed.", "error");
    }
  }

  async function generateDiagram() {
    const prompt = els.promptInput.value.trim();
    if (prompt.length < 3) {
      showToast("Describe your diagram (at least 3 characters).", "error");
      els.promptInput.focus();
      return;
    }

    state.lastPrompt = prompt;
    setGenerating(true);

    const payload = {
      prompt,
      diagram_type: state.diagramType,
    };
    if (state.isDirty && canvas.diagram.nodes.length) {
      payload.existing = canvas.getDiagram();
    }

    try {
      const res = await fetch(withRoot("/api/generate-diagram"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "Generation failed.");
      }

      applyDiagramToCanvas(data.diagram, "AI · Editable");
      showToast(
        `${data.diagram_type_label}: ${(data.diagram?.nodes || []).length} editable shapes from toolbox.`,
        "success",
      );
      canvas.scheduleFitToContent();
    } catch (err) {
      showToast(err.message || "Something went wrong.", "error");
    } finally {
      setGenerating(false);
      canvas.scheduleFitToContent();
    }
  }

  function loadSample() {
    const sample = SAMPLE_DIAGRAMS[state.diagramType];
    if (!sample) {
      showToast("No sample for this diagram type yet.", "error");
      return;
    }
    applyDiagramToCanvas(sample, "Sample");
    showToast("Sample loaded — every element is an editable toolbox shape.", "success");
  }

  function clearCanvas() {
    canvas.setDiagram({
      diagram_type: state.diagramType,
      title: "Untitled Diagram",
      nodes: [],
      edges: [],
    });
    els.diagramTitle.value = "Untitled Diagram";
    state.isDirty = false;
    els.canvasBadge.textContent = "Empty";
    els.canvasBadge.classList.remove("is-live");
  }

  function exportSvg() {
    const svg = canvas.exportSvg();
    const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.diagramType}-${Date.now()}.svg`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("SVG exported.", "success");
  }

  function exportJson() {
    const diagram = canvas.getDiagram();
    diagram.title = els.diagramTitle.value.trim() || diagram.title;
    const blob = new Blob([JSON.stringify(diagram, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.diagramType}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast("Diagram JSON exported.", "success");
  }

  function onDiagramTypeChange(value) {
    selectDiagramType(value, { clearCanvasOnChange: canvas.diagram.nodes.length > 0 });
  }

  els.diagramTypeSelect?.addEventListener("change", () => {
    onDiagramTypeChange(els.diagramTypeSelect.value);
  });

  els.diagramTypeSelectLeft?.addEventListener("change", () => {
    onDiagramTypeChange(els.diagramTypeSelectLeft.value);
  });

  els.promptInput.addEventListener("input", updateCharCount);
  els.generateBtn.addEventListener("click", generateDiagram);
  els.sampleBtn.addEventListener("click", loadSample);
  els.clearBtn.addEventListener("click", clearCanvas);
  els.deleteBtn.addEventListener("click", () => canvas.deleteSelection());
  els.duplicateBtn?.addEventListener("click", duplicateSelection);

  els.selectTool.addEventListener("click", () => setActiveTool("select"));
  els.panTool.addEventListener("click", () => setActiveTool("pan"));

  els.propLabel.addEventListener("input", () => canvas.updateSelectedLabel(els.propLabel.value));

  els.diagramTitle.addEventListener("change", () => {
    canvas.diagram.title = els.diagramTitle.value.trim() || "Untitled Diagram";
    state.isDirty = true;
  });

  els.zoomInBtn.addEventListener("click", () => {
    const r = canvas.viewport.getBoundingClientRect();
    canvas.zoomBy(1, r.left + r.width / 2, r.top + r.height / 2);
  });
  els.zoomOutBtn.addEventListener("click", () => {
    const r = canvas.viewport.getBoundingClientRect();
    canvas.zoomBy(-1, r.left + r.width / 2, r.top + r.height / 2);
  });
  els.fitBtn.addEventListener("click", () => canvas.fitToContent());
  els.exportSvgBtn.addEventListener("click", exportSvg);
  els.exportJsonBtn.addEventListener("click", exportJson);

  els.panelToggleLeft?.addEventListener("click", () => els.leftPanel.classList.toggle("is-collapsed"));
  els.panelToggleRight?.addEventListener("click", () => els.rightPanel.classList.toggle("is-collapsed"));

  els.tabAi?.addEventListener("click", () => switchSidebarTab("ai"));
  els.tabProject?.addEventListener("click", () => switchSidebarTab("project"));

  els.projectSelect?.addEventListener("change", () => {
    if (els.projectSelect.value) loadProject(els.projectSelect.value);
  });
  els.newProjectBtn?.addEventListener("click", newProject);
  els.saveProjectBtn?.addEventListener("click", saveProject);
  els.deleteProjectBtn?.addEventListener("click", deleteCurrentProject);
  els.transferProjectBtn?.addEventListener("click", transferProject);
  els.copyCanvasExportBtn?.addEventListener("click", copyCanvasExport);

  updateCharCount();
  checkHealth();
  selectDiagramType("use_case");
  canvas.resetView();
})();
