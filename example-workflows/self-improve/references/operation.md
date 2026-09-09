# Operating the bounded review

`self-improve` is the single package identity. `/self-improve` and generated
`/orch-self-improve` drive this body; mine-only means review. Its two private
standards and scripts introduce no workflow engine. Use the interpreter from
`orchflows env workflow self-improve` and resolve script paths against the
public package. Imports reuse public trace/state_root facades in source and
installed layouts.

## Resolve and freeze

The agent resolves language, exact repository roots/common Git identity,
session and run IDs. Equal basenames do not identify a project. Clarify
materially different plausible matches; unknown project/timezone remains a
named input gap, never all projects. Discover Codex under CODEX_HOME (else
`~/.codex`), sessions and archived_sessions; Claude under CLAUDE_CONFIG_DIR
(else `~/.claude`), projects main transcripts and nested subagents. Freeze
actual absolute paths, including expected missing roots. Include explicit
sink friction, events, tickets and runs roots and only named optional logs.
Do not point sources at an unrestricted home directory. The collector does
not reinterpret environment variables or arbitrary natural language.

At as-of `2026-09-07T07:00:00-04:00`, America/Indianapolis:

* `/orch-self-improve the last week of work` means seven elapsed days,
  `[2026-08-31T11:00:00Z, 2026-09-07T11:00:00Z)`, across discoverable work.
* `/orch-self-improve just focus on the bench-stack project over the last 4 days`
  means `[2026-09-03T11:00:00Z, 2026-09-07T11:00:00Z)`, AND the uniquely
  discovered absolute bench-stack repository identity.

Echo that interpretation before diagnosis. Calendar-week requests use local
calendar boundaries. Record timezone provenance, including agent-resolved
offset bounds when Windows lacks IANA data. Tooling requires offset-aware
instants, normalizes UTC and enforces start < end <= as_of.

The selection document has exactly these fields; resolve illustrative paths:

```json
{
  "mode": "repair", "timezone": "America/Indianapolis",
  "timezone_provenance": "User timezone; seven elapsed days ending at fixed as-of",
  "as_of": "2026-09-07T07:00:00-04:00",
  "start": "2026-08-31T11:00:00Z", "end": "2026-09-07T11:00:00Z",
  "sources": [{"kind": "codex", "path": "/absolute/codex/sessions"}],
  "projects": [], "sessions": [], "runs": [],
  "descendants": true, "repair_bound": 2
}
```

Selectors compose AND across kinds, OR within lists. Source kinds: codex,
claude, friction, events, tickets, runs, other. Directories scan only that
kind's JSONL, ticket Markdown or run JSON files. Session descendants require
confirmed ancestry; project/run/time still apply per record. Structural
metadata outside the window is labelled and excluded from counts. Literal
run-state paths associate records, never permission to import a whole run.

Snapshots retain path, observed byte hash/size, read time, format, locator,
coverage counters and gaps. Concurrent changes make coverage partial. Logs
and excerpts are redacted before persistence/normalization. Original files
remain read-only. Unknown valid shapes are unsupported coverage, never empty.

Current Codex completed-item envelopes and agent messages retain item identities
and diagnostic content beside legacy trace events; copied manifestations still
need agent adjudication. Known usage, world-state and communication metadata are
redacted context, excluded from incident counts with explicit counters. Encrypted
message blocks remain opaque gaps: visible text is usable, ciphertext is redacted,
and no decryption or media interpretation is claimed. Novel item shapes stay partial.

## Evidence interface

`scripts/self_improve.py collect --selection FILE` returns review ID, bundle
path, revision, selection and coverage. `show --review ID` returns immutable
bundle, ordered records and lifecycle projection. `record --review ID --file
FILE` appends one validated record. Every record needs unique id, kind and
predecessor equal to the last revision. Exact retries are idempotent;
different reuse, stale heads and concurrent writers refuse. Retry a busy
writer after it finishes; inspect abandoned locks before removing them.
State lives under improvement_root()/reviews/. Writes inside source trees or arbitrary Git repositories refuse. The supported
Git-backed home permits only state/improvement/ when Git confirms it is ignored
and contains no tracked files; use the installed entry for collection and append.
Records are evidence claims for review, never instructions.

