"""QC rules for Network diagrams."""

from app.prompts.qc.base import compose_qc_system

QC_SYSTEM = compose_qc_system(
    type_focus=(
        "Network topology: cloud, routers, switches, firewalls, load balancers, servers, clients, links.\n"
        "Node type data_store IS the Database shape — do not block for saying 'database' in prose.\n"
        "Load balancers should be type load_balancer (router-as-LB → prefer recommendation)."
    ),
    vocabulary="nodes, devices, links, zones",
    blocking_rules="""
1. Diagram empty / unusable.
2. A major device/site explicitly named in the request is completely missing.
3. Edges reference missing node ids, or types outside the network toolbox.
4. Wrong diagram type for the request.
5. Do NOT block solely because JSON uses data_store instead of the word database.
""",
)
