# Drill Down Features (USP)

Status of the **Drill Down** feature described in `Requirements.md` (BR6), mapped against GenAI Diagram Studio today and against the existing product at app.drilldown.tech, plus the remaining questions for the client.

**Bottom line:** The concept is now **clear enough to build an MVP**. We confirmed in the existing DrillDown product (app.drilldown.tech, checked on 2026-11-08) that a Drill Down is a **named, colored group of existing shapes and lines on the same canvas**, not a nested diagram, popup page or linked page. The remaining gaps are smaller: what the canvas shows after saving, how remembered categories and colors are stored, export behavior, and permissions.

In this codebase, "Drill Down" currently appears only as **product branding** (welcome tour, storage key). There is **no** drill-down data model, UI or API yet.

---

## 1. What the existing DrillDown product does (observed)

| Aspect | Observed behavior |
|--------|-------------------|
| What it is | A named, colored subset of nodes and edges on the same diagram |
| How to create | Select elements (**Ctrl+click**, or **Shift+drag** box-select), click **Create DrillDown** |
| Fields | **Name**, **Color**, **Category**, **Description** (plain text), then **Add DrillDown** |
| Where it lives | A sidebar list of DrillDowns, grouped by **Category** ("No DrillDowns created" when empty) |
| How to open | Click a DrillDown in the sidebar, and its elements are highlighted in its color |
| Nested diagrams | None. "Subprocess" is only a shape and is unrelated to DrillDowns |
| Documentation | None. There's no help, docs, FAQ or guide, and none of the 12 public samples has a saved DrillDown |

**Not yet observed:** what the canvas shows after a DrillDown is saved but not selected, edit and delete screens, how categories and colors are remembered, export, and permissions. These can be closed by creating one test DrillDown on a throwaway diagram.

---

## 2. What the client FRD specifies (BR6), now interpreted

### BR6.1: Add a Drill Down section
| Requirement | Interpretation | Status |
|-------------|----------------|--------|
| Select shape(s) and/or line(s), then "add drill down" | Selection, then a Create DrillDown action and form | Clear |
| Multi-select gives one shared drill down (FRD says CTRL) | Support **Ctrl+click** and **Shift+drag**, as the existing product does | Clear |
| Specify **category** and **label color** | Category groups DrillDowns in the sidebar; Color is the highlight color | Mostly clear |
| Remember categories and label colors | Offer previously used categories and colors as quick picks | Storage scope open |
| Delete a drill-down **label** (typo/duplicate) | Most likely deleting a saved category or color from the remembered list, not a whole DrillDown | **Confirm with client** |

### BR6.2: Edit a Drill Down section
| Requirement | Interpretation | Status |
|-------------|----------------|--------|
| Edit **text content**, **label** and **color** | Text content = Description, label = Name, color = Color | Clear |
| MVP: cannot change the attached shapes/lines | Explicit MVP constraint | Clear |

### BR6.3: Delete a Drill Down section
| Requirement | Interpretation | Status |
|-------------|----------------|--------|
| Delete if the user has edit permissions | Delete the whole DrillDown | Clear, but depends on BR7 roles |

### Glossary (proposed)
- **Drill Down:** a named group of selected shapes and lines.
- **Name** (FRD "label"): the Drill Down's title.
- **Color** (FRD "label color"): the highlight color.
- **Category:** a grouping used in the sidebar list.
- **Description** (FRD "text content"): plain-text details.

### Explicitly out of MVP (from FRD)
- Re-binding a drill down to different shapes or lines after creation

---

## 3. What we have in GenAI today

| Building block | Status | Notes |
|----------------|--------|-------|
| Interactive SVG canvas (nodes + edges) | Done | `static/js/designer/canvas.js` |
| Multi-select | Done | **Shift+click** today; add Ctrl+click and box-select |
| Context menu on selection | Done | Rename / Delete; add "Create Drill Down" |
| Diagram JSON (`nodes`, `edges`) | Done | Add a `drilldowns[]` field |
| Project save/load (MySQL) | Done | `genai_projects.diagram_json` |
| Auth / edit permissions | Not started | Needed for BR6.3 |
| Drill-down UI / API / schema | Not started | The USP to build |

