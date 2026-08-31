# Improvement

1. Friction law: on friction — more than two attempts at one step, a
   missing input, tool, or document, surprising output, a contract gap,
   or a workaround — the agent logs and continues, through the installed
   friction logger the host instruction block names, whose fallback that
   block spells too.
   Record observations only, never causes. Logging is exempt from every
   bound. Logging friction is part of completing the task: a session that
   hit friction and logged nothing failed silently.
2. Observation changes nothing. Logs and proposals are passive; only a
   human-reviewed merge activates a change, and only a later matching
   run verifies it.
3. Every finding routes to exactly one causal owner — a library file
   (skill, rule, contract, pack cell, reference, script, workflow,
   or the host block template), a custom workflow file, a project
   file, or a named host-environment defect (interpreter, tool, or
   configuration). The owner fixes the proposal's scope:
   `environment` — host machine state; `project` — the repository the
   friction arose in; `workflow` — library or custom workflow files
   at any authoring scope.
   Blame classes recorded at joins (caller under-supplied vs child
   under-delivered) are the router.
4. A proposal qualifies on recurrence — the same owner-assigned
   cluster, grouped by observed-text similarity, at least three times,
   or across two distinct sessions, where a differing run or host
   counts when entries carry no session — or on a checked contradiction:
   an entry whose observed contradiction checks true against its owner's
   current text qualifies alone. An `environment` cluster qualifies on
   a probe — the exact command whose failure reproduces the defect;
   the probe is its oracle. Other one-off friction is noise until
   it repeats. A recurring cluster qualifies a `consolidate` proposal
   instead, targeting bloat rather than incorrectness.
5. Replay: a proposal whose friction cluster includes a replayable item
   (its ticket and the run's frozen statement still present) must
   re-run that item against the amended owner and pass before it is
   proposed for merge. A proposal that cannot replay says so.
6. The library improves through the same delivery machinery it provides.
   Scope routes activation: an accepted `workflow` proposal is a root
   ticket delivered under the code pack with the validator and tests as
   oracles, whose last act appends the proposal's covered line through
   `tickets.py improvement --covered`; a `project` proposal, the same
   machinery in its own repository under its own oracles; an
   `environment` proposal is actioned directly by the human and verified
   by its probe passing. The cycle end to end — mine, then deliver — is
   the `self-improve` workflow under `example-workflows/`, one run in the sink
   per cycle.
