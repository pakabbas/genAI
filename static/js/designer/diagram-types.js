export const DIAGRAM_TYPE_LABELS = {
  use_case: "Use Case Diagram",
  erd: "Entity Relationship (ERD)",
  swim_lane: "Swim Lane / BPMN",
  flowchart: "Flowchart",
  sequence: "Sequence Diagram",
  class_diagram: "Class Diagram",
  network: "Network Diagram",
};

export const SAMPLE_DIAGRAMS = {
  use_case: {
    diagram_type: "use_case",
    title: "Online Bookstore",
    nodes: [
      { id: "n1", type: "system_boundary", label: "Bookstore System", x: 220, y: 80, width: 420, height: 320 },
      { id: "n2", type: "actor", label: "Customer", x: 60, y: 200, width: 72, height: 96 },
      { id: "n3", type: "actor", label: "Admin", x: 60, y: 380, width: 72, height: 96 },
      { id: "n4", type: "use_case", label: "Browse Catalog", x: 280, y: 140, width: 140, height: 56 },
      { id: "n5", type: "use_case", label: "Place Order", x: 480, y: 140, width: 140, height: 56 },
      { id: "n6", type: "use_case", label: "Manage Inventory", x: 380, y: 300, width: 160, height: 56 },
    ],
    edges: [
      { id: "e1", from: "n2", to: "n4", label: "", type: "association" },
      { id: "e2", from: "n2", to: "n5", label: "", type: "association" },
      { id: "e3", from: "n3", to: "n6", label: "", type: "association" },
      { id: "e4", from: "n5", to: "n4", label: "«include»", type: "include" },
    ],
  },
  erd: {
    diagram_type: "erd",
    title: "Library Database",
    nodes: [
      { id: "n1", type: "entity", label: "Book", x: 120, y: 180, width: 140, height: 72 },
      { id: "n2", type: "entity", label: "Member", x: 520, y: 180, width: 140, height: 72 },
      { id: "n3", type: "relationship", label: "Borrows", x: 320, y: 170, width: 72, height: 72 },
      { id: "n4", type: "attribute", label: "ISBN (PK)", x: 80, y: 60, width: 120, height: 44 },
      { id: "n5", type: "attribute", label: "Title", x: 220, y: 60, width: 100, height: 44 },
      { id: "n6", type: "attribute", label: "MemberID (PK)", x: 500, y: 60, width: 130, height: 44 },
    ],
    edges: [
      { id: "e1", from: "n4", to: "n1", label: "", type: "identifying" },
      { id: "e2", from: "n5", to: "n1", label: "", type: "identifying" },
      { id: "e3", from: "n6", to: "n2", label: "", type: "identifying" },
      { id: "e4", from: "n1", to: "n3", label: "N", type: "one_to_many" },
      { id: "e5", from: "n3", to: "n2", label: "M", type: "many_to_many" },
    ],
  },
  swim_lane: {
    diagram_type: "swim_lane",
    title: "Order Fulfillment",
    nodes: [
      { id: "n1", type: "lane", label: "Sales", x: 40, y: 60, width: 880, height: 140 },
      { id: "n2", type: "lane", label: "Warehouse", x: 40, y: 220, width: 880, height: 140 },
      { id: "n3", type: "lane", label: "Shipping", x: 40, y: 380, width: 880, height: 140 },
      { id: "n4", type: "start", label: "", x: 80, y: 110, width: 48, height: 48 },
      { id: "n5", type: "process", label: "Receive Order", x: 160, y: 100, width: 140, height: 64 },
      { id: "n6", type: "process", label: "Pick Items", x: 160, y: 260, width: 140, height: 64 },
      { id: "n7", type: "process", label: "Ship Package", x: 160, y: 420, width: 140, height: 64 },
      { id: "n8", type: "end", label: "", x: 340, y: 430, width: 48, height: 48 },
    ],
    edges: [
      { id: "e1", from: "n4", to: "n5", label: "", type: "flow" },
      { id: "e2", from: "n5", to: "n6", label: "", type: "flow" },
      { id: "e3", from: "n6", to: "n7", label: "", type: "flow" },
      { id: "e4", from: "n7", to: "n8", label: "", type: "flow" },
    ],
  },
  flowchart: {
    diagram_type: "flowchart",
    title: "Login Flow",
    nodes: [
      { id: "n1", type: "start", label: "Start", x: 200, y: 40, width: 120, height: 48 },
      { id: "n2", type: "input", label: "Enter credentials", x: 180, y: 120, width: 160, height: 56 },
      { id: "n3", type: "decision", label: "Valid?", x: 210, y: 210, width: 88, height: 88 },
      { id: "n4", type: "process", label: "Grant access", x: 380, y: 220, width: 140, height: 64 },
      { id: "n5", type: "process", label: "Show error", x: 60, y: 220, width: 120, height: 64 },
      { id: "n6", type: "start", label: "End", x: 400, y: 340, width: 100, height: 48 },
    ],
    edges: [
      { id: "e1", from: "n1", to: "n2", label: "", type: "connector" },
      { id: "e2", from: "n2", to: "n3", label: "", type: "connector" },
      { id: "e3", from: "n3", to: "n4", label: "Yes", type: "connector" },
      { id: "e4", from: "n3", to: "n5", label: "No", type: "connector" },
      { id: "e5", from: "n4", to: "n6", label: "", type: "connector" },
    ],
  },
};

export function defaultNodeSize(type) {
  const sizes = {
    actor: [72, 96],
    use_case: [140, 56],
    system_boundary: [360, 280],
    package: [200, 120],
    note: [120, 80],
    text_box: [120, 48],
    entity: [160, 80],
    attribute: [120, 48],
    relationship: [72, 72],
    weak_entity: [160, 80],
    data_store: [100, 64],
    lane: [920, 150],
    process: [140, 64],
    subprocess: [160, 72],
    start: [48, 48],
    end: [48, 48],
    decision: [88, 88],
    document: [120, 72],
    manual_input: [120, 56],
    delay: [56, 56],
    input: [140, 56],
    parallelogram: [140, 56],
    terminator: [120, 48],
    preparation: [140, 56],
    display: [120, 56],
    off_page: [48, 48],
    connector_node: [40, 40],
    lifeline: [80, 320],
    object: [100, 48],
    activation: [16, 80],
    fragment: [280, 160],
    class: [180, 120],
    interface: [180, 100],
    enum: [160, 90],
    cloud: [140, 88],
    router: [80, 56],
    switch: [88, 48],
    firewall: [72, 72],
    server: [72, 96],
    client: [72, 72],
    workstation: [80, 64],
  };
  return sizes[type] || [120, 60];
}

export function nextId(prefix, items) {
  let max = 0;
  for (const item of items) {
    const match = String(item.id).match(new RegExp(`^${prefix}(\\d+)$`));
    if (match) max = Math.max(max, Number(match[1]));
  }
  return `${prefix}${max + 1}`;
}