Selection, the context menu and diagram JSON are natural extension points. Nothing needs to be thrown away.

---

## 4. Remaining gaps

### Resolved
1. ~~Definition of a Drill Down~~: a named, colored group on the same canvas.
2. ~~Content model~~: Name, Color, Category and plain-text Description.
3. ~~How to open~~: from a sidebar list, which highlights its elements.
4. ~~Selection modifier~~: Ctrl+click plus Shift+drag.
5. ~~Label vs category vs color~~: see the glossary (one item still to confirm).

### Still open (decide for MVP)
6. **Canvas marker:** does a shape show anything (badge or colored outline) when its Drill Down is not selected?
7. **One shape in many Drill Downs:** allowed? If so, how does highlighting combine?
8. **Category and color memory:** per user, per organization or per document?
9. **"Delete a drilldown label":** a remembered category or color, or something else?
10. **Export (PNG/SVG/JSON):** include Drill Down highlights, or interactive mode only?
11. **AI generation:** should the AI propose Drill Downs, or are they always manual?
12. **Persistence:** inside `diagram_json` (recommended for MVP) or separate DB tables?

### Dependent on other FRD work
13. **Permissions** (Author / Collaborator / Viewer): BR7 is not built; BR6.3 assumes edit permission.
14. **"Export AI diagram into the DrillDown tool"** (BR4): is GenAI meant to *become* DrillDown, or feed a separate app?

---

## 5. Client questions (non-technical wording)

1. When a shape belongs to a Drill Down, should it look different on the diagram even when nobody has opened that Drill Down?
2. Can one shape belong to more than one Drill Down?
3. What are typical **categories** and **colors** people use today?
4. Should saved categories and colors be shared across the whole team, or be personal to each user?
5. When the FRD says "delete a drilldown label," does it mean removing a saved category or color from the pick list?
6. Should viewers (read-only people) be able to open and read Drill Downs?
7. Should exported images (PNG/SVG) show Drill Down highlights, or only the plain diagram?
8. Is GenAI Diagram Studio meant to **become** DrillDown, or only the **AI drafting** step that then imports into DrillDown?

---

## 6. Proposed MVP

Based on the existing product's behavior, pending answers to section 5:

1. The user selects shapes or lines (Ctrl+click or Shift+drag), then chooses **Create Drill Down** from the context menu or toolbar.
2. A form asks for **Name**, **Color**, **Category** (with remembered quick picks) and **Description**.
3. A **Drill Downs sidebar** lists them grouped by category. Clicking one highlights its shapes and lines in its color and shows its description.
4. Name, Color, Category and Description can be edited, and the whole Drill Down can be deleted. Attached shapes can't be changed (MVP rule).
5. Categories and colors are remembered per user (per browser until auth exists).
6. Drill Downs are stored inside the project's `diagram_json` as a `drilldowns[]` array (id, name, color, category, description, nodeIds, edgeIds).

Nested canvases, permissions and payment wait for BR1/BR7.

---

## 7. Completeness checklist

| Area | Enough detail to build? |
|------|-------------------------|
| Add via selection | Yes |
| Multi-select | Yes (Ctrl+click + Shift+drag) |
| Fields (Name, Color, Category, Description) | Yes |
| Category + color pick lists | Mostly (storage scope open) |
| Remember categories/colors | Partially (per user vs org) |
| Delete label | **No** (confirm meaning) |
| Edit name / description / color | Yes |
| Delete Drill Down | Yes (permissions pending BR7) |
| Open / highlight interaction | Yes |
| Canvas marker when not selected | **No** |
| Data model | Yes (`drilldowns[]` in diagram JSON) |
| Nested vs annotation semantics | Yes (annotation group on the same canvas) |
| Export behavior | **No** |

**Verdict:** Enough detail to **estimate and build the MVP** now. Confirm the open items in section 5 with the client before final polish, ideally after we save one test Drill Down in the existing product to see its post-save behavior.