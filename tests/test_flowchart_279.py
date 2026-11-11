"""2.7.9 flowchart fixes: coverage false positives, planner kinds, no-progress stop, layout, versions."""

import re
from pathlib import Path

import pytest

from app.schemas.diagram import DiagramDocument
from app.schemas.generation import QCAuditResult
from app.schemas.process_model import ProcessModel, coerce_flowchart_kinds
from app.services import diagram_pipeline as pipe
from app.services import flowchart_layout as fl
from app.services.diagram_normalizer import normalize_diagram
from app.services.process_coverage import (
    flowchart_merged_activity_gaps,
    validate_process_coverage,
)
from app.version import APP_VERSION

ROOT = Path(__file__).resolve().parent.parent


def _model(*labels):
    return ProcessModel(
        title="t",
        elements=[{"id": f"a{i}", "kind": "activity", "label": lb} for i, lb in enumerate(labels)],
    )


def _doc(nodes, edges):
    return DiagramDocument.model_validate(
        {"diagram_type": "flowchart", "title": "t", "nodes": nodes, "edges": edges}
    )


def _n(i, t, label, y=0):
    return {"id": i, "type": t, "label": label, "x": 0, "y": y, "width": 140, "height": 60}


def _e(i, a, b, label=""):
    return {"id": i, "from": a, "to": b, "label": label, "type": "connector"}


@pytest.mark.parametrize(
    "label",
    [
        "Send confirmation SMS and email",
        "Submit request and notify line manager",
        "Show order confirmation & est. delivery time",
    ],
)
def test_merged_gap_false_positives_gone(label):
    model = _model(
        "Show order confirmation & est. delivery time",
        "Send confirmation SMS and email",
        "Submit request and notify line manager",
        "Show login / register",
        "Show changes & ask user to confirm",
    )
    doc = _doc([_n("s", "terminator", "Start"), _n("a", "process", label), _n("e", "terminator", "End")],
               [_e("e1", "s", "a"), _e("e2", "a", "e")])
    assert flowchart_merged_activity_gaps(model, doc) == []
    gaps = validate_process_coverage(model, doc, diagram_type="flowchart")
    assert not any(g.startswith("Merged") for g in gaps)


def test_merged_gap_true_positive_is_advisory():
    model = _model("Pick up order", "Deliver order")
    doc = _doc([_n("a", "process", "Pick up order and deliver order")], [])
    adv = flowchart_merged_activity_gaps(model, doc)
    assert adv and "advisory" in adv[0]


def test_planner_accepts_flowchart_kinds():
    raw = {
        "title": "x",
        "elements": [
            {"id": "s", "kind": "start", "label": "Start"},
            {"id": "i", "kind": "input", "label": "Enter email"},
            {"id": "o", "kind": "output", "label": "Show message"},
            {"id": "g", "kind": "gateway", "label": "Valid?"},
            {"id": "f", "kind": "fork", "label": "Fork"},
            {"id": "j", "kind": "join", "label": "Join"},
        ],
    }
    m = ProcessModel.model_validate(coerce_flowchart_kinds(raw))
    kinds = [e.kind for e in m.elements]
    assert kinds == ["start", "activity", "activity", "decision", "parallel", "parallel"]
    assert len(m.decisions()) == 1


