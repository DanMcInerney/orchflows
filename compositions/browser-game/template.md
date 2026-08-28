---
name: browser-game
description: Turn an incomplete browser-game brief into evidence-bound checkpoints and pack-stamped successor delivery.
entry: named
placeholders: [brief, workspace]
---

One incomplete product request enters as `brief`; `workspace` is the
git-backed product repository. Those are the only required invocation
inputs. The workflow returns a versioned program record, fixed evidence
identities, one checkpoint disposition, and a successor plan whose
distinct artifact kinds carry their existing pack stamps and run/root
identities.

Missing fields never become product defaults. An empirical gap becomes
a declared experiment or open decision. A `kind: user-only` gap returns
one verbatim question for the root to relay and cannot be answered by
evidence. Every checkpoint emits exactly one of `advance`, `revise`,
`experiment`, `user-decision-required`, or `stop`, bound to the exact
candidate, evidence, and governing requirement identities it covers.

`00-record` establishes the program record without choosing a stack or
promise. `01-evidence` resolves only independently schedulable empirical
questions. `02-checkpoint` fixes the disposition and, when lawful,
materializes or preserves the pack-separated successor plan; later work
continues through the successor lifecycle rather than being folded into
this run.

Instantiate with `brief` and `workspace`. Completion is the terminal
checkpoint result: the current record and evidence identities, exact product
disposition, open question or successor identities, and invalidation or
revalidation boundary are all observable without any historical input.
