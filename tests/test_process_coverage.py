"""Unit tests for process coverage validation (no Gemini required)."""

from app.schemas.diagram import DiagramDocument, DiagramEdge, DiagramNode
from app.schemas.process_model import ProcessBranch, ProcessElement, ProcessFlow, ProcessModel
from app.services.process_coverage import validate_process_coverage


def _food_inventory() -> ProcessModel:
    return ProcessModel(
        title="Food Delivery",
        lanes=["Customer", "Restaurant", "Delivery Rider", "Payment Gateway"],
        elements=[
            ProcessElement(id="s1", kind="start", label="Start", lane="Customer"),
            ProcessElement(id="a1", kind="activity", label="Place Order & Pay", lane="Customer"),
            ProcessElement(
                id="a2", kind="activity", label="Process Payment", lane="Payment Gateway"
            ),
            ProcessElement(
                id="d1",
                kind="decision",
                label="Payment Successful?",
                lane="Payment Gateway",
                branches=[
                    ProcessBranch(label="Yes", outcome="continue", next_element_id="d2"),
                    ProcessBranch(
                        label="No",
                        outcome="notify and end",
                        next_element_id="a_notify_pay",
                    ),
                ],
            ),
            ProcessElement(
                id="a_notify_pay",
                kind="activity",
                label="Notify Customer Payment Failed",
                lane="Customer",
            ),
            ProcessElement(
                id="d2",
                kind="decision",
                label="Accept Order?",
                lane="Restaurant",
                branches=[
                    ProcessBranch(label="Yes", outcome="prepare", next_element_id="a3"),
                    ProcessBranch(
                        label="No",
                        outcome="notify and end",
                        next_element_id="a_notify_rej",
                    ),
                ],
            ),
            ProcessElement(id="a3", kind="activity", label="Prepare Food", lane="Restaurant"),
            ProcessElement(id="a4", kind="activity", label="Mark Order Ready", lane="Restaurant"),
            ProcessElement(id="a5", kind="activity", label="Pick Up Order", lane="Delivery Rider"),
            ProcessElement(
                id="a6", kind="activity", label="Deliver Order", lane="Delivery Rider"
            ),
            ProcessElement(id="a7", kind="activity", label="Confirm Delivery", lane="Customer"),
            ProcessElement(
                id="a8", kind="activity", label="Release Payout", lane="Payment Gateway"
            ),
            ProcessElement(id="e1", kind="end", label="End", lane="Customer"),
        ],
        flows=[
            ProcessFlow(from_id="s1", to_id="a1"),
            ProcessFlow(from_id="a1", to_id="a2"),
        ],
    )


def _incomplete_like_screenshot() -> DiagramDocument:
    """Mirrors the incomplete diagram from the reported bug."""
    nodes = [
        DiagramNode(id="pool", type="pool", label="Online Food Delivery Pool", x=40, y=40, width=900, height=500),
        DiagramNode(id="l1", type="lane", label="Customer", x=60, y=60, width=860, height=110),
        DiagramNode(id="l2", type="lane", label="Payment Gateway", x=60, y=170, width=860, height=110),
        DiagramNode(id="l3", type="lane", label="Restaurant", x=60, y=280, width=860, height=110),
        DiagramNode(id="l4", type="lane", label="Delivery Rider", x=60, y=390, width=860, height=110),
        DiagramNode(id="s1", type="start", label="Start", x=80, y=90, width=48, height=48),
        DiagramNode(id="p1", type="process", label="Process Payment", x=200, y=200, width=140, height=64),
        DiagramNode(id="d1", type="gateway_xor", label="?", x=400, y=200, width=72, height=72),
        DiagramNode(id="p2", type="process", label="Prepare Food", x=520, y=300, width=140, height=64),
        DiagramNode(id="p3", type="process", label="Pickup & Deliver", x=680, y=410, width=140, height=64),
        DiagramNode(id="p4", type="process", label="Confirm Delivery", x=820, y=90, width=140, height=64),
        DiagramNode(id="e1", type="end", label="End", x=980, y=90, width=48, height=48),
        DiagramNode(id="e2", type="end", label="End", x=400, y=90, width=48, height=48),
    ]
    edges = [
        DiagramEdge(id="e1", **{"from": "s1", "to": "p1", "label": "", "type": "flow"}),
        DiagramEdge(id="e2", **{"from": "p1", "to": "d1", "label": "", "type": "flow"}),
        DiagramEdge(id="e3", **{"from": "d1", "to": "e2", "label": "No", "type": "flow"}),
        DiagramEdge(id="e4", **{"from": "d1", "to": "p2", "label": "Yes", "type": "flow"}),
        DiagramEdge(id="e5", **{"from": "p2", "to": "p3", "label": "Ready", "type": "flow"}),
        DiagramEdge(id="e6", **{"from": "p3", "to": "p4", "label": "Delivered", "type": "flow"}),
        DiagramEdge(id="e7", **{"from": "p4", "to": "e1", "label": "", "type": "flow"}),
    ]
    return DiagramDocument(diagram_type="swim_lane", title="Test", nodes=nodes, edges=edges)


def test_incomplete_diagram_flags_missing_requirements():
    gaps = validate_process_coverage(
        _food_inventory(),
        _incomplete_like_screenshot(),
        diagram_type="swim_lane",
    )
    joined = " | ".join(gaps).lower()
    assert "place order" in joined
    assert "accept order" in joined or "decision" in joined
    assert "mark order ready" in joined or "mark" in joined
    assert "pick up" in joined or "pickup" in joined
    assert "release payout" in joined or "payout" in joined
    # Merged pickup+deliver should not satisfy separate pick-up requirement alone enough —
    # deliver may still match Deliver Order partially; pick up must still be flagged if only merged.
    assert any("pick" in g.lower() for g in gaps) or any("deliver order" in g.lower() for g in gaps)


