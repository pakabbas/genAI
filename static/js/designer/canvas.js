import { defaultNodeSize, nextId } from "./diagram-types.js";

const GRID = 20;
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 2.5;

export class DiagramCanvas {
  constructor(container, options = {}) {
    this.container = container;
    this.onChange = options.onChange || (() => {});
    this.onSelectionChange = options.onSelectionChange || (() => {});

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

    this.svg.append(this.gridLayer, this.edgesLayer, this.nodesLayer, this.overlayLayer);
    this.viewport.appendChild(this.svg);
    this.container.appendChild(this.viewport);
  }

  _buildMarkers() {
    const defs = this.defs;
    defs.innerHTML = "";

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
    diamondPath.setAttribute("fill", "#4a5568");
    diamond.appendChild(diamondPath);
    defs.appendChild(diamond);
  }

  _bindEvents() {
    this.viewport.addEventListener("wheel", (e) => this._onWheel(e), { passive: false });
    this.svg.addEventListener("mousedown", (e) => this._onMouseDown(e));
    window.addEventListener("mousemove", (e) => this._onMouseMove(e));
    window.addEventListener("mouseup", (e) => this._onMouseUp(e));
    window.addEventListener("keydown", (e) => this._onKeyDown(e));
  }

  setDiagram(diagram) {
    this.diagram = JSON.parse(JSON.stringify(diagram));
    this.selectedIds.clear();
    this.connectFrom = null;
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
    this.onChange(this.getDiagram());
  }

  addNode(type, label = "", x = 120, y = 120) {
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

  deleteSelection() {
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
    const pad = 48;
    const scaleX = (rect.width - pad * 2) / bounds.width;
    const scaleY = (rect.height - pad * 2) / bounds.height;
    this.view.scale = Math.min(1.2, Math.max(MIN_ZOOM, Math.min(scaleX, scaleY)));
    this.view.x = (rect.width - bounds.width * this.view.scale) / 2 - bounds.x * this.view.scale;
    this.view.y = (rect.height - bounds.height * this.view.scale) / 2 - bounds.y * this.view.scale;
    this._applyViewTransform();
  }

  exportSvg() {
    const clone = this.svg.cloneNode(true);
    clone.removeAttribute("style");
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
    for (const n of this.diagram.nodes) {
      minX = Math.min(minX, n.x);
      minY = Math.min(minY, n.y);
      maxX = Math.max(maxX, n.x + n.width);
      maxY = Math.max(maxY, n.y + n.height);
    }
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  }

  _applyViewTransform() {
    this.svg.style.transform = `translate(${this.view.x}px, ${this.view.y}px) scale(${this.view.scale})`;
    this.svg.style.transformOrigin = "0 0";
  }

  _screenToWorld(clientX, clientY) {
    const rect = this.viewport.getBoundingClientRect();
    const x = (clientX - rect.left - this.view.x) / this.view.scale;
    const y = (clientY - rect.top - this.view.y) / this.view.scale;
    return { x, y };
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
    } else {
      if (this.selectedIds.has(id)) this.selectedIds.delete(id);
      else this.selectedIds.add(id);
      this.onSelectionChange(this.getSelection());
      this.render();
    }

    if (kind === "node") {
      const node = this.diagram.nodes.find((n) => n.id === id);
      if (node) {
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
    this._drawGrid();
    this._drawEdges();
    this._drawNodes();
    this._applyViewTransform();
  }

  _drawGrid() {
    this.gridLayer.innerHTML = "";
    const pattern = document.createElementNS("http://www.w3.org/2000/svg", "pattern");
    pattern.setAttribute("id", "grid");
    pattern.setAttribute("width", String(GRID));
    pattern.setAttribute("height", String(GRID));
    pattern.setAttribute("patternUnits", "userSpaceOnUse");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", `M ${GRID} 0 L 0 0 0 ${GRID}`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#e8ecf4");
    path.setAttribute("stroke-width", "1");
    pattern.appendChild(path);
    this.defs.appendChild(pattern);

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
    for (const edge of this.diagram.edges) {
      const from = this.diagram.nodes.find((n) => n.id === edge.from);
      const to = this.diagram.nodes.find((n) => n.id === edge.to);
      if (!from || !to) continue;

      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.dataset.id = edge.id;
      g.dataset.kind = "edge";
      g.setAttribute("class", `diagram-edge${this.selectedIds.has(edge.id) ? " is-selected" : ""}`);

      const { x1, y1, x2, y2 } = this._edgePoints(from, to);
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("x1", x1);
      line.setAttribute("y1", y1);
      line.setAttribute("x2", x2);
      line.setAttribute("y2", y2);
      line.setAttribute("stroke", "#4a5568");
      line.setAttribute("stroke-width", "2");
      line.setAttribute("marker-end", "url(#arrow)");

      if (edge.type === "include" || edge.type === "extend" || edge.type === "dependency" || edge.type === "async_message" || edge.type === "wireless" || edge.type === "return_message") {
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

  _edgePoints(from, to) {
    const cx1 = from.x + from.width / 2;
    const cy1 = from.y + from.height / 2;
    const cx2 = to.x + to.width / 2;
    const cy2 = to.y + to.height / 2;
    return {
      x1: cx1,
      y1: cy1,
      x2: cx2,
      y2: cy2,
    };
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
        node.type !== "interface"
      ) {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", node.width / 2);
        label.setAttribute("y", node.height / 2);
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("dominant-baseline", "middle");
        label.setAttribute("class", "node-label");
        label.textContent = node.label;
        g.appendChild(label);
      } else if (node.type === "lane") {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", 16);
        label.setAttribute("y", 28);
        label.setAttribute("class", "lane-label");
        label.textContent = node.label;
        g.appendChild(label);
      } else if (["package", "fragment", "lifeline", "object", "cloud", "class", "enum"].includes(node.type) && node.label) {
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", node.type === "lane" ? 16 : node.width / 2);
        label.setAttribute("y", node.type === "class" || node.type === "enum" ? 18 : node.type === "lifeline" ? 24 : 20);
        label.setAttribute("text-anchor", node.type === "lane" ? "start" : "middle");
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
      g.setAttribute("class", "selection-handles");
      g.setAttribute("pointer-events", "none");
      const pad = 4;
      const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", node.x - pad);
      rect.setAttribute("y", node.y - pad);
      rect.setAttribute("width", node.width + pad * 2);
      rect.setAttribute("height", node.height + pad * 2);
      rect.setAttribute("fill", "none");
      rect.setAttribute("stroke", "#6c7cff");
      rect.setAttribute("stroke-width", "2");
      rect.setAttribute("stroke-dasharray", "5 3");
      rect.setAttribute("rx", "6");
      g.appendChild(rect);
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
      if (type === "interface") {
        const tag = document.createElementNS(ns, "text");
        tag.setAttribute("x", w / 2);
        tag.setAttribute("y", 18);
        tag.setAttribute("text-anchor", "middle");
        tag.setAttribute("class", "node-label");
        tag.textContent = "«interface»";
        g.appendChild(tag);
      }
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
}
