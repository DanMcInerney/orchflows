# Delegation contract

The packet every dispatch carries — the one dispatch currency.
`orch-delegate` requires all six parts below and refuses a dispatch
missing any. A [work item](work-item.md) extends this packet: packet
parts ⊕ completion test ⊕ lifecycle ⊕ graph position — and a work-item
dispatch may supply the six parts by reference to the ticket path.

- `objective` — one explicit outcome; a child with two objectives is two
  dispatches.
- `inputs` — the fixed evidence the child works from, by identity; the
  child gathers nothing outside them unless the objective is itself
  investigation. The spec's `binding_constraints` ([spec.md](spec.md))
  ride `inputs` verbatim — never re-derived or summarized.
- `authority` — the write scope granted, a subset of the caller's own,
  plus named excluded actions. User interaction is excluded from every
  child by default, per rules/delegation.md rule 2 (user interaction is
  glue); a packet grants it explicitly to lift the exclusion. Hitting an
  excluded action never runs silently: a work-item dispatch suspends
  through the ticket's `## Handoff` ([work-item.md](work-item.md)); a
  packet-only child stops and returns partial results plus the exclusion
  hit, per rules/composition.md rule 8 — the caller re-dispatches with a
  ticket when resume matters.
- `bounds` — the effort budget (tool calls, iterations, tokens, or time)
  and any tool or source guidance.
- `return_contract` — the named fields the child's return must carry; a
  dispatch granting a non-empty write scope contracts for
  `changed_artifacts` among them, and a result whose changed_artifacts
  exceed the granted write scope is rejected at the join regardless of
  its verdicts. The payload lives in the dispatch's durable artifact
  where the dispatch has one, the closing message delivering it or
  pointing to it, per rules/delegation.md §10; a packet naming no
  durable artifact contracts for a message-only return; nothing else
  crosses back.
- `reply_to` — the literal identifier the child's closing message must
  address, computed once from the dispatcher's own identity: its own
  assigned name where the dispatcher is itself a named child, `main`
  where the dispatcher is the top-level orchestrator. Never left for
  the child to infer — nothing in a child's own context reveals who
  dispatched it, and a spawn surface whose return travels only by an
  addressed message (references/profiles.md) turns a missing `reply_to`
  into a silently misdirected return, not a loud refusal.

A seventh, optional part: `profile` — an explicit role override per
rules/roles.md §4, binding only the dispatch naming it (one-shot) and
never propagating to a descendant dispatch; its absence defers role
resolution to rules/roles.md §4's remaining order. Only a missing part
among the six refuses a dispatch; a missing `profile` never does.

Blame rule, recorded at every failed join: a failure traceable to a
missing or false packet field is the caller's defect; a failure to
deliver the return contract inside authority and bounds is the child's.
The blame class routes the finding to its causal owner.

A child never re-dispatches its primary work, and may sub-delegate only
with authority attenuated to a subset of its own.
