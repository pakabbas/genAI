import { DIAGRAM_TYPE_LABELS, SAMPLE_DIAGRAMS } from "./diagram-types.js";
import { DiagramCanvas } from "./canvas.js";

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
  };

  const els = {
    apiStatus: document.getElementById("apiStatus"),
    diagramTypeCards: document.querySelectorAll(".diagram-type-card"),
    toolboxGrid: document.getElementById("toolboxGrid"),
    toolboxHint: document.getElementById("toolboxHint"),
    canvasHost: document.getElementById("canvasHost"),
    diagramTitle: document.getElementById("diagramTitle"),
    promptInput: document.getElementById("promptInput"),
    charCount: document.getElementById("charCount"),
    generateBtn: document.getElementById("generateBtn"),
    sampleBtn: document.getElementById("sampleBtn"),
    clearBtn: document.getElementById("clearBtn"),
    deleteBtn: document.getElementById("deleteBtn"),
    selectTool: document.getElementById("selectTool"),
    panTool: document.getElementById("panTool"),
    connectHint: document.getElementById("connectHint"),
    propsPanel: document.getElementById("propsPanel"),
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

  function selectDiagramType(type) {
    state.diagramType = type;
    els.diagramTypeCards.forEach((card) => {
      const selected = card.dataset.type === type;
      card.classList.toggle("is-selected", selected);
      card.setAttribute("aria-checked", selected ? "true" : "false");
    });
    canvas.setDiagramType(type);
    loadToolbox(type);
  }

  async function loadToolbox(type) {
    try {
      const res = await fetch(withRoot(`/api/toolbox/${type}`));
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to load toolbox");
      state.toolbox = data.items;
      renderToolbox(data.items);
      els.toolboxHint.textContent = `Shapes for ${data.label}`;
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  function renderToolbox(items) {
    els.toolboxGrid.innerHTML = "";
    for (const item of items) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `toolbox-item toolbox-${item.kind}`;
      btn.dataset.shape = item.shape;
      btn.dataset.kind = item.kind;
      btn.title = item.label;
      btn.innerHTML = `
        <span class="toolbox-icon" aria-hidden="true">${toolboxIcon(item.shape)}</span>
        <span class="toolbox-label">${item.label}</span>
      `;
      btn.addEventListener("click", () => onToolboxClick(item));
      els.toolboxGrid.appendChild(btn);
    }
  }

  function toolboxIcon(shape) {
    const icons = {
      actor: "👤",
      use_case: "⬭",
      system_boundary: "▭",
      note: "📝",
      entity: "▣",
      attribute: "◯",
      relationship: "◇",
      lane: "≡",
      process: "▢",
      start: "●",
      end: "◉",
      decision: "◆",
      document: "📄",
      input: "▱",
      parallelogram: "▱",
      terminator: "⬭",
    };
    if (icons[shape]) return icons[shape];
    return shape.includes("edge") || ["association", "flow", "connector"].includes(shape) ? "↗" : "▢";
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
      els.connectHint.textContent = `Connect mode: click source then target (${item.label})`;
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

  async function checkHealth() {
    try {
      const res = await fetch(withRoot("/api/health"));
      const data = await res.json();
      if (data.api_key_configured) {
        els.apiStatus.classList.add("is-ready");
        els.apiStatus.innerHTML = '<span class="status-dot"></span> Gemini ready';
      } else {
        els.apiStatus.classList.add("is-error");
        els.apiStatus.innerHTML = '<span class="status-dot"></span> API key missing';
        showToast("Set GEMINI_API_KEY in .env to enable AI generation.", "error");
      }
    } catch {
      els.apiStatus.classList.add("is-error");
      els.apiStatus.innerHTML = '<span class="status-dot"></span> Offline';
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

      canvas.setDiagram(data.diagram);
      els.diagramTitle.value = data.diagram.title;
      state.isDirty = false;
      canvas.fitToContent();
      els.canvasBadge.textContent = "AI Generated";
      showToast(`${data.diagram_type_label} ready — drag nodes to refine.`, "success");
    } catch (err) {
      showToast(err.message || "Something went wrong.", "error");
    } finally {
      setGenerating(false);
    }
  }

  function loadSample() {
    const sample = SAMPLE_DIAGRAMS[state.diagramType];
    if (!sample) return;
    canvas.setDiagram(sample);
    els.diagramTitle.value = sample.title;
    state.isDirty = false;
    canvas.fitToContent();
    els.canvasBadge.textContent = "Sample";
    showToast("Sample diagram loaded. Connect Gemini to generate custom diagrams.", "success");
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

  els.diagramTypeCards.forEach((card) => {
    card.addEventListener("click", () => selectDiagramType(card.dataset.type));
  });

  els.promptInput.addEventListener("input", updateCharCount);
  els.generateBtn.addEventListener("click", generateDiagram);
  els.sampleBtn.addEventListener("click", loadSample);
  els.clearBtn.addEventListener("click", clearCanvas);
  els.deleteBtn.addEventListener("click", () => canvas.deleteSelection());

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

  els.panelToggleLeft?.addEventListener("click", () => {
    els.leftPanel.classList.toggle("is-collapsed");
  });
  els.panelToggleRight?.addEventListener("click", () => {
    els.rightPanel.classList.toggle("is-collapsed");
  });

  updateCharCount();
  checkHealth();
  selectDiagramType("use_case");
  canvas.resetView();
})();
