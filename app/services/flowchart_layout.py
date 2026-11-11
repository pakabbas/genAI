"""2.7.9 deterministic flowchart layout (Sugiyama-lite) + flowchart-only clean-ups.

Everything here is used ONLY for diagram_type == "flowchart".

- ranks = longest path over forward edges (back-edges found by DFS from Start)
- the main spine follows the "main" successor; side branches go one column to the right
- an if/then detour whose other branch is the merge point keeps the bypass straight down
- End terminators of failure branches sit to the right of their predecessor
- node sizes come from the label (same wrap metrics as the canvas at 13 px)
- edge.meta.back_edge = True on real loop-backs (the canvas draws those in a gutter)
"""

from __future__ import annotations

import math
import re
import threading
from collections import defaultdict

from app.schemas.diagram import DiagramDocument, DiagramEdge, DiagramNode

LAYOUT_TAG = "fc-layered-1"
FONT = 13.0
CHAR_W = FONT * 0.56
LINE_H = FONT + 2
ROW_GAP = 42.0
COL_GAP = 90.0
ORIGIN_X = 40.0
ORIGIN_Y = 40.0

TERMINAL_TYPES = {"terminator", "start", "end"}
DECISION_TYPES = {"decision", "gateway_xor"}
BOX_TYPES = {
    "process",
    "subprocess",
    "input",
    "document",
    "preparation",
    "display",
    "manual_input",
    "data_store",
    "parallelogram",
}

_notes = threading.local()


def take_notes() -> list[str]:
    """Advisory notes from the last flowchart clean-up on this thread (then cleared)."""
    out = list(getattr(_notes, "items", []) or [])
    _notes.items = []
    return out


def _note(msg: str) -> None:
    if not hasattr(_notes, "items") or _notes.items is None:
        _notes.items = []
    _notes.items.append(msg)


# ---------------------------------------------------------------- labels / sizes


def norm_label(text: str) -> str:
    t = (text or "").lower().replace("&", " and ")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _wrap(text: str, max_w: float) -> list[str]:
    """Mirror of canvas._wrapLabelLines (word wrap, hard-break long tokens)."""
    cpl = max(4, int(math.floor(max_w / CHAR_W)))
    tokens: list[str] = []
    for part in re.split(r"\s+", (text or "").replace("\\n", " ").strip()):
        if not part:
            continue
        if len(part) <= cpl:
            tokens.append(part)
        else:
            tokens.extend(part[i : i + cpl] for i in range(0, len(part), cpl))
    lines: list[str] = []
    cur = ""
    for tok in tokens:
        nxt = f"{cur} {tok}" if cur else tok
        if len(nxt) > cpl and cur:
            lines.append(cur)
            cur = tok
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    return lines or [""]


def is_fork_join(node: DiagramNode) -> bool:
    return node.type == "connector_node" and bool(
        re.search(r"\b(fork|join|parallel|split|sync)\b", node.label or "", re.I)
    )


def size_for(node: DiagramNode) -> tuple[float, float]:
    label = (node.label or "").strip()
    t = node.type
    if t in DECISION_TYPES:
        w, h = 180.0, 92.0
        for _ in range(8):
            lines = _wrap(label, w * 0.62)
            longest = max((len(x) for x in lines), default=1)
            fits_h = len(lines) * LINE_H + 16 <= h and len(lines) * LINE_H <= h * 0.62 + 2
            fits_w = longest * CHAR_W <= w * 0.62
            if fits_h and fits_w:
                break
            w += 24
            h += 16
        return w, h
    if t in TERMINAL_TYPES:
        lines = _wrap(label, 232)
        longest = max((len(x) for x in lines), default=1)
        w = min(260.0, max(150.0, longest * CHAR_W + 40))
        h = max(48.0, len(_wrap(label, w - 28)) * LINE_H + 18)
        return w, h
    if is_fork_join(node):
        return 220.0, 14.0
    if t == "connector_node":
        return 40.0, 40.0
    if t == "delay":
        return max(node.width, 120.0), max(node.height, 56.0)
    if t in BOX_TYPES:
        w = 230.0 if t in {"input", "parallelogram", "manual_input", "preparation"} else 210.0
        inner = w - 40 if t in {"input", "parallelogram", "manual_input", "preparation"} else w - 16
        lines = _wrap(label, inner)
        extra = 30 if t == "document" else 22
        h = max(60.0, len(lines) * LINE_H + extra)
        return w, h
    return float(node.width or 140), float(node.height or 60)


