import { defaultNodeSize } from "./diagram-types.js?v=2.5.1";

const BACKGROUND = new Set(["system_boundary", "pool", "lane", "package", "fragment"]);
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
  actor: "actor",
  user: "actor",
  person: "actor",
  stickfigure: "actor",
  database: "data_store",
  db: "data_store",
  load_balancer: "load_balancer",
  loadbalancer: "load_balancer",
  lb: "load_balancer",
  service: "service",
  microservice: "service",
  api: "api",
  api_gateway: "api",
  gateway_xor: "gateway_xor",
  gateway_and: "gateway_and",
  xor: "gateway_xor",
  pool: "pool",
};

const HUMAN_PARTICIPANT =
  /^(user|actor|customer|person|human|visitor|guest|member|admin|employee|student|patient|buyer|seller|operator|clerk|cashier|driver|rider|end[\s_-]?user|enduser)s?\b/i;

function isHumanSequenceLabel(label) {
  const text = String(label || "").trim();
  if (!text) return false;
  if (HUMAN_PARTICIPANT.test(text)) return true;
  return ["user", "actor", "customer", "person", "admin"].includes(text.toLowerCase());
}

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
  if (!["class", "interface", "enum", "entity", "weak_entity"].includes(type)) return label;
  let text = String(label || "")
    .replace(/\\r\\n/g, "\n")
    .replace(/\\n/g, "\n")
    .replace(/\\r/g, "\n")
    .replace(/\\t/g, "\t")
    .trim();
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

function renumberSequenceLabels(edges) {
  const msg = edges.filter((e) => SEQUENCE_MESSAGE_TYPES.has(e.type));
  if (!msg.length) return edges;
  const numbered = msg.some((e) => /^\d+\s*[.):\-]/.test(String(e.label || "").trim()));
  if (!numbered) return edges;
  const ordered = [...msg].sort(
    (a, b) => Number(a.meta?.message_y || 0) - Number(b.meta?.message_y || 0) || String(a.id).localeCompare(String(b.id)),
  );
  const idToNum = new Map(ordered.map((e, i) => [e.id, i + 1]));
  return edges.map((edge) => {
    const num = idToNum.get(edge.id);
    if (!num) return edge;
    const label = String(edge.label || "").trim();
    const m = label.match(/^\d+\s*[.):\-]\s*(.*)$/);
    const rest = m ? m[1].trim() : label;
    return { ...edge, label: rest ? `${num}. ${rest}` : `${num}.` };
  });
}

function layoutSequenceMessages(diagram) {
  if (diagram.diagram_type !== "sequence") return diagram;

  let messageIndex = 0;
  let maxY = SEQUENCE_MESSAGE_START_Y;
  let edges = (diagram.edges || []).map((edge) => {
    const resolved = resolveSequenceEdgeType(edge.type) || edge.type;
    const isMessage =
      SEQUENCE_MESSAGE_TYPES.has(resolved) ||
      SEQUENCE_MESSAGE_TYPES.has(edge.type) ||
      (diagram.diagram_type === "sequence" && edge.type === "connector");

    if (!isMessage) return { ...edge, type: resolved || edge.type };

    const y = SEQUENCE_MESSAGE_START_Y + messageIndex * SEQUENCE_MESSAGE_STEP;
    messageIndex += 1;
    maxY = Math.max(maxY, y + 24);
    return {
      ...edge,
      type: SEQUENCE_MESSAGE_TYPES.has(resolved) ? resolved : edge.type === "connector" ? "message" : edge.type,
      meta: { ...(edge.meta || {}), message_y: y },
    };
  });
  edges = renumberSequenceLabels(edges);

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
  const isArchitecture = diagram.diagram_type === "architecture";
  const isSwimLane = diagram.diagram_type === "swim_lane";
  const actorAllowed = Boolean(nodesById.actor) || toolboxItems.some((i) => i.shape === "actor");

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

    let label = String(node.label || "").trim();

    // Sequence: humans must stay type actor (stick figure), never lifeline/object box
    if (isSequence && actorAllowed && (type === "lifeline" || type === "object") && isHumanSequenceLabel(label)) {
      type = nodesById.actor || "actor";
    }

    if (isArchitecture) {
      const processLike = [
        "api",
        "apigateway",
        "api_gateway",
        "service",
        "microservice",
        "process",
        "task",
        "activity",
        "box",
        "rectangle",
      ].includes(rawType);
      if (
        ["api", "apigateway", "api_gateway"].includes(rawType) ||
        (processLike && /\b(api|gateway)\b/i.test(label))
      ) {
        type = nodesById.api || "api";
      } else if (processLike) {
        type = nodesById.service || "service";
      }
    }

    if (isSwimLane) {
      if (["decision", "gateway", "xor", "exclusive_gateway"].includes(rawType) || type === "decision") {
        type = nodesById.gateway_xor || "gateway_xor";
      }
      if (["and", "gateway_and", "parallel_gateway"].includes(rawType)) {
        type = nodesById.gateway_and || "gateway_and";
      }
    }

    const [dw, dh] = defaultNodeSize(type);
    label = formatClassLabel(label, type);

    let width = Number(node.width) > 0 ? Number(node.width) : dw;
    let height = Number(node.height) > 0 ? Number(node.height) : dh;
    if (type === "actor") {
      width = dw;
      height = Math.max(dh, height);
    }

    out.nodes.push({
      id,
      type,
      label,
      x: Number(node.x) || 40 + index * 24,
      y: Number(node.y) || 40 + index * 24,
      width,
      height,
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
    } else if (isSwimLane && ["connector", "message_flow", "messageflow"].includes(rawType)) {
      type = edgesById.message_flow || "message_flow";
    } else if (isArchitecture && ["connector", "arrow", "data_flow", "dataflow"].includes(rawType)) {
      type = edgesById.data_flow || "data_flow";
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
