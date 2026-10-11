"""Tests for edit detection, brief gaps, and edge border clipping (2.7.4)."""

from app.schemas.diagram import DiagramDocument, DiagramEdge, DiagramNode
from app.services.brief_coverage import looks_like_edit_request, validate_brief_coverage
from app.services.edge_geometry import border_point


def test_edit_detector_rejects_fresh_briefs_with_domain_verbs():
    assert not looks_like_edit_request(
        "Make a flowchart where users can rename files and move items between folders",
        True,
    )
    assert not looks_like_edit_request("Make a use case diagram for login", True)
    assert looks_like_edit_request("add a retry loop to the existing diagram", True)
    assert looks_like_edit_request("make these boxes wider on this diagram", True)
    assert not looks_like_edit_request("add a retry loop to the existing diagram", False)


def test_return_message_respects_negation():
    d = DiagramDocument(
        diagram_type="sequence",
        title="t",
        nodes=[DiagramNode(id="n1", type="lifeline", label="A", x=0, y=0, width=80, height=200)],
        edges=[],
    )
    gaps = validate_brief_coverage(
        "sequence",
        "There are no return messages. Participants: A, B.",
        d,
    )
    assert not any("return messages" in g.lower() for g in gaps.blocking)


def test_border_point_rect_is_outside_center():
    node = {"type": "entity", "x": 0, "y": 0, "width": 100, "height": 60}
    x, y = border_point(node, 200, 30)
    assert abs(x - 100) < 0.5
    assert abs(y - 30) < 0.5
    # Must not be the centre
    assert abs(x - 50) > 10


def test_border_point_diamond():
    node = {"type": "decision", "x": 0, "y": 0, "width": 80, "height": 80}
    x, y = border_point(node, 200, 40)
    assert x > 40  # past centre toward the right tip
    assert abs(y - 40) < 1


def test_edit_detector_requires_existing_canvas():
    assert not looks_like_edit_request("add a retry loop to the existing diagram", False)
    assert looks_like_edit_request("add a retry loop to the existing diagram", True)
