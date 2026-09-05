# Roles

The generated [receiver lifecycle cell](../docs/lifecycle.md#ticket-lifecycle)
names the worker-or-planner authority a dispatched child files under.

1. The starting agent is the orchestrator. It owns user questions, scope
   decisions, and undelegated irreversible effects; it never delegates
   accountability.
2. Dispatched children take one of two profiles — capability classes, never
   personas:
   - `orch-planner` — judgment: planning, critique, adjudication,
     architecture, review, synthesis.
   - `orch-worker` — execution: implementation, repair, investigation,
     diagnosis, and shape-checked mechanics.
3. Concrete model and effort bindings per host are owned solely by
   [profiles.md](../hosts/profiles.md).
4. Resolve profile at each dispatch against the active host's bindings
   (clause 3). An explicit ticket profile wins and must name exactly
   `orch-planner` or `orch-worker`; an unknown or decorative value is refused.
   Without one, `orch-do` prefers `orch-worker` and `orch-judge` prefers
   `orch-planner` for compatibility. Those defaults are operation preferences,
   not authority rules: either operation may run under either explicit profile.
   A hand-written dispatch outside those registered operations names its
   profile or is refused, never silently substituted.
5. An override binds only the dispatch naming it; it never propagates to
   a descendant dispatch.
6. A role-bearing applied skill runs only in an established child matching
   clause 4's resolved profile. Its declaration is checked against that
   profile; it does not select or change the running model. The emitted launch
   uses the selected host's real entry mechanism and carries the prompt
   verbatim. The `role: none` on a profile-neutral kernel operation only means
   the operation does not choose authority: it still runs through that launch
   in a profiled child. Root and glue-only `role: none` contexts never execute
   the deliverable, and a mismatched child refuses it.
7. A child needing a user-only decision returns a `kind: user-only`
   question and resume state. Root asks its text verbatim and returns
   the answer without deciding it.
8. The [dispatch contract](../contracts/dispatch.md) binds every record a
   child files to the attempt it was dispatched under. A write naming another
   authority is a structured refusal; the child never substitutes or repairs
   that authority.
