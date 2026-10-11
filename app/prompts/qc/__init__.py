"""Per-diagram-type QC auditor system instructions."""

from app.prompts.qc import architecture as architecture_qc
from app.prompts.qc import class_diagram as class_diagram_qc
from app.prompts.qc import erd as erd_qc
from app.prompts.qc import flowchart as flowchart_qc
from app.prompts.qc import network as network_qc
from app.prompts.qc import sequence as sequence_qc
from app.prompts.qc import swim_lane as swim_lane_qc
from app.prompts.qc import use_case as use_case_qc
from app.prompts.qc.base import QC_COMMON_PREAMBLE, QC_RESPONSE_FORMAT
from app.schemas.diagram import DiagramType

_QC_BY_TYPE: dict[str, str] = {
    "swim_lane": swim_lane_qc.QC_SYSTEM,
    "flowchart": flowchart_qc.QC_SYSTEM,
    "erd": erd_qc.QC_SYSTEM,
    "sequence": sequence_qc.QC_SYSTEM,
    "use_case": use_case_qc.QC_SYSTEM,
    "class_diagram": class_diagram_qc.QC_SYSTEM,
    "network": network_qc.QC_SYSTEM,
    "architecture": architecture_qc.QC_SYSTEM,
}


def qc_system_for(diagram_type: DiagramType | str) -> str:
    """Return the QC system instruction specialized for this diagram type."""
    key = f"qc.type.{diagram_type}"
    try:
        from app.services import settings_service as cfg

        body = cfg.active_prompt_body(key)
        # When base prompts are customized, swap them into the type body.
        preamble = cfg.active_prompt_body("qc.base.preamble").strip()
        response_fmt = cfg.active_prompt_body("qc.base.response_format").strip()
        if preamble and preamble != QC_COMMON_PREAMBLE.strip():
            body = body.replace(QC_COMMON_PREAMBLE.strip(), preamble)
        if response_fmt and response_fmt != QC_RESPONSE_FORMAT.strip():
            body = body.replace(QC_RESPONSE_FORMAT.strip(), response_fmt)

        max_recs = int(cfg.get_value("pipeline.max_recommendations"))
        body = body.replace("at most 5 short bullets", f"at most {max_recs} short bullets")
        body = body.replace("at most 5", f"at most {max_recs}")
        body = body.replace("at most 8 short bullets", f"at most {max_recs} short bullets")
        return body
    except Exception:
        return _QC_BY_TYPE.get(str(diagram_type), use_case_qc.QC_SYSTEM)


# Backward-compatible default for imports that expect a constant.
QC_SYSTEM_INSTRUCTION = use_case_qc.QC_SYSTEM
