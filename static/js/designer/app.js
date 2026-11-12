// Cache-bust every module — app.js?v= alone is not enough; browsers cache bare imports.
import { DIAGRAM_TYPE_LABELS, SAMPLE_DIAGRAMS, setToolboxSizes } from "./diagram-types.js?v=2.7.9-left-dd";
import { DiagramCanvas } from "./canvas.js?v=2.7.9-left-dd";
import { applyNormalizeConfig, normalizeDiagram } from "./normalize.js?v=2.7.9-left-dd";

(() => {
  const APP_ROOT = document.querySelector('meta[name="app-root"]')?.content || "";

  function withRoot(path) {
    return `${APP_ROOT}${path}`;
  }

  function formatApiError(data, fallback = "Request failed.") {
    const detail = data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item.msg === "string") return item.msg;
          if (item && typeof item.message === "string") return item.message;
          return JSON.stringify(item);
        })
        .join("; ");
    }
    if (detail && typeof detail === "object") {
      return detail.message || JSON.stringify(detail);
    }
    return fallback;
  }

  let WELCOME_MESSAGE =
    "Tell me what diagram you need. I will ask questions if something important is unclear — then I'll shape a clear brief for your generation.";

  const state = {
    diagramType: "flowchart",
    toolbox: [],
    lastPrompt: "",
    originalPrompt: "",
    enhancedPrompt: "",
    briefReady: false,
    chatMessages: [],
    isChatting: false,
    isGenerating: false,
    isDirty: false,
    editedSinceAiLoad: false,
    suppressDirty: false,
    currentProjectId: null,
    externalProjectId: null,
    dbConnected: false,
    lastGenerationTrace: [],
    lastRecommendations: [],
    publicConfig: {},
    chatMessageChars: 8000,
    confirmPrompts: true,
    leaveWarning: true,
    welcomeTourEnabled: true,
  };

  function confirmAction(message) {
    if (!state.confirmPrompts) return true;
    return confirm(message);
  }

  function markDirty() {
    if (state.suppressDirty) return;
    state.isDirty = true;
    state.editedSinceAiLoad = true;
    if (els.canvasBadge) {
      els.canvasBadge.textContent = "Edited";
      els.canvasBadge.classList.add("is-live");
    }
  }

  function clearDirty() {
    state.isDirty = false;
  }

  /** Explicit canvas-edit phrasing only (never match domain verbs like rename/move in a brief). */
  function looksLikeEditRequest(text) {
    return /(?:\bon\s+this\s+diagram\b|\bthe\s+current\s+diagram\b|\bthis\s+canvas\b|\bedit\s+(the\s+|this\s+|current\s+)?diagram\b|\badd\s+.+\s+to\s+the\s+existing\b|\bmake\s+these\s+(boxes|shapes|nodes)\b)/i.test(
      String(text || ""),
    );
  }

  const els = {
    apiStatus: document.getElementById("apiStatus"),
    diagramTypeSelectLeft: document.getElementById("diagramTypeSelectLeft"),
    designerWorkspace: document.getElementById("designerWorkspace"),
    leftResizer: document.getElementById("leftResizer"),
    rightResizer: document.getElementById("rightResizer"),
    collapseLeftBtn: document.getElementById("collapseLeftBtn"),
    collapseRightBtn: document.getElementById("collapseRightBtn"),
    expandLeftBtn: document.getElementById("expandLeftBtn"),
    expandRightBtn: document.getElementById("expandRightBtn"),
    activeTypeLabel: document.getElementById("activeTypeLabel"),
    toolboxNodes: document.getElementById("toolboxNodes"),
    toolboxEdges: document.getElementById("toolboxEdges"),
    toolboxHint: document.getElementById("toolboxHint"),
    canvasHost: document.getElementById("canvasHost"),
    diagramTitle: document.getElementById("diagramTitle"),
    promptInput: document.getElementById("promptInput"),
    charCount: document.getElementById("charCount"),
    sendChatBtn: document.getElementById("sendChatBtn"),
    forceReadyBtn: document.getElementById("forceReadyBtn"),
    reqChatMessages: document.getElementById("reqChatMessages"),
    viewBriefBtn: document.getElementById("viewBriefBtn"),
    generateBtn: document.getElementById("generateBtn"),
    aiThinkingLogBtn: document.getElementById("aiThinkingLogBtn"),
    aiThinkingModal: document.getElementById("aiThinkingModal"),
    aiThinkingBody: document.getElementById("aiThinkingBody"),
    aiThinkingBackdrop: document.getElementById("aiThinkingBackdrop"),
    closeAiThinkingBtn: document.getElementById("closeAiThinkingBtn"),
    briefModal: document.getElementById("briefModal"),
    briefBackdrop: document.getElementById("briefBackdrop"),
    briefEditor: document.getElementById("briefEditor"),
    closeBriefBtn: document.getElementById("closeBriefBtn"),
    cancelBriefBtn: document.getElementById("cancelBriefBtn"),
    saveBriefBtn: document.getElementById("saveBriefBtn"),
    qcRecommendations: document.getElementById("qcRecommendations"),
    qcRecommendationsList: document.getElementById("qcRecommendationsList"),
    qcRecommendationsToggle: document.getElementById("qcRecommendationsToggle"),
    qcRecommendationsTitle: document.getElementById("qcRecommendationsTitle"),
    canvasLoadingTitle: document.getElementById("canvasLoadingTitle"),
    canvasLoadingSub: document.getElementById("canvasLoadingSub"),
    sampleBtn: document.getElementById("sampleBtn"),
    clearBtn: document.getElementById("clearBtn"),
    deleteBtn: document.getElementById("deleteBtn"),
    undoBtn: document.getElementById("undoBtn"),
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
    exportPngBtn: document.getElementById("exportPngBtn"),
    copyDiagramBtn: document.getElementById("copyDiagramBtn"),
    copyDiagramMenu: document.getElementById("copyDiagramMenu"),
    copyDiagramImageBtn: document.getElementById("copyDiagramImageBtn"),
    copyDiagramJsonBtn: document.getElementById("copyDiagramJsonBtn"),
    exportJsonBtn: document.getElementById("exportJsonBtn"),
    canvasBadge: document.getElementById("canvasBadge"),
    canvasLoading: document.getElementById("canvasLoading"),
    toastContainer: document.getElementById("toastContainer"),
    leftPanel: document.getElementById("leftPanel"),
    rightPanel: document.getElementById("rightPanel"),
    panelToggleLeft: document.getElementById("panelToggleLeft"),
    panelToggleRight: document.getElementById("panelToggleRight"),
    mobilePanelBackdrop: document.getElementById("mobilePanelBackdrop"),
    mobileDock: document.getElementById("mobileDock"),
    mobileDockLeft: document.getElementById("mobileDockLeft"),
    mobileDockCanvas: document.getElementById("mobileDockCanvas"),
    mobileDockRight: document.getElementById("mobileDockRight"),
    tabShapes: document.getElementById("tabShapes"),
    tabDrilldowns: document.getElementById("tabDrilldowns"),
    tabAi: document.getElementById("tabAi"),
    tabProject: document.getElementById("tabProject"),
    panelShapes: document.getElementById("panelShapes"),
    panelDrilldowns: document.getElementById("panelDrilldowns"),
    panelAi: document.getElementById("panelAi"),
    panelProject: document.getElementById("panelProject"),
    createDrillDownBtn: document.getElementById("createDrillDownBtn"),
    clearDrillDownHighlightBtn: document.getElementById("clearDrillDownHighlightBtn"),
    ddSelectionHint: document.getElementById("ddSelectionHint"),
    ddList: document.getElementById("ddList"),
    ddEmpty: document.getElementById("ddEmpty"),
    ddDetail: document.getElementById("ddDetail"),
    ddDetailTitle: document.getElementById("ddDetailTitle"),
    ddDetailMeta: document.getElementById("ddDetailMeta"),
    ddDetailDesc: document.getElementById("ddDetailDesc"),
    editDrillDownBtn: document.getElementById("editDrillDownBtn"),
    deleteDrillDownBtn: document.getElementById("deleteDrillDownBtn"),
    ctxCreateDrillDown: document.getElementById("ctxCreateDrillDown"),
    drillDownModal: document.getElementById("drillDownModal"),
    ddModalBackdrop: document.getElementById("ddModalBackdrop"),
    ddModalCloseBtn: document.getElementById("ddModalCloseBtn"),
    ddModalTitle: document.getElementById("ddModalTitle"),
    ddForm: document.getElementById("ddForm"),
    ddNameInput: document.getElementById("ddNameInput"),
    ddCategoryInput: document.getElementById("ddCategoryInput"),
    ddCategorySuggestions: document.getElementById("ddCategorySuggestions"),
    ddColorInput: document.getElementById("ddColorInput"),
    ddColorSwatches: document.getElementById("ddColorSwatches"),
    ddDescriptionInput: document.getElementById("ddDescriptionInput"),
    ddFormError: document.getElementById("ddFormError"),
    ddFormSaveBtn: document.getElementById("ddFormSaveBtn"),
    ddFormCancelBtn: document.getElementById("ddFormCancelBtn"),
    projectSelect: document.getElementById("projectSelect"),
    projectNameInput: document.getElementById("projectNameInput"),
    newProjectBtn: document.getElementById("newProjectBtn"),
    saveProjectBtn: document.getElementById("saveProjectBtn"),
    deleteProjectBtn: document.getElementById("deleteProjectBtn"),
    transferTargetSelect: document.getElementById("transferTargetSelect"),
    transferProjectBtn: document.getElementById("transferProjectBtn"),
    copyCanvasExportBtn: document.getElementById("copyCanvasExportBtn"),
    openApiDemoLink: document.getElementById("openApiDemoLink"),
    projectStatus: document.getElementById("projectStatus"),
    canvasContextMenu: document.getElementById("canvasContextMenu"),
    ctxRename: document.getElementById("ctxRename"),
    ctxDelete: document.getElementById("ctxDelete"),
    canvasInlineEditor: document.getElementById("canvasInlineEditor"),
    canvasInlineInput: document.getElementById("canvasInlineInput"),
    welcomeModal: document.getElementById("welcomeModal"),
    welcomeBackdrop: document.getElementById("welcomeBackdrop"),
    welcomeCloseBtn: document.getElementById("welcomeCloseBtn"),
    welcomeBackBtn: document.getElementById("welcomeBackBtn"),
    welcomeNextBtn: document.getElementById("welcomeNextBtn"),
    welcomeDontShow: document.getElementById("welcomeDontShow"),
    welcomeSlides: document.getElementById("welcomeSlides"),
    welcomeDots: document.getElementById("welcomeDots"),
    welcomeProgressFill: document.getElementById("welcomeProgressFill"),
    welcomeVisualStage: document.getElementById("welcomeVisualStage"),
    welcomeVisualCaption: document.getElementById("welcomeVisualCaption"),
    tourHelpBtn: document.getElementById("tourHelpBtn"),
  };

  let contextMenuTargetId = null;
  let ddFormMode = "create";
  let ddEditingId = null;
  const DD_PREF_KEY = "genai-drilldown-prefs-v1";
  const DD_DEFAULT_COLORS = ["#2563eb", "#16a34a", "#dc2626", "#ca8a04", "#9333ea", "#0891b2", "#ea580c", "#db2777"];
  const mobileMq = window.matchMedia("(max-width: 768px)");
  const WELCOME_STORAGE_KEY = "genai-drilldown-welcome-v1";
  const WELCOME_CAPTIONS = [
    "Drill Down Project",
    "AI or manual canvas",
    "Agent 0 · Analyst",
    "Generator agent",
    "QC Auditor",
  ];
  let welcomeSlideIndex = 0;
  let welcomeSlideCount = 5;

  function isMobileLayout() {
    return mobileMq.matches;
  }

  function updateMobileDock(active) {
    els.mobileDockLeft?.classList.toggle("is-active", active === "left");
    els.mobileDockCanvas?.classList.toggle("is-active", active === "canvas");
    els.mobileDockRight?.classList.toggle("is-active", active === "right");
  }

  function setMobileBackdrop(visible) {
    if (!els.mobilePanelBackdrop) return;
    els.mobilePanelBackdrop.hidden = !visible;
    els.mobilePanelBackdrop.setAttribute("aria-hidden", visible ? "false" : "true");
  }

  function closeMobilePanels() {
    if (!isMobileLayout()) return;
    els.leftPanel?.classList.add("is-collapsed");
    els.rightPanel?.classList.add("is-collapsed");
    setMobileBackdrop(false);
    updateMobileDock("canvas");
    canvas.scheduleFitToContent();
  }

  function openMobilePanel(side) {
    if (!isMobileLayout()) return;
    if (side === "left") {
      els.leftPanel?.classList.remove("is-collapsed");
      els.rightPanel?.classList.add("is-collapsed");
      updateMobileDock("left");
    } else if (side === "right") {
      els.rightPanel?.classList.remove("is-collapsed");
      els.leftPanel?.classList.add("is-collapsed");
      updateMobileDock("right");
    } else {
      closeMobilePanels();
      return;
    }
    setMobileBackdrop(true);
  }

  const PANEL_LAYOUT_KEY = "genai-panel-layout-v1";
  const PANEL_MIN = 200;
  const PANEL_MAX_LEFT = 480;
  const PANEL_MAX_RIGHT = 560;
  let panelLayout = {
    left: 280,
    right: 360,
    leftCollapsed: false,
    rightCollapsed: false,
  };

  function loadPanelLayout() {
    try {
      const raw = localStorage.getItem(PANEL_LAYOUT_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Number.isFinite(parsed.left)) panelLayout.left = Math.min(PANEL_MAX_LEFT, Math.max(PANEL_MIN, parsed.left));
      if (Number.isFinite(parsed.right)) panelLayout.right = Math.min(PANEL_MAX_RIGHT, Math.max(PANEL_MIN, parsed.right));
      panelLayout.leftCollapsed = Boolean(parsed.leftCollapsed);
      panelLayout.rightCollapsed = Boolean(parsed.rightCollapsed);
    } catch {
      /* ignore */
    }
  }

  function savePanelLayout() {
    try {
      localStorage.setItem(PANEL_LAYOUT_KEY, JSON.stringify(panelLayout));
    } catch {
      /* ignore */
    }
  }

  function applyPanelLayout() {
    const root = document.documentElement;
    root.style.setProperty("--panel-w", `${panelLayout.leftCollapsed ? 0 : panelLayout.left}px`);
    root.style.setProperty("--right-panel-w", `${panelLayout.rightCollapsed ? 0 : panelLayout.right}px`);
    els.designerWorkspace?.classList.toggle("left-collapsed", !isMobileLayout() && panelLayout.leftCollapsed);
    els.designerWorkspace?.classList.toggle("right-collapsed", !isMobileLayout() && panelLayout.rightCollapsed);
    els.leftPanel?.classList.toggle("is-collapsed", panelLayout.leftCollapsed);
    els.rightPanel?.classList.toggle("is-collapsed", panelLayout.rightCollapsed);
    if (els.expandLeftBtn) els.expandLeftBtn.hidden = isMobileLayout() || !panelLayout.leftCollapsed;
    if (els.expandRightBtn) els.expandRightBtn.hidden = isMobileLayout() || !panelLayout.rightCollapsed;
    if (els.leftResizer) els.leftResizer.hidden = isMobileLayout() || panelLayout.leftCollapsed;
    if (els.rightResizer) els.rightResizer.hidden = isMobileLayout() || panelLayout.rightCollapsed;
    canvas?.scheduleFitToContent?.();
  }

  function setPanelCollapsed(side, collapsed) {
    if (side === "left") panelLayout.leftCollapsed = collapsed;
    else panelLayout.rightCollapsed = collapsed;
    savePanelLayout();
    applyPanelLayout();
  }

  function togglePanel(side) {
    if (isMobileLayout()) {
      const panel = side === "left" ? els.leftPanel : els.rightPanel;
      const isOpen = panel && !panel.classList.contains("is-collapsed");
      if (isOpen) {
        closeMobilePanels();
      } else {
        openMobilePanel(side);
      }
      return;
    }
    if (side === "left") setPanelCollapsed("left", !panelLayout.leftCollapsed);
    else setPanelCollapsed("right", !panelLayout.rightCollapsed);
  }

  function bindPanelResizer(resizer, side) {
    if (!resizer) return;
    let startX = 0;
    let startWidth = 0;

    const onMove = (e) => {
      const clientX = e.touches?.[0]?.clientX ?? e.clientX;
      const delta = clientX - startX;
      let next = side === "left" ? startWidth + delta : startWidth - delta;
      const max = side === "left" ? PANEL_MAX_LEFT : PANEL_MAX_RIGHT;
      next = Math.min(max, Math.max(PANEL_MIN, next));
      if (side === "left") panelLayout.left = next;
      else panelLayout.right = next;
      applyPanelLayout();
    };

    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.removeEventListener("touchmove", onMove);
      document.removeEventListener("touchend", onUp);
      resizer.classList.remove("is-active");
      els.designerWorkspace?.classList.remove("is-resizing");
      savePanelLayout();
      canvas?.scheduleFitToContent?.();
    };

    const onDown = (e) => {
      if (isMobileLayout()) return;
      if (side === "left" && panelLayout.leftCollapsed) return;
      if (side === "right" && panelLayout.rightCollapsed) return;
      e.preventDefault();
      startX = e.touches?.[0]?.clientX ?? e.clientX;
      startWidth = side === "left" ? panelLayout.left : panelLayout.right;
      resizer.classList.add("is-active");
      els.designerWorkspace?.classList.add("is-resizing");
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      document.addEventListener("touchmove", onMove, { passive: false });
      document.addEventListener("touchend", onUp);
    };

    resizer.addEventListener("mousedown", onDown);
    resizer.addEventListener("touchstart", onDown, { passive: false });
    resizer.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      const step = e.key === "ArrowRight" ? 16 : -16;
      const delta = side === "left" ? step : -step;
      const max = side === "left" ? PANEL_MAX_LEFT : PANEL_MAX_RIGHT;
      const current = side === "left" ? panelLayout.left : panelLayout.right;
      const next = Math.min(max, Math.max(PANEL_MIN, current + delta));
      if (side === "left") panelLayout.left = next;
      else panelLayout.right = next;
      savePanelLayout();
      applyPanelLayout();
    });
  }

  function initMobileLayout() {
    if (isMobileLayout()) {
      els.leftPanel?.classList.add("is-collapsed");
      els.rightPanel?.classList.add("is-collapsed");
      panelLayout.leftCollapsed = true;
      panelLayout.rightCollapsed = true;
      updateMobileDock("canvas");
      setMobileBackdrop(false);
      els.designerWorkspace?.classList.remove("left-collapsed", "right-collapsed");
      if (els.expandLeftBtn) els.expandLeftBtn.hidden = true;
      if (els.expandRightBtn) els.expandRightBtn.hidden = true;
      if (els.leftResizer) els.leftResizer.hidden = true;
      if (els.rightResizer) els.rightResizer.hidden = true;
    } else {
      loadPanelLayout();
      applyPanelLayout();
      setMobileBackdrop(false);
    }
    canvas.scheduleFitToContent();
  }

  function hideContextMenu() {
    if (els.canvasContextMenu) els.canvasContextMenu.hidden = true;
    contextMenuTargetId = null;
  }

  function hideCopyDiagramMenu() {
    if (els.copyDiagramMenu) els.copyDiagramMenu.hidden = true;
    if (els.copyDiagramBtn) els.copyDiagramBtn.setAttribute("aria-expanded", "false");
  }

  function toggleCopyDiagramMenu() {
    if (!els.copyDiagramMenu || !els.copyDiagramBtn) return;
    const willOpen = els.copyDiagramMenu.hidden;
    hideContextMenu();
    els.copyDiagramMenu.hidden = !willOpen;
    els.copyDiagramBtn.setAttribute("aria-expanded", willOpen ? "true" : "false");
  }

  function hideInlineEditor() {
    if (els.canvasInlineEditor) els.canvasInlineEditor.hidden = true;
    if (els.canvasInlineInput) els.canvasInlineInput.dataset.itemId = "";
  }

  function startInlineRename(id) {
    const found = canvas.getItemById(id);
    if (!found) return;

    hideContextMenu();
    const { kind, item } = found;
    let wx;
    let wy;
    let width;
    let height;

    if (kind === "node") {
      wx = item.x;
      wy = item.y;
      width = item.width;
      height = item.height;
    } else {
      const from = canvas.diagram.nodes.find((n) => n.id === item.from);
      const to = canvas.diagram.nodes.find((n) => n.id === item.to);
      if (!from || !to) return;
      width = 160;
      height = 32;
      wx = (from.x + from.width / 2 + to.x + to.width / 2) / 2 - width / 2;
      wy = (from.y + from.height / 2 + to.y + to.height / 2) / 2 - height / 2;
    }

    const topLeft = canvas.worldToScreen(wx, wy);
    els.canvasInlineEditor.style.left = `${topLeft.x}px`;
    els.canvasInlineEditor.style.top = `${topLeft.y}px`;
    els.canvasInlineEditor.style.width = `${Math.max(width * canvas.view.scale, 96)}px`;
    els.canvasInlineInput.style.fontSize = `${Math.max(12, 12 * canvas.view.scale)}px`;
    els.canvasInlineInput.dataset.itemId = id;
    els.canvasInlineInput.value = item.label || "";
    els.canvasInlineEditor.hidden = false;
    els.canvasInlineInput.focus();
    els.canvasInlineInput.select();
  }

  function commitInlineRename() {
    const id = els.canvasInlineInput.dataset.itemId;
    if (!id) {
      hideInlineEditor();
      return;
    }
    canvas.renameItem(id, els.canvasInlineInput.value.trim());
    hideInlineEditor();
  }

  const canvas = new DiagramCanvas(els.canvasHost, {
    onChange: () => {
      markDirty();
      if (els.diagramTitle && els.diagramTitle.value !== canvas.diagram.title) {
        els.diagramTitle.value = canvas.diagram.title;
      }
      renderDrillDownSidebar();
    },
    onSelectionChange: (selection) => {
      updatePropertiesPanel(selection);
      updateDdSelectionHint();
    },
    onContextMenu: ({ id, clientX, clientY }) => {
      contextMenuTargetId = id;
      hideCopyDiagramMenu();
      const menu = els.canvasContextMenu;
      if (!menu) return;
      menu.style.left = `${clientX}px`;
      menu.style.top = `${clientY}px`;
      menu.hidden = false;
    },
    onRequestRename: ({ id }) => {
      startInlineRename(id);
    },
  });

  function switchLeftTab(tab) {
    const panels = [
      { tab: els.tabShapes, panel: els.panelShapes, id: "shapes" },
      { tab: els.tabDrilldowns, panel: els.panelDrilldowns, id: "drilldowns" },
    ];
    for (const item of panels) {
      const active = item.id === tab;
      item.tab?.classList.toggle("is-active", active);
      item.tab?.setAttribute("aria-selected", active ? "true" : "false");
      item.panel?.classList.toggle("is-active", active);
      if (item.panel) item.panel.hidden = !active;
    }
    if (tab === "drilldowns") {
      if (!isMobileLayout() && panelLayout.leftCollapsed) setPanelCollapsed("left", false);
      renderDrillDownSidebar();
    }
  }

  function switchSidebarTab(tab) {
    if (tab === "shapes" || tab === "drilldowns") {
      switchLeftTab(tab);
      return;
    }
    const panels = [
      { tab: els.tabAi, panel: els.panelAi, id: "ai" },
      { tab: els.tabProject, panel: els.panelProject, id: "project" },
    ];
    for (const item of panels) {
      const active = item.id === tab;
      item.tab?.classList.toggle("is-active", active);
      item.tab?.setAttribute("aria-selected", active ? "true" : "false");
      item.panel?.classList.toggle("is-active", active);
      if (item.panel) item.panel.hidden = !active;
    }
  }

  function loadDdPrefs() {
    try {
      const raw = localStorage.getItem(DD_PREF_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return {
        categories: Array.isArray(parsed.categories) ? parsed.categories.map(String) : [],
        colors: Array.isArray(parsed.colors) ? parsed.colors.map(String) : [],
      };
    } catch {
      return { categories: [], colors: [] };
    }
  }

  function saveDdPrefs(prefs) {
    try {
      localStorage.setItem(
        DD_PREF_KEY,
        JSON.stringify({
          categories: (prefs.categories || []).slice(0, 24),
          colors: (prefs.colors || []).slice(0, 16),
        }),
      );
    } catch {
      /* ignore */
    }
  }

  function rememberDdPrefs(category, color) {
    const prefs = loadDdPrefs();
    const cat = String(category || "").trim();
    const col = String(color || "").trim();
    if (cat) prefs.categories = [cat, ...prefs.categories.filter((c) => c !== cat)];
    if (col) prefs.colors = [col, ...prefs.colors.filter((c) => c !== col)];
    saveDdPrefs(prefs);
  }

  function updateDdSelectionHint() {
    const sel = canvas.getSelection();
    const count = sel.nodes.length + sel.edges.length;
    if (els.ddSelectionHint) {
      els.ddSelectionHint.textContent = count
        ? `${count} item${count === 1 ? "" : "s"} selected — ready to create a Drill Down.`
        : "Select one or more shapes or lines (Ctrl/Shift+click, or drag a box).";
    }
    if (els.createDrillDownBtn) els.createDrillDownBtn.disabled = count === 0;
  }

  function renderDrillDownSidebar() {
    const list = canvas.getDrilldowns();
    const activeId = canvas.activeDrillDownId;
    if (els.ddEmpty) els.ddEmpty.hidden = list.length > 0;
    if (!els.ddList) return;
    els.ddList.innerHTML = "";

    const groups = new Map();
    for (const dd of list) {
      const key = dd.category || "Uncategorized";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(dd);
    }

    for (const [category, items] of groups) {
      const group = document.createElement("div");
      group.className = "dd-category-group";
      const label = document.createElement("p");
      label.className = "dd-category-label";
      label.textContent = category;
      group.appendChild(label);
      for (const dd of items) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `dd-item${dd.id === activeId ? " is-active" : ""}`;
        btn.dataset.ddId = dd.id;
        const count = (dd.nodeIds?.length || 0) + (dd.edgeIds?.length || 0);
        btn.innerHTML = `
          <span class="dd-item-swatch" style="background:${escapeAttr(dd.color || "#2563eb")}"></span>
          <span class="dd-item-body">
            <span class="dd-item-name">${escapeHtml(dd.name || "Untitled")}</span>
            <span class="dd-item-meta">${count} linked item${count === 1 ? "" : "s"}</span>
          </span>`;
        btn.addEventListener("click", () => activateDrillDown(dd.id));
        group.appendChild(btn);
      }
      els.ddList.appendChild(group);
    }

    const active = list.find((d) => d.id === activeId);
    if (!active) {
      if (els.ddDetail) els.ddDetail.hidden = true;
      return;
    }
    if (els.ddDetail) els.ddDetail.hidden = false;
    if (els.ddDetailTitle) els.ddDetailTitle.textContent = active.name || "Untitled";
    if (els.ddDetailMeta) {
      const count = (active.nodeIds?.length || 0) + (active.edgeIds?.length || 0);
      els.ddDetailMeta.textContent = `${active.category || "Uncategorized"} · ${count} linked · ${active.color}`;
    }
    if (els.ddDetailDesc) {
      els.ddDetailDesc.textContent = active.description || "No description.";
    }
  }

  function activateDrillDown(id) {
    const dd = canvas.getDrilldowns().find((item) => item.id === id);
    if (!dd) return;
    canvas.setDrillDownHighlight(dd);
    renderDrillDownSidebar();
    switchSidebarTab("drilldowns");
  }

  function openDrillDownModal(mode = "create", dd = null) {
    ddFormMode = mode;
    ddEditingId = dd?.id || null;
    if (els.ddModalTitle) els.ddModalTitle.textContent = mode === "edit" ? "Edit Drill Down" : "Create Drill Down";
    if (els.ddFormSaveBtn) els.ddFormSaveBtn.textContent = mode === "edit" ? "Save changes" : "Add Drill Down";
    if (els.ddFormError) {
      els.ddFormError.hidden = true;
      els.ddFormError.textContent = "";
    }
    const prefs = loadDdPrefs();
    if (els.ddCategorySuggestions) {
      els.ddCategorySuggestions.innerHTML = prefs.categories
        .map((c) => `<option value="${escapeAttr(c)}"></option>`)
        .join("");
    }
    const colors = [...new Set([...prefs.colors, ...DD_DEFAULT_COLORS])].slice(0, 12);
    if (els.ddColorSwatches) {
      els.ddColorSwatches.innerHTML = colors
        .map(
          (c) =>
            `<button type="button" class="dd-swatch" data-color="${escapeAttr(c)}" style="background:${escapeAttr(c)}" title="${escapeAttr(c)}" aria-label="Use ${escapeAttr(c)}"></button>`,
        )
        .join("");
      els.ddColorSwatches.querySelectorAll(".dd-swatch").forEach((btn) => {
        btn.addEventListener("click", () => {
          if (els.ddColorInput) els.ddColorInput.value = btn.dataset.color;
          syncDdSwatchActive();
        });
      });
    }
    if (els.ddNameInput) els.ddNameInput.value = dd?.name || "";
    if (els.ddCategoryInput) els.ddCategoryInput.value = dd?.category || prefs.categories[0] || "";
    if (els.ddColorInput) els.ddColorInput.value = dd?.color || prefs.colors[0] || DD_DEFAULT_COLORS[0];
    if (els.ddDescriptionInput) els.ddDescriptionInput.value = dd?.description || "";
    syncDdSwatchActive();
    if (els.drillDownModal) els.drillDownModal.hidden = false;
    els.ddNameInput?.focus();
  }

  function syncDdSwatchActive() {
    const current = els.ddColorInput?.value?.toLowerCase();
    els.ddColorSwatches?.querySelectorAll(".dd-swatch").forEach((btn) => {
      btn.classList.toggle("is-active", (btn.dataset.color || "").toLowerCase() === current);
    });
  }

  function closeDrillDownModal() {
    if (els.drillDownModal) els.drillDownModal.hidden = true;
    ddEditingId = null;
  }

  function beginCreateDrillDown() {
    const sel = canvas.getSelection();
    if (!sel.nodes.length && !sel.edges.length) {
      showToast("Select shapes or lines first.", "error");
      return;
    }
    hideContextMenu();
    openDrillDownModal("create");
  }

  function submitDrillDownForm(e) {
    e?.preventDefault?.();
    const name = (els.ddNameInput?.value || "").trim();
    const category = (els.ddCategoryInput?.value || "").trim();
    const color = (els.ddColorInput?.value || "#2563eb").trim();
    const description = els.ddDescriptionInput?.value || "";
    if (!name) {
      if (els.ddFormError) {
        els.ddFormError.hidden = false;
        els.ddFormError.textContent = "Enter a name for this Drill Down.";
      }
      return;
    }

    if (ddFormMode === "edit" && ddEditingId) {
      const updated = canvas.updateDrillDown(ddEditingId, { name, category, color, description });
      if (!updated) {
        showToast("Could not update Drill Down.", "error");
        return;
      }
      rememberDdPrefs(category, color);
      closeDrillDownModal();
      renderDrillDownSidebar();
      showToast("Drill Down updated.", "success");
      return;
    }

    const sel = canvas.getSelection();
    if (!sel.nodes.length && !sel.edges.length) {
      if (els.ddFormError) {
        els.ddFormError.hidden = false;
        els.ddFormError.textContent = "Select shapes or lines on the canvas first.";
      }
      return;
    }
    const created = canvas.addDrillDown({
      name,
      category,
      color,
      description,
      nodeIds: sel.nodes.map((n) => n.id),
      edgeIds: sel.edges.map((ed) => ed.id),
    });
    rememberDdPrefs(category, color);
    closeDrillDownModal();
    canvas.setDrillDownHighlight(created);
    switchSidebarTab("drilldowns");
    renderDrillDownSidebar();
    showToast("Drill Down created.", "success");
  }


  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast${type === "error" ? " is-error" : type === "success" ? " is-success" : ""}`;
    toast.textContent = message;
    els.toastContainer.appendChild(toast);
    setTimeout(() => toast.remove(), 4200);
  }

  function setGenerating(isGenerating, stageTitle = "Creating your diagram…", stageSub = "") {
    state.isGenerating = isGenerating;
    updateActionButtons();
    els.generateBtn.classList.toggle("is-loading", isGenerating);
    const spinner = els.generateBtn.querySelector(".btn-spinner");
    if (spinner) spinner.hidden = !isGenerating;
    els.canvasLoading.hidden = !isGenerating;
    if (els.canvasBadge) els.canvasBadge.classList.toggle("is-loading", isGenerating);
    if (els.canvasLoadingTitle) els.canvasLoadingTitle.textContent = stageTitle;
    if (els.canvasLoadingSub) {
      els.canvasLoadingSub.textContent = stageSub || "Understanding your requirements…";
    }
    // Prevent mid-generation type switches from dropping the result under the wrong type.
    if (els.diagramTypeSelectLeft) els.diagramTypeSelectLeft.disabled = Boolean(isGenerating);
  }

  function setChatting(isChatting) {
    state.isChatting = isChatting;
    updateActionButtons();
    if (els.sendChatBtn) {
      els.sendChatBtn.classList.toggle("is-loading", isChatting);
      const spinner = els.sendChatBtn.querySelector(".btn-spinner");
      if (spinner) spinner.hidden = !isChatting;
    }
  }

  function updateActionButtons() {
    const busy = state.isGenerating || state.isChatting;
    if (els.sendChatBtn) els.sendChatBtn.disabled = busy;
    if (els.forceReadyBtn) {
      els.forceReadyBtn.disabled = busy || !state.chatMessages.some((m) => m.role === "user");
    }
    if (els.viewBriefBtn) {
      els.viewBriefBtn.disabled = busy || !state.briefReady || !state.enhancedPrompt;
    }
    if (els.generateBtn) {
      els.generateBtn.disabled = busy || !state.briefReady || !state.enhancedPrompt;
      els.generateBtn.title = state.briefReady
        ? "Generate diagram from the brief"
        : "Chat until the brief is ready, or use Proceed";
    }
    if (els.promptInput) els.promptInput.disabled = busy;
  }

  // 2.7.9: the loading overlay only ever shows these fixed, friendly stage labels —
  // never raw trace text (QC findings, coverage notes, errors stay in the AI thinking log).
  const STAGE_LABELS = {
    understanding: "Understanding your requirements…",
    planning: "Planning the flow…",
    drawing: "Drawing the diagram…",
    checking: "Checking quality…",
    polishing: "Polishing the diagram…",
    layout: "Polishing layout…",
    done: "Done",
  };
  const PHASE_STAGE = {
    start: "understanding",
    brief_ready: "understanding",
    new_diagram: "planning",
    edit_mode: "planning",
    process_plan: "planning",
    process_plan_ready: "planning",
    process_plan_skip: "planning",
    draft: "drawing",
    brief_advisory: "drawing",
    brief_validate: "polishing",
    draft_complete: "drawing",
    coverage_check: "checking",
    coverage_advisory: "checking",
    review: "checking",
    verdict: "checking",
    skipped: "checking",
    revision_handoff: "polishing",
    revision: "polishing",
    revision_complete: "polishing",
    coverage_recheck: "polishing",
    re_review: "polishing",
    final_verdict: "polishing",
    revision_skipped: "layout",
    layout: "layout",
    complete: "done",
  };

  function stageLabelFor(entry) {
    const key = entry?.stage && STAGE_LABELS[entry.stage] ? entry.stage : PHASE_STAGE[entry?.phase];
    return STAGE_LABELS[key] || null;
  }

  function agentLabel(agent) {
    const map = {
      requirements_analyst: "Requirements Analyst",
      generator: "Diagram Generator",
      qc_auditor: "QC Auditor",
      system: "Pipeline",
    };
    return map[agent] || agent;
  }

  function agentClass(agent) {
    if (agent === "requirements_analyst") return "is-requirements";
    if (agent === "generator") return "is-generator";
    if (agent === "qc_auditor") return "is-qc";
    return "is-system";
  }

  function renderChatMessages() {
    if (!els.reqChatMessages) return;
    els.reqChatMessages.innerHTML = "";
    for (const msg of state.chatMessages) {
      const bubble = document.createElement("div");
      bubble.className = `req-chat-bubble ${msg.role === "user" ? "is-user" : "is-assistant"}`;
      const who = msg.role === "user" ? "You" : "Assistant";
      bubble.innerHTML = `<span class="req-chat-bubble-meta">${who}</span>${escapeHtml(msg.content)}`;
      bubble.setAttribute("aria-label", who);
      els.reqChatMessages.appendChild(bubble);
    }
    els.reqChatMessages.scrollTop = els.reqChatMessages.scrollHeight;
  }

  function setBriefReady(ready, enhancedPrompt = "") {
    state.briefReady = Boolean(ready);
    state.enhancedPrompt = ready ? String(enhancedPrompt || "").trim() : "";
    if (!ready) closeBriefModal();
    updateActionButtons();
  }

  function openBriefModal() {
    if (!state.briefReady || !state.enhancedPrompt) {
      showToast("No brief yet — chat until it is ready, or click Proceed.", "info");
      return;
    }
    if (els.briefEditor) els.briefEditor.value = state.enhancedPrompt;
    if (els.briefModal) els.briefModal.hidden = false;
    els.briefEditor?.focus();
  }

  function closeBriefModal() {
    if (els.briefModal) els.briefModal.hidden = true;
  }

  function welcomeShouldShow() {
    if (!state.welcomeTourEnabled) return false;
    try {
      return localStorage.getItem(WELCOME_STORAGE_KEY) !== "1";
    } catch {
      return true;
    }
  }

  function applyPublicConfig(cfg) {
    state.publicConfig = cfg || {};
    state.chatMessageChars = Number(cfg["limits.chat_message_chars"]) || 8000;
    state.confirmPrompts = cfg["ux.confirm_prompts"] !== false;
    state.leaveWarning = cfg["ux.leave_warning"] !== false;
    state.welcomeTourEnabled = cfg["ux.welcome_tour_enabled"] !== false;
    if (typeof cfg["ux.welcome_message"] === "string" && cfg["ux.welcome_message"].trim()) {
      WELCOME_MESSAGE = cfg["ux.welcome_message"].trim();
    }
    const defaultType = cfg["diagrams.default_type"] || "flowchart";
    if (defaultType) state.diagramType = defaultType;

    if (els.promptInput) els.promptInput.maxLength = state.chatMessageChars;
    canvas.applyPublicConfig(cfg);
    applyNormalizeConfig(cfg);

    if (cfg["theme.accent"]) {
      document.documentElement.style.setProperty("--accent", cfg["theme.accent"]);
    }
    if (cfg["theme.canvas_bg"]) {
      document.documentElement.style.setProperty("--canvas-bg", cfg["theme.canvas_bg"]);
    }
    if (els.exportSvgBtn) els.exportSvgBtn.hidden = cfg["export.svg_enabled"] === false;
    if (els.exportPngBtn) els.exportPngBtn.hidden = cfg["export.svg_enabled"] === false;
    if (els.exportJsonBtn) els.exportJsonBtn.hidden = cfg["export.json_enabled"] === false;

    const labels = cfg["diagrams.type_labels"];
    if (labels && typeof labels === "object") {
      Object.assign(DIAGRAM_TYPE_LABELS, labels);
    }
    filterDiagramTypeSelects(cfg["diagrams.enabled_types"]);
    if (typeof canvas.rebuildGrid === "function") canvas.rebuildGrid();
    updateCharCount();
  }

  function filterDiagramTypeSelects(enabled) {
    const allowed = Array.isArray(enabled) && enabled.length ? new Set(enabled) : null;
    const sel = els.diagramTypeSelectLeft;
    if (!sel) return;
    Array.from(sel.options).forEach((opt) => {
      opt.hidden = Boolean(allowed && !allowed.has(opt.value));
    });
    if (allowed && !allowed.has(sel.value)) {
      const first = Array.from(sel.options).find((o) => !o.hidden);
      if (first) sel.value = first.value;
    }
  }

  async function loadPublicConfig() {
    try {
      const res = await fetch(withRoot("/api/config/public"));
      if (!res.ok) return;
      const data = await res.json();
      applyPublicConfig(data);
    } catch {
      /* keep code defaults */
    }
  }

  function persistWelcomeDismiss() {
    if (!els.welcomeDontShow?.checked) return;
    try {
      localStorage.setItem(WELCOME_STORAGE_KEY, "1");
    } catch {
      /* ignore quota / private mode */
    }
  }

  function buildWelcomeDots() {
    if (!els.welcomeDots) return;
    els.welcomeDots.innerHTML = "";
    for (let i = 0; i < welcomeSlideCount; i += 1) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "welcome-dot";
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-label", `Go to slide ${i + 1}`);
      btn.addEventListener("click", () => setWelcomeSlide(i));
      els.welcomeDots.appendChild(btn);
    }
  }

  function setWelcomeSlide(index) {
    const slides = els.welcomeSlides
      ? Array.from(els.welcomeSlides.querySelectorAll(".welcome-slide"))
      : [];
    welcomeSlideCount = slides.length || 5;
    welcomeSlideIndex = Math.max(0, Math.min(index, welcomeSlideCount - 1));
    const isLast = welcomeSlideIndex >= welcomeSlideCount - 1;

    slides.forEach((slide, i) => {
      const active = i === welcomeSlideIndex;
      slide.hidden = !active;
      slide.classList.toggle("is-active", active);
      if (active) {
        slide.style.animation = "none";
        void slide.offsetHeight;
        slide.style.animation = "";
      }
    });

    if (els.welcomeDots) {
      Array.from(els.welcomeDots.children).forEach((dot, i) => {
        dot.classList.toggle("is-active", i === welcomeSlideIndex);
        dot.classList.toggle("is-done", i < welcomeSlideIndex);
        dot.setAttribute("aria-selected", i === welcomeSlideIndex ? "true" : "false");
      });
    }

    if (els.welcomeProgressFill) {
      const pct = ((welcomeSlideIndex + 1) / welcomeSlideCount) * 100;
      els.welcomeProgressFill.style.width = `${pct}%`;
    }

    if (els.welcomeVisualStage) {
      els.welcomeVisualStage.dataset.slide = String(welcomeSlideIndex);
      Array.from(els.welcomeVisualStage.querySelectorAll(".welcome-art")).forEach((art, i) => {
        art.classList.toggle("is-active", i === welcomeSlideIndex);
      });
    }

    if (els.welcomeVisualCaption) {
      els.welcomeVisualCaption.textContent = WELCOME_CAPTIONS[welcomeSlideIndex] || "Drill Down Project";
    }

    const activeTitle = slides[welcomeSlideIndex]?.querySelector(".welcome-title");
    if (activeTitle) {
      slides.forEach((s, i) => {
        const t = s.querySelector(".welcome-title");
        if (!t) return;
        if (i === welcomeSlideIndex) t.id = "welcomeSlideTitle";
        else t.removeAttribute("id");
      });
    }

    if (els.welcomeBackBtn) els.welcomeBackBtn.disabled = welcomeSlideIndex === 0;
    if (els.welcomeNextBtn) {
      els.welcomeNextBtn.textContent = isLast ? "Get started" : "Next";
    }
  }

  function openWelcomeModal() {
    if (!els.welcomeModal) return;
    buildWelcomeDots();
    setWelcomeSlide(0);
    if (els.welcomeDontShow) els.welcomeDontShow.checked = false;
    els.welcomeModal.hidden = false;
    els.welcomeNextBtn?.focus();
  }

  function closeWelcomeModal() {
    persistWelcomeDismiss();
    if (els.welcomeModal) els.welcomeModal.hidden = true;
  }

  function welcomeNext() {
    if (welcomeSlideIndex >= welcomeSlideCount - 1) {
      closeWelcomeModal();
      return;
    }
    setWelcomeSlide(welcomeSlideIndex + 1);
  }

  function welcomeBack() {
    if (welcomeSlideIndex <= 0) return;
    setWelcomeSlide(welcomeSlideIndex - 1);
  }

  function saveBriefFromModal() {
    const next = (els.briefEditor?.value || "").trim();
    if (next.length < 3) {
      showToast("Brief is too short.", "error");
      els.briefEditor?.focus();
      return;
    }
    state.enhancedPrompt = next;
    state.briefReady = true;
    updateActionButtons();
    closeBriefModal();
    showToast("Brief saved.", "success");
  }

  function resetRequirementsChat({ quiet = false } = {}) {
    state.chatMessages = [{ role: "assistant", content: WELCOME_MESSAGE }];
    state.originalPrompt = "";
    state.lastPrompt = "";
    setBriefReady(false);
    showRecommendations([]);
    renderChatMessages();
    if (els.promptInput) {
      els.promptInput.value = "";
      updateCharCount();
    }
    if (!quiet) showToast("New chat started.", "info");
  }

  async function sendRequirementsMessage({ forceReady = false } = {}) {
    try {
      const field = document.getElementById("promptInput") || els.promptInput;
      const text = String(field?.value || "").trim();
      if (!forceReady && text.length < 3) {
        showToast("Describe your diagram (at least 3 characters).", "error");
        field?.focus();
        return;
      }
      if (state.isChatting || state.isGenerating) return;

      if (text) {
        state.chatMessages.push({ role: "user", content: text });
        if (!state.originalPrompt) state.originalPrompt = text;
        else state.originalPrompt = `${state.originalPrompt}\n${text}`.slice(0, state.chatMessageChars);
        if (els.promptInput) els.promptInput.value = "";
        updateCharCount();
        renderChatMessages();
      } else if (forceReady && !state.chatMessages.some((m) => m.role === "user")) {
        showToast("Describe your diagram before proceeding.", "error");
        return;
      }

      const apiMessages = state.chatMessages.filter(
        (m) => !(m.role === "assistant" && m.content === WELCOME_MESSAGE),
      );
      if (!apiMessages.length) {
        showToast("Describe your diagram first.", "error");
        return;
      }

      setChatting(true);
      try {
        const res = await fetch(withRoot("/api/requirements-chat"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            diagram_type: state.diagramType,
            messages: apiMessages,
            force_ready: forceReady,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(formatApiError(data, "Requirements chat failed."));
        }

        const reply = (data.assistant_message || "").trim() || "Got it.";
        state.chatMessages.push({ role: "assistant", content: reply });
        renderChatMessages();

        if (data.status === "rejected") {
          setBriefReady(false);
          showToast(reply, "error");
          return;
        }

        const enhanced = (data.enhanced_prompt || "").trim();
        if (data.status === "ready" && enhanced) {
          setBriefReady(true, enhanced);
          showToast("Brief ready — View Brief or Generate Now.", "success");
        } else {
          setBriefReady(false);
          showToast("Answer the Analyst’s question, then continue.", "info");
        }
      } finally {
        setChatting(false);
      }
    } catch (err) {
      setChatting(false);
      showToast(err.message || "Chat failed.", "error");
    }
  }

  function renderThinkingLog(trace) {
    if (!els.aiThinkingBody) return;
    els.aiThinkingBody.innerHTML = "";
    if (!trace?.length) {
      els.aiThinkingBody.innerHTML = '<p class="ai-thinking-empty">No log entries yet. Run Generate with AI first.</p>';
      return;
    }
    for (const entry of trace) {
      const item = document.createElement("article");
      item.className = `ai-thinking-entry ${agentClass(entry.agent)}`;
      const time = entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : "";
      item.innerHTML = `
        <div class="ai-thinking-entry-head">
          <span class="ai-thinking-agent">${agentLabel(entry.agent)}</span>
          <span class="ai-thinking-phase">${entry.phase.replace(/_/g, " ")}</span>
          ${time ? `<span class="ai-thinking-time">${time}</span>` : ""}
        </div>
        <p class="ai-thinking-message">${escapeHtml(entry.message)}</p>
        ${entry.detail ? `<pre class="ai-thinking-detail">${escapeHtml(entry.detail)}</pre>` : ""}
      `;
      els.aiThinkingBody.appendChild(item);
    }
    els.aiThinkingBody.scrollTop = els.aiThinkingBody.scrollHeight;
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function escapeAttr(text) {
    return escapeHtml(text).replace(/"/g, "&quot;");
  }

  // 2.7.9: internal pipeline wording never reaches the user (item 10).
  const INTERNAL_WORDING = /\b(qc|revision|revised|missing|corrupt\w*|coverage|gaps?|error|failed|required|duplicated)\b/i;

  function setRecommendationsExpanded(expanded) {
    if (!els.qcRecommendations || !els.qcRecommendationsList) return;
    els.qcRecommendations.classList.toggle("is-expanded", expanded);
    els.qcRecommendationsList.hidden = !expanded;
    els.qcRecommendationsToggle?.setAttribute("aria-expanded", expanded ? "true" : "false");
  }

  /** Suggestions row: collapsed by default; click / Enter / Space toggles; capped height when open. */
  function showRecommendations(recommendations) {
    if (!els.qcRecommendations || !els.qcRecommendationsList) return;
    els.qcRecommendationsList.innerHTML = "";
    const items = (recommendations || [])
      .map((r) => String(r || "").trim())
      .filter((r) => r && !INTERNAL_WORDING.test(r));
    if (!items.length) {
      els.qcRecommendations.hidden = true;
      setRecommendationsExpanded(false);
      return;
    }
    for (const rec of items) {
      const li = document.createElement("li");
      li.textContent = rec;
      els.qcRecommendationsList.appendChild(li);
    }
    if (els.qcRecommendationsTitle) els.qcRecommendationsTitle.textContent = `Suggestions (${items.length})`;
    setRecommendationsExpanded(false);
    els.qcRecommendations.hidden = false;
  }

  function openThinkingLog() {
    renderThinkingLog(state.lastGenerationTrace);
    if (els.aiThinkingModal) els.aiThinkingModal.hidden = false;
  }

  function closeThinkingLog() {
    if (els.aiThinkingModal) els.aiThinkingModal.hidden = true;
  }

  function updateCharCount() {
    if (!els.charCount || !els.promptInput) return;
    els.charCount.textContent = `${els.promptInput.value.length} / ${state.chatMessageChars}`;
  }

  function applyDiagramToCanvas(diagram, badge = "Ready") {
    state.suppressDirty = true;
    try {
      // Prefer the UI-selected type so sequence layout always engages
      const payload = {
        ...diagram,
        diagram_type: state.diagramType || diagram.diagram_type,
      };
      const normalized = normalizeDiagram(payload, state.toolbox);
      canvas.setDiagramType(payload.diagram_type);
      canvas.loadNormalizedDiagram(normalized);
      if (els.diagramTitle) els.diagramTitle.value = normalized.title;
      clearDirty();
      state.editedSinceAiLoad = false;
      canvas.scheduleFitToContent();
      // 2.7.9: the toolbar status badge was removed (it wrapped the toolbar).
      if (els.canvasBadge) {
        els.canvasBadge.textContent = badge;
        els.canvasBadge.classList.add("is-live");
      }
    } finally {
      state.suppressDirty = false;
    }
  }

  function selectDiagramType(type, { clearCanvasOnChange = false } = {}) {
    const alreadySelected = state.diagramType === type && !clearCanvasOnChange;
    if (alreadySelected && state.toolbox.length > 0) {
      return;
    }
    state.diagramType = type;
    if (els.diagramTypeSelectLeft) els.diagramTypeSelectLeft.value = type;
    if (els.activeTypeLabel) {
      els.activeTypeLabel.textContent = DIAGRAM_TYPE_LABELS[type] || type;
    }
    canvas.setDiagramType(type);
    // Clear stale shapes immediately so previous type is never clickable
    state.toolbox = [];
    renderToolbox([]);
    if (els.toolboxHint) els.toolboxHint.textContent = "Loading shape library…";
    if (els.toolboxNodes) {
      els.toolboxNodes.innerHTML =
        '<p class="block-subtitle" style="margin:0;grid-column:1/-1">Loading shapes…</p>';
    }
    if (els.toolboxEdges) els.toolboxEdges.innerHTML = "";

    loadToolbox(type).then(() => {
      if (clearCanvasOnChange) {
        clearCanvas({ skipConfirm: true });
      }
    });
  }

  async function loadToolbox(type) {
    try {
      const res = await fetch(withRoot(`/api/toolbox/${type}`));
      const data = await res.json();
      if (!res.ok) throw new Error(formatApiError(data, "Failed to load toolbox"));
      if (state.diagramType !== type) return; // stale response
      state.toolbox = data.items;
      setToolboxSizes(data.items);
      renderToolbox(data.items);
      if (els.toolboxHint) els.toolboxHint.textContent = data.label;
    } catch (err) {
      showToast(err.message, "error");
      if (els.toolboxHint) els.toolboxHint.textContent = "Failed to load shapes";
    }
  }

  const TOOLBOX_DRAG_MIME = "application/x-genai-shape";
  let toolboxDragItem = null;
  let suppressToolboxClick = false;
  let toolboxTouchDrag = null;

  function serializeToolboxItem(item) {
    return JSON.stringify({
      kind: item.kind,
      shape: item.shape,
      label: item.label,
      default_width: item.default_width,
      default_height: item.default_height,
    });
  }

  function parseToolboxItem(raw) {
    if (!raw) return null;
    try {
      const item = JSON.parse(raw);
      if (item && item.kind === "node" && item.shape) return item;
    } catch (_) {
      /* ignore non-JSON drops */
    }
    return null;
  }

  function itemFromDragEvent(e) {
    const dt = e.dataTransfer;
    if (dt) {
      const raw = dt.getData(TOOLBOX_DRAG_MIME) || dt.getData("text/plain");
      const parsed = parseToolboxItem(raw);
      if (parsed) return parsed;
    }
    return toolboxDragItem;
  }

  function isPointInCanvas(clientX, clientY) {
    const rect = canvas.viewport.getBoundingClientRect();
    return clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom;
  }

  function clearShapeDragChrome() {
    canvas.viewport.classList.remove("is-shape-drag-over");
    if (typeof canvas.clearDropTargetEdge === "function") canvas.clearDropTargetEdge();
  }

  function dropHitBox(item, clientX, clientY) {
    const world = canvas._screenToWorld(clientX, clientY);
    const dw = Number(item?.default_width) || 120;
    const dh = Number(item?.default_height) || 60;
    return { x: world.x - dw / 2, y: world.y - dh / 2, width: dw, height: dh };
  }

  function updateConnectorDropHighlight(clientX, clientY, item) {
    if (typeof canvas.hitTestEdgeAtScreen !== "function" || typeof canvas.setDropTargetEdge !== "function") {
      return;
    }
    const src = item || toolboxDragItem || toolboxTouchDrag?.item;
    const box = src ? dropHitBox(src, clientX, clientY) : null;
    const edge = canvas.hitTestEdgeAtScreen(clientX, clientY, 16, box ? { box } : {});
    canvas.setDropTargetEdge(edge ? edge.id : null);
  }

  function addToolboxNodeAtClient(item, clientX, clientY) {
    if (!item || item.kind !== "node") return;
    canvas.setMode("select");
    setActiveTool("select");
    const world = canvas._screenToWorld(clientX, clientY);
    const dw = Number(item.default_width) || 120;
    const dh = Number(item.default_height) || 60;
    const x = world.x - dw / 2;
    const y = world.y - dh / 2;
    // Hit-test the connector against the pointer and the would-be node box
    // BEFORE adding the node, so the new shape cannot block or reroute the edge.
    const hit =
      typeof canvas.hitTestEdgeAtScreen === "function"
        ? canvas.hitTestEdgeAtScreen(clientX, clientY, 16, { box: { x, y, width: dw, height: dh } })
        : null;
    if (typeof canvas.clearDropTargetEdge === "function") canvas.clearDropTargetEdge();
    if (hit && typeof canvas.insertNodeOnEdge === "function") {
      const node = canvas.insertNodeOnEdge(hit.id, item.shape, x, y, { width: dw, height: dh });
      if (node) {
        showToast(`Inserted ${item.label}`, "success");
        return;
      }
    }
    // exact: land on the drop point (grid-snapped by addNode); skip palette overlap-stepping.
    canvas.addNode(item.shape, "", x, y, { exact: true });
    showToast(`Added ${item.label}`, "success");
  }

  function isToolboxShapeDrag(e) {
    if (toolboxDragItem) return true;
    const types = e.dataTransfer ? Array.from(e.dataTransfer.types) : [];
    return types.includes(TOOLBOX_DRAG_MIME);
  }

  function onToolboxDragStart(e, item) {
    if (item.kind !== "node") {
      e.preventDefault();
      return;
    }
    toolboxDragItem = item;
    suppressToolboxClick = true;
    const payload = serializeToolboxItem(item);
    e.dataTransfer.effectAllowed = "copy";
    e.dataTransfer.setData(TOOLBOX_DRAG_MIME, payload);
    e.dataTransfer.setData("text/plain", payload);
  }

  function onToolboxDragEnd() {
    toolboxDragItem = null;
    clearShapeDragChrome();
    setTimeout(() => {
      suppressToolboxClick = false;
    }, 0);
  }

  function onCanvasDragOver(e) {
    if (!isToolboxShapeDrag(e)) return;
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
    canvas.viewport.classList.add("is-shape-drag-over");
    updateConnectorDropHighlight(e.clientX, e.clientY);
  }

  function onCanvasDragLeave(e) {
    const next = e.relatedTarget;
    if (next && canvas.viewport.contains(next)) return;
    clearShapeDragChrome();
  }

  function onCanvasDrop(e) {
    const item = itemFromDragEvent(e);
    clearShapeDragChrome();
    if (!item) return;
    e.preventDefault();
    addToolboxNodeAtClient(item, e.clientX, e.clientY);
    toolboxDragItem = null;
  }

  function clearToolboxTouch() {
    if (toolboxTouchDrag?.ghost) toolboxTouchDrag.ghost.remove();
    document.body.classList.remove("is-toolbox-touch-drag");
    clearShapeDragChrome();
    toolboxTouchDrag = null;
  }

  function onToolboxTouchStart(e, item) {
    if (item.kind !== "node" || e.touches.length !== 1) return;
    const t = e.touches[0];
    toolboxTouchDrag = {
      item,
      startX: t.clientX,
      startY: t.clientY,
      dragging: false,
      ghost: null,
      id: t.identifier,
    };
  }

  function onToolboxTouchMove(e) {
    if (!toolboxTouchDrag) return;
    const t = [...e.touches].find((x) => x.identifier === toolboxTouchDrag.id) || e.touches[0];
    if (!t) return;
    const dx = t.clientX - toolboxTouchDrag.startX;
    const dy = t.clientY - toolboxTouchDrag.startY;
    if (!toolboxTouchDrag.dragging) {
      if (dx * dx + dy * dy < 64) return;
      toolboxTouchDrag.dragging = true;
      suppressToolboxClick = true;
      const ghost = document.createElement("div");
      ghost.className = "toolbox-drag-ghost";
      ghost.textContent = toolboxTouchDrag.item.label;
      document.body.appendChild(ghost);
      toolboxTouchDrag.ghost = ghost;
      document.body.classList.add("is-toolbox-touch-drag");
    }
    e.preventDefault();
    toolboxTouchDrag.ghost.style.transform = `translate(${t.clientX + 12}px, ${t.clientY + 12}px)`;
    const overCanvas = isPointInCanvas(t.clientX, t.clientY);
    canvas.viewport.classList.toggle("is-shape-drag-over", overCanvas);
    if (overCanvas) updateConnectorDropHighlight(t.clientX, t.clientY);
    else if (typeof canvas.clearDropTargetEdge === "function") canvas.clearDropTargetEdge();
  }

  function onToolboxTouchEnd(e) {
    if (!toolboxTouchDrag) return;
    const wasDragging = toolboxTouchDrag.dragging;
    const item = toolboxTouchDrag.item;
    const t = [...e.changedTouches].find((x) => x.identifier === toolboxTouchDrag.id) || e.changedTouches[0];
    clearToolboxTouch();
    if (wasDragging && t && isPointInCanvas(t.clientX, t.clientY)) {
      addToolboxNodeAtClient(item, t.clientX, t.clientY);
    }
    if (wasDragging) {
      setTimeout(() => {
        suppressToolboxClick = false;
      }, 0);
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
      btn.addEventListener("click", (e) => {
        if (suppressToolboxClick) {
          e.preventDefault();
          e.stopPropagation();
          return;
        }
        onToolboxClick(item);
      });
      if (item.kind === "node") {
        btn.draggable = true;
        btn.addEventListener("dragstart", (e) => onToolboxDragStart(e, item));
        btn.addEventListener("dragend", onToolboxDragEnd);
        btn.addEventListener("touchstart", (e) => onToolboxTouchStart(e, item), { passive: true });
        els.toolboxNodes.appendChild(btn);
      } else {
        els.toolboxEdges.appendChild(btn);
      }
    }
  }

  function glyphFor(item) {
    const shape = item.shape || item.id;
    if (item.kind === "edge") {
      const edgeGlyphs = {
        association: "—",
        include: "«i»",
        extend: "«e»",
        generalization: "◁",
        dependency: "⇢",
        one: "1",
        many: "*",
        one_or_many: "1..*",
        zero_or_one: "0..1",
        zero_or_many: "0..*",
        one_to_many: "1—*",
        one_to_one: "1—1",
        many_to_many: "*—*",
        identifying: "═",
        message: "→",
        async_message: "⇢",
        return_message: "↩",
        flow: "→",
        message_flow: "⇏",
        connector: "→",
        inheritance: "△",
        realization: "△̆",
        composition: "◆",
        aggregation: "◇",
        network_link: "━",
        wireless: "≋",
        data_flow: "⇒",
      };
      return (
        `<svg class="toolbox-glyph-svg" viewBox="0 0 32 16" aria-hidden="true">` +
        `<text x="16" y="12" text-anchor="middle" font-size="11" font-weight="700">${edgeGlyphs[shape] || "→"}</text></svg>`
      );
    }
    const icons = {
      actor: '<circle cx="12" cy="7" r="3.2"/><path d="M12 10v6M8 13h8M9 22l3-6 3 6"/>',
      use_case: '<ellipse cx="12" cy="12" rx="9" ry="6"/>',
      system_boundary: '<rect x="3" y="3" width="18" height="18" rx="2"/>',
      package: '<path d="M3 8h7l2 3h9v10H3z"/>',
      note: '<path d="M6 4h10l4 4v12H6zM16 4v4h4"/>',
      text_box: '<rect x="4" y="7" width="16" height="10" rx="1"/><path d="M7 12h10"/>',
      entity: '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="M3 10h18"/>',
      weak_entity: '<rect x="3" y="5" width="18" height="14" rx="1"/><rect x="5" y="7" width="14" height="10"/>',
      attribute: '<ellipse cx="12" cy="12" rx="8" ry="5"/>',
      relationship: '<path d="M12 4l7 8-7 8-7-8z"/>',
      pool: '<rect x="2" y="4" width="20" height="16"/><path d="M2 10h20"/>',
      lane: '<rect x="2" y="6" width="20" height="12"/><path d="M7 6v12"/>',
      start: '<circle cx="12" cy="12" r="7"/>',
      end: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="4"/>',
      process: '<rect x="3" y="7" width="18" height="10" rx="1"/>',
      subprocess: '<rect x="3" y="7" width="18" height="10" rx="1"/><path d="M6 7v10M18 7v10"/>',
      gateway_xor: '<path d="M12 3l9 9-9 9-9-9z"/><path d="M9 9l6 6M15 9l-6 6"/>',
      gateway_and: '<path d="M12 3l9 9-9 9-9-9z"/><path d="M12 7v10M7 12h10"/>',
      decision: '<path d="M12 3l9 9-9 9-9-9z"/>',
      document: '<path d="M5 4h12v12c-2 2-4 2-6 0s-4-2-6 0V4z"/>',
      data_store: '<path d="M4 7c0-2 3.5-3 8-3s8 1 8 3v10c0 2-3.5 3-8 3s-8-1-8-3z"/><path d="M4 7c0 2 3.5 3 8 3s8-1 8-3"/>',
      terminator: '<rect x="3" y="8" width="18" height="8" rx="4"/>',
      input: '<path d="M6 7h14l-3 10H3z"/>',
      lifeline: '<rect x="5" y="3" width="14" height="7" rx="1"/><path d="M12 10v11" stroke-dasharray="2 2"/>',
      object: '<rect x="4" y="6" width="16" height="8" rx="1"/>',
      activation: '<rect x="10" y="4" width="4" height="16"/>',
      fragment: '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 9h8l2 3"/>',
      class: '<rect x="3" y="4" width="18" height="16"/><path d="M3 9h18M3 14h18"/>',
      interface: '<rect x="3" y="5" width="18" height="14" rx="1"/><path d="M3 10h18"/>',
      enum: '<rect x="3" y="5" width="18" height="14"/><path d="M3 10h18"/>',
      cloud: '<path d="M7 16c-3 0-4-2-4-4 0-2 2-3 3-3 0-3 2-5 5-5 3 0 5 2 5 4 2 0 4 1 4 3s-2 5-5 5H7z"/>',
      router: '<rect x="5" y="8" width="14" height="8" rx="1"/><circle cx="9" cy="12" r="1.2"/><circle cx="15" cy="12" r="1.2"/>',
      switch: '<rect x="4" y="8" width="16" height="8" rx="1"/><path d="M8 10v4M12 10v4M16 10v4"/>',
      firewall: '<rect x="6" y="4" width="12" height="16" rx="1"/><path d="M6 8h12M6 12h12M6 16h12"/>',
      load_balancer: '<path d="M4 12h6l2-5 2 10 2-5h4"/>',
      server: '<rect x="7" y="3" width="10" height="18" rx="1"/><path d="M7 8h10M7 13h10M7 18h10"/>',
      client: '<rect x="5" y="5" width="14" height="10" rx="1"/><path d="M9 18h6"/>',
      workstation: '<rect x="4" y="5" width="16" height="10"/><path d="M8 18h8M10 15v3M14 15v3"/>',
      service: '<rect x="3" y="6" width="18" height="12" rx="2"/>',
      api: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/>',
    };
    const path = icons[shape] || '<rect x="5" y="5" width="14" height="14" rx="2"/>';
    return (
      `<svg class="toolbox-glyph-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
      `stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`
    );
  }

  function onToolboxClick(item) {
    if (item.kind === "node") {
      canvas.setMode("select");
      setActiveTool("select");
      const center = canvas.viewport.getBoundingClientRect();
      const world = canvas._screenToWorld(center.left + center.width / 2, center.top + center.height / 2);
      const dw = Number(item.default_width) || 120;
      const dh = Number(item.default_height) || 60;
      canvas.addNode(item.shape, "", world.x - dw / 2, world.y - dh / 2);
      showToast(`Added ${item.label}`, "success");
    } else {
      const edgeType = item.shape || item.id;
      canvas.setMode("connect", edgeType);
      setActiveTool("connect");
      els.connectHint.hidden = false;
      els.connectHint.textContent = `Connect: click source, then target (${item.label})`;
      showToast(`Connect mode: ${item.label}`, "info");
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
      canvas.addNode(node.type, node.label, node.x + 40, node.y + 40, { exact: true });
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
        els.apiStatus.innerHTML = `<span class="status-dot"></span><span class="status-text">Gemini ready${dbLabel}</span>`;
      } else {
        els.apiStatus.classList.add("is-error");
        els.apiStatus.innerHTML = '<span class="status-dot"></span><span class="status-text">API key missing</span>';
        showToast("Set GEMINI_API_KEY in .env to enable AI generation.", "error");
      }
      if (!data.db_connected) {
        setProjectStatus("Database offline — save disabled");
      } else {
        await refreshProjectList();
        await restoreProjectFromUrl({ quiet: true });
      }
    } catch {
      els.apiStatus.classList.add("is-error");
      els.apiStatus.innerHTML = '<span class="status-dot"></span><span class="status-text">Offline</span>';
    }
  }

  function setProjectStatus(text) {
    if (els.projectStatus) els.projectStatus.textContent = text;
  }

  function updateApiDemoLink(projectId) {
    if (!els.openApiDemoLink) return;
    const demoPath = projectId
      ? `${withRoot("/demo")}?project=${encodeURIComponent(projectId)}`
      : withRoot("/demo");
    els.openApiDemoLink.href = demoPath;
  }

  function getProjectIdFromUrl() {
    try {
      const params = new URLSearchParams(window.location.search);
      const id = (params.get("project") || "").trim();
      return id || null;
    } catch {
      return null;
    }
  }

  function setProjectUrl(projectId, { push = false } = {}) {
    try {
      const url = new URL(window.location.href);
      if (projectId) url.searchParams.set("project", projectId);
      else url.searchParams.delete("project");
      const next = `${url.pathname}${url.search}${url.hash}`;
      if (push) window.history.pushState({ projectId: projectId || null }, "", next);
      else window.history.replaceState({ projectId: projectId || null }, "", next);
    } catch {
      /* ignore */
    }
  }

  function designerProjectUrl(projectId) {
    if (!projectId) return window.location.pathname;
    const url = new URL(window.location.href);
    url.searchParams.set("project", projectId);
    return `${url.pathname}?project=${encodeURIComponent(projectId)}`;
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

  async function loadProject(projectId, { quiet = false, syncUrl = true } = {}) {
    if (!projectId) return false;
    try {
      const res = await fetch(withRoot(`/api/projects/${projectId}`));
      const data = await res.json();
      if (!res.ok) throw new Error(formatApiError(data, "Load failed."));

      state.currentProjectId = data.id;
      state.externalProjectId = data.external_project_id || null;
      els.projectNameInput.value = data.name;
      const diagramPayload = {
        ...(data.diagram || {}),
        diagram_type: data.diagram_type,
        title: data.title || data.diagram?.title || "Untitled Diagram",
      };
      // Wait for toolbox sizes before normalize so actor/use_case etc. keep server dims.
      await loadToolboxAndSelect(data.diagram_type);
      applyDiagramToCanvas(diagramPayload, "Loaded");
      clearDirty();
      setProjectStatus(`Saved · ${data.id.slice(0, 8)}…`);
      updateApiDemoLink(data.id);
      if (syncUrl) setProjectUrl(data.id);
      await refreshProjectList();
      if (els.projectSelect) els.projectSelect.value = data.id;
      if (!quiet) showToast(`Opened project “${data.name}”.`, "success");
      return true;
    } catch (err) {
      showToast(err.message, "error");
      return false;
    }
  }

  async function loadToolboxAndSelect(type) {
    state.diagramType = type;
    if (els.diagramTypeSelectLeft) els.diagramTypeSelectLeft.value = type;
    if (els.activeTypeLabel) {
      els.activeTypeLabel.textContent = DIAGRAM_TYPE_LABELS[type] || type;
    }
    canvas.setDiagramType(type);
    await loadToolbox(type);
  }

  async function restoreProjectFromUrl({ quiet = false } = {}) {
    const projectId = getProjectIdFromUrl();
    if (!projectId) return;
    if (!state.dbConnected) {
      showToast("Cannot open project from URL — database offline.", "error");
      return;
    }
    const ok = await loadProject(projectId, { quiet, syncUrl: true });
    if (!ok) {
      // Invalid / missing id — drop it from the address bar
      setProjectUrl(null);
    }
  }

  function newProject({ skipConfirm = false } = {}) {
    const hasContent =
      canvas.diagram.nodes.length > 0 ||
      canvas.diagram.edges.length > 0 ||
      state.isDirty ||
      ((els.diagramTitle?.value || "").trim() &&
        els.diagramTitle.value.trim() !== "Untitled Diagram");
    if (
      !skipConfirm &&
      hasContent &&
      !confirmAction("Start a new project? The canvas, title, and chat will be cleared.")
    ) {
      return;
    }
    state.currentProjectId = null;
    state.externalProjectId = null;
    els.projectNameInput.value = "Untitled Project";
    els.projectSelect.value = "";
    selectDiagramType(state.publicConfig?.["diagrams.default_type"] || "flowchart");
    clearCanvas({ skipConfirm: true });
    resetRequirementsChat({ quiet: true });
    state.editedSinceAiLoad = false;
    setProjectStatus("Not saved yet");
    updateApiDemoLink(null);
    setProjectUrl(null);
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
      if (!res.ok) throw new Error(formatApiError(data, "Save failed."));

      state.currentProjectId = data.id;
      state.externalProjectId = data.external_project_id || null;
      clearDirty();
      setProjectStatus(`Saved · ${data.id.slice(0, 8)}…`);
      updateApiDemoLink(data.id);
      setProjectUrl(data.id);
      await refreshProjectList();
      els.projectSelect.value = data.id;
      showToast(`Project saved. Bookmark ${designerProjectUrl(data.id)}`, "success");
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function deleteCurrentProject() {
    if (!state.currentProjectId) {
      showToast("No saved project selected.", "error");
      return;
    }
    if (!confirmAction("Delete this project from the database?")) return;

    try {
      const res = await fetch(withRoot(`/api/projects/${state.currentProjectId}`), { method: "DELETE" });
      const data = await res.json();
      if (!res.ok) throw new Error(formatApiError(data, "Delete failed."));
      newProject({ skipConfirm: true });
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
    if (
      !confirmAction(
        "Send this diagram to the selected target project? The target copy will be replaced.",
      )
    ) {
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
      if (!res.ok) throw new Error(formatApiError(data, "Transfer failed."));
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
    if (!state.briefReady || !state.enhancedPrompt) {
      showToast("Finish the Requirements chat first (or click Proceed).", "error");
      els.promptInput?.focus();
      return;
    }

    const prompt = state.enhancedPrompt.trim();
    state.lastPrompt = prompt;
    if (els.aiThinkingLogBtn) els.aiThinkingLogBtn.disabled = true;
    showRecommendations([]);

    const payload = {
      prompt,
      diagram_type: state.diagramType,
      prompt_enhanced: true,
      original_prompt: state.originalPrompt || prompt,
    };
    // Edit mode is always on once the canvas has a diagram (one project = one ongoing diagram).
    const editRequest = canvas.diagram.nodes.length > 0;
    const previousDiagram = editRequest ? canvas.getDiagram() : null;
    if (editRequest) {
      payload.existing = previousDiagram;
      payload.edit_mode = true;
      const lastUser = [...state.chatMessages].reverse().find((m) => m.role === "user");
      if (lastUser?.content) payload.edit_request = String(lastUser.content).slice(0, 8000);
    }
    setGenerating(
      true,
      editRequest ? "Updating your diagram…" : "Creating your diagram…",
      STAGE_LABELS.understanding,
    );

    const controller = new AbortController();
    const timeoutMs = 540000; // under nginx 600s
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    state.lastGenerationTrace = [
      {
        step: 0,
        agent: "system",
        phase: "start",
        message: editRequest ? "Edit started — waiting for Generator…" : "Generation started…",
        timestamp: new Date().toISOString(),
      },
    ];
    if (els.aiThinkingLogBtn) els.aiThinkingLogBtn.disabled = false;
    // 2.7.9: never open the thinking log automatically (it stays behind the Log button).

    try {
      const res = await fetch(withRoot("/api/generate-diagram"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/x-ndjson" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const err = new Error(formatApiError(errBody, "Generation failed."));
        err.detail = err.message;
        // Refusals / validation (4xx) are written for users; 5xx text is internal.
        err.userFacing = res.status === 400 || res.status === 429;
        throw err;
      }
      const data = await readGenerateResponse(res);
      if (!data?.diagram) {
        throw new Error("no-diagram");
      }

      state.lastGenerationTrace = data.trace?.length ? data.trace : state.lastGenerationTrace;
      state.lastRecommendations = data.recommendations || [];
      if (els.aiThinkingLogBtn) els.aiThinkingLogBtn.disabled = !state.lastGenerationTrace.length;
      renderThinkingLog(state.lastGenerationTrace);

      let diagramOut = data.diagram;
      if (editRequest && previousDiagram) {
        diagramOut = mergeEditPreserveLayout(previousDiagram, data.diagram, prompt);
      }
      // 2.7.9: no toolbar badge; the toast carries no QC / revision wording.
      applyDiagramToCanvas(diagramOut, editRequest ? "AI edited" : "AI generated");
      // Suggestions: one collapsed row (expand on demand); never auto-opened.
      showRecommendations(state.lastRecommendations);

      const nodeCount = (diagramOut?.nodes || []).length;
      const typeLabel = data.diagram_type_label || DIAGRAM_TYPE_LABELS[state.diagramType] || "Diagram";
      showToast(
        editRequest ? `${typeLabel} updated - ${nodeCount} shapes` : `${typeLabel} ready - ${nodeCount} shapes`,
        "success",
      );
      canvas.scheduleFitToContent();
    } catch (err) {
      // 2.7.9: one plain message. Off-topic refusals (HTTP 400) keep their own wording.
      const msg =
        err?.userFacing && err?.message
          ? err.message
          : err?.name === "AbortError"
            ? "This is taking longer than expected. Please try again."
            : "Couldn't finish this diagram. Please try again.";
      showToast(msg, "error");
      state.lastGenerationTrace = [
        ...(state.lastGenerationTrace || []),
        {
          step: 99,
          agent: "system",
          phase: "error",
          message: err?.detail || err?.message || msg,
          timestamp: new Date().toISOString(),
        },
      ];
      if (els.aiThinkingLogBtn) els.aiThinkingLogBtn.disabled = false;
      renderThinkingLog(state.lastGenerationTrace);
    } finally {
      clearTimeout(timeoutId);
      setGenerating(false);
      canvas.scheduleFitToContent();
    }
  }

  async function readGenerateResponse(res) {
    const ctype = res.headers.get("content-type") || "";
    if (!ctype.includes("ndjson") || !res.body) {
      return res.json();
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let result = null;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (!line) continue;
        let msg;
        try {
          msg = JSON.parse(line);
        } catch {
          continue;
        }
        if (msg.type === "trace" && msg.data) {
          state.lastGenerationTrace = [...(state.lastGenerationTrace || []), msg.data];
          if (els.aiThinkingLogBtn) els.aiThinkingLogBtn.disabled = false;
          renderThinkingLog(state.lastGenerationTrace);
          const stage = stageLabelFor(msg.data);
          if (stage && els.canvasLoadingSub) els.canvasLoadingSub.textContent = stage;
        } else if (msg.type === "result") {
          result = msg.data;
        } else if (msg.type === "error") {
          const err = new Error(
            msg.user_facing && typeof msg.data === "string" ? msg.data : "Generation failed.",
          );
          err.detail = typeof msg.data === "string" ? msg.data : "Generation failed.";
          err.userFacing = Boolean(msg.user_facing);
          throw err;
        }
      }
    }
    return result || (buf.trim() ? JSON.parse(buf) : null);
  }

  /**
   * Keep prior geometry only when the generator left it unchanged (and the prompt is not a resize/move).
   * 2.7.9: if the server deliberately moved a node (|dx| or |dy| > 8) keep the SERVER position unless the
   * old spot is still free of every new/moved node; then run an overlap pass.
   */
  function mergeEditPreserveLayout(previous, next, prompt = "") {
    if (!previous?.nodes?.length || !next?.nodes) return next;
    const geomRequest =
      /\b(wider|taller|narrower|smaller|bigger|resize|move|align|position|size|shift|spread|scale)\b/i.test(
        String(prompt || ""),
      );
    const prevById = new Map(previous.nodes.map((n) => [n.id, n]));
    const overlaps = (a, b, pad = 0) =>
      a.x < b.x + b.width + pad &&
      a.x + a.width + pad > b.x &&
      a.y < b.y + b.height + pad &&
      a.y + a.height + pad > b.y;
    const isFlow = (next.diagram_type || state.diagramType) === "flowchart";
    const fresh = next.nodes.filter((n) => !prevById.has(n.id));
    const nodes = next.nodes.map((n) => {
      const old = prevById.get(n.id);
      if (!old) return n;
      const sizeChanged =
        Math.abs(Number(n.width) - Number(old.width)) > 8 ||
        Math.abs(Number(n.height) - Number(old.height)) > 8;
      if (geomRequest || sizeChanged) {
        return { ...n, label: n.label || old.label };
      }
      const moved = Math.abs(Number(n.x) - Number(old.x)) > 8 || Math.abs(Number(n.y) - Number(old.y)) > 8;
      if (moved && isFlow) {
        const oldBox = { x: Number(old.x), y: Number(old.y), width: Number(old.width), height: Number(old.height) };
        const blocked = fresh.some((f) => overlaps(oldBox, f, 12));
        if (blocked || isFlow) return { ...n, label: n.label || old.label };
        void blocked;
      }
      return {
        ...n,
        x: old.x,
        y: old.y,
        width: old.width,
        height: old.height,
        label: n.label || old.label,
      };
    });
    // Overlap pass: push any colliding node down (top-to-bottom flow), a few rounds.
    const bg = new Set(["pool", "lane", "system_boundary", "package", "fragment"]);
    for (let round = 0; isFlow && round < 6; round += 1) {
      let movedAny = false;
      const sorted = [...nodes].filter((n) => !bg.has(n.type)).sort((a, b) => a.y - b.y || a.x - b.x);
      for (let i = 0; i < sorted.length; i += 1) {
        for (let j = i + 1; j < sorted.length; j += 1) {
          const a = sorted[i];
          const b = sorted[j];
          if (overlaps(a, b, 8)) {
            b.y = a.y + a.height + 40;
            movedAny = true;
          }
        }
      }
      if (!movedAny) break;
    }
    return { ...next, nodes };
  }

  function loadSample() {
    const sample = SAMPLE_DIAGRAMS[state.diagramType];
    if (!sample) {
      const available = Object.keys(SAMPLE_DIAGRAMS).join(", ") || "(none)";
      showToast(`No sample for “${state.diagramType}”. Available: ${available}`, "error");
      return;
    }
    // Deep clone so message_y / labels are not shared across loads
    const clone = JSON.parse(JSON.stringify(sample));
    clone.diagram_type = state.diagramType;
    applyDiagramToCanvas(clone, "Sample");
    showToast(`Sample loaded (${DIAGRAM_TYPE_LABELS[state.diagramType] || state.diagramType}).`, "success");
  }

  function clearCanvas({ skipConfirm = false } = {}) {
    if (
      !skipConfirm &&
      canvas.diagram.nodes.length &&
      !confirmAction("Clear all shapes from the canvas?")
    ) {
      return;
    }
    state.suppressDirty = true;
    try {
      canvas.setDiagram({
        diagram_type: state.diagramType,
        title: "Untitled Diagram",
        nodes: [],
        edges: [],
        drilldowns: [],
      });
      if (els.diagramTitle) els.diagramTitle.value = "Untitled Diagram";
      clearDirty();
      if (els.canvasBadge) {
        els.canvasBadge.textContent = "Empty";
        els.canvasBadge.classList.remove("is-live");
      }
    } finally {
      state.suppressDirty = false;
    }
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

  async function exportPng() {
    try {
      const blob = await canvas.exportPngBlob(2);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${state.diagramType}-${Date.now()}.png`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      showToast("PNG exported.", "success");
    } catch {
      showToast("PNG export is not available in this browser.", "error");
    }
  }

  async function copySvgText() {
    const svg = canvas.exportSvg();
    if (!navigator.clipboard?.writeText) {
      throw new Error("clipboard unavailable");
    }
    await navigator.clipboard.writeText(svg);
  }

  async function copyDiagram() {
    const canWriteImage =
      typeof navigator.clipboard?.write === "function" && typeof window.ClipboardItem === "function";
    if (canWriteImage) {
      try {
        const pngPromise = canvas.exportPngBlob(2);
        const svgTextPromise = Promise.resolve().then(() => {
          const svg = canvas.exportSvg();
          return new Blob([svg], { type: "text/plain" });
        });
        try {
          await navigator.clipboard.write([
            new ClipboardItem({
              "image/png": pngPromise,
              "text/plain": svgTextPromise,
            }),
          ]);
        } catch {
          await navigator.clipboard.write([
            new ClipboardItem({ "image/png": canvas.exportPngBlob(2) }),
          ]);
        }
        showToast("Image copied", "success");
        return;
      } catch {
        /* fall through to SVG text */
      }
    }
    try {
      await copySvgText();
      showToast("Image copied", "success");
    } catch {
      showToast("Copy is not available in this browser.", "error");
    }
  }

  async function copyDiagramJson() {
    try {
      const diagram = buildDiagramPayload();
      if (!navigator.clipboard?.writeText) {
        throw new Error("clipboard unavailable");
      }
      await navigator.clipboard.writeText(JSON.stringify(diagram, null, 2));
      showToast("JSON copied", "success");
    } catch {
      showToast("Copy is not available in this browser.", "error");
    }
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
    if (value === state.diagramType) return;
    if (canvas.diagram.nodes.length) {
      if (
        !confirmAction(
          "Change diagram type? The canvas will be cleared and the title reset to Untitled.",
        )
      ) {
        if (els.diagramTypeSelectLeft) els.diagramTypeSelectLeft.value = state.diagramType;
        return;
      }
    }
    selectDiagramType(value, { clearCanvasOnChange: canvas.diagram.nodes.length > 0 });
    resetRequirementsChat({ quiet: true });
  }

  els.diagramTypeSelectLeft?.addEventListener("change", () => {
    onDiagramTypeChange(els.diagramTypeSelectLeft.value);
  });

  els.promptInput?.addEventListener("input", updateCharCount);
  els.promptInput?.addEventListener("keydown", (e) => {
    if (e.isComposing || e.keyCode === 229) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendRequirementsMessage();
    }
  });
  document.querySelector(".req-chat-compose")?.addEventListener("mousedown", (e) => {
    if (e.target === els.promptInput) return;
    if (e.target.closest("#sendChatBtn")) return;
    els.promptInput?.focus();
  });
  // Bind Send reliably (click + pointerup fallback)
  const onSendChat = (e) => {
    e.preventDefault();
    e.stopPropagation();
    sendRequirementsMessage();
  };
  els.sendChatBtn?.addEventListener("click", onSendChat);
  document.getElementById("reqChat")?.addEventListener("click", (e) => {
    const btn = e.target.closest("#sendChatBtn");
    if (btn) onSendChat(e);
  });
  els.forceReadyBtn?.addEventListener("click", () => sendRequirementsMessage({ forceReady: true }));
  els.generateBtn.addEventListener("click", generateDiagram);
  els.viewBriefBtn?.addEventListener("click", openBriefModal);
  els.closeBriefBtn?.addEventListener("click", closeBriefModal);
  els.cancelBriefBtn?.addEventListener("click", closeBriefModal);
  els.briefBackdrop?.addEventListener("click", closeBriefModal);
  els.saveBriefBtn?.addEventListener("click", saveBriefFromModal);
  els.aiThinkingLogBtn?.addEventListener("click", openThinkingLog);
  els.qcRecommendationsToggle?.addEventListener("click", () => {
    setRecommendationsExpanded(els.qcRecommendationsToggle.getAttribute("aria-expanded") !== "true");
  });
  els.closeAiThinkingBtn?.addEventListener("click", closeThinkingLog);
  els.aiThinkingBackdrop?.addEventListener("click", closeThinkingLog);
  els.sampleBtn.addEventListener("click", loadSample);
  els.clearBtn.addEventListener("click", clearCanvas);
  els.deleteBtn.addEventListener("click", () => canvas.deleteSelection());
  els.undoBtn?.addEventListener("click", () => {
    if (typeof canvas.undo !== "function") {
      showToast("Undo unavailable — hard-refresh the page (Cmd+Shift+R).", "error");
      return;
    }
    if (!canvas.undo()) showToast("Nothing to undo.", "info");
  });
  els.duplicateBtn?.addEventListener("click", duplicateSelection);

  els.selectTool.addEventListener("click", () => setActiveTool("select"));
  els.panTool.addEventListener("click", () => setActiveTool("pan"));

  canvas.viewport.addEventListener("dragover", onCanvasDragOver);
  canvas.viewport.addEventListener("dragleave", onCanvasDragLeave);
  canvas.viewport.addEventListener("drop", onCanvasDrop);
  document.addEventListener("touchmove", onToolboxTouchMove, { passive: false });
  document.addEventListener("touchend", onToolboxTouchEnd);
  document.addEventListener("touchcancel", () => {
    if (toolboxTouchDrag?.dragging) suppressToolboxClick = true;
    clearToolboxTouch();
    setTimeout(() => {
      suppressToolboxClick = false;
    }, 0);
  });

  els.propLabel.addEventListener("input", () => canvas.updateSelectedLabel(els.propLabel.value));

  els.ctxRename?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (contextMenuTargetId) startInlineRename(contextMenuTargetId);
  });

  els.ctxDelete?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (contextMenuTargetId) {
      canvas.selectOnly(contextMenuTargetId);
      canvas.deleteSelection();
    }
    hideContextMenu();
  });

  els.canvasInlineInput?.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Enter") {
      e.preventDefault();
      commitInlineRename();
    } else if (e.key === "Escape") {
      e.preventDefault();
      hideInlineEditor();
    }
  });

  els.canvasInlineInput?.addEventListener("blur", () => {
    if (!els.canvasInlineEditor?.hidden) commitInlineRename();
  });

  document.addEventListener("click", (e) => {
    if (!els.canvasContextMenu?.contains(e.target)) hideContextMenu();
    const inCopyMenu =
      els.copyDiagramMenu?.contains(e.target) || els.copyDiagramBtn?.contains(e.target);
    if (!inCopyMenu) hideCopyDiagramMenu();
  });

  els.welcomeCloseBtn?.addEventListener("click", closeWelcomeModal);
  els.welcomeBackdrop?.addEventListener("click", closeWelcomeModal);
  els.welcomeNextBtn?.addEventListener("click", welcomeNext);
  els.welcomeBackBtn?.addEventListener("click", welcomeBack);
  els.tourHelpBtn?.addEventListener("click", () => {
    if (els.welcomeDontShow) els.welcomeDontShow.checked = false;
    openWelcomeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (els.drillDownModal && !els.drillDownModal.hidden) {
        e.preventDefault();
        closeDrillDownModal();
        return;
      }
      if (els.copyDiagramMenu && !els.copyDiagramMenu.hidden) {
        e.preventDefault();
        hideCopyDiagramMenu();
        return;
      }
      if (els.welcomeModal && !els.welcomeModal.hidden) {
        e.preventDefault();
        closeWelcomeModal();
        return;
      }
      if (els.briefModal && !els.briefModal.hidden) {
        e.preventDefault();
        closeBriefModal();
        return;
      }
      if (els.aiThinkingModal && !els.aiThinkingModal.hidden) {
        e.preventDefault();
        closeThinkingLog();
        return;
      }
    }
    if (els.welcomeModal && !els.welcomeModal.hidden) {
      if (e.key === "ArrowRight") {
        e.preventDefault();
        welcomeNext();
        return;
      }
      if (e.key === "ArrowLeft") {
        e.preventDefault();
        welcomeBack();
        return;
      }
    }
    if (e.target.matches("input, textarea, select") && e.key !== "Escape") return;
    if (e.key === "F2") {
      const sel = canvas.getSelection();
      const item = sel.nodes[0] || sel.edges[0];
      if (item) {
        e.preventDefault();
        startInlineRename(item.id);
      }
    }
  });

  els.diagramTitle.addEventListener("change", () => {
    canvas.diagram.title = els.diagramTitle.value.trim() || "Untitled Diagram";
    markDirty();
  });

  // Register leave warning as early as possible
  window.addEventListener("beforeunload", (e) => {
    if (!state.leaveWarning || !state.isDirty) return;
    e.preventDefault();
    e.returnValue = "You have unsaved diagram changes.";
    return e.returnValue;
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
  els.exportPngBtn?.addEventListener("click", exportPng);
  els.copyDiagramBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleCopyDiagramMenu();
  });
  els.copyDiagramImageBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    hideCopyDiagramMenu();
    copyDiagram();
  });
  els.copyDiagramJsonBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    hideCopyDiagramMenu();
    copyDiagramJson();
  });
  els.exportJsonBtn.addEventListener("click", exportJson);

  els.panelToggleLeft?.addEventListener("click", () => togglePanel("left"));
  els.panelToggleRight?.addEventListener("click", () => togglePanel("right"));
  els.collapseLeftBtn?.addEventListener("click", () => setPanelCollapsed("left", true));
  els.collapseRightBtn?.addEventListener("click", () => setPanelCollapsed("right", true));
  els.expandLeftBtn?.addEventListener("click", () => setPanelCollapsed("left", false));
  els.expandRightBtn?.addEventListener("click", () => setPanelCollapsed("right", false));
  bindPanelResizer(els.leftResizer, "left");
  bindPanelResizer(els.rightResizer, "right");
  loadPanelLayout();
  applyPanelLayout();

  els.mobileDockLeft?.addEventListener("click", () => togglePanel("left"));
  els.mobileDockRight?.addEventListener("click", () => togglePanel("right"));
  els.mobileDockCanvas?.addEventListener("click", () => closeMobilePanels());
  els.mobilePanelBackdrop?.addEventListener("click", () => closeMobilePanels());

  mobileMq.addEventListener("change", initMobileLayout);

  els.tabShapes?.addEventListener("click", () => switchLeftTab("shapes"));
  els.tabDrilldowns?.addEventListener("click", () => switchLeftTab("drilldowns"));
  els.tabAi?.addEventListener("click", () => switchSidebarTab("ai"));
  els.tabProject?.addEventListener("click", () => switchSidebarTab("project"));

  els.createDrillDownBtn?.addEventListener("click", beginCreateDrillDown);
  els.clearDrillDownHighlightBtn?.addEventListener("click", () => {
    canvas.clearDrillDownHighlight();
    canvas.render();
    renderDrillDownSidebar();
  });
  els.editDrillDownBtn?.addEventListener("click", () => {
    const dd = canvas.getDrilldowns().find((item) => item.id === canvas.activeDrillDownId);
    if (!dd) {
      showToast("Select a Drill Down first.", "error");
      return;
    }
    openDrillDownModal("edit", dd);
  });
  els.deleteDrillDownBtn?.addEventListener("click", () => {
    const id = canvas.activeDrillDownId;
    if (!id) {
      showToast("Select a Drill Down first.", "error");
      return;
    }
    if (!confirmAction("Delete this Drill Down? Shapes on the canvas are kept.")) return;
    canvas.deleteDrillDown(id);
    renderDrillDownSidebar();
    showToast("Drill Down deleted.", "success");
  });
  els.ctxCreateDrillDown?.addEventListener("click", (e) => {
    e.stopPropagation();
    beginCreateDrillDown();
  });
  els.ddForm?.addEventListener("submit", submitDrillDownForm);
  els.ddFormCancelBtn?.addEventListener("click", closeDrillDownModal);
  els.ddModalCloseBtn?.addEventListener("click", closeDrillDownModal);
  els.ddModalBackdrop?.addEventListener("click", closeDrillDownModal);
  els.ddColorInput?.addEventListener("input", syncDdSwatchActive);

  els.projectSelect?.addEventListener("change", () => {
    if (els.projectSelect.value) loadProject(els.projectSelect.value);
    else newProject();
  });
  els.newProjectBtn?.addEventListener("click", newProject);
  els.saveProjectBtn?.addEventListener("click", saveProject);
  els.deleteProjectBtn?.addEventListener("click", deleteCurrentProject);
  els.transferProjectBtn?.addEventListener("click", transferProject);
  els.copyCanvasExportBtn?.addEventListener("click", copyCanvasExport);

  window.addEventListener("popstate", () => {
    const id = getProjectIdFromUrl();
    if (id) loadProject(id, { quiet: true, syncUrl: false });
    else if (state.currentProjectId) newProject({ skipConfirm: true });
  });

  resetRequirementsChat({ quiet: true });
  updateCharCount();
  updateDdSelectionHint();
  renderDrillDownSidebar();
  initMobileLayout();
  updateApiDemoLink(null);
  clearDirty();

  loadPublicConfig().finally(() => {
    checkHealth();
    selectDiagramType(state.diagramType || "flowchart");
    canvas.resetView();
    if (welcomeShouldShow()) {
      requestAnimationFrame(() => openWelcomeModal());
    }
  });
})();