def test_repair_splits_merged_pickup_deliver():
    from app.services.process_coverage import repair_merged_process_nodes

    model = ProcessModel(
        title="t",
        lanes=["Delivery Rider"],
        elements=[
            ProcessElement(id="a1", kind="activity", label="Pick Up Order", lane="Delivery Rider"),
            ProcessElement(id="a2", kind="activity", label="Deliver Order", lane="Delivery Rider"),
        ],
    )
    diagram = DiagramDocument(
        diagram_type="swim_lane",
        title="t",
        nodes=[
            DiagramNode(id="p1", type="process", label="Picks up the order and delivers it", x=10, y=10, width=140, height=64),
            DiagramNode(id="e1", type="end", label="End", x=200, y=10, width=48, height=48),
        ],
        edges=[DiagramEdge(id="x1", **{"from": "p1", "to": "e1", "label": "", "type": "flow"})],
    )
    fixed = repair_merged_process_nodes(diagram, model)
    process_labels = [n.label for n in fixed.nodes if n.type == "process"]
    assert len(process_labels) == 2
    assert any("pick" in l.lower() for l in process_labels)
    assert any("deliver" in l.lower() for l in process_labels)


def test_prompt_heuristics_catch_missing_accept_reject():
    from app.services.process_coverage import enrich_process_model_from_prompt, prompt_decision_gaps

    prompt = (
        "Show decisions for payment success/failure and restaurant accept/reject. "
        "If declined, Customer is notified."
    )
    model = ProcessModel(
        title="t",
        lanes=["Customer", "Restaurant", "Payment Gateway"],
        elements=[
            ProcessElement(
                id="d1",
                kind="decision",
                label="Payment Successful?",
                lane="Payment Gateway",
                branches=[
                    ProcessBranch(label="Yes", outcome="ok"),
                    ProcessBranch(label="No", outcome="end", ends_process=True),
                ],
            )
        ],
    )
    enriched = enrich_process_model_from_prompt(model, prompt)
    assert len(enriched.decisions()) >= 2
    assert any("accept" in d.label.lower() for d in enriched.decisions())

    incomplete = _incomplete_like_screenshot()
    gaps = prompt_decision_gaps(prompt, incomplete)
    assert any("accept" in g.lower() for g in gaps)


def test_complete_diagram_has_no_gaps():
    model = _food_inventory()
    nodes = [
        DiagramNode(id="l1", type="lane", label="Customer", x=0, y=0, width=800, height=100),
        DiagramNode(id="l2", type="lane", label="Restaurant", x=0, y=100, width=800, height=100),
        DiagramNode(id="l3", type="lane", label="Delivery Rider", x=0, y=200, width=800, height=100),
        DiagramNode(id="l4", type="lane", label="Payment Gateway", x=0, y=300, width=800, height=100),
        DiagramNode(id="s1", type="start", label="Start", x=40, y=30, width=48, height=48),
        DiagramNode(id="a1", type="process", label="Place Order & Pay", x=120, y=30, width=140, height=64),
        DiagramNode(id="a2", type="process", label="Process Payment", x=280, y=330, width=140, height=64),
        DiagramNode(id="d1", type="gateway_xor", label="Payment Successful?", x=440, y=330, width=72, height=72),
        DiagramNode(
            id="an1",
            type="process",
            label="Notify Customer Payment Failed",
            x=440,
            y=30,
            width=140,
            height=64,
        ),
        DiagramNode(id="d2", type="gateway_xor", label="Accept Order?", x=560, y=130, width=72, height=72),
        DiagramNode(
            id="an2",
            type="process",
            label="Notify Customer Rejected",
            x=560,
            y=30,
            width=140,
            height=64,
        ),
        DiagramNode(id="a3", type="process", label="Prepare Food", x=680, y=130, width=140, height=64),
        DiagramNode(id="a4", type="process", label="Mark Order Ready", x=840, y=130, width=140, height=64),
        DiagramNode(id="a5", type="process", label="Pick Up Order", x=680, y=230, width=140, height=64),
        DiagramNode(id="a6", type="process", label="Deliver Order", x=840, y=230, width=140, height=64),
        DiagramNode(id="a7", type="process", label="Confirm Delivery", x=680, y=30, width=140, height=64),
        DiagramNode(id="a8", type="process", label="Release Payout", x=840, y=330, width=140, height=64),
        DiagramNode(id="e1", type="end", label="End", x=1000, y=30, width=48, height=48),
        DiagramNode(id="e2", type="end", label="End", x=600, y=30, width=48, height=48),
        DiagramNode(id="e3", type="end", label="End", x=720, y=30, width=48, height=48),
    ]
    edges = [
        DiagramEdge(id="x1", **{"from": "d1", "to": "d2", "label": "Yes", "type": "flow"}),
        DiagramEdge(id="x2", **{"from": "d1", "to": "an1", "label": "No", "type": "flow"}),
        DiagramEdge(id="x3", **{"from": "d2", "to": "a3", "label": "Yes", "type": "flow"}),
        DiagramEdge(id="x4", **{"from": "d2", "to": "an2", "label": "No", "type": "flow"}),
        DiagramEdge(id="x5", **{"from": "a1", "to": "a2", "label": "", "type": "flow"}),
    ]
    diagram = DiagramDocument(diagram_type="swim_lane", title="Complete", nodes=nodes, edges=edges)
    gaps = validate_process_coverage(model, diagram, diagram_type="swim_lane")
    assert gaps == [], gaps
