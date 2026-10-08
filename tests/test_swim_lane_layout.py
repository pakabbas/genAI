"""Swim lane layout spreads cramped AI output."""

from app.schemas.diagram import DiagramDocument, DiagramNode
from app.services.diagram_normalizer import _layout_swim_lane, normalize_diagram


def test_layout_swim_lane_expands_and_spreads():
    cramped = DiagramDocument(
        diagram_type="swim_lane",
        title="Cramped",
        nodes=[
            DiagramNode(id="pool", type="pool", label="P", x=20, y=20, width=600, height=300),
            DiagramNode(id="l1", type="lane", label="Customer", x=40, y=40, width=560, height=90),
            DiagramNode(id="l2", type="lane", label="Restaurant", x=40, y=140, width=560, height=90),
            DiagramNode(id="a1", type="process", label="Place order", x=80, y=50, width=140, height=64),
            DiagramNode(id="a2", type="process", label="Pay", x=160, y=55, width=140, height=64),
            DiagramNode(id="a3", type="process", label="Prepare", x=100, y=150, width=140, height=64),
            DiagramNode(id="a4", type="process", label="Ready", x=180, y=155, width=140, height=64),
        ],
        edges=[],
    )
    out = _layout_swim_lane(cramped)
    lanes = [n for n in out.nodes if n.type == "lane"]
    pool = next(n for n in out.nodes if n.type == "pool")
    tasks = [n for n in out.nodes if n.type == "process"]

    assert all(lane.width >= 1580 for lane in lanes)
    assert all(lane.height >= 180 for lane in lanes)
    assert pool.width >= 1680
    assert pool.height >= 780

    # Tasks in same lane should not overlap horizontally
    by_lane = {}
    for t in tasks:
        lane = min(lanes, key=lambda l: abs((l.y + l.height / 2) - (t.y + t.height / 2)))
        by_lane.setdefault(lane.id, []).append(t)
    for members in by_lane.values():
        members.sort(key=lambda n: n.x)
        for i in range(len(members) - 1):
            assert members[i].x + members[i].width + 40 <= members[i + 1].x + 1e-6


def test_normalize_swim_lane_runs_layout():
    doc = DiagramDocument(
        diagram_type="swim_lane",
        title="T",
        nodes=[
            DiagramNode(id="pool", type="pool", label="P", x=0, y=0, width=500, height=200),
            DiagramNode(id="l1", type="lane", label="A", x=10, y=10, width=480, height=80),
            DiagramNode(id="p1", type="process", label="Do", x=40, y=20, width=140, height=64),
        ],
    )
    out = normalize_diagram("swim_lane", doc)
    lane = next(n for n in out.nodes if n.type == "lane")
    assert lane.width >= 1580
