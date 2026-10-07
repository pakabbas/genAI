import { defaultNodeSize, nextId } from "./diagram-types.js?v=2.3.2";

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
    arrowPath.setAttribute("fill", "#4a5568");
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
    diamondPath.setAttribute("stroke", "#4a5568");
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
    diamondFilledPath.setAttribute("fill", "#4a5568");
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
    trianglePath.setAttribute("stroke", "#4a5568");
    trianglePath.setAttribute("stroke-width", "1.5");
    triangle.appendChild(trianglePath);
    defs.appendChild(triangle);
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

  addNode(type, label = "", x = 120, y = 120) {
    this._saveUndoPoint();
    const [w, h] = defaultNodeSize(type);
    const node = {
      id: nextId("n", this.diagram.nodes),
      type,
      label: label || type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
      x: Math.round(x / GRID) * GRID,
      y: Math.round(y / GRID) * GRID,
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
    if (fromId === toId) return null;
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
      type,
      meta: {},
    };
    this.diagram.edges.push(edge);
    this.selectOnly(edge.id);
    this.render();
    this.onChange(this.getDiagram());
    return edge;
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
    const target = e.target.closest("[data-id]");
    if (!target) return;
    e.preventDefault();
    const id = target.dataset.id;
    if (!this.selectedIds.has(id)) this.selectOnly(id);
    this.onContextMenu({
      id,
      kind: target.dataset.kind,
      clientX: e.clientX,
      clientY: e.clientY,
    });
  }

  _onDoubleClick(e) {
    const target = e.target.closest("[data-id]");
    if (!target) return;
    e.preventDefault();
    e.stopPropagation();
    const id = target.dataset.id;
    this.selectOnly(id);
    this.onRequestRename({ id, kind: target.dataset.kind });
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

    const target = e.target.closest("[data-id]");
    if (!target) {
      if (this.mode === "select") this.clearSelection();
      return;
    }

    const id = target.dataset.id;
    const kind = target.dataset.kind;
    const world = this._screenToWorld(e.clientX, e.clientY);

    if (this.mode === "connect") {
      if (kind === "node") {
        if (!this.connectFrom) {
          this.connectFrom = id;
        } else if (this.connectFrom !== id) {
          this.addEdge(this.connectFrom, id, this.pendingEdgeType);
          this.connectFrom = null;
        }
      }
      return;
    }

    if (!e.shiftKey) {
      if (!this.selectedIds.has(id)) this.selectOnly(id);
      else {
        this.onSelectionChange(this.getSelection());
        this.render();
      }
    } else {
      if (this.selectedIds.has(id)) this.selectedIds.delete(id);
      else this.selectedIds.add(id);
      this.onSelectionChange(this.getSelection());
      this.render();
    }

    if (kind === "node") {
      const node = this.diagram.nodes.find((n) => n.id === id);
      if (node) {
        this._saveUndoPoint();
        this.dragState = {
          id,
          offsetX: world.x - node.x,
          offsetY: world.y - node.y,
          startPositions: this.diagram.nodes
            .filter((n) => this.selectedIds.has(n.id))
            .map((n) => ({ id: n.id, x: n.x, y: n.y })),
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
    const node = this.diagram.nodes.find((n) => n.id === this.dragState.id);
    if (!node) return;

    const dx = Math.round((world.x - this.dragState.offsetX - this.dragState.startPositions.find((p) => p.id === this.dragState.id).x) / GRID) * GRID;
    const dy = Math.round((world.y - this.dragState.offsetY - this.dragState.startPositions.find((p) => p.id === this.dragState.id).y) / GRID) * GRID;

    for (const pos of this.dragState.startPositions) {
      const n = this.diagram.nodes.find((item) => item.id === pos.id);
      if (n) {
        n.x = pos.x + dx;
        n.y = pos.y + dy;
      }
    }
    this.render();
  }

  _onMouseUp() {
    if (this.dragState) {
      this.dragState = null;
      this.onChange(this.getDiagram());
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
      g.dataset.id = edge.id;
      g.dataset.kind = "edge";
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
      line.setAttribute("stroke", "#4a5568");
      line.setAttribute("stroke-width", "2");
      this._applyEdgeMarkers(line, edge);

      if (
        edge.type === "include" ||
        edge.type === "extend" ||
        edge.type === "dependency" ||
        edge.type === "realization" ||
        edge.type === "async_message" ||
        edge.type === "wireless" ||
        edge.type === "return_message"
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
    if (edge.type === "composition") {
      line.setAttribute("marker-end", "url(#diamond-filled)");
      return;
    }
    if (edge.type === "aggregation") {
      line.setAttribute("marker-end", "url(#diamond-end)");
      return;
    }
    if (
      edge.type === "inheritance" ||
      edge.type === "generalization" ||
      edge.type === "realization"
    ) {
      line.setAttribute("marker-end", "url(#triangle-hollow)");
      return;
    }
    if (edge.type === "async_message" || edge.type === "return_message") {
      line.setAttribute("marker-end", "url(#triangle-hollow)");
      return;
    }
    if (edge.type === "network_link") {
      line.removeAttribute("marker-end");
      return;
    }
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

    const zOrder = (type) => (["system_boundary", "lane", "package", "fragment"].includes(type) ? 0 : 1);
    const sorted = [...this.diagram.nodes].sort(
      (a, b) => zOrder(a.type) - zOrder(b.type) || a.y - b.y || a.x - b.x,
    );

    for (const node of sorted) {
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.dataset.id = node.id;
      g.dataset.kind = "node";
      g.setAttribute(
        "class",
        `diagram-node node-${node.type}${this.selectedIds.has(node.id) ? " is-selected" : ""}`,
      );
      g.setAttribute("transform", `translate(${node.x}, ${node.y})`);

      this._drawNodeShape(g, node);

      if (
        node.type !== "start" &&
        node.type !== "end" &&
        node.type !== "lane" &&
        node.type !== "system_boundary" &&
        node.type !== "relationship" &&
        node.type !== "package" &&
        node.type !== "fragment" &&
        node.type !== "class" &&
        node.type !== "interface" &&
        node.type !== "use_case"
      ) {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", node.width / 2);
        label.setAttribute("y", node.height / 2);
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("dominant-baseline", "middle");
        label.setAttribute("class", "node-label");
        label.textContent = node.label;
        g.appendChild(label);
      } else if (node.type === "use_case" && node.label) {
        this._appendWrappedLabel(g, node.label, node.width / 2, node.height / 2, node.width - 16, node.height - 12, 11);
      } else if (node.type === "lane") {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", 16);
        label.setAttribute("y", 28);
        label.setAttribute("class", "lane-label");
        label.textContent = node.label;
        g.appendChild(label);
      } else if (["class", "interface", "enum"].includes(node.type) && node.label) {
        this._appendClassCompartments(g, node);
      } else if (["package", "fragment", "lifeline", "object", "cloud"].includes(node.type) && node.label) {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", node.width / 2);
        label.setAttribute("y", node.type === "lifeline" ? 24 : 20);
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("class", "node-label");
        label.textContent = node.label;
        g.appendChild(label);
      }

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
      const head = document.createElementNS(ns, "circle");
      head.setAttribute("cx", w / 2);
      head.setAttribute("cy", 18);
      head.setAttribute("r", 12);
      head.setAttribute("fill", "none");
      head.setAttribute("stroke", "#334155");
      head.setAttribute("stroke-width", "2");
      const body = document.createElementNS(ns, "line");
      body.setAttribute("x1", w / 2);
      body.setAttribute("y1", 30);
      body.setAttribute("x2", w / 2);
      body.setAttribute("y2", 58);
      body.setAttribute("stroke", "#334155");
      body.setAttribute("stroke-width", "2");
      const arms = document.createElementNS(ns, "line");
      arms.setAttribute("x1", w / 2 - 18);
      arms.setAttribute("y1", 40);
      arms.setAttribute("x2", w / 2 + 18);
      arms.setAttribute("y2", 40);
      arms.setAttribute("stroke", "#334155");
      arms.setAttribute("stroke-width", "2");
      const legs = document.createElementNS(ns, "path");
      legs.setAttribute("d", `M ${w / 2} 58 L ${w / 2 - 14} ${h - 8} M ${w / 2} 58 L ${w / 2 + 14} ${h - 8}`);
      legs.setAttribute("stroke", "#334155");
      legs.setAttribute("stroke-width", "2");
      legs.setAttribute("fill", "none");
      g.append(head, body, arms, legs);
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
      const rect = document.createElementNS(ns, "rect");
      rect.setAttribute("width", w);
      rect.setAttribute("height", h);
      rect.setAttribute("rx", 4);
      rect.setAttribute("fill", "#eff6ff");
      rect.setAttribute("stroke", "#1d4ed8");
      rect.setAttribute("stroke-width", "2");
      if (type === "weak_entity") rect.setAttribute("stroke-dasharray", "6 3");
      g.appendChild(rect);
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
      const label = document.createElementNS(ns, "text");
      label.setAttribute("x", w / 2);
      label.setAttribute("y", h / 2);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("dominant-baseline", "middle");
      label.setAttribute("class", "node-label");
      label.textContent = node.label;
      g.appendChild(label);
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

    if (type === "decision") {
      const el = document.createElementNS(ns, "polygon");
      el.setAttribute(
        "points",
        `${w / 2},2 ${w - 2},${h / 2} ${w / 2},${h - 2} 2,${h / 2}`,
      );
      el.setAttribute("fill", "#fffbeb");
      el.setAttribute("stroke", "#b45309");
      el.setAttribute("stroke-width", "2");
      g.appendChild(el);
      return;
    }

    if (type === "start" || type === "end" || type === "terminator") {
      const el = document.createElementNS(ns, "rect");
      el.setAttribute("width", w);
      el.setAttribute("height", h);
      el.setAttribute("rx", h / 2);
      el.setAttribute("fill", type === "end" ? "#fee2e2" : "#dcfce7");
      el.setAttribute("stroke", type === "end" ? "#dc2626" : "#16a34a");
      el.setAttribute("stroke-width", type === "end" ? "3" : "2");
      g.appendChild(el);
      if (node.label) {
        const label = document.createElementNS(ns, "text");
        label.setAttribute("x", w / 2);
        label.setAttribute("y", h / 2);
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("dominant-baseline", "middle");
        label.setAttribute("class", "node-label");
        label.textContent = node.label;
        g.appendChild(label);
      }
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
      tag.setAttribute("font-size", "11");
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

  _appendWrappedLabel(parent, text, cx, cy, maxWidth, maxHeight, fontSize = 12) {
    const lines = this._wrapLabelLines(String(text), maxWidth, fontSize, maxHeight);
    const lineHeight = fontSize + 2;
    const startY = cy - ((lines.length - 1) * lineHeight) / 2;
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
    const approxChar = Math.max(4, Math.floor(maxWidth / (fontSize * 0.55)));
    const maxLines = Math.max(1, Math.floor(maxHeight / (fontSize + 2)));
    const words = text.split(/\s+/).filter(Boolean);
    const lines = [];
    let current = "";
    for (const word of words) {
      const next = current ? `${current} ${word}` : word;
      if (next.length > approxChar && current) {
        lines.push(current);
        current = word;
      } else {
        current = next;
      }
      if (lines.length >= maxLines) break;
    }
    if (current && lines.length < maxLines) lines.push(current);
    if (lines.length > maxLines) return lines.slice(0, maxLines);
    if (lines.length === maxLines && words.join(" ").length > lines.join(" ").length) {
      const last = lines[maxLines - 1];
      lines[maxLines - 1] = last.length > 3 ? `${last.slice(0, Math.max(0, last.length - 1))}…` : `${last}…`;
    }
    return lines.length ? lines : [text.slice(0, approxChar)];
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
      tag.setAttribute("font-size", "10");
      tag.textContent = "«interface»";
      g.appendChild(tag);
    }

    const name = document.createElementNS(ns, "text");
    name.setAttribute("x", node.width / 2);
    name.setAttribute("y", node.type === "interface" ? 28 : 18);
    name.setAttribute("text-anchor", "middle");
    name.setAttribute("class", "node-label");
    name.setAttribute("font-weight", "600");
    name.textContent = title || (node.type === "interface" ? "Interface" : "Class");
    g.appendChild(name);

    const lineHeight = 14;
    const startY = node.type === "interface" ? 48 : 40;
    const maxLines = Math.max(0, Math.floor((node.height - startY - 6) / lineHeight));
    if (bodyLines.length && maxLines > 0) {
      const text = document.createElementNS(ns, "text");
      text.setAttribute("x", 8);
      text.setAttribute("y", startY);
      text.setAttribute("class", "node-label");
      text.setAttribute("font-size", "11");
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
