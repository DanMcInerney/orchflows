---
name: toy-digest-traced
description: Turn raw notes into a deduplicated digest and a trace table resolving every digest line back to a source note.
entry: routed
---

Require: the raw note set, the digest line budget, and the trace row format.

Steps:
- collect — `orch-investigate` — produces `notes.jsonl`: one record per raw note, each with a record id and its source path.
- reduce — `orch-synthesize` — produces `digest.md`: one line per distinct claim, each naming the record ids it rests on.
- trace — `orch-verify` — produces `trace.md`: one row per digest line, resolving its record ids back to source paths.

Edges: seq collect → reduce — carries `notes.jsonl`; seq reduce → trace — carries `digest.md`.

Invariants — Never:
- collect — emit a record for a note absent from the raw set.
- reduce — write a digest line no `notes.jsonl` record supports, or exceed the declared line budget.
- trace — mark a digest line resolved when its record ids resolve to no source path.

Done check: `trace.md` resolves every line of `digest.md` to at least one source path, and the digest line count is within the declared budget.

Return: status, result — `digest.md` and `trace.md`; then the budget spend and any line left unresolved.