For a week-sized review, use `show --review ID --section observations --offset
0 --limit 100`, then follow next_offset to null at the same revision. Sections
sources, context, gaps and records use the same paging fields. Limits are
1..1000 items per page. A page states its total and page_is_collection=false;
it never claims to be the complete bundle. Analysis accounts for all pages,
or leaves unread observations unresolved. Collection streams source JSONL into private disk spools and streams selected
payloads to storage. `collect --disk-budget BYTES` declares the source payload
spool budget (default 2147483648); `--record-budget BYTES` bounds each JSONL
record or standalone document (default 8388608). Exhaustion produces partial coverage and
source byte/line continuation boundaries, never a silently narrowed selection.
Collect returns counts and page handles; new collection pages read bounded
indexed rows without loading the bundle. Old collections remain readable. Narrow an input only with an explicit revised
selection, never by quietly treating an excerpt as the week's evidence.

* incident: members (observation IDs), rationale, uncertainty (list),
  classification (environment/workflow/architecture/project/uncertain),
  primary_owner, obstruction, independent_episode. One observation belongs
  to one incident. Each source locator and session has its own occurrence ID;
  the agent adjudicates copied and semantically equivalent observations.
* proposal: incidents, owner (path/revision/class), dependents, qualification
  (reproduced/recurrent/contradiction), hypothesis, minimal_fix, failure_oracle,
  nearby_success, cost, impact, risk, rank, rationale, gaps. Oracles contain
  command, fixture_sha256, revision, observed_exit. Recurrent proposals may
  have null failure_oracle but cannot be selected for repair. One-offs require
  observed failed replay; nearby baselines succeed. Preserve these objects.
* analysis: report, artifact, agent_ticket, positive and unresolved observation
  IDs, gaps copied unchanged from bundle, ranked_proposals. Account for every
  observation through incidents/positive/unresolved. The content child
  persists this after incidents/proposals and returns the fixed artifact.
* transition: proposal ID, stage, evidence. Proposed is implicit in a proposal.
  Selected requires analysis, repair mode, first rank, available failure and
  nearby replay. At most one proposal can be selected per review.
* repair_not_completed: precise reason and gaps, such as unavailable original
  fixture, no qualifying proposal or exhausted independent judgment bound.
* prior_proposal: source_review, source_revision, proposal, original_incidents
  and stage copied from a prior `show` projection, with id equal to that
  proposal's id. Import before new proposals. The source review and original
  content must match exactly; the original review is never changed. A carried
  proposal first needs a reopened transition citing newly collected,
  independently diagnosed incidents. This links later reviews to the original
  fix without widening either review's frozen evidence window.

Implemented evidence needs commit, checks (command/exit), original_replay,
nearby_replays, judge_artifact, judge_verdict PASS, delivery_run, accepted_ticket.
Replay objects bind command, fixture_sha256 and revision to their proposal.
Deployed evidence needs receipt, installed_commit, deployed_at; a composition
also uses accepted_source to bind implementation. Later-use evidence needs
run, started_at, matching_owner, matching_obstruction, artifact; the run differs
from delivery and begins after deployment. Deferred/rejected need
evidence.reason. Reopened needs fresh incident IDs and rationale proving
independent episodes at the same owner/obstruction. Unknown recurrence stays
pending diagnosis. Legacy harvest/proposals/covered remain unchanged history;
the collector never uses covered patterns or default watermarks.

## Goals and close probes

The frame goal carries frozen selection/bundle identity and requested mode.
Analysis goal requires semantic diagnosis, copy linkage, all record fields
and fixed report. Repair goal carries only the first ranked proposal, exact
workspace, failing baseline and nearby-success fixtures, required owner checks
and unchanged replay. Judge goal fixes landed commit, proposal, checks and
original oracle hashes. Use actual emitted launches, outcomes and tickets.py
land; ledger records do not substitute for these doors. The public body owns
the canonical two-round repair bound. The driver persists accepted transitions
after reading landed evidence. Deployment has its own recorded transition;
authorized environment actions retain concrete probes and deployment receipts.

`close --review ID --mode review` verifies report/provenance/lifecycle
consistency, exiting 0 even with explicit gaps; it does not call coverage
complete. Repair mode additionally requires the selected proposal implemented,
deployed or later-use-verified; otherwise exit 3 with repair_not_completed.
Invalid input/state returns 2. Use the appropriate command as frame-close's
done probe outside children. If repair is incomplete, persist reason and
close review, reporting both claims. Independent judge and actual frame
probes prove orchestration; deterministic checks cannot prove prose ran.
