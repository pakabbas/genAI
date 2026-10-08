"""Per-diagram-type QC auditor system instructions."""

from app.prompts.qc import architecture as architecture_qc
from app.prompts.qc import class_diagram as class_diagram_qc
from app.prompts.qc import erd as erd_qc
from app.prompts.qc import flowchart as flowchart_qc
from app.prompts.qc import network as network_qc
from app.prompts.qc import sequence as sequence_qc
from app.prompts.qc import swim_lane as swim_lane_qc
from app.prompts.qc import use_case as use_case_qc
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
    return _QC_BY_TYPE.get(str(diagram_type), use_case_qc.QC_SYSTEM)


# Backward-compatible default for imports that expect a constant.
QC_SYSTEM_INSTRUCTION = use_case_qc.QC_SYSTEM