# ---------------------------------------------------------------- clean-ups


def apply_show_output_shapes(nodes: list[DiagramNode]) -> list[DiagramNode]:
    """Addendum B: every 'Show …' step is Output (parallelogram) — consistently."""
    out = []
    for n in nodes:
        if n.type in {"process", "display"} and re.match(r"^\s*(show|display)\b", n.label or "", re.I):
            n = n.model_copy(update={"type": "input"})
        out.append(n)
    return out


def merge_consecutive_duplicates(
    nodes: list[DiagramNode], edges: list[DiagramEdge]
) -> tuple[list[DiagramNode], list[DiagramEdge]]:
    """Item 9: two directly-connected process/input nodes with the same label become one."""
    mergeable = {"process", "input", "subprocess", "display", "document"}
    changed = True
    guard = 0
    while changed and guard < 50:
        changed = False
        guard += 1
        by_id = {n.id: n for n in nodes}
        for e in edges:
            a = by_id.get(e.from_node)
            b = by_id.get(e.to_node)
            if not a or not b or a.id == b.id:
                continue
            if a.type not in mergeable or b.type not in mergeable:
                continue
            if not norm_label(a.label) or norm_label(a.label) != norm_label(b.label):
                continue
            # b folds into a
            new_edges: list[DiagramEdge] = []
            seen: set[tuple[str, str, str]] = set()
            for x in edges:
                if x.id == e.id:
                    continue
                src = a.id if x.from_node == b.id else x.from_node
                dst = a.id if x.to_node == b.id else x.to_node
                if src == dst:
                    continue
                key = (src, dst, (x.label or "").strip().lower())
                if key in seen:
                    continue
                seen.add(key)
                new_edges.append(x.model_copy(update={"from_node": src, "to_node": dst}))
            edges = new_edges
            nodes = [n for n in nodes if n.id != b.id]
            _note(f"Merged duplicate consecutive step '{b.label}' ({b.id} into {a.id}).")
            changed = True
            break
    # Identically named End terminators (e.g. two "End: Rejected") are the same end.
    outs = {e.from_node for e in edges}
    first_end: dict[str, str] = {}
    remap: dict[str, str] = {}
    for n in nodes:
        if n.type not in TERMINAL_TYPES or n.id in outs:
            continue
        k = norm_label(n.label)
        if not k or k in {"end", "stop", "start"}:
            continue
        if k in first_end:
            remap[n.id] = first_end[k]
        else:
            first_end[k] = n.id
    if remap:
        nodes = [n for n in nodes if n.id not in remap]
        seen_e: set[tuple[str, str, str]] = set()
        new_edges = []
        for x in edges:
            dst = remap.get(x.to_node, x.to_node)
            key = (x.from_node, dst, (x.label or "").strip().lower())
            if key in seen_e:
                continue
            seen_e.add(key)
            new_edges.append(x.model_copy(update={"to_node": dst}) if dst != x.to_node else x)
        edges = new_edges
        _note(f"Merged {len(remap)} identically named End terminator(s).")
    # Non-consecutive duplicates: advisory only.
    seen_labels: dict[str, str] = {}
    for n in nodes:
        if n.type not in mergeable:
            continue
        k = norm_label(n.label)
        if not k:
            continue
        if k in seen_labels:
            _note(f"Two steps share the label '{n.label}' ({seen_labels[k]}, {n.id}).")
        else:
            seen_labels[k] = n.id
    return nodes, edges


# ---------------------------------------------------------------- graph helpers


