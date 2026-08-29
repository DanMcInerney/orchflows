# Roles

The generated [receiver lifecycle cell](../docs/lifecycle.md#ticket-lifecycle)
names the worker-or-planner authority established at receipt.

1. The starting agent is the orchestrator. It owns user questions, scope
   decisions, and undelegated irreversible effects; it never delegates
   accountability.
2. Children take one of two roles — capability classes, never personas:
   - `orch-planner` — judgment: planning, critique, adjudication,
     architecture, review, synthesis.
   - `orch-worker` — execution: implementation, repair, investigation,
     diagnosis, and shape-checked mechanics.
3. Concrete model and effort bindings per host are owned solely by
   [profiles.md](../skills/engines/orch-frontier/references/profiles.md).
4. Resolve role at each dispatch, against the active host's profile
   bindings (clause 3), in order: an explicit packet profile wins; else
   the applied skill's declared role — for a stated skill `sequence`, its
   head `executor`'s, binding every skill in the chain; a pack-cell
   `sequence` is stage data, so its ticket executor establishes the one
   role; a `none` declaration or a dispatch naming no applied skill takes
   only a caller-named profile (name `orch-planner` for a dispatched
   template stub unless judgment says otherwise); absent a caller-named
   profile the dispatch is refused, never substituted silently. A
   continuation's declared `role:` never changes that established binding.
5. An override binds only the dispatch naming it; it never propagates to
   a descendant dispatch.
6. A role-bearing skill runs only in an established child of the
   matching role — clause 4's resolved role, never a chained skill's own
   declaration. That child executes the exact named skill directly;
   root, `role: none`, and a mismatched child refuse it.
7. A child needing a user-only decision returns a `kind: user-only`
   question and resume state. Root asks its text verbatim and returns
   the answer without deciding it.
8. The [dispatch contract](../contracts/dispatch.md)'s receipt compares the
   established child with the committed authority before clause 6 permits
   execution. A disagreement is a structured refusal; the child never
   substitutes or repairs the packet.
