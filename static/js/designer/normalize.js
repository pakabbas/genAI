import { defaultNodeSize } from "./diagram-types.js";

const BACKGROUND = new Set(["system_boundary", "lane", "package", "fragment"]);
const SEQUENCE_MESSAGE_TYPES = new Set(["message", "async_message", "return_message"]);
const SEQUENCE_LIFELINE_TYPES = new Set(["lifeline", "object", "actor"]);
const SEQUENCE_MESSAGE_START_Y = 88;
const SEQUENCE_MESSAGE_STEP = 52;

function sanitizeMeta(meta) {
  if (!meta || typeof meta !== "object") return {};
  const forbidden = new Set(["src", "href", "url", "image", "svg", "html", "base64", "data"]);
  const clean = {};
  for (const [key, value] of Object.entries(meta)) {
    if (forbidden.has(String(key).toLowerCase())) continue;
    if (typeof value === "string" && (value.toLowerCase().includes("<svg") || value.toLowerCase().includes("data:image"))) {
      continue;
    }
    clean[key] = value;
  }
  return clean;
}

function layoutSequenceMessages(diagram) {
  if (diagram.diagram_type !== "sequence") return diagram;
  const hasMessages = (diagram.edges || []).some((e) => SEQUENCE_MESSAGE_TYPES.has(e.type));
  if (!hasMessages) return diagram;

  let messageIndex = 0;
  let maxY = SEQUENCE_MESSAGE_START_Y;
  const edges = (diagram.edges || []).map((edge) => {
    if (!SEQUENCE_MESSAGE_TYPES.has(edge.type)) return edge;
    const y =
      typeof edge.meta?.message_y === "number"
        ? edge.meta.message_y
        : SEQUENCE_MESSAGE_START_Y + messageIndex * SEQUENCE_MESSAGE_STEP;
    messageIndex += 1;
    maxY = Math.max(maxY, y + 24);
    return {
      ...edge,
      meta: { ...(edge.meta || {}), message_y: y },
    };
  });

  const minHeight = maxY + 80;
  const nodes = (diagram.nodes || []).map((node) => {
    if (SEQUENCE_LIFELINE_TYPES.has(node.type) && node.height < minHeight) {
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

  // Network toolbox uses id "database" with shape "data_store"
  if (!nodesById.database && nodesById.data_store) nodesById.database = "data_store";
  if (!nodesById.data_store && nodesById.database) nodesById.data_store = nodesById.database;

  const defaultNode = toolboxItems.find((i) => i.kind === "node")?.shape || "process";
  const defaultEdge = toolboxItems.find((i) => i.kind === "edge")?.shape || "connector";

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
    const type = nodesById[rawType] || nodesById[defaultNode] || defaultNode;
    const [dw, dh] = defaultNodeSize(type);

    out.nodes.push({
      id,
      type,
      label: String(node.label || "").trim(),
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
    out.edges.push({
      id: edge.id || `e${index + 1}`,
      from,
      to,
      label: String(edge.label || "").trim(),
      type: edgesById[rawType] || edgesById[defaultEdge] || defaultEdge,
      meta: sanitizeMeta(edge.meta),
    });
  });

  return layoutSequenceMessages(out);
}
