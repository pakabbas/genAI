import { defaultNodeSize } from "./diagram-types.js";

const BACKGROUND = new Set(["system_boundary", "lane", "package", "fragment"]);

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
      meta: {},
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
      meta: {},
    });
  });

  return out;
}