def test_splitter_never_runs_and_pipeline_stops_on_identical_gap(monkeypatch):
    calls = {"gen": 0, "qc": 0}
    base = _doc(
        [
            _n("s", "terminator", "Start", 0),
            _n("a", "process", "Send confirmation SMS and email", 100),
            _n("e", "terminator", "End", 200),
        ],
        [_e("e1", "s", "a"), _e("e2", "a", "e")],
    )

    def fake_gen(*a, **k):
        calls["gen"] += 1
        return base

    def fake_qc(*a, **k):
        calls["qc"] += 1
        return QCAuditResult(
            approved=False, revision_required=True, blocking_issues=["Same issue"], summary="needs work"
        )

    monkeypatch.setattr(pipe, "_generate_diagram_document", fake_gen)
    monkeypatch.setattr(pipe, "_run_qc_audit", fake_qc)
    monkeypatch.setattr(pipe, "extract_process_model", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    monkeypatch.setattr(pipe, "repair_merged_process_nodes", lambda *a, **k: pytest.fail("splitter ran"))
    res = pipe.generate_diagram_with_qc("flowchart", "Create a flowchart for checkout with steps")
    assert not any(n.id.startswith("n_split") for n in res.diagram.nodes)
    # draft + 1 revision, then identical issue set ⇒ stop (never 3 rounds)
    assert calls["gen"] == 2
    assert any(t.phase == "revision_skipped" for t in res.trace)
    assert all(t.stage for t in res.trace)


def _quickbite_like():
    nodes = [
        _n("s", "terminator", "Start: Checkout clicked"),
        _n("d1", "decision", "Logged in?"),
        _n("login", "input", "Show login / register"),
        _n("d2", "decision", "Cart empty?"),
        _n("empty", "input", "Show 'Cart is empty'"),
        _n("e_empty", "terminator", "End (cart empty)"),
        _n("addr", "input", "Select delivery address"),
        _n("d3", "decision", "Inside zone?"),
        _n("err", "input", "Show zone error"),
        _n("pay", "input", "Choose payment"),
        _n("d4", "decision", "Payment approved?"),
        _n("retry", "decision", "Retry < 3?"),
        _n("fail", "terminator", "End (Checkout failed)"),
        _n("create", "process", "Create order record, clear cart"),
        _n("e", "terminator", "End: Order placed"),
    ]
    edges = [
        _e("1", "s", "d1"), _e("2", "d1", "login", "No"), _e("3", "login", "d1"), _e("4", "d1", "d2", "Yes"),
        _e("5", "d2", "empty", "Yes"), _e("6", "empty", "e_empty"), _e("7", "d2", "addr", "No"),
        _e("8", "addr", "d3"), _e("9", "d3", "err", "No"), _e("10", "err", "addr"), _e("11", "d3", "pay", "Yes"),
        _e("12", "pay", "d4"), _e("13", "d4", "create", "Yes"), _e("14", "d4", "retry", "No"),
        _e("15", "retry", "pay", "Yes"), _e("16", "retry", "fail", "No"), _e("17", "create", "e"),
    ]
    return _doc(nodes, edges)


def test_back_edges_from_graph_and_top_to_bottom_layout():
    doc = normalize_diagram("flowchart", _quickbite_like())
    back = {e.id for e in doc.edges if e.meta.get("back_edge")}
    assert back == {"3", "10", "15"}
    by = {n.id: n for n in doc.nodes}
    for e in doc.edges:
        if e.id in back:
            continue
        a, b = by[e.from_node], by[e.to_node]
        assert b.y + 1 >= a.y, f"{a.label} -> {b.label} goes upward"
    # spine stays in one column
    assert by["s"].x + by["s"].width / 2 == pytest.approx(by["e"].x + by["e"].width / 2, abs=1)
    # Show … steps are Output (parallelogram)
    assert all(n.type == "input" for n in doc.nodes if n.label.startswith("Show"))
    # deterministic: auto-layout recognised
    assert fl.is_auto_layout(doc)


def test_duplicate_consecutive_steps_merged():
    doc = _doc(
        [_n("s", "terminator", "Start"), _n("a", "process", "Send email"), _n("c", "process", "Send  Email"), _n("e", "terminator", "End")],
        [_e("1", "s", "a"), _e("2", "a", "c"), _e("3", "c", "e")],
    )
    out = normalize_diagram("flowchart", doc)
    labels = [n.label for n in out.nodes if n.type == "process"]
    assert labels.count("Send email") == 1
    assert {(e.from_node, e.to_node) for e in out.edges} >= {("s", "a"), ("a", "e")}


def test_other_types_unchanged_layout():
    doc = DiagramDocument.model_validate(
        {"diagram_type": "erd", "title": "t", "nodes": [_n("a", "entity", "User", 10), _n("b", "entity", "Order", 300)], "edges": []}
    )
    out = normalize_diagram("erd", doc)
    assert [(n.x, n.y) for n in out.nodes] == [(0, 10), (0, 300)]


def test_cache_bust_matches_app_version():
    js_version = re.search(r'APP_VERSION = "([^"]+)"', (ROOT / "static/js/version.js").read_text()).group(1)
    assert js_version == APP_VERSION
    for path in (ROOT / "static/js").rglob("*.js"):
        if "vendor" in path.parts:
            continue
        for v in re.findall(r"\?v=([0-9][0-9.]*)", path.read_text()):
            assert v == APP_VERSION, f"{path.name} imports ?v={v}"


def test_lock_unrelated_labels():
    from app.services.flowchart_layout import lock_unrelated_labels
    from app.schemas.diagram import DiagramEdge
    prev = _doc([_n("a", "process", "Show error"), _n("b", "process", "Choose payment (Card / Cash on Delivery)")],
                [DiagramEdge(id="e1", from_node="a", to_node="b", label="Retry")])
    new = _doc([_n("a", "process", "Show address error"),
                _n("b", "process", "Choose payment (Card / Gift card / Cash on Delivery)"),
                _n("c", "decision", "Gift card valid?")],
               [DiagramEdge(id="e1", from_node="a", to_node="b", label="Try again")])
    out = lock_unrelated_labels(prev, new, "Add a 'Gift card' payment option before Cash on Delivery.")
    labels = {n.id: n.label for n in out.nodes}
    assert labels["a"] == "Show error"
    assert "Gift card" in labels["b"]
    assert labels["c"] == "Gift card valid?"
    assert out.edges[0].label == "Retry"


def test_identical_ends_merged():
    from app.schemas.diagram import DiagramEdge
    from app.services.flowchart_layout import merge_consecutive_duplicates
    nodes = [_n("s", "terminator", "Start"), _n("d", "decision", "OK?"), _n("e1", "terminator", "End: Rejected"),
             _n("x", "process", "Check"), _n("e2", "terminator", "End: Rejected")]
    edges = [DiagramEdge(id="a", from_node="s", to_node="d"), DiagramEdge(id="b", from_node="d", to_node="e1", label="No"),
             DiagramEdge(id="c", from_node="d", to_node="x", label="Yes"), DiagramEdge(id="f", from_node="x", to_node="e2")]
    d = _doc(nodes, [e.model_dump(by_alias=True) for e in edges])
    n2, e2 = merge_consecutive_duplicates(list(d.nodes), list(d.edges))
    assert [n.id for n in n2].count("e2") == 0
    assert any(e.from_node == "x" and e.to_node == "e1" for e in e2)
