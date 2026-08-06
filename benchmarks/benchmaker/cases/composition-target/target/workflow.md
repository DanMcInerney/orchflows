---
name: toy-digest
description: Turn a folder of raw notes into one deduplicated digest inside a declared line budget.
entry: named
---

Require: the raw note set and the digest line budget.

Steps:
- collect — `orch-investigate` — produces `notes.jsonl`: one record per raw note, each with a record id and its source path.
- reduce — `orch-synthesize` — produces `digest.md`: one line per distinct claim, each naming the record ids it rests on.

Edges: seq collect → reduce — carries `notes.jsonl`.

Invariants — Never:
- collect — emit a record for a note absent from the raw set, or drop a note without recording it as unreadable.
- reduce — write a digest line no `notes.jsonl` record supports, or exceed the declared line budget.

Done check: `digest.md` exists, every one of its lines names at least one record id present in `notes.jsonl`, and its line count is within the declared budget.

Return: status, result — `digest.md` with the record ids each line names; then the budget spend and any note recorded as unreadable.
