"""One generator context per supported diagram type (no mixed-type rules)."""

from . import (
    flowchart,
    use_case,
    erd,
    swim_lane,
    sequence,
    class_diagram,
    network,
    architecture,
)

TYPE_CONTEXTS = {
    'flowchart': flowchart,
    'use_case': use_case,
    'erd': erd,
    'swim_lane': swim_lane,
    'sequence': sequence,
    'class_diagram': class_diagram,
    'network': network,
    'architecture': architecture,
}