def _label_pref(label: str) -> int:
    """Lower = more 'main-line'. Yes/unlabeled before No/fail."""
    t = (label or "").strip().lower()
    if not t:
        return 1
    if re.search(r"\b(no|fail|failed|invalid|reject|rejected|declin|denied|false|error|cancel)\b", t):
        return 3
    if re.search(r"\b(yes|ok|valid|success|approved|true|accept|continue)\b", t):
        return 0
    return 2


def _is_start_like(n: DiagramNode) -> bool:
    return n.type in {"start", "terminator"} and not re.search(
        r"\b(end|stop|done|complete|completed|failed|placed|finish)\b", n.label or "", re.I
    )


def find_back_edges(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> tuple[set[str], list[str]]:
    """DFS from Start (then any other roots). Returns (back edge ids, root order)."""
    ids = [n.id for n in nodes]
    by_id = {n.id: n for n in nodes}
    order_index = {e.id: i for i, e in enumerate(edges)}
    outs: dict[str, list[DiagramEdge]] = defaultdict(list)
    indeg: dict[str, int] = defaultdict(int)
    for e in edges:
        outs[e.from_node].append(e)
        indeg[e.to_node] += 1
    for k in outs:
        outs[k].sort(key=lambda e: (_label_pref(e.label), order_index[e.id]))

    starts = [n for n in nodes if _is_start_like(n) and indeg[n.id] == 0]
    if not starts:
        starts = [n for n in nodes if indeg[n.id] == 0 and outs.get(n.id)]
    if not starts:
        starts = [n for n in nodes if _is_start_like(n)] or list(nodes[:1])
    starts.sort(key=lambda n: (0 if re.search(r"start|begin", n.label or "", re.I) else 1, n.y, n.x))
    roots = [s.id for s in starts]
    for nid in sorted(ids, key=lambda i: (by_id[i].y, by_id[i].x)):
        if nid not in roots and indeg[nid] == 0:
            roots.append(nid)

    color: dict[str, int] = {}
    back: set[str] = set()

    def dfs(root: str) -> None:
        stack: list[tuple[str, int]] = [(root, 0)]
        color[root] = 1
        while stack:
            nid, i = stack[-1]
            lst = outs.get(nid, [])
            if i < len(lst):
                stack[-1] = (nid, i + 1)
                e = lst[i]
                c = color.get(e.to_node, 0)
                if c == 1:
                    back.add(e.id)
                elif c == 0:
                    color[e.to_node] = 1
                    stack.append((e.to_node, 0))
            else:
                color[nid] = 2
                stack.pop()

    for r in roots:
        if color.get(r, 0) == 0:
            dfs(r)
    for nid in sorted(ids, key=lambda i: (by_id[i].y, by_id[i].x)):
        if color.get(nid, 0) == 0:
            roots.append(nid)
            dfs(nid)
    return back, roots


# ---------------------------------------------------------------- layout


def layout_flowchart(document: DiagramDocument) -> DiagramDocument:
    nodes = [n.model_copy(deep=True) for n in document.nodes]
    edges = list(document.edges)
    if len(nodes) < 2:
        return document

    # Free-floating annotations stay out of the flow grid.
    connected = {e.from_node for e in edges} | {e.to_node for e in edges}
    flow = [n for n in nodes if n.id in connected or n.type != "text_box"]
    loose = [n for n in nodes if n not in flow]
    by_id = {n.id: n for n in flow}
    edges = [e for e in edges if e.from_node in by_id and e.to_node in by_id]

    for n in flow:
        n.width, n.height = size_for(n)

    back, roots = find_back_edges(flow, edges)
    fwd = [e for e in edges if e.id not in back]
    order_index = {e.id: i for i, e in enumerate(edges)}
    f_out: dict[str, list[DiagramEdge]] = defaultdict(list)
    f_in: dict[str, list[DiagramEdge]] = defaultdict(list)
    for e in fwd:
        f_out[e.from_node].append(e)
        f_in[e.to_node].append(e)

    # Topological order (Kahn, roots first, stable by original y)
    indeg = {n.id: len(f_in[n.id]) for n in flow}
    pos_key = {n.id: (n.y, n.x) for n in flow}
    ready = sorted([i for i, d in indeg.items() if d == 0], key=lambda i: (0 if i in roots[:1] else 1, pos_key[i]))
    topo: list[str] = []
    while ready:
        nid = ready.pop(0)
        topo.append(nid)
        for e in sorted(f_out[nid], key=lambda e: (_label_pref(e.label), order_index[e.id])):
            indeg[e.to_node] -= 1
            if indeg[e.to_node] == 0:
                ready.append(e.to_node)
    if len(topo) < len(flow):  # defensive: should not happen after DFS
        topo.extend(n.id for n in flow if n.id not in topo)

    rank: dict[str, int] = {}
    for nid in topo:
        preds = [rank[e.from_node] for e in f_in[nid] if e.from_node in rank]
        rank[nid] = (max(preds) + 1) if preds else 0

    # Distance to sink + forward reachability (DAG)
    dist: dict[str, int] = {}
    reach: dict[str, set[str]] = {}
    for nid in reversed(topo):
        kids = [e.to_node for e in f_out[nid]]
        dist[nid] = (max(dist[k] for k in kids) + 1) if kids else 0
        r: set[str] = set()
        for k in kids:
            r.add(k)
            r |= reach[k]
        reach[nid] = r

    sinks = [nid for nid in topo if not f_out[nid]]
    main_end = None
    if sinks:
        start_id = roots[0] if roots else topo[0]
        reachable_sinks = [s for s in sinks if s in reach.get(start_id, set())] or sinks

        def end_score(s: str) -> tuple:
            lbl = by_id[s].label or ""
            bad = 1 if re.search(r"\b(fail|failed|error|cancel|reject|denied|empty|abort)\b", lbl, re.I) else 0
            return (-bad, rank[s], -topo.index(s))

        main_end = max(reachable_sinks, key=end_score)

    def leads_to_main(nid: str) -> bool:
        return main_end is not None and (nid == main_end or main_end in reach.get(nid, set()))

    main_child: dict[str, str] = {}
    for nid in topo:
        outs = f_out[nid]
        if not outs:
            continue
        if len(outs) == 1:
            main_child[nid] = outs[0].to_node
            continue
        kids = [e.to_node for e in outs]
        bypass = [k for k in kids if any(k != o and k in reach.get(o, set()) for o in kids)]
        if bypass:
            main_child[nid] = max(bypass, key=lambda k: (rank[k], -kids.index(k)))
            continue
        best = max(
            outs,
            key=lambda e: (
                1 if leads_to_main(e.to_node) else 0,
                -_label_pref(e.label),
                dist[e.to_node],
                -order_index[e.id],
            ),
        )
        main_child[nid] = best.to_node

    # Column assignment with corridor reservation
    occupied: dict[tuple[int, int], str] = {}
    col: dict[str, int] = {}
    root_col = 0
    for nid in topo:
        preds = [e.from_node for e in f_in[nid] if e.from_node in col]
        if not preds:
            want = root_col if nid == (roots[0] if roots else None) else (max(col.values(), default=-1) + 1 if col else 0)
        else:
            mains = [p for p in preds if main_child.get(p) == nid]
            if mains:
                want = min(col[p] for p in mains)
            else:
                want = min(col[p] for p in preds) + 1
        c = want
        while (rank[nid], c) in occupied and occupied[(rank[nid], c)] != nid:
            c += 1
        col[nid] = c
        occupied[(rank[nid], c)] = nid
        mc = main_child.get(nid)
        if mc is not None and rank.get(mc, 0) > rank[nid] + 1:
            for r in range(rank[nid] + 1, rank[mc]):
                occupied.setdefault((r, c), f"corridor:{nid}")

    # Failure End terminators sit to the right of their predecessor.
    for nid in topo:
        n = by_id[nid]
        if nid == main_end or f_out[nid] or n.type not in TERMINAL_TYPES:
            continue
        ins = [e for e in edges if e.to_node == nid]
        if len(ins) != 1:
            continue
        p = ins[0].from_node
        if p not in rank or rank[nid] != rank[p] + 1:
            continue
        rp = rank[p]
        c = col[p] + 1
        if (rp, c) in occupied:
            continue  # only when the cell right of the predecessor is free
        occupied.pop((rank[nid], col[nid]), None)
        rank[nid] = rp
        col[nid] = c
        occupied[(rp, c)] = nid

    # Compact empty rows
    used_rows = sorted({rank[n] for n in rank})
    remap = {r: i for i, r in enumerate(used_rows)}
    for nid in rank:
        rank[nid] = remap[rank[nid]]

    n_rows = (max(rank.values()) + 1) if rank else 0
    n_cols = (max(col.values()) + 1) if col else 0
    col_w = [0.0] * n_cols
    row_h = [0.0] * n_rows
    for nid in topo:
        n = by_id[nid]
        col_w[col[nid]] = max(col_w[col[nid]], n.width)
        row_h[rank[nid]] = max(row_h[rank[nid]], n.height)
    col_w = [w or 160.0 for w in col_w]

    left_loops = 0
    for e in edges:
        if e.id in back:
            s, t = by_id[e.from_node], by_id[e.to_node]
            if col.get(e.from_node, 0) <= col.get(e.to_node, 0):
                left_loops += 1
    origin_x = ORIGIN_X + min(6, left_loops) * 22.0 + (30.0 if left_loops else 0.0)

    # Wider gaps where a same-row side edge carries a long label (e.g. "Yes (after 3 failures)").
    gap = [COL_GAP] * max(n_cols, 1)
    for e in edges:
        a, b = e.from_node, e.to_node
        if a in rank and b in rank and rank[a] == rank[b] and col[b] == col[a] + 1 and e.label:
            need = len(e.label) * 6.8 + 36.0
            gap[col[a]] = max(gap[col[a]], need)
    col_x: list[float] = []
    x = origin_x
    for c in range(n_cols):
        col_x.append(x)
        x += col_w[c] + gap[c]
    row_y: list[float] = []
    y = ORIGIN_Y
    for r in range(n_rows):
        row_y.append(y)
        y += row_h[r] + ROW_GAP

    for nid in topo:
        n = by_id[nid]
        c, r = col[nid], rank[nid]
        n.x = round(col_x[c] + (col_w[c] - n.width) / 2, 1)
        n.y = round(row_y[r] + (row_h[r] - n.height) / 2, 1)
        meta = dict(n.meta or {})
        meta.update({"layout": LAYOUT_TAG, "fc_rank": r, "fc_col": c})
        n.meta = meta

    # Fork / Join bars span the columns of the branches they fan out to / merge.
    for nid in topo:
        n = by_id[nid]
        if not is_fork_join(n):
            continue
        nb = [e.to_node for e in edges if e.from_node == nid] + [e.from_node for e in edges if e.to_node == nid]
        cxs = [by_id[m].x + by_id[m].width / 2 for m in nb if m in rank and m != nid]
        if len(cxs) < 2:
            continue
        x0, x1 = min(cxs) - 60.0, max(cxs) + 60.0
        if x1 - x0 <= n.width:
            continue
        clash = any(
            m != nid and rank[m] == rank[nid] and by_id[m].x < x1 and by_id[m].x + by_id[m].width > x0
            for m in rank
        )
        if not clash:
            n.x, n.width = round(x0, 1), round(x1 - x0, 1)

    # Loose annotations: right of the grid, stacked.
    ly = ORIGIN_Y
    lx = (col_x[-1] + col_w[-1] + COL_GAP) if col_x else ORIGIN_X
    for n in loose:
        n.x, n.y = lx, ly
        ly += n.height + 24

    new_edges: list[DiagramEdge] = []
    for e in document.edges:
        meta = dict(e.meta or {})
        meta.pop("waypoints", None)
        if e.id in back:
            meta["back_edge"] = True
        else:
            meta.pop("back_edge", None)
        new_edges.append(e.model_copy(update={"meta": meta}))

    out_nodes = flow + loose
    out_nodes.sort(key=lambda n: (n.y, n.x))
    return DiagramDocument(
        diagram_type=document.diagram_type,
        title=document.title,
        nodes=out_nodes,
        edges=new_edges,
    )


def mark_back_edges(document: DiagramDocument) -> DiagramDocument:
    """Edit fallback (no relayout): only flag the loop-backs for the canvas."""
    back, _ = find_back_edges(list(document.nodes), list(document.edges))
    edges = []
    for e in document.edges:
        meta = dict(e.meta or {})
        meta.pop("waypoints", None)
        if e.id in back:
            meta["back_edge"] = True
        else:
            meta.pop("back_edge", None)
        edges.append(e.model_copy(update={"meta": meta}))
    return document.model_copy(update={"edges": edges})


def is_auto_layout(document: DiagramDocument | None) -> bool:
    """True when `document` is exactly what layout_flowchart would produce (user did not move shapes)."""
    if document is None or not document.nodes:
        return False
    if not all((n.meta or {}).get("layout") == LAYOUT_TAG for n in document.nodes if n.type != "text_box"):
        return False
    relaid = layout_flowchart(document)
    want = {n.id: (n.x, n.y) for n in relaid.nodes}
    for n in document.nodes:
        if n.id not in want:
            continue
        wx, wy = want[n.id]
        if abs(n.x - wx) > 2 or abs(n.y - wy) > 2:
            return False
    return True


_STOP = {
    "the", "and", "for", "add", "with", "before", "after", "into", "from", "option", "step", "please",
    "new", "make", "change", "update", "also", "then", "that", "this", "between", "when", "should",
    "can", "you", "all", "any", "are", "out", "not", "but", "its", "has", "have", "use",
}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) >= 3 and t not in _STOP}


