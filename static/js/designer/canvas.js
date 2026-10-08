import { defaultNodeSize, nextId } from "./diagram-types.js?v=2.6.3";

const GRID = 20;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 2.5;
const SEQUENCE_MESSAGE_TYPES = new Set(["message", "async_message", "return_message"]);
const MAX_UNDO = 48;

export class DiagramCanvas {
  constructor(container, options = {}) {
    this.container = container;
    this.onChange = options.onChange || (() => {});
    this.onSelectionChange = options.onSelectionChange || (() => {});
    this.onContextMenu = options.onContextMenu || (() => {});
    this.onRequestRename = options.onRequestRename || (() => {});

    this.diagram = {
      diagram_type: "use_case",
      title: "Untitled Diagram",
      nodes: [],
      edges: [],
    };

    this.view = { x: 0, y: 0, scale: 1 };
    this.selectedIds = new Set();
    this.mode = "select"; // select | connect | pan
    this.connectFrom = null;
    this.pendingEdgeType = "association";
    this.dragState = null;
    this.panState = null;
    this._history = [];
    this._historyIndex = -1;
    this._buildDom();
    this._bindEvents();
    this.render();
  }

  _buildDom() {
    this.container.innerHTML = "";
    this.container.classList.add("designer-canvas-root");

    this.viewport = document.createElement("div");
    this.viewport.className = "designer-viewport";

    this.svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    this.svg.setAttribute("class", "designer-svg");
    this.svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");

    this.defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    this._buildMarkers();
    this.svg.appendChild(this.defs);

    this.gridLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.gridLayer.setAttribute("class", "layer-grid");
    this.edgesLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.edgesLayer.setAttribute("class", "layer-edges");
    this.nodesLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.nodesLayer.setAttribute("class", "layer-nodes");
    this.overlayLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.overlayLayer.setAttribute("class", "layer-overlay");

    this.worldLayer = document.createElementNS("http://www.w3.org/2000/svg", "g");
    this.worldLayer.setAttribute("class", "diagram-world");
    this.worldLayer.append(this.gridLayer, this.edgesLayer, this.nodesLayer, this.overlayLayer);
    this.svg.appendChild(this.worldLayer);
    this.viewport.appendChild(this.svg);
    this.container.appendChild(this.viewport);
  }

  _resetHistory() {
    const snap = JSON.stringify(this.diagram);
    this._history = [snap];
    this._historyIndex = 0;
  }

  _saveUndoPoint() {
    const snap = JSON.stringify(this.diagram);
    this._history = this._history.slice(0, this._historyIndex + 1);
    this._history.push(snap);
    if (this._history.length > MAX_UNDO) {
      this._history.shift();
    } else {
      this._historyIndex += 1;
    }
  }

  undo() {
    if (this._historyIndex <= 0) return false;
    this._historyIndex -= 1;
    this.diagram = JSON.parse(this._history[this._historyIndex]);
    this.selectedIds.clear();
    this.connectFrom = null;
    this.render();
    this.onChange(this.getDiagram());
    this.onSelectionChange(this.getSelection());
    return true;
  }

  _buildMarkers() {
    const defs = this.defs;
    defs.innerHTML = "";

    const gridPattern = document.createElementNS("http://www.w3.org/2000/svg", "pattern");
    gridPattern.setAttribute("id", "grid");
    gridPattern.setAttribute("width", String(GRID));
    gridPattern.setAttribute("height", String(GRID));
    gridPattern.setAttribute("patternUnits", "userSpaceOnUse");
    const gridPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    gridPath.setAttribute("d", `M ${GRID} 0 L 0 0 0 ${GRID}`);
    gridPath.setAttribute("fill", "none");
    gridPath.setAttribute("stroke", "#e8ecf4");
    gridPath.setAttribute("stroke-width", "1");
    gridPattern.appendChild(gridPath);
    defs.appendChild(gridPattern);

    const arrow = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    arrow.setAttribute("id", "arrow");
    arrow.setAttribute("viewBox", "0 0 10 10");
    arrow.setAttribute("refX", "9");
    arrow.setAttribute("refY", "5");
    arrow.setAttribute("markerWidth", "6");
    arrow.setAttribute("markerHeight", "6");
    arrow.setAttribute("orient", "auto-start-reverse");
    const arrowPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    arrowPath.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
    arrowPath.setAttribute("fill", "#1e293b");
    arrow.appendChild(arrowPath);
    defs.appendChild(arrow);

    const diamond = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    diamond.setAttribute("id", "diamond-end");
    diamond.setAttribute("viewBox", "0 0 10 10");
    diamond.setAttribute("refX", "5");
    diamond.setAttribute("refY", "5");
    diamond.setAttribute("markerWidth", "8");
    diamond.setAttribute("markerHeight", "8");
    diamond.setAttribute("orient", "auto");
    const diamondPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    diamondPath.setAttribute("d", "M 5 0 L 10 5 L 5 10 L 0 5 Z");
    diamondPath.setAttribute("fill", "#fff");
    diamondPath.setAttribute("stroke", "#1e293b");
    diamondPath.setAttribute("stroke-width", "1.5");
    diamond.appendChild(diamondPath);
    defs.appendChild(diamond);

    const diamondFilled = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    diamondFilled.setAttribute("id", "diamond-filled");
    diamondFilled.setAttribute("viewBox", "0 0 10 10");
    diamondFilled.setAttribute("refX", "5");
    diamondFilled.setAttribute("refY", "5");
    diamondFilled.setAttribute("markerWidth", "8");
    diamondFilled.setAttribute("markerHeight", "8");
    diamondFilled.setAttribute("orient", "auto");
    const diamondFilledPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    diamondFilledPath.setAttribute("d", "M 5 0 L 10 5 L 5 10 L 0 5 Z");
    diamondFilledPath.setAttribute("fill", "#1e293b");
    diamondFilled.appendChild(diamondFilledPath);
    defs.appendChild(diamondFilled);

    const triangle = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    triangle.setAttribute("id", "triangle-hollow");
    triangle.setAttribute("viewBox", "0 0 10 10");
    triangle.setAttribute("refX", "9");
    triangle.setAttribute("refY", "5");
    triangle.setAttribute("markerWidth", "7");
    triangle.setAttribute("markerHeight", "7");
    triangle.setAttribute("orient", "auto");
    const trianglePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    trianglePath.setAttribute("d", "M 0 0 L 10 5 L 0 10 Z");
    trianglePath.setAttribute("fill", "#fff");
    trianglePath.setAttribute("stroke", "#1e293b");
    trianglePath.setAttribute("stroke-width", "1.5");
    triangle.appendChild(trianglePath);
    defs.appendChild(triangle);

    const openArrow = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    openArrow.setAttribute("id", "arrow-open");
    openArrow.setAttribute("viewBox", "0 0 10 10");
    openArrow.setAttribute("refX", "9");
    openArrow.setAttribute("refY", "5");
    openArrow.setAttribute("markerWidth", "7");
    openArrow.setAttribute("markerHeight", "7");
    openArrow.setAttribute("orient", "auto-start-reverse");
    const openPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    openPath.setAttribute("d", "M 0 0 L 10 5 L 0 10");
    openPath.setAttribute("fill", "none");
    openPath.setAttribute("stroke", "#1e293b");
    openPath.setAttribute("stroke-width", "1.5");
    openArrow.appendChild(openPath);
    defs.appendChild(openArrow);

    // Crow's-foot ERD markers (tip points along the edge toward the connected entity)
    const addCf = (id, d, refX = 12) => {
      const m = document.createElementNS("http://www.w3.org/2000/svg", "marker");
      m.setAttribute("id", id);
      m.setAttribute("viewBox", "0 0 14 14");
      m.setAttribute("refX", String(refX));
      m.setAttribute("refY", "7");
      m.setAttribute("markerWidth", "10");
      m.setAttribute("markerHeight", "10");
      m.setAttribute("orient", "auto");
      const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
      p.setAttribute("d", d);
      p.setAttribute("fill", "none");
      p.setAttribute("stroke", "#1e293b");
      p.setAttribute("stroke-width", "1.5");
      p.setAttribute("stroke-linecap", "round");
      m.appendChild(p);
      defs.appendChild(m);
    };
    // Vertical bar = one
    addCf("cf-one", "M 11 2 L 11 12");
    // Crow's foot = many
    addCf("cf-many", "M 12 7 L 2 2 M 12 7 L 2 7 M 12 7 L 2 12");
    // Bar + crow's foot = one or many
    addCf("cf-one-many", "M 13 2 L 13 12 M 11 7 L 1 2 M 11 7 L 1 7 M 11 7 L 1 12");
    // Circle + bar = zero or one
    addCf("cf-zero-one", "M 3 7 A 2.5 2.5 0 1 1 3.01 7 M 11 2 L 11 12", 12);
    // Circle + crow's foot = zero or many
    addCf("cf-zero-many", "M 3 7 A 2.5 2.5 0 1 1 3.01 7 M 12 7 L 5 2 M 12 7 L 5 7 M 12 7 L 5 12", 12);
  }

