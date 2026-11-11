# Generator contexts

Each `<diagram_type>.py` owns `GUIDANCE` (all generator rules for that type)
and `TOOLBOX` (`ToolboxItem` shapes with default sizes). `__init__.py` maps the
eight supported type ids to those modules. Generic JSON/edit/layout rules live
in `../base.py`; no type-specific rules belong in that base.

`../diagrams.py` keeps the public `TOOLBOX`, `DIAGRAM_TYPE_GUIDANCE`, and
`DIAGRAM_SYSTEM_INSTRUCTION` aliases and builds the selected context only.
The pipeline still sends the shared base as the system instruction. Request,
process inventory, and surgical edit data remain in the user message.

## Runtime configuration

Under `/config` → **Agent Prompts**:

- **Shared Base** edits `generator.system`.
- Each diagram tab edits `generator.context.<diagram_type>`: rules plus the
  complete catalog text (including sizes). Saves use the existing versioned
  `genai_prompts` table; activation/reset semantics are unchanged.
- **Other Agent Prompts** retains Analyst, Planner, QC, and the existing
  `generator.guidance.<diagram_type>` keys for compatibility.

Without a saved full-context override, the context is built from its type's
file defaults, any legacy guidance override, and the effective toolbox (the
existing `toolbox.overrides` settings still apply). A saved full context wins
over those defaults: it is an explicit text snapshot. Resetting the context
reactivates the file-backed/legacy/effective-toolbox fallback. No existing DB
override is migrated or deleted.

Analyst and QC consume the same effective type context as the Generator.
Existing QC system prompts remain separately configurable as before.

The catalog in a full-context override is generation input, not registration
of new canvas shapes. Use **Diagram Types & Toolbox** to change actual toolbox
availability/default dimensions; keep any saved context catalog in sync.