def lock_unrelated_labels(
    previous: DiagramDocument, document: DiagramDocument, edit_request: str
) -> DiagramDocument:
    """Edit mode: undo label rewrites of existing shapes the user's request does not touch.

    A kept id may change its label only when the new label gains a word that appears in the
    edit request (e.g. "Gift card" added to the payment-method choice) or the request quotes
    the old label. Everything else keeps its old label word-for-word.
    """
    req = _tokens(edit_request)
    req_low = (edit_request or "").lower()
    old_nodes = {n.id: n for n in previous.nodes}
    old_edges = {e.id: e for e in previous.edges}

    def allowed(old: str, new: str) -> bool:
        if norm_label(old) == norm_label(new):
            return True
        if old and norm_label(old) in norm_label(req_low):
            return True
        return bool((_tokens(new) - _tokens(old)) & req)

    nodes = []
    for n in document.nodes:
        o = old_nodes.get(n.id)
        if o is not None and (n.label or "") != (o.label or "") and not allowed(o.label or "", n.label or ""):
            _note(f"Kept original label of {n.id!r} ({o.label!r}); edit request does not mention it.")
            n = n.model_copy(update={"label": o.label})
        nodes.append(n)
    edges = []
    for e in document.edges:
        o = old_edges.get(e.id)
        if (
            o is not None
            and o.from_node == e.from_node
            and (e.label or "") != (o.label or "")
            and not allowed(o.label or "", e.label or "")
        ):
            e = e.model_copy(update={"label": o.label})
        edges.append(e)
    return document.model_copy(update={"nodes": nodes, "edges": edges})