  _bindEvents() {
    this.viewport.addEventListener("wheel", (e) => this._onWheel(e), { passive: false });
    this.svg.addEventListener("mousedown", (e) => this._onMouseDown(e));
    this.svg.addEventListener("dblclick", (e) => this._onDoubleClick(e));
    this.viewport.addEventListener("contextmenu", (e) => this._onContextMenu(e));
    window.addEventListener("mousemove", (e) => this._onMouseMove(e));
    window.addEventListener("mouseup", (e) => this._onMouseUp(e));
    window.addEventListener("keydown", (e) => this._onKeyDown(e));

    if (typeof ResizeObserver !== "undefined") {
      this._resizeObserver = new ResizeObserver(() => {
        if (this.diagram.nodes.length) this.scheduleFitToContent();
      });
      this._resizeObserver.observe(this.viewport);
    }
  }

  setDiagram(diagram) {
    this.diagram = JSON.parse(JSON.stringify(diagram));
    this.selectedIds.clear();
    this.connectFrom = null;
    this._resetHistory();
    this.render();
    this.onChange(this.getDiagram());
    this.onSelectionChange(this.getSelection());
  }

  /** Load diagram after normalizing to toolbox shapes (from AI or import). */
  loadNormalizedDiagram(diagram) {
    this.setDiagram(diagram);
  }

  getDiagram() {
    return JSON.parse(JSON.stringify(this.diagram));
  }

  getSelection() {
    return {
      nodes: this.diagram.nodes.filter((n) => this.selectedIds.has(n.id)),
      edges: this.diagram.edges.filter((e) => this.selectedIds.has(e.id)),
    };
  }

  setMode(mode, edgeType = null) {
    this.mode = mode;
    if (edgeType) this.pendingEdgeType = edgeType;
    this.connectFrom = null;
    this.viewport.classList.toggle("mode-connect", mode === "connect");
    this.viewport.classList.toggle("mode-pan", mode === "pan");
  }

  setDiagramType(type) {
    this.diagram.diagram_type = type;
    // Do not notify onChange — type switches are handled by the app shell
    // and must not flip the dirty flag by themselves.
  }

  addNode(type, label = "", x = 120, y = 120, opts = {}) {
    this._saveUndoPoint();
    const [w, h] = defaultNodeSize(type);
    let nx = Math.round((Number.isFinite(x) ? x : 120) / GRID) * GRID;
    let ny = Math.round((Number.isFinite(y) ? y : 120) / GRID) * GRID;
    // Palette drops: nudge until the top-left does not sit on an existing node
    if (!opts.exact) {
      let guard = 0;
      while (
        guard < 40 &&
        this.diagram.nodes.some((n) => Math.abs(n.x - nx) < 12 && Math.abs(n.y - ny) < 12)
      ) {
        nx += GRID * 2;
        ny += GRID;
        guard += 1;
      }
    }
    const node = {
      id: nextId("n", this.diagram.nodes),
      type,
      label: label || type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      x: nx,
      y: ny,
      width: w,
      height: h,
      meta: {},
    };
    this.diagram.nodes.push(node);
    this.selectOnly(node.id);
    this.render();
    this.onChange(this.getDiagram());
    return node;
  }

  addEdge(fromId, toId, type = "connector", label = "") {
    if (!fromId || !toId || fromId === toId) return null;
    if (!this.diagram.nodes.some((n) => n.id === fromId)) return null;
    if (!this.diagram.nodes.some((n) => n.id === toId)) return null;
    this._saveUndoPoint();
    const exists = this.diagram.edges.some(
      (e) => e.from === fromId && e.to === toId && e.type === type,
    );
    if (exists) return null;
    const edge = {
      id: nextId("e", this.diagram.edges),
      from: fromId,
      to: toId,
      label,
      type: type || "connector",
      meta: {},
    };
    // Sequence messages need an initial Y so they draw immediately
    if (
      this.diagram.diagram_type === "sequence" &&
      SEQUENCE_MESSAGE_TYPES.has(edge.type)
    ) {
      const prior = this.diagram.edges.filter((e) => SEQUENCE_MESSAGE_TYPES.has(e.type)).length;
      edge.meta.message_y = 88 + prior * 52;
    }
    this.diagram.edges.push(edge);
    this.selectOnly(edge.id);
    this.render();
    this.onChange(this.getDiagram());
    return edge;
  }

  /** Resolve click target — use attributes (SVG dataset is unreliable in some engines). */
  _hitFromEvent(e) {
    const el = e.target?.closest?.("[data-id]");
    if (!el) return null;
    const id = el.getAttribute("data-id");
    if (!id) return null;
    let kind = el.getAttribute("data-kind") || "";
    if (!kind) {
      if (this.diagram.nodes.some((n) => n.id === id)) kind = "node";
      else if (this.diagram.edges.some((ed) => ed.id === id)) kind = "edge";
    }
    return { el, id, kind };
  }

  renameItem(id, label) {
    this._saveUndoPoint();
    const node = this.diagram.nodes.find((n) => n.id === id);
    if (node) {
      node.label = label;
    } else {
      const edge = this.diagram.edges.find((e) => e.id === id);
      if (edge) edge.label = label;
    }
    this.render();
    this.onChange(this.getDiagram());
    this.onSelectionChange(this.getSelection());
  }

  worldToScreen(wx, wy) {
    const rect = this.viewport.getBoundingClientRect();
    return {
      x: rect.left + this.view.x + wx * this.view.scale,
      y: rect.top + this.view.y + wy * this.view.scale,
    };
  }

  getItemById(id) {
    const node = this.diagram.nodes.find((n) => n.id === id);
    if (node) return { kind: "node", item: node };
    const edge = this.diagram.edges.find((e) => e.id === id);
    if (edge) return { kind: "edge", item: edge };
    return null;
  }

  deleteSelection() {
    if (!this.selectedIds.size) return;
    this._saveUndoPoint();
    const nodeIds = new Set(
      this.diagram.nodes.filter((n) => this.selectedIds.has(n.id)).map((n) => n.id),
    );
    if (nodeIds.size) {
      this.diagram.edges = this.diagram.edges.filter(
        (e) => !nodeIds.has(e.from) && !nodeIds.has(e.to) && !this.selectedIds.has(e.id),
      );
      this.diagram.nodes = this.diagram.nodes.filter((n) => !nodeIds.has(n.id));
    } else {
      this.diagram.edges = this.diagram.edges.filter((e) => !this.selectedIds.has(e.id));
    }
    this.selectedIds.clear();
    this.render();
    this.onChange(this.getDiagram());
    this.onSelectionChange(this.getSelection());
  }

  updateSelectedLabel(label) {
    for (const node of this.diagram.nodes) {
      if (this.selectedIds.has(node.id)) node.label = label;
    }
    for (const edge of this.diagram.edges) {
      if (this.selectedIds.has(edge.id)) edge.label = label;
    }
    this.render();
    this.onChange(this.getDiagram());
  }

  selectOnly(id) {
    this.selectedIds.clear();
    if (id) this.selectedIds.add(id);
    this.onSelectionChange(this.getSelection());
    this.render();
  }

  clearSelection() {
    this.selectedIds.clear();
    this.onSelectionChange(this.getSelection());
    this.render();
  }

