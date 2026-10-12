"""Tests for edit detection, brief gaps, edges, sequence layout (2.7.5)."""

from app.schemas.diagram import DiagramDocument, DiagramEdge, DiagramNode
from app.services.brief_coverage import looks_like_edit_request, validate_brief_coverage
from app.services.diagram_normalizer import normalize_diagram
from app.services.edge_geometry import (
    border_point,
    label_anchor,
    new_project_empty_diagram,
    sequence_message_ends,
)


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


def test_sequence_message_ends_on_lifeline_centres():
    left = {"id": "a", "type": "lifeline", "x": 70, "y": 0, "width": 80, "height": 400}
    right = {"id": "b", "type": "lifeline", "x": 340, "y": 0, "width": 80, "height": 400}
    ends = sequence_message_ends(left, right, 88)
    assert abs(ends["x1"] - 110) < 0.5
    assert abs(ends["x2"] - 380) < 0.5
    assert ends["y1"] == ends["y2"] == 88
    self_ends = sequence_message_ends(right, right, 140)
    assert self_ends["self"] is True
    assert abs(self_ends["x1"] - 380) < 0.5


def test_label_anchor_is_midpoint_of_longest_segment():
    route = [{"x": 0, "y": 0}, {"x": 200, "y": 0}, {"x": 200, "y": 10}]
    x, y = label_anchor(route)
    assert 80 < x < 120
    assert abs(y) > 4  # offset off the line, not on the arrowhead at 200


def test_fragment_ranges_are_per_fragment():
    doc = DiagramDocument(
        diagram_type="sequence",
        title="t",
        nodes=[
            DiagramNode(id="l1", type="lifeline", label="A", x=100, y=0, width=80, height=400),
            DiagramNode(id="l2", type="lifeline", label="B", x=300, y=0, width=80, height=400),
            DiagramNode(id="f1", type="fragment", label="alt", x=80, y=20, width=200, height=80),
            DiagramNode(id="f2", type="fragment", label="loop", x=80, y=20, width=200, height=80),
        ],
        edges=[
            DiagramEdge(id="e1", type="message", from_node="l1", to_node="l2", label="1. login"),
            DiagramEdge(id="e2", type="message", from_node="l2", to_node="l1", label="2. ok"),
            DiagramEdge(id="e3", type="message", from_node="l1", to_node="l2", label="3. retry"),
            DiagramEdge(id="e4", type="message", from_node="l2", to_node="l1", label="4. fail"),
        ],
    )
    out = normalize_diagram("sequence", doc)
    frags = [n for n in out.nodes if n.type == "fragment"]
    assert len(frags) == 2
    tops = sorted(n.y for n in frags)
    assert tops[1] - tops[0] > 40  # not stacked on the same y


def test_new_project_clears_canvas_contract():
    empty = new_project_empty_diagram("erd")
    assert empty["nodes"] == []
    assert empty["edges"] == []
    assert empty["title"] == "Untitled Diagram"