def repair_duplicate_branch_labels(
    nodes: list[DiagramNode], edges: list[DiagramEdge]
) -> tuple[list[DiagramNode], list[DiagramEdge]]:
    """A decision with two same-label branches (e.g. Yes→A and Yes→B) means "do A and B in
    parallel": insert a Fork bar (and a Join bar when A and B continue to the same node)."""
    by_id = {n.id: n for n in nodes}
    used_ids = set(by_id) | {e.id for e in edges}

    def new_id(base: str) -> str:
        i, cand = 1, base
        while cand in used_ids:
            i += 1
            cand = f"{base}_{i}"
        used_ids.add(cand)
        return cand

    forks: dict[tuple[str, ...], str] = {}
    out_edges: list[DiagramEdge] = list(edges)
    for d in list(nodes):
        if d.type not in DECISION_TYPES:
            continue
        groups: dict[str, list[DiagramEdge]] = defaultdict(list)
        for e in out_edges:
            if e.from_node == d.id and e.label and e.to_node in by_id:
                groups[norm_label(e.label)].append(e)
        for _, grp in groups.items():
            targets = tuple(sorted({e.to_node for e in grp}))
            if len(grp) < 2 or len(targets) < 2:
                continue
            fork_id = forks.get(targets)
            if fork_id is None:
                fork_id = new_id(f"{d.id}_fork")
                forks[targets] = fork_id
                w, h = 220.0, 14.0
                fork = DiagramNode(id=fork_id, type="connector_node", label="Fork", x=0, y=0, width=w, height=h)
                nodes.append(fork)
                by_id[fork_id] = fork
                for t in targets:
                    out_edges.append(
                        DiagramEdge(id=new_id(f"e_{fork_id}_{t}"), type=grp[0].type, from_node=fork_id, to_node=t)
                    )
                # Join when every branch continues to the same single node.
                nexts = []
                for t in targets:
                    o = [e for e in out_edges if e.from_node == t]
                    nexts.append(o[0].to_node if len(o) == 1 else None)
                if nexts and None not in nexts and len(set(nexts)) == 1:
                    join_id = new_id(f"{d.id}_join")
                    join = DiagramNode(id=join_id, type="connector_node", label="Join", x=0, y=0, width=w, height=h)
                    nodes.append(join)
                    by_id[join_id] = join
                    c = nexts[0]
                    out_edges = [e for e in out_edges if not (e.from_node in targets and e.to_node == c)]
                    for t in targets:
                        out_edges.append(
                            DiagramEdge(id=new_id(f"e_{t}_{join_id}"), type=grp[0].type, from_node=t, to_node=join_id)
                        )
                    out_edges.append(
                        DiagramEdge(id=new_id(f"e_{join_id}_{c}"), type=grp[0].type, from_node=join_id, to_node=c)
                    )
            keep = grp[0]
            drop = {e.id for e in grp[1:]}
            out_edges = [
                (e.model_copy(update={"to_node": fork_id}) if e.id == keep.id else e)
                for e in out_edges
                if e.id not in drop
            ]
            _note(f"{d.label!r}: {len(grp)} '{keep.label}' branches treated as parallel steps (Fork/Join).")
    return nodes, out_edges


def pin_above_insertion(previous: DiagramDocument, document: DiagramDocument) -> DiagramDocument:
    """Edit mode after a relayout: shapes above the first NEW shape keep their exact old x/y
    (when that spot is still free), so an edit never shuffles the untouched top of the chart."""
    old = {n.id: n for n in previous.nodes}
    new_nodes = [n for n in document.nodes if n.id not in old]
    if not new_nodes:
        return document
    cut = min(n.y for n in new_nodes)
    nodes = [n.model_copy(deep=True) for n in document.nodes]

    def clash(a: DiagramNode, x: float, y: float) -> bool:
        for b in nodes:
            if b.id == a.id:
                continue
            if x < b.x + b.width + 8 and x + a.width + 8 > b.x and y < b.y + b.height + 8 and y + a.height + 8 > b.y:
                return True
        return False

    for n in nodes:
        o = old.get(n.id)
        if o is None or o.y + o.height > cut:
            continue
        if (abs(n.x - o.x) > 0.5 or abs(n.y - o.y) > 0.5) and abs(n.width - o.width) < 1 and abs(n.height - o.height) < 1:
            if not clash(n, o.x, o.y):
                n.x, n.y = o.x, o.y
    return document.model_copy(update={"nodes": nodes})
