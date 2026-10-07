import { defaultNodeSize } from "./diagram-types.js";

const BACKGROUND = new Set(["system_boundary", "lane", "package", "fragment"]);
const SEQUENCE_MESSAGE_TYPES = new Set(["message", "async_message", "return_message"]);
const SEQUENCE_LIFELINE_TYPES = new Set(["lifeline", "object", "actor"]);
const SEQUENCE_MESSAGE_START_Y = 88;
const SEQUENCE_MESSAGE_STEP = 52;

const SEQUENCE_EDGE_ALIASES = {
  message: "message",
  sync: "message",
  sync_message: "message",
  call: "message",
  async_message: "async_message",
  async: "async_message",
  asynchronous: "async_message",
  return_message: "return_message",
  return: "return_message",
  reply: "return_message",
};

const NODE_ALIASES = {
  database: "data_store",
  db: "data_store",
  load_balancer: "load_balancer",
  loadbalancer: "load_balancer",
  lb: "load_balancer",
  service: "process",
  api: "process",
  api_gateway: "process",
};

function sanitizeMeta(meta) {
  if (!meta || typeof meta !== "object") return {};
  const forbidden = new Set(["src", "href", "url", "image", "svg", "html", "base64", "data"]);
  const clean = {};
  for (const [key, value] of Object.entries(meta)) {
    if (forbidden.has(String(key).toLowerCase())) continue;
    if (
      typeof value === "string" &&
      (value.toLowerCase().includes("<svg") || value.toLowerCase().includes("data:image"))
    ) {
      continue;
    }
    clean[key] = value;
  }
  if (clean.message_y != null && clean.message_y !== "") {
    const y = Number(clean.message_y);
    if (Number.isFinite(y)) clean.message_y = y;
    else delete clean.message_y;
  }
  return clean;
}

function resolveSequenceEdgeType(rawType) {
  const key = String(rawType || "")
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  return SEQUENCE_EDGE_ALIASES[key] || null;
}

function formatClassLabel(label, type) {
  if (!["class", "interface", "enum"].includes(type)) return label;
  let text = String(label || "").replace(/\\n/g, "\n").trim();
  if (!text) return type === "interface" ? "Interface" : "Class";
  if (/\n-{2,}\n/.test(text) || text.includes("\n--\n")) return text;

  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length <= 1) {
    // Single-line "Name | attr; attr | method()" style
    const chunks = text.split(/\s*\|\s*|\s*;\s*/).map((c) => c.trim()).filter(Boolean);
    if (chunks.length <= 1) return text;
    const name = chunks[0];
    const rest = chunks.slice(1);
    const methods = rest.filter((l) => /\(.*\)/.test(l));
    const attrs = rest.filter((l) => !methods.includes(l));
    const parts = [name];
    if (attrs.length) parts.push("--", ...attrs);
    if (methods.length) parts.push("--", ...methods);
    return parts.join("\n");
  }

  const name = lines[0];
  const rest = lines.slice(1);
  const methods = rest.filter((l) => /\(.*\)/.test(l) || l.startsWith("+"));
  const attrs = rest.filter((l) => !methods.includes(l));
  const parts = [name];
  if (attrs.length) parts.push("--", ...attrs);
  if (methods.length) parts.push("--", ...methods);
  else if (!attrs.length && rest.length) parts.push("--", ...rest);
  return parts.join("\n");
}

function layoutSequenceMessages(diagram) {
  if (diagram.diagram_type !== "sequence") return diagram;

  let messageIndex = 0;
  let maxY = SEQUENCE_MESSAGE_START_Y;
  const edges = (diagram.edges || []).map((edge) => {
    const resolved = resolveSequenceEdgeType(edge.type) || edge.type;
    const isMessage =
      SEQUENCE_MESSAGE_TYPES.has(resolved) ||
      SEQUENCE_MESSAGE_TYPES.has(edge.type) ||
      // Remapped "connector" between participants still needs stacking
      (diagram.diagram_type === "sequence" && edge.type === "connector");

    if (!isMessage) return { ...edge, type: resolved || edge.type };

    const existing = Number(edge.meta?.message_y);
    const y = Number.isFinite(existing)
      ? existing
      : SEQUENCE_MESSAGE_START_Y + messageIndex * SEQUENCE_MESSAGE_STEP;
    messageIndex += 1;
    maxY = Math.max(maxY, y + 24);
    return {
      ...edge,
      type: SEQUENCE_MESSAGE_TYPES.has(resolved) ? resolved : edge.type === "connector" ? "message" : edge.type,
      meta: { ...(edge.meta || {}), message_y: y },
    };
  });

  const minHeight = maxY + 100;
  const nodes = (diagram.nodes || []).map((node) => {
    if (SEQUENCE_LIFELINE_TYPES.has(node.type) && Number(node.height) < minHeight) {
      return { ...node, height: minHeight };
    }
    return node;
  });

  return { ...diagram, nodes, edges };
}

