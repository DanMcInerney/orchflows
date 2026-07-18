# Roles

1. The starting agent is the orchestrator. It owns user questions, scope
   decisions, and undelegated irreversible effects; it never delegates
   accountability.
2. Children take one of two roles — capability tiers, never personas:
   - `orch-planner` — judgment: planning, critique, adjudication,
     architecture, review, synthesis.
   - `orch-worker` — execution: implementation, repair, investigation,
     diagnosis, and shape-checked mechanics.
3. Concrete model and effort bindings per host are owned solely by
   [profiles.md](../skills/kernel/orch-delegate/references/profiles.md).
4. Resolve role at each dispatch, against the active host's profile
   bindings (clause 3), in order: an explicit packet profile wins; else
   the applied skill's declared role; a `none` declaration or a
   dispatch naming no applied skill takes only a caller-named profile
   (name `orch-planner` for a dispatched composition body unless
   judgment says otherwise); absent a caller-named profile the dispatch
   is refused, never substituted silently.
5. An override binds only the dispatch naming it; it never propagates to
   a descendant dispatch.