  zoomBy(delta, clientX, clientY) {
    const rect = this.viewport.getBoundingClientRect();
    const px = clientX - rect.left;
    const py = clientY - rect.top;
    const prevScale = this.view.scale;
    const nextScale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prevScale * (delta > 0 ? 1.1 : 0.9)));
    const wx = (px - this.view.x) / prevScale;
    const wy = (py - this.view.y) / prevScale;
    this.view.scale = nextScale;
    this.view.x = px - wx * nextScale;
    this.view.y = py - wy * nextScale;
    this._applyViewTransform();
  }

  resetView() {
    this.view = { x: 40, y: 40, scale: 1 };
    this._applyViewTransform();
  }

  fitToContent() {
    if (!this.diagram.nodes.length) {
      this.resetView();
      return;
    }
    const bounds = this._contentBounds();
    const rect = this.viewport.getBoundingClientRect();
    if (rect.width < 40 || rect.height < 40) return;

    const pad = 56;
    const scaleX = (rect.width - pad * 2) / Math.max(bounds.width, 1);
    const scaleY = (rect.height - pad * 2) / Math.max(bounds.height, 1);
    this.view.scale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.min(scaleX, scaleY)));
    this.view.x = (rect.width - bounds.width * this.view.scale) / 2 - bounds.x * this.view.scale;
    this.view.y = (rect.height - bounds.height * this.view.scale) / 2 - bounds.y * this.view.scale;
    this._applyViewTransform();
  }

  /** Defer fit until layout and overlays have settled (e.g. after AI generation). */
  scheduleFitToContent() {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => this.fitToContent());
    });
  }

  exportSvg() {
    const clone = this.svg.cloneNode(true);
    clone.removeAttribute("style");
    const world = clone.querySelector(".diagram-world");
    world?.removeAttribute("transform");
    const bounds = this._contentBounds();
    const pad = 40;
    clone.setAttribute(
      "viewBox",
      `${bounds.x - pad} ${bounds.y - pad} ${bounds.width + pad * 2} ${bounds.height + pad * 2}`,
    );
    clone.setAttribute("width", String(bounds.width + pad * 2));
    clone.setAttribute("height", String(bounds.height + pad * 2));
    const grid = clone.querySelector(".layer-grid");
    grid?.remove();
    return new XMLSerializer().serializeToString(clone);
  }

  _contentBounds() {
    if (!this.diagram.nodes.length) return { x: 0, y: 0, width: 800, height: 600 };
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    const margin = 24;
    for (const n of this.diagram.nodes) {
      minX = Math.min(minX, n.x);
      minY = Math.min(minY, n.y);
      maxX = Math.max(maxX, n.x + n.width);
      maxY = Math.max(maxY, n.y + n.height);
    }
    return {
      x: minX - margin,
      y: minY - margin,
      width: maxX - minX + margin * 2,
      height: maxY - minY + margin * 2,
    };
  }

  _applyViewTransform() {
    this.worldLayer.setAttribute(
      "transform",
      `translate(${this.view.x} ${this.view.y}) scale(${this.view.scale})`,
    );
  }

  _screenToWorld(clientX, clientY) {
    const rect = this.viewport.getBoundingClientRect();
    const x = (clientX - rect.left - this.view.x) / this.view.scale;
    const y = (clientY - rect.top - this.view.y) / this.view.scale;
    return { x, y };
  }

  _onContextMenu(e) {
    const hit = this._hitFromEvent(e);
    if (!hit) return;
    e.preventDefault();
    if (!this.selectedIds.has(hit.id)) this.selectOnly(hit.id);
    this.onContextMenu({
      id: hit.id,
      kind: hit.kind,
      clientX: e.clientX,
      clientY: e.clientY,
    });
  }

  _onDoubleClick(e) {
    const hit = this._hitFromEvent(e);
    if (!hit) return;
    e.preventDefault();
    e.stopPropagation();
    this.selectOnly(hit.id);
    this.onRequestRename({ id: hit.id, kind: hit.kind });
  }

  _onWheel(e) {
    e.preventDefault();
    this.zoomBy(e.deltaY < 0 ? 1 : -1, e.clientX, e.clientY);
  }

  _onMouseDown(e) {
    if (e.button === 1 || (e.button === 0 && (e.altKey || this.mode === "pan"))) {
      this.panState = { startX: e.clientX, startY: e.clientY, viewX: this.view.x, viewY: this.view.y };
      e.preventDefault();
      return;
    }

    const hit = this._hitFromEvent(e);
    if (!hit) {
      if (this.mode === "select") this.clearSelection();
      if (this.mode === "connect") {
        this.connectFrom = null;
        this.render();
      }
      return;
    }

    const { id, kind } = hit;
    const world = this._screenToWorld(e.clientX, e.clientY);

    if (this.mode === "connect") {
      e.preventDefault();
      e.stopPropagation();
      if (kind === "node") {
        if (!this.connectFrom) {
          this.connectFrom = id;
          this.selectOnly(id);
          this.render();
        } else if (this.connectFrom !== id) {
          const created = this.addEdge(this.connectFrom, id, this.pendingEdgeType || "connector");
          this.connectFrom = null;
          if (!created) this.render();
        }
      }
      return;
    }

    if (!e.shiftKey) {
      if (!this.selectedIds.has(id)) this.selectOnly(id);
      else this.onSelectionChange(this.getSelection());
    } else {
      if (this.selectedIds.has(id)) this.selectedIds.delete(id);
      else this.selectedIds.add(id);
      this.onSelectionChange(this.getSelection());
      this.render();
    }

    if (kind === "node") {
      const node = this.diagram.nodes.find((n) => n.id === id);
      if (node) {
        e.preventDefault();
        this._saveUndoPoint();
        const selected = this.diagram.nodes.filter((n) => this.selectedIds.has(n.id));
        this.dragState = {
          id,
          startWorldX: world.x,
          startWorldY: world.y,
          moved: false,
          startPositions: selected.map((n) => ({ id: n.id, x: n.x, y: n.y })),
        };
      }
    }
  }

  _onMouseMove(e) {
    if (this.panState) {
      this.view.x = this.panState.viewX + (e.clientX - this.panState.startX);
      this.view.y = this.panState.viewY + (e.clientY - this.panState.startY);
      this._applyViewTransform();
      return;
    }

    if (!this.dragState) return;
    const world = this._screenToWorld(e.clientX, e.clientY);
    const rawDx = world.x - this.dragState.startWorldX;
    const rawDy = world.y - this.dragState.startWorldY;
    const dx = Math.round(rawDx / GRID) * GRID;
    const dy = Math.round(rawDy / GRID) * GRID;
    if (dx === 0 && dy === 0 && !this.dragState.moved) return;

    this.dragState.moved = true;
    for (const pos of this.dragState.startPositions) {
      const n = this.diagram.nodes.find((item) => item.id === pos.id);
      if (n) {
        n.x = pos.x + dx;
        n.y = pos.y + dy;
      }
    }
    this.render();
  }

  _onMouseUp(e) {
    if (this.dragState) {
      const moved = this.dragState.moved;
      this.dragState = null;
      if (moved) this.onChange(this.getDiagram());
      else this.render();
    }
    // Drag-to-connect: release on a different node to create the edge
    if (this.mode === "connect" && this.connectFrom && e) {
      const hit = this._hitFromEvent(e);
      if (hit?.kind === "node" && hit.id !== this.connectFrom) {
        this.addEdge(this.connectFrom, hit.id, this.pendingEdgeType || "connector");
        this.connectFrom = null;
      }
    }
    this.panState = null;
  }

  _onKeyDown(e) {
    if (e.target.matches("input, textarea, select")) return;
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z" && !e.shiftKey) {
      e.preventDefault();
      if (this.undo()) return;
    }
    if (e.key === "Delete" || e.key === "Backspace") {
      e.preventDefault();
      this.deleteSelection();
    }
    if (e.key === "Escape") {
      this.connectFrom = null;
      this.setMode("select");
    }
  }

  render() {
    this._ensureSequenceMessageLayout();
    this._drawGrid();
    this._drawEdges();
    this._drawNodes();
    this._applyViewTransform();
  }

  _isSequenceParticipant(node) {
    return node && ["lifeline", "object", "actor", "activation"].includes(node.type);
  }

  _ensureSequenceMessageLayout() {
    if (this.diagram.diagram_type !== "sequence") return;
    const startY = 88;
    const step = 52;
    let index = 0;
    let maxY = startY;

    // Always re-stack: never trust a shared/collapsed message_y from the model
    // (lifeline vertical centers are ~370 and look like "all edges at one y").
    for (const edge of this.diagram.edges) {
      const from = this.diagram.nodes.find((n) => n.id === edge.from);
      const to = this.diagram.nodes.find((n) => n.id === edge.to);
      if (!from || !to) continue;

      const typedMessage = SEQUENCE_MESSAGE_TYPES.has(edge.type);
      const betweenParticipants =
        this._isSequenceParticipant(from) && this._isSequenceParticipant(to);
      if (!typedMessage && !betweenParticipants) continue;

      if (!SEQUENCE_MESSAGE_TYPES.has(edge.type)) {
        edge.type = "message";
      }

      const y = startY + index * step;
      edge.meta = { ...(edge.meta || {}), message_y: y };
      index += 1;
      maxY = Math.max(maxY, y + 24);
    }

    const minHeight = maxY + 100;
    for (const node of this.diagram.nodes) {
      if (["lifeline", "object", "actor"].includes(node.type) && node.height < minHeight) {
        node.height = minHeight;
      }
    }
  }

  _drawGrid() {
    this.gridLayer.innerHTML = "";
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", "-2000");
    rect.setAttribute("y", "-2000");
    rect.setAttribute("width", "6000");
    rect.setAttribute("height", "6000");
    rect.setAttribute("fill", "url(#grid)");
    this.gridLayer.appendChild(rect);
  }

  _drawEdges() {
    this.edgesLayer.innerHTML = "";
    let sequenceIndex = 0;
    for (const edge of this.diagram.edges) {
      const from = this.diagram.nodes.find((n) => n.id === edge.from);
      const to = this.diagram.nodes.find((n) => n.id === edge.to);
      if (!from || !to) continue;

      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("data-id", edge.id);
      g.setAttribute("data-kind", "edge");
      g.setAttribute("class", `diagram-edge${this.selectedIds.has(edge.id) ? " is-selected" : ""}`);

      // Draw-time sequence Y: do not depend on meta surviving normalize/export
      let points;
      if (this.diagram.diagram_type === "sequence") {
        const isMsg =
          SEQUENCE_MESSAGE_TYPES.has(edge.type) ||
          (this._isSequenceParticipant(from) && this._isSequenceParticipant(to));
        if (isMsg) {
          const y = 88 + sequenceIndex * 52;
          sequenceIndex += 1;
          edge.meta = { ...(edge.meta || {}), message_y: y };
          const cx1 = from.x + from.width / 2;
          const cx2 = to.x + to.width / 2;
          points = { x1: cx1, y1: y, x2: cx2, y2: y };
        }
      }
      const { x1, y1, x2, y2 } = points || this._edgePoints(from, to, edge);
      const isSelected = this.selectedIds.has(edge.id);

      const hitLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
      hitLine.setAttribute("x1", x1);
      hitLine.setAttribute("y1", y1);
      hitLine.setAttribute("x2", x2);
      hitLine.setAttribute("y2", y2);
      hitLine.setAttribute("stroke", "transparent");
      hitLine.setAttribute("stroke-width", "18");
      hitLine.setAttribute("class", "edge-hit");
      g.appendChild(hitLine);

      if (isSelected) {
        const glow = document.createElementNS("http://www.w3.org/2000/svg", "line");
        glow.setAttribute("x1", x1);
        glow.setAttribute("y1", y1);
        glow.setAttribute("x2", x2);
        glow.setAttribute("y2", y2);
        glow.setAttribute("class", "edge-glow");
        glow.setAttribute("stroke", "rgba(37, 99, 235, 0.35)");
        glow.setAttribute("stroke-width", "10");
        glow.setAttribute("stroke-linecap", "round");
        g.appendChild(glow);
      }

      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", x2);
      line.setAttribute("y2", y2);
      line.setAttribute("stroke", "#1e293b");
      line.setAttribute("stroke-width", "2.5");
      this._applyEdgeMarkers(line, edge);

      if (
        edge.type === "include" ||
        edge.type === "extend" ||
        edge.type === "dependency" ||
        edge.type === "realization" ||
        edge.type === "async_message" ||
        edge.type === "wireless" ||
        edge.type === "return_message" ||
        edge.type === "message_flow"
      ) {
        line.setAttribute("stroke-dasharray", "6 4");
      }

      g.appendChild(line);

      if (edge.label) {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", (x1 + x2) / 2);
        text.setAttribute("y", (y1 + y2) / 2 - 6);
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("class", "edge-label");
        text.textContent = edge.label;
        g.appendChild(text);
      }

      this.edgesLayer.appendChild(g);
    }
  }

  _applyEdgeMarkers(line, edge) {
    const t = edge.type;
    line.removeAttribute("marker-start");
    line.removeAttribute("marker-end");

    // Undirected / no arrowhead
    if (t === "association" || t === "network_link" || t === "identifying") {
      if (t === "identifying") {
        line.setAttribute("stroke-width", "2.5");
      }
      return;
    }

    // UML diamonds / triangles
    if (t === "composition") {
      line.setAttribute("marker-end", "url(#diamond-filled)");
      return;
    }
    if (t === "aggregation") {
      line.setAttribute("marker-end", "url(#diamond-end)");
      return;
    }
    if (t === "inheritance" || t === "generalization" || t === "realization") {
      line.setAttribute("marker-end", "url(#triangle-hollow)");
      return;
    }

    // Open arrow (dependency / include / extend / message flow)
    if (
      t === "dependency" ||
      t === "include" ||
      t === "extend" ||
      t === "message_flow"
    ) {
      line.setAttribute("marker-end", "url(#arrow-open)");
      return;
    }

    // Sequence async / return
    if (t === "async_message" || t === "return_message") {
      line.setAttribute("marker-end", "url(#triangle-hollow)");
      return;
    }

    // Crow's-foot ERD (marker on the "near entity" end = marker-end)
    if (t === "one") {
      line.setAttribute("marker-end", "url(#cf-one)");
      return;
    }
    if (t === "many") {
      line.setAttribute("marker-end", "url(#cf-many)");
      return;
    }
    if (t === "one_or_many") {
      line.setAttribute("marker-end", "url(#cf-one-many)");
      return;
    }
    if (t === "zero_or_one") {
      line.setAttribute("marker-end", "url(#cf-zero-one)");
      return;
    }
    if (t === "zero_or_many") {
      line.setAttribute("marker-end", "url(#cf-zero-many)");
      return;
    }
    if (t === "one_to_many") {
      line.setAttribute("marker-start", "url(#cf-one)");
      line.setAttribute("marker-end", "url(#cf-many)");
      return;
    }
    if (t === "many_to_many") {
      line.setAttribute("marker-start", "url(#cf-many)");
      line.setAttribute("marker-end", "url(#cf-many)");
      return;
    }

    // Default directed: filled arrow (flow, data_flow, connector, message, …)
    line.setAttribute("marker-end", "url(#arrow)");
  }

  _edgePoints(from, to, edge = null) {
    const cx1 = from.x + from.width / 2;
    const cx2 = to.x + to.width / 2;
    if (this.diagram.diagram_type === "sequence" && edge) {
      const yRaw = Number(edge.message_y ?? edge.meta?.message_y);
      if (Number.isFinite(yRaw)) {
        return { x1: cx1, y1: yRaw, x2: cx2, y2: yRaw };
      }
      if (
        SEQUENCE_MESSAGE_TYPES.has(edge.type) ||
        (this._isSequenceParticipant(from) && this._isSequenceParticipant(to))
      ) {
        // Last resort: derive from edge list order (never use lifeline center)
        const msgEdges = this.diagram.edges.filter((e) => {
          const a = this.diagram.nodes.find((n) => n.id === e.from);
          const b = this.diagram.nodes.find((n) => n.id === e.to);
          return (
            SEQUENCE_MESSAGE_TYPES.has(e.type) ||
            (this._isSequenceParticipant(a) && this._isSequenceParticipant(b))
          );
        });
        const idx = Math.max(0, msgEdges.findIndex((e) => e.id === edge.id));
        const y = 88 + idx * 52;
        return { x1: cx1, y1: y, x2: cx2, y2: y };
      }
    }
    const cy1 = from.y + from.height / 2;
    const cy2 = to.y + to.height / 2;
    return { x1: cx1, y1: cy1, x2: cx2, y2: cy2 };
  }

  _drawNodes() {
    this.nodesLayer.innerHTML = "";
    this.overlayLayer.innerHTML = "";

    const zOrder = (type) => (["system_boundary", "pool", "lane", "package", "fragment"].includes(type) ? 0 : 1);
    const sorted = [...this.diagram.nodes].sort(
      (a, b) => zOrder(a.type) - zOrder(b.type) || a.y - b.y || a.x - b.x,
    );

    for (const node of sorted) {
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("data-id", node.id);
      g.setAttribute("data-kind", "node");
      g.setAttribute(
        "class",
        `diagram-node node-${node.type}${this.selectedIds.has(node.id) ? " is-selected" : ""}${
          this.connectFrom === node.id ? " is-connect-from" : ""
        }`,
      );
      g.setAttribute("transform", `translate(${node.x}, ${node.y})`);

      this._maybeGrowNodeForLabel(node);
      this._drawNodeShape(g, node);
      this._appendNodeLabel(g, node);

      this.nodesLayer.appendChild(g);
    }

    this._drawSelectionHandles();
  }

  _drawSelectionHandles() {
    for (const node of this.diagram.nodes) {
      if (!this.selectedIds.has(node.id)) continue;
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("class", "selection-handles selection-handles-node");
      g.setAttribute("pointer-events", "none");
      const pad = 6;
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", node.x - pad);
      rect.setAttribute("y", node.y - pad);
      rect.setAttribute("width", node.width + pad * 2);
      rect.setAttribute("height", node.height + pad * 2);
      rect.setAttribute("fill", "rgba(37, 99, 235, 0.08)");
      rect.setAttribute("stroke", "#2563eb");
      rect.setAttribute("stroke-width", "2");
      rect.setAttribute("stroke-dasharray", "6 4");
      rect.setAttribute("rx", "8");
      g.appendChild(rect);
      this.overlayLayer.appendChild(g);
    }

    for (const edge of this.diagram.edges) {
      if (!this.selectedIds.has(edge.id)) continue;
      const from = this.diagram.nodes.find((n) => n.id === edge.from);
      const to = this.diagram.nodes.find((n) => n.id === edge.to);
      if (!from || !to) continue;
      const { x1, y1, x2, y2 } = this._edgePoints(from, to, edge);
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("class", "selection-handles selection-handles-edge");
      g.setAttribute("pointer-events", "none");
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", x2);
      line.setAttribute("y2", y2);
      line.setAttribute("stroke", "#2563eb");
      line.setAttribute("stroke-width", "3");
      line.setAttribute("stroke-dasharray", "8 5");
      line.setAttribute("stroke-linecap", "round");
      g.appendChild(line);
      for (const [cx, cy] of [
        [x1, y1],
        [x2, y2],
        [(x1 + x2) / 2, (y1 + y2) / 2],
      ]) {
        const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        dot.setAttribute("cx", cx);
        dot.setAttribute("cy", cy);
        dot.setAttribute("r", 5);
        dot.setAttribute("fill", "#2563eb");
        dot.setAttribute("stroke", "#fff");
        dot.setAttribute("stroke-width", "2");
        g.appendChild(dot);
      }
      this.overlayLayer.appendChild(g);
    }
  }

  _drawNodeShape(g, node) {
    const { type, width: w, height: h } = node;
    const ns = "http://www.w3.org/2000/svg";

    if (type === "actor") {
      // Stick figure uses FIXED proportions (~72×96 toolbox default).
      // Sequence layout may stretch node.height for hit-testing / message span,
      // but legs must never scale to h — draw a dashed lifeline below the feet instead.
      const cx = w / 2;
      const hipY = 58;
      const footY = 88;
      // Name sits ~124; dashed lifeline starts under the label
      const lifeStartY = 140;

      // Invisible hit target so thin stick-figure strokes are easy to click/drag
      const hit = document.createElementNS(ns, "rect");
      hit.setAttribute("x", 0);
      hit.setAttribute("y", 0);
      hit.setAttribute("width", w);
      hit.setAttribute("height", Math.min(h, 136));
      hit.setAttribute("fill", "transparent");
      hit.setAttribute("pointer-events", "all");
      g.appendChild(hit);

      const head = document.createElementNS(ns, "circle");
      head.setAttribute("cx", cx);
      head.setAttribute("cy", 18);
      head.setAttribute("r", 12);
      head.setAttribute("fill", "none");
      head.setAttribute("stroke", "#334155");
      head.setAttribute("stroke-width", "2");
      const body = document.createElementNS(ns, "line");
      body.setAttribute("x1", cx);
      body.setAttribute("y1", 30);
      body.setAttribute("x2", cx);
      body.setAttribute("y2", hipY);
      body.setAttribute("stroke", "#334155");
      body.setAttribute("stroke-width", "2");
      const arms = document.createElementNS(ns, "line");
      arms.setAttribute("x1", cx - 18);
      arms.setAttribute("y1", 40);
      arms.setAttribute("x2", cx + 18);
      arms.setAttribute("y2", 40);
      arms.setAttribute("stroke", "#334155");
      arms.setAttribute("stroke-width", "2");
      const legs = document.createElementNS(ns, "path");
      legs.setAttribute("d", `M ${cx} ${hipY} L ${cx - 14} ${footY} M ${cx} ${hipY} L ${cx + 14} ${footY}`);
      legs.setAttribute("stroke", "#334155");
      legs.setAttribute("stroke-width", "2");
      legs.setAttribute("fill", "none");
      g.append(head, body, arms, legs);

      if (h > lifeStartY + 8) {
        const life = document.createElementNS(ns, "line");
        life.setAttribute("x1", cx);
        life.setAttribute("y1", lifeStartY);
        life.setAttribute("x2", cx);
        life.setAttribute("y2", h);
        life.setAttribute("stroke", "#64748b");
        life.setAttribute("stroke-width", "2");
        life.setAttribute("stroke-dasharray", "6 4");
        g.appendChild(life);
      }
      return;
    }

    if (type === "use_case") {
      const el = document.createElementNS(ns, "ellipse");
      el.setAttribute("cx", w / 2);
      el.setAttribute("cy", h / 2);
      el.setAttribute("rx", w / 2 - 2);
      el.setAttribute("ry", h / 2 - 2);
      el.setAttribute("fill", "#f0f9ff");
      el.setAttribute("stroke", "#0369a1");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "system_boundary") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 8);
      rect.setAttribute("fill", "rgba(248,250,252,0.5)");
      rect.setAttribute("stroke", "#64748b");
      rect.setAttribute("stroke-width", "2");
      rect.setAttribute("stroke-dasharray", "8 4");
      g.appendChild(rect);
      const title = document.createElementNS(ns, "text");
      title.setAttribute("x", 12);
      title.setAttribute("y", 22);
      title.setAttribute("class", "boundary-label");
      title.textContent = node.label;
      g.appendChild(title);
      return;
    }

    if (type === "note") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("fill", "#fef9c3");
      rect.setAttribute("stroke", "#ca8a04");
      rect.setAttribute("stroke-width", "1.5");
      g.appendChild(rect);
      return;
    }

    if (type === "entity" || type === "weak_entity") {
      // Table-style entity: header + attribute compartment (labels via _appendClassCompartments)
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 4);
      rect.setAttribute("fill", "#eff6ff");
      rect.setAttribute("stroke", "#1d4ed8");
      rect.setAttribute("stroke-width", type === "weak_entity" ? "3" : "2");
      g.appendChild(rect);
      if (type === "weak_entity") {
        const inner = document.createElementNS(ns, "rect");
        inner.setAttribute("x", 4);
        inner.setAttribute("y", 4);
        inner.setAttribute("width", w - 8);
        inner.setAttribute("height", h - 8);
        inner.setAttribute("rx", 2);
        inner.setAttribute("fill", "none");
        inner.setAttribute("stroke", "#1d4ed8");
        inner.setAttribute("stroke-width", "1.5");
        g.appendChild(inner);
      }
      const headerH = 28;
      const div = document.createElementNS(ns, "line");
      div.setAttribute("x1", 0);
      div.setAttribute("y1", headerH);
      div.setAttribute("x2", w);
      div.setAttribute("y2", headerH);
      div.setAttribute("stroke", "#1d4ed8");
      div.setAttribute("stroke-width", "1.5");
      g.appendChild(div);
      return;
    }

    if (type === "attribute") {
      const el = document.createElementNS(ns, "ellipse");
      el.setAttribute("cx", w / 2);
      el.setAttribute("cy", h / 2);
      el.setAttribute("rx", w / 2 - 2);
      el.setAttribute("ry", h / 2 - 2);
      el.setAttribute("fill", "#f5f3ff");
      el.setAttribute("stroke", "#6d28d9");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "relationship") {
      const el = document.createElementNS(ns, "polygon");
      el.setAttribute(
        "points",
        `${w / 2},2 ${w - 2},${h / 2} ${w / 2},${h - 2} 2,${h / 2}`,
      );
      el.setAttribute("fill", "#fff7ed");
      el.setAttribute("stroke", "#c2410c");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "pool") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 6);
      rect.setAttribute("fill", "rgba(248,250,252,0.55)");
      rect.setAttribute("stroke", "#475569");
      rect.setAttribute("stroke-width", "2");
      g.appendChild(rect);
      const band = document.createElementNS(ns, "rect");
      band.setAttribute("width", 28);
      band.setAttribute("height", h);
      band.setAttribute("fill", "#e2e8f0");
      band.setAttribute("stroke", "#475569");
      band.setAttribute("stroke-width", "1.5");
      g.appendChild(band);
      return;
    }

    if (type === "lane") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("fill", "rgba(241,245,249,0.85)");
      rect.setAttribute("stroke", "#94a3b8");
      rect.setAttribute("stroke-width", "1.5");
      g.appendChild(rect);
      const divider = document.createElementNS(ns, "line");
      divider.setAttribute("x1", 120);
      divider.setAttribute("y1", 0);
      divider.setAttribute("x2", 120);
      divider.setAttribute("y2", h);
      divider.setAttribute("stroke", "#94a3b8");
      divider.setAttribute("stroke-width", "1.5");
      g.appendChild(divider);
      return;
    }

    if (type === "decision" || type === "gateway_xor" || type === "gateway_and") {
      const el = document.createElementNS(ns, "polygon");
      el.setAttribute(
        "points",
        `${w / 2},2 ${w - 2},${h / 2} ${w / 2},${h - 2} 2,${h / 2}`,
      );
      el.setAttribute("fill", "#fffbeb");
      el.setAttribute("stroke", "#b45309");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      const cx = w / 2;
      const cy = h / 2;
      if (type === "gateway_xor" || (type === "decision" && this.diagram.diagram_type === "swim_lane")) {
        const xMark = document.createElementNS(ns, "path");
        const s = Math.min(w, h) * 0.22;
        xMark.setAttribute("d", `M ${cx - s} ${cy - s} L ${cx + s} ${cy + s} M ${cx + s} ${cy - s} L ${cx - s} ${cy + s}`);
        xMark.setAttribute("stroke", "#b45309");
        xMark.setAttribute("stroke-width", "2.5");
        xMark.setAttribute("stroke-linecap", "round");
        g.appendChild(xMark);
      } else if (type === "gateway_and") {
        const plus = document.createElementNS(ns, "path");
        const s = Math.min(w, h) * 0.22;
        plus.setAttribute("d", `M ${cx - s} ${cy} L ${cx + s} ${cy} M ${cx} ${cy - s} L ${cx} ${cy + s}`);
        plus.setAttribute("stroke", "#b45309");
        plus.setAttribute("stroke-width", "2.5");
        plus.setAttribute("stroke-linecap", "round");
        g.appendChild(plus);
      }
      return;
    }

    // BPMN start/end = event circles; flowchart terminator stays stadium
    if (type === "start" || type === "end") {
      const r = Math.min(w, h) / 2 - 2;
      const el = document.createElementNS(ns, "circle");
      el.setAttribute("cx", w / 2);
      el.setAttribute("cy", h / 2);
      el.setAttribute("r", r);
      el.setAttribute("fill", type === "end" ? "#fee2e2" : "#dcfce7");
      el.setAttribute("stroke", type === "end" ? "#dc2626" : "#16a34a");
      el.setAttribute("stroke-width", type === "end" ? "3.5" : "2.5");
      g.appendChild(el);
      if (type === "end") {
        const inner = document.createElementNS(ns, "circle");
        inner.setAttribute("cx", w / 2);
        inner.setAttribute("cy", h / 2);
        inner.setAttribute("r", Math.max(4, r - 5));
        inner.setAttribute("fill", "none");
        inner.setAttribute("stroke", "#dc2626");
        inner.setAttribute("stroke-width", "2");
        g.appendChild(inner);
      }
      return;
    }

    if (type === "terminator") {
      const el = document.createElementNS(ns, "rect");
      el.setAttribute("width", w);
      el.setAttribute("height", h);
      el.setAttribute("rx", h / 2);
      el.setAttribute("fill", "#dcfce7");
      el.setAttribute("stroke", "#16a34a");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "service") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 10);
      rect.setAttribute("fill", "#ecfdf5");
      rect.setAttribute("stroke", "#059669");
      rect.setAttribute("stroke-width", "2");
      g.appendChild(rect);
      const bar = document.createElementNS(ns, "rect");
      bar.setAttribute("width", w);
      bar.setAttribute("height", 10);
      bar.setAttribute("rx", 10);
      bar.setAttribute("fill", "#059669");
      g.appendChild(bar);
      return;
    }

    if (type === "api") {
      // Hexagon-ish gateway look (distinct from service)
      const el = document.createElementNS(ns, "polygon");
      const inset = 18;
      el.setAttribute(
        "points",
        `${inset},2 ${w - inset},2 ${w - 2},${h / 2} ${w - inset},${h - 2} ${inset},${h - 2} 2,${h / 2}`,
      );
      el.setAttribute("fill", "#eff6ff");
      el.setAttribute("stroke", "#2563eb");
      el.setAttribute("stroke-width", "2.5");
      g.appendChild(el);
      return;
    }

    if (type === "input" || type === "parallelogram") {
      const el = document.createElementNS(ns, "polygon");
      el.setAttribute(
        "points",
        `16,2 ${w - 2},2 ${w - 16},${h - 2} 2,${h - 2}`,
      );
      el.setAttribute("fill", "#ecfeff");
      el.setAttribute("stroke", "#0891b2");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "document") {
      const path = document.createElementNS(ns, "path");
      path.setAttribute(
        "d",
        `M 2 2 H ${w - 2} V ${h - 14} Q ${w / 2} ${h + 4} 2 ${h - 14} Z`,
      );
      path.setAttribute("fill", "#f8fafc");
      path.setAttribute("stroke", "#475569");
      path.setAttribute("stroke-width", "2");
      g.appendChild(path);
      return;
    }

    if (type === "data_store") {
      const body = document.createElementNS(ns, "path");
      body.setAttribute(
        "d",
        `M 8 8 Q ${w / 2} 0 ${w - 8} 8 V ${h - 8} Q ${w / 2} ${h} 8 ${h - 8} Z`,
      );
      body.setAttribute("fill", "#f1f5f9");
      body.setAttribute("stroke", "#475569");
      body.setAttribute("stroke-width", "2");
      g.appendChild(body);
      return;
    }

    if (type === "text_box") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 4);
      rect.setAttribute("fill", "#fff");
      rect.setAttribute("stroke", "#94a3b8");
      rect.setAttribute("stroke-width", "1.5");
      g.appendChild(rect);
      return;
    }

    if (type === "package" || type === "fragment") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 6);
      rect.setAttribute("fill", type === "fragment" ? "rgba(255,251,235,0.6)" : "rgba(248,250,252,0.55)");
      rect.setAttribute("stroke", "#64748b");
      rect.setAttribute("stroke-width", "2");
      if (type === "fragment") rect.setAttribute("stroke-dasharray", "4 3");
      g.appendChild(rect);
      const tab = document.createElementNS(ns, "rect");
      tab.setAttribute("x", 8);
      tab.setAttribute("y", -12);
      tab.setAttribute("width", Math.min(100, w - 16));
      tab.setAttribute("height", 20);
      tab.setAttribute("rx", 4);
      tab.setAttribute("fill", "#e2e8f0");
      tab.setAttribute("stroke", "#64748b");
      g.appendChild(tab);
      return;
    }

    if (type === "subprocess") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("x", 4);
      rect.setAttribute("y", 4);
      rect.setAttribute("width", w - 8);
      rect.setAttribute("height", h - 8);
      rect.setAttribute("rx", 8);
      rect.setAttribute("fill", "#f8fafc");
      rect.setAttribute("stroke", "#334155");
      rect.setAttribute("stroke-width", "2");
      g.appendChild(rect);
      const inner = document.createElementNS(ns, "rect");
      inner.setAttribute("width", w);
      inner.setAttribute("height", h);
      inner.setAttribute("rx", 10);
      inner.setAttribute("fill", "none");
      inner.setAttribute("stroke", "#334155");
      inner.setAttribute("stroke-width", "2");
      g.appendChild(inner);
      return;
    }

    if (type === "manual_input" || type === "preparation") {
      const el = document.createElementNS(ns, "polygon");
      if (type === "preparation") {
        el.setAttribute("points", `2,${h / 2} ${w / 2},2 ${w - 2},${h / 2} ${w / 2},${h - 2}`);
      } else {
        el.setAttribute("points", `2,2 ${w - 12},2 ${w - 2},${h - 2} 12,${h - 2}`);
      }
      el.setAttribute("fill", "#f8fafc");
      el.setAttribute("stroke", "#334155");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "display") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 4);
      rect.setAttribute("fill", "#f8fafc");
      rect.setAttribute("stroke", "#334155");
      rect.setAttribute("stroke-width", "2");
      g.appendChild(rect);
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", 8);
      line.setAttribute("y1", h - 10);
      line.setAttribute("x2", w - 8);
      line.setAttribute("y2", h - 10);
      line.setAttribute("stroke", "#64748b");
      g.appendChild(line);
      return;
    }

    if (type === "delay") {
      const el = document.createElementNS(ns, "path");
      el.setAttribute("d", `M 4 ${h / 2} Q 4 4 ${w / 2} 4 Q ${w - 4} 4 ${w - 4} ${h / 2} Q ${w - 4} ${h - 4} ${w / 2} ${h - 4} Q 4 ${h - 4} 4 ${h / 2}`);
      el.setAttribute("fill", "#fef3c7");
      el.setAttribute("stroke", "#b45309");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "off_page" || type === "connector_node") {
      const el = document.createElementNS(ns, "polygon");
      el.setAttribute("points", type === "off_page" ? `2,2 ${w - 2},2 ${w - 2},${h - 2} ${w / 2},${h - 2} 2,${h - 2}` : `${w / 2},2 ${w - 2},${h / 2} ${w / 2},${h - 2} 2,${h / 2}`);
      el.setAttribute("fill", "#eef2ff");
      el.setAttribute("stroke", "#4338ca");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "lifeline") {
      const box = document.createElementNS(ns, "rect");
      box.setAttribute("x", 8);
      box.setAttribute("width", w - 16);
      box.setAttribute("height", 36);
      box.setAttribute("rx", 4);
      box.setAttribute("fill", "#fff");
      box.setAttribute("stroke", "#334155");
      box.setAttribute("stroke-width", "2");
      g.appendChild(box);
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", w / 2);
      line.setAttribute("y1", 36);
      line.setAttribute("x2", w / 2);
      line.setAttribute("y2", h);
      line.setAttribute("stroke", "#64748b");
      line.setAttribute("stroke-width", "2");
      line.setAttribute("stroke-dasharray", "6 4");
      g.appendChild(line);
      return;
    }

    if (type === "object") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 6);
      rect.setAttribute("fill", "#fff");
      rect.setAttribute("stroke", "#334155");
      rect.setAttribute("stroke-width", "2");
      g.appendChild(rect);
      return;
    }

    if (type === "activation") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("fill", "#dbeafe");
      rect.setAttribute("stroke", "#2563eb");
      rect.setAttribute("stroke-width", "1.5");
      g.appendChild(rect);
      return;
    }

    if (type === "class" || type === "interface" || type === "enum") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("fill", "#fff");
      rect.setAttribute("stroke", "#1e293b");
      rect.setAttribute("stroke-width", "2");
      g.appendChild(rect);
      const line1 = document.createElementNS(ns, "line");
      line1.setAttribute("x1", 0);
      line1.setAttribute("y1", 28);
      line1.setAttribute("x2", w);
      line1.setAttribute("y2", 28);
      line1.setAttribute("stroke", "#1e293b");
      g.appendChild(line1);
      const line2 = document.createElementNS(ns, "line");
      line2.setAttribute("x1", 0);
      line2.setAttribute("y1", 52);
      line2.setAttribute("x2", w);
      line2.setAttribute("y2", 52);
      line2.setAttribute("stroke", "#1e293b");
      g.appendChild(line2);
      return;
    }

    if (type === "cloud") {
      const path = document.createElementNS(ns, "path");
      path.setAttribute(
        "d",
        `M ${w * 0.2} ${h * 0.65} Q 0 ${h * 0.45} ${w * 0.15} ${h * 0.35} Q ${w * 0.1} ${h * 0.1} ${w * 0.4} ${h * 0.15} Q ${w * 0.55} 0 ${w * 0.75} ${h * 0.12} Q ${w} ${h * 0.15} ${w * 0.92} ${h * 0.4} Q ${w} ${h * 0.65} ${w * 0.75} ${h * 0.65} Z`,
      );
      path.setAttribute("fill", "#e0f2fe");
      path.setAttribute("stroke", "#0284c7");
      path.setAttribute("stroke-width", "2");
      g.appendChild(path);
      return;
    }

    if (type === "router" || type === "switch") {
      const el = document.createElementNS(ns, "polygon");
      el.setAttribute(
        "points",
        type === "router"
          ? `${w / 2},2 ${w - 2},${h * 0.35} ${w * 0.72},${h - 2} ${w * 0.28},${h - 2} 2,${h * 0.35}`
          : `8,2 ${w - 8},2 ${w - 2},${h - 2} 2,${h - 2}`,
      );
      el.setAttribute("fill", "#f1f5f9");
      el.setAttribute("stroke", "#334155");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "firewall") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("fill", "#fef2f2");
      rect.setAttribute("stroke", "#dc2626");
      rect.setAttribute("stroke-width", "3");
      g.appendChild(rect);
      return;
    }

    if (type === "server") {
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("x", 12);
      rect.setAttribute("width", w - 24);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 4);
      rect.setAttribute("fill", "#f8fafc");
      rect.setAttribute("stroke", "#334155");
      rect.setAttribute("stroke-width", "2");
      g.appendChild(rect);
      for (let i = 1; i <= 3; i += 1) {
        const slot = document.createElementNS(ns, "line");
        slot.setAttribute("x1", 16);
        slot.setAttribute("x2", w - 16);
        slot.setAttribute("y1", (h / 4) * i);
        slot.setAttribute("y2", (h / 4) * i);
        slot.setAttribute("stroke", "#94a3b8");
        g.appendChild(slot);
      }
      return;
    }

    if (type === "client" || type === "workstation") {
      const screen = document.createElementNS(ns, "rect");
      screen.setAttribute("x", 8);
      screen.setAttribute("y", 6);
      screen.setAttribute("width", w - 16);
      screen.setAttribute("height", h - 22);
      screen.setAttribute("rx", 3);
      screen.setAttribute("fill", "#fff");
      screen.setAttribute("stroke", "#334155");
      screen.setAttribute("stroke-width", "2");
      g.appendChild(screen);
      const base = document.createElementNS(ns, "rect");
      base.setAttribute("x", w / 2 - 14);
      base.setAttribute("y", h - 14);
      base.setAttribute("width", 28);
      base.setAttribute("height", 8);
      base.setAttribute("fill", "#64748b");
      g.appendChild(base);
      return;
    }

    if (type === "load_balancer") {
      const el = document.createElementNS(ns, "polygon");
      el.setAttribute(
        "points",
        `${w * 0.2},2 ${w * 0.8},2 ${w - 2},${h / 2} ${w * 0.8},${h - 2} ${w * 0.2},${h - 2} 2,${h / 2}`,
      );
      el.setAttribute("fill", "#ecfdf5");
      el.setAttribute("stroke", "#059669");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      const tag = document.createElementNS(ns, "text");
      tag.setAttribute("x", w / 2);
      tag.setAttribute("y", h / 2 + 4);
      tag.setAttribute("text-anchor", "middle");
      tag.setAttribute("class", "node-label");
      tag.setAttribute("font-size", "9");
      tag.setAttribute("font-weight", "700");
      tag.textContent = "LB";
      g.appendChild(tag);
      return;
    }

    // process and default rectangle
    const rect = document.createElementNS(ns, "rect");
    rect.setAttribute("width", w);
    rect.setAttribute("height", h);
    rect.setAttribute("rx", 8);
    rect.setAttribute("fill", "#f8fafc");
    rect.setAttribute("stroke", "#334155");
    rect.setAttribute("stroke-width", "2");
    g.appendChild(rect);
  }

  _labelLayout(node) {
    const type = node.type;
    const w = node.width;
    const h = node.height;
    const fontSize = 9.5;

    if (["decision", "relationship", "gateway_xor", "gateway_and"].includes(type)) {
      return {
        cx: w / 2,
        cy: h / 2,
        maxW: Math.max(28, w * 0.46),
        maxH: Math.max(24, h * 0.46),
        fontSize: 8.5,
        align: "middle",
      };
    }
    if (["input", "parallelogram", "manual_input", "preparation"].includes(type)) {
      return { cx: w / 2, cy: h / 2, maxW: Math.max(36, w - 40), maxH: Math.max(20, h - 14), fontSize, align: "middle" };
    }
    if (type === "terminator") {
      return { cx: w / 2, cy: h / 2, maxW: Math.max(36, w - 28), maxH: Math.max(18, h - 12), fontSize, align: "middle" };
    }
    if (type === "use_case" || type === "attribute") {
      return { cx: w / 2, cy: h / 2, maxW: Math.max(36, w - 20), maxH: Math.max(20, h - 14), fontSize: 9, align: "middle" };
    }
    if (type === "api") {
      return { cx: w / 2, cy: h / 2, maxW: Math.max(36, w - 40), maxH: Math.max(20, h - 16), fontSize, align: "middle" };
    }
    if (["package", "fragment", "cloud", "service"].includes(type)) {
      return { cx: w / 2, cy: 14, maxW: Math.max(36, w - 16), maxH: 34, fontSize, align: "top" };
    }
    if (type === "lifeline" || type === "object") {
      return { cx: w / 2, cy: 16, maxW: Math.max(36, w - 12), maxH: 28, fontSize, align: "top" };
    }
    return {
      cx: w / 2,
      cy: h / 2,
      maxW: Math.max(40, w - 16),
      maxH: Math.max(20, h - 12),
      fontSize,
      align: "middle",
    };
  }

  _canGrowLabelNode(type) {
    return [
      "process",
      "subprocess",
      "input",
      "parallelogram",
      "document",
      "text_box",
      "terminator",
      "manual_input",
      "preparation",
      "data_store",
      "decision",
      "relationship",
      "use_case",
    ].includes(type);
  }

  _maybeGrowNodeForLabel(node) {
    if (!node?.label || !this._canGrowLabelNode(node.type)) return;
    const layout = this._labelLayout(node);
    // Use a tall budget so wrap measures true line count, then grow the node to fit.
    const lines = this._wrapLabelLines(String(node.label), layout.maxW, layout.fontSize, 400);
    const lineHeight = layout.fontSize + 2;
    const neededH = lines.length * lineHeight + (layout.align === "top" ? 20 : 16);
    if (neededH > node.height) {
      node.height = Math.min(220, Math.ceil(neededH));
    }
    const longest = Math.max(...lines.map((l) => l.length), 1);
    const neededW = Math.ceil(longest * layout.fontSize * 0.56 + (node.width - layout.maxW));
    if (neededW > node.width) {
      const nextW = Math.min(280, Math.max(node.width, neededW));
      if (["decision", "relationship"].includes(node.type)) {
        const side = Math.min(168, Math.max(nextW, neededH, node.height));
        node.width = side;
        node.height = side;
      } else {
        node.width = nextW;
      }
    }
  }

  _appendNodeLabel(g, node) {
    if (!node?.label) return;
    const type = node.type;

    if (type === "actor") {
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", node.width / 2);
      label.setAttribute("y", 124);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("class", "node-label");
      label.textContent = node.label;
      g.appendChild(label);
      return;
    }

    if (type === "lane" || type === "pool") {
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", 16);
      label.setAttribute("y", 28);
      label.setAttribute("class", "lane-label");
      label.textContent = node.label;
      g.appendChild(label);
      return;
    }

    if (type === "system_boundary") {
      return; // title drawn with shape
    }

    if (["class", "interface", "enum", "entity", "weak_entity"].includes(type)) {
      this._appendClassCompartments(g, node);
      return;
    }

    if (type === "start" || type === "end") {
      return; // BPMN events are unlabeled icons
    }

    if (type === "gateway_xor" || type === "gateway_and") {
      return; // glyph only
    }

    const layout = this._labelLayout(node);
    this._appendWrappedLabel(
      g,
      node.label,
      layout.cx,
      layout.cy,
      layout.maxW,
      layout.maxH,
      layout.fontSize,
      { align: layout.align },
    );
  }

  _appendWrappedLabel(parent, text, cx, cy, maxWidth, maxHeight, fontSize = 9.5, opts = {}) {
    const align = opts.align || "middle";
    const lines = this._wrapLabelLines(String(text), maxWidth, fontSize, maxHeight);
    const lineHeight = fontSize + 2;
    const startY =
      align === "top" ? cy + fontSize : cy - ((lines.length - 1) * lineHeight) / 2;
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", cx);
    label.setAttribute("y", startY);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "node-label");
    lines.forEach((line, index) => {
      const tspan = document.createElementNS("http://www.w3.org/2000/svg", "tspan");
      tspan.setAttribute("x", cx);
      tspan.setAttribute("dy", index === 0 ? 0 : lineHeight);
      tspan.setAttribute("font-size", String(fontSize));
      tspan.textContent = line;
      label.appendChild(tspan);
    });
    parent.appendChild(label);
  }

  _wrapLabelLines(text, maxWidth, fontSize, maxHeight) {
    const decoded = this._decodeLabel(text).trim();
    const approxChar = Math.max(4, Math.floor(maxWidth / (fontSize * 0.56)));
    const maxLines = Math.max(1, Math.floor(maxHeight / (fontSize + 2)));
    const softParts = decoded.split(/\n+/).flatMap((para) => para.split(/\s+/)).filter(Boolean);
    const tokens = [];
    for (const part of softParts) {
      if (part.length <= approxChar) tokens.push(part);
      else {
        for (let i = 0; i < part.length; i += approxChar) tokens.push(part.slice(i, i + approxChar));
      }
    }

    const lines = [];
    let current = "";
    for (const token of tokens) {
      const next = current ? `${current} ${token}` : token;
      if (next.length > approxChar && current) {
        lines.push(current);
        current = token;
        if (lines.length >= maxLines) {
          current = "";
          break;
        }
      } else {
        current = next;
      }
    }
    if (current && lines.length < maxLines) lines.push(current);

    if (!lines.length) lines.push(decoded.slice(0, approxChar) || " ");
    if (lines.length > maxLines) lines.length = maxLines;

    const full = decoded.replace(/\s+/g, " ");
    const shown = lines.join(" ");
    if (lines.length === maxLines && full.length > shown.length) {
      const last = lines[maxLines - 1];
      lines[maxLines - 1] =
        last.length > 2 ? `${last.slice(0, Math.max(1, last.length - 1))}…` : `${last}…`;
    }
    return lines;
  }

  _decodeLabel(label) {
    // Gemini often emits literal backslash-n instead of real newlines
    return String(label ?? "")
      .replace(/\\r\\n/g, "\n")
      .replace(/\\n/g, "\n")
      .replace(/\\r/g, "\n")
      .replace(/\r\n/g, "\n")
      .replace(/\r/g, "\n");
  }

  _appendClassCompartments(g, node) {
    const ns = "http://www.w3.org/2000/svg";
    const raw = this._decodeLabel(node.label);
    // Split on real newlines OR literal "--" compartment markers
    const sections = raw
      .split(/\n-{2,}\n|\n--\n|(?:^|\n)\s*--\s*(?:\n|$)|\|--\|/)
      .map((s) => s.trim())
      .filter((s, i, arr) => s || i === 0 || i < arr.length - 1);

    let title = (sections[0] || "").split("\n")[0].trim();
    title = title.replace(/^«\s*interface\s*»\s*/i, "").trim();

    const bodyLines = [];
    for (let i = 1; i < sections.length; i += 1) {
      for (const line of sections[i].split("\n")) {
        const trimmed = line.trim();
        if (trimmed && trimmed !== "--") bodyLines.push(trimmed);
      }
    }

    // Fallback: single blob with spaces — still show full label as wrapped lines
    if (!bodyLines.length && sections[0] && sections[0].includes("\n")) {
      const extra = sections[0].split("\n").slice(1).map((l) => l.trim()).filter(Boolean);
      bodyLines.push(...extra);
    }

    if (node.type === "interface") {
      const tag = document.createElementNS(ns, "text");
      tag.setAttribute("x", node.width / 2);
      tag.setAttribute("y", 14);
      tag.setAttribute("text-anchor", "middle");
      tag.setAttribute("class", "node-label");
      tag.setAttribute("font-size", "8");
      tag.textContent = "«interface»";
      g.appendChild(tag);
    }

    const name = document.createElementNS(ns, "text");
    name.setAttribute("x", node.width / 2);
    name.setAttribute("y", node.type === "interface" ? 26 : 16);
    name.setAttribute("text-anchor", "middle");
    name.setAttribute("class", "node-label");
    name.setAttribute("font-size", "10");
    name.setAttribute("font-weight", "600");
    const fallbackName =
      node.type === "interface"
        ? "Interface"
        : node.type === "entity" || node.type === "weak_entity"
          ? "Entity"
          : "Class";
    name.textContent = title || fallbackName;
    g.appendChild(name);

    const lineHeight = 12;
    const startY = node.type === "interface" ? 44 : 36;
    const maxLines = Math.max(0, Math.floor((node.height - startY - 6) / lineHeight));
    if (bodyLines.length && maxLines > 0) {
      const text = document.createElementNS(ns, "text");
      text.setAttribute("x", 8);
      text.setAttribute("y", startY);
      text.setAttribute("class", "node-label");
      text.setAttribute("font-size", "9");
      bodyLines.slice(0, maxLines).forEach((line, index) => {
        const tspan = document.createElementNS(ns, "tspan");
        tspan.setAttribute("x", 8);
        tspan.setAttribute("dy", index === 0 ? 0 : lineHeight);
        tspan.textContent = line;
        text.appendChild(tspan);
      });
      g.appendChild(text);
    }
  }
}
