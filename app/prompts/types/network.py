"""Network Diagram: generator rules and the editable-shape catalog defaults."""

from app.schemas.diagram import ToolboxItem

GUIDANCE = (
    'Network topology: cloud, routers, switches, load_balancer, servers, clients, links. Use node type data_store for databases. Use load_balancer (not router) for LB/HAProxy/NLB. Ethernet network_link has no arrowhead.'
)

TOOLBOX = [
    ToolboxItem(id="cloud", label="Cloud / Internet", kind="node", shape="cloud", default_width=140, default_height=88),
    ToolboxItem(id="router", label="Router", kind="node", shape="router", default_width=80, default_height=56),
    ToolboxItem(id="switch", label="Switch", kind="node", shape="switch", default_width=88, default_height=48),
    ToolboxItem(id="firewall", label="Firewall", kind="node", shape="firewall", default_width=72, default_height=72),
    ToolboxItem(id="load_balancer", label="Load Balancer", kind="node", shape="load_balancer", default_width=100, default_height=64),
    ToolboxItem(id="server", label="Server", kind="node", shape="server", default_width=72, default_height=96),
    ToolboxItem(id="data_store", label="Database", kind="node", shape="data_store", default_width=100, default_height=64),
    ToolboxItem(id="client", label="Client", kind="node", shape="client", default_width=72, default_height=72),
    ToolboxItem(id="workstation", label="Workstation", kind="node", shape="workstation", default_width=80, default_height=64),
    ToolboxItem(id="text_box", label="Label", kind="node", shape="text_box", default_width=100, default_height=40),
    ToolboxItem(id="network_link", label="Ethernet Link", kind="edge", shape="network_link"),
    ToolboxItem(id="wireless", label="Wireless", kind="edge", shape="wireless"),
]
