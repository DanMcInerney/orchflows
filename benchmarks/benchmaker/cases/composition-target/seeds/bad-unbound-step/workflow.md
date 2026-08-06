---
name: toy-digest
description: Turn a folder of raw notes into one deduplicated digest, rendered for circulation, inside a declared line budget.
entry: named
---

Require: the raw note set and the digest line budget.

Steps:
- collect — `orch-investigate` — produces `notes.jsonl`: one record per raw note, each with a record id and its source path.
- reduce — `orch-synthesize` — produces `digest.md`: one line per distinct claim, each naming the record ids it rests on.
- publish — `orch-deliver` — produces `digest.pdf`: the digest rendered for circulation to the note owners.

Edges: seq collect → reduce — carries `notes.jsonl`; seq reduce → publish — carries `digest.md`.

Invariants — Never:
- collect — emit a record for a note absent from the raw set, or drop a note without recording it as unreadable.
- reduce — write a digest line no `notes.jsonl` record supports, or exceed the declared line budget.

Done check: `digest.pdf` carries every line of `digest.md` and its line count is within the declared budget.

Return: status, result — `digest.pdf` with the record ids each line names; then the budget spend and the circulation list.
