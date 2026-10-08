"""QC rules for Architecture diagrams."""

from app.prompts.qc.base import compose_qc_system

QC_SYSTEM = compose_qc_system(
    type_focus=(
        "Software/system architecture.\n"
        "Valid node types: actor, service, api, package, cloud, data_store, note, text_box.\n"
        "service and api must remain distinct shapes (not both process).\n"
        "data_store IS the Database shape."
    ),
    vocabulary="services, APIs, components, data stores, dependencies / data flows",
    blocking_rules="""
1. Diagram empty / unusable.
2. A major service, API, or datastore explicitly named in the request is missing.
3. Edges reference missing node ids, or types outside the architecture toolbox.
4. Wrong diagram type for the request.
5. Do NOT block solely because JSON uses data_store instead of the word database.
""",
)