export function normalizeDiagram(diagram, toolboxItems = []) {
  const nodesById = {};
  const edgesById = {};
  for (const item of toolboxItems) {
    if (item.kind === "node") {
      nodesById[item.id] = item.shape;
      nodesById[item.shape] = item.shape;
    } else {
      edgesById[item.id] = item.shape;
      edgesById[item.shape] = item.shape;
    }
  }

  if (!nodesById.database && nodesById.data_store) nodesById.database = "data_store";
  if (!nodesById.data_store && nodesById.database) nodesById.data_store = nodesById.database;
  if (!nodesById.lb && nodesById.load_balancer) nodesById.lb = "load_balancer";
  if (!nodesById.loadbalancer && nodesById.load_balancer) nodesById.loadbalancer = "load_balancer";

  const defaultNode = toolboxItems.find((i) => i.kind === "node")?.shape || "process";
  const defaultEdge = toolboxItems.find((i) => i.kind === "edge")?.shape || "connector";
  const isSequence = diagram.diagram_type === "sequence";

  const out = {
    diagram_type: diagram.diagram_type,
    title: diagram.title || "Untitled Diagram",
    nodes: [],
    edges: [],
  };

  const seen = new Set();
  (diagram.nodes || []).forEach((node, index) => {
    let id = node.id || `n${index + 1}`;
    if (seen.has(id)) id = `n${index + 1}`;
    seen.add(id);

    const rawType = String(node.type || "").toLowerCase().replace(/[\s-]+/g, "_");
    const aliased = NODE_ALIASES[rawType];
    let type =
      nodesById[rawType] ||
      (aliased && nodesById[aliased]) ||
      aliased ||
      nodesById[defaultNode] ||
      defaultNode;
    // Prefer shape ids that exist in size table
    if (aliased && (nodesById[aliased] || !toolboxItems.length)) {
      type = nodesById[aliased] || aliased;
    }

    const [dw, dh] = defaultNodeSize(type);
    let label = String(node.label || "").trim();
    label = formatClassLabel(label, type);

    out.nodes.push({
      id,
      type,
      label,
      x: Number(node.x) || 40 + index * 24,
      y: Number(node.y) || 40 + index * 24,
      width: Number(node.width) > 0 ? Number(node.width) : dw,
      height: Number(node.height) > 0 ? Number(node.height) : dh,
      meta: sanitizeMeta(node.meta),
    });
  });

  out.nodes.sort((a, b) => {
    const az = BACKGROUND.has(a.type) ? 0 : 1;
    const bz = BACKGROUND.has(b.type) ? 0 : 1;
    return az - bz || a.y - b.y || a.x - b.x;
  });

  const ids = new Set(out.nodes.map((n) => n.id));
  (diagram.edges || []).forEach((edge, index) => {
    const from = edge.from || edge.from_node;
    const to = edge.to || edge.to_node;
    if (!from || !to || !ids.has(from) || !ids.has(to) || from === to) return;
    const rawType = String(edge.type || "").toLowerCase().replace(/[\s-]+/g, "_");

    let type;
    if (isSequence) {
      type =
        resolveSequenceEdgeType(rawType) ||
        edgesById[rawType] ||
        (SEQUENCE_MESSAGE_TYPES.has(rawType) ? rawType : null) ||
        "message";
    } else {
      type = edgesById[rawType] || edgesById[defaultEdge] || defaultEdge;
    }

    out.edges.push({
      id: edge.id || `e${index + 1}`,
      from,
      to,
      label: String(edge.label || "").trim(),
      type,
      meta: sanitizeMeta(edge.meta),
    });
  });

  return layoutSequenceMessages(out);
}
