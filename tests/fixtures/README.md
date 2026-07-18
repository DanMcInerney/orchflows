# trace.py fixture corpus

Every fixture under `claude/` and `codex/` is derived by **redaction**
from one real session on this host, not hand-invented: key names,
nesting, and event framing are copied verbatim from the source; every
value (ids, timestamps, paths, prompt/response text, model names) is
replaced with a synthetic placeholder. Sources are named by session id
and date only -- no path or real content is committed.

| fixture | source session id | source date | host schema mirrored |
|---|---|---|---|
| `claude/clean/` | `a8992f68-2b4f-47e5-92d1-f1a7e76748d5` | 2026-07-14 | Claude Code CLI 2.1.209 |
| `claude/malformed/` | (hand-drifted from the same schema, to exercise criterion 3) | 2026-07-14 | Claude Code CLI 2.1.209 |
| `codex/clean/` | `019f6c77-a5d5-7812-a8d0-1569e4354553` (+ parent `019f6c55-9459-72f0-af1c-c56e0cc6b5ed`) | 2026-07-16 | Codex Desktop 0.144.5, multi-agent v2 |
| `codex/malformed/` | (hand-drifted from the same schema, to exercise criterion 3) | 2026-07-16 | Codex Desktop 0.144.5 |

## Procedure

1. Open the real transcript read-only; never copy it into the repo.
2. For each JSONL line to carry into the fixture, keep every key name
   and the nesting depth of every object/array exactly as observed.
3. Replace every value: strings become short `REDACTED ...` /
   `redacted-...` placeholders (still non-empty, so shape checks that
   depend on truthiness still exercise the real code path); ids become
   synthetic sequential tokens (`u-0001`, `toolu-0001`, ...); timestamps
   become a synthetic strictly-increasing `2026-01-01T00:00:0N.000Z`
   sequence so ordering-by-timestamp is still exercised without
   revealing when the source session ran.
4. Drop nothing that changes the record's *shape* (e.g. an absent
   `is_error` key on a successful `tool_result` is preserved as absent,
   not added) so the extractor's real branch logic is exercised, not a
   simplified stand-in for it.
5. `claude/clean/subagents/agent-worker-a.meta.json` is carried for
   directory-layout fidelity (a real subagent transcript always has a
   sibling `.meta.json`); `scripts/trace.py` currently derives model
   attribution from each message's own `model` field instead, which is
   more precise per-message than the session-level meta, so this file
   is not read by the extractor today.
6. `claude/malformed/` and `codex/malformed/` are not redacted from one
   single real session -- they mirror the same real key/nesting shapes
   above but each deliberately introduces one instance of: invalid JSON
   on a line, a recognized record type with a required key removed
   (drift), and one *unrecognized-but-valid* record type (to prove
   schema drift that merely adds new record kinds is not treated as an
   error -- see `scripts/trace.py` module docstring).

The live-session, zero-`parse_errors` authoring check required before
these fixtures were frozen was performed against a live session before
they were committed.
