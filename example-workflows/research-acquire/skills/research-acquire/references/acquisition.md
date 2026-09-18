# Bounded acquisition

[acquire.py](../scripts/acquire.py) discovers, pauses for semantic selection, then reads selected depth. Use the [offline fixture](../scripts/acquire_fixture.py) as an executable example. Resolve `<method>` to this skill, `<interpreter>` to the caller's Python 3.9+, and plan/selection/output arguments to absolute task paths. The backend uses only standard library.

## Plan and run

Write plan and outputs in the task workspace, outside this package:

```json
{
  "version": 1,
  "plan_id": "source-question-1",
  "question": "The bounded source question",
  "as_of": "2026-09-10T23:59:59Z",
  "window": {"start": "2026-09-08T00:00:00Z", "end": "2026-09-10T00:00:00Z"},
  "allowed_adapters": ["reddit_archive", "reddit_shreddit"],
  "limits": {"max_steps": 3, "max_requests": 5, "max_records": 30, "max_seconds": 120},
  "discovery": [
    {"step_id": "community", "adapter_id": "reddit_archive", "query": "search:subreddit=python", "max_items": 10}
  ],
  "depth": [
    {"depth_id": "comments", "adapter_id": "reddit_shreddit", "operation": "comments", "from_steps": ["community"], "max_items": 10, "max_targets": 2}
  ]
}
```

```text
<interpreter> <method>/scripts/acquire.py --plan <output>/plan.json --output <output>/evidence
```

Replace example dates/sources from the request. `window: null` explicitly chooses all-time. Put bounds here, not in query operators. Discovery and discussion depth inherit the window; selected `open_page` depth does not, so an older original date remains available to correct discovery metadata. Freeze `as_of` as the finite observation deadline and stop reads when it expires. Keep it distinct from publication, event, revision and completed observation times.

Worst-case steps/records must fit plan limits. Discovery has at most five pages per step; `max_targets` bounds depth choices and `max_items` bounds each result. Request reservations are charged before I/O and shared across stages/resumes; redirect hops are not separate attempts. `max_seconds` bounds active work and new read/pacing admission; an in-flight read retains its transport timeout. These are ceilings, not completeness or wall-time guarantees.

Allocate caller budgets across separately enforced plans. One plan shares paced/cache state and serializes each origin; serialize separate plans sharing an origin. Only explicitly permitted adapters may run; supply no credentials. An origin that refuses (`auth_required`, `attestation_required`, `rate_limited`) refuses every later read in the plan with that same code, before any budget is spent; refusals and reserved pacing state survive resume; there is no retry and no substitute stage.

## Select and deepen

At `selection_required`, inspect outcomes/losses and capped `candidates.json`. Choose exact record/depth IDs from retained text/context, explaining relevance and evidential value. `date_eligibility` and `date_qualification` distinguish reported feed/archive dates from verified original publication; `reported_in_window` alone does not establish freshness. Inspect selected depth before final inclusion. Do not infer quality from counts or hide omissions/caps.

```json
{
  "candidate_id": "sha256:<from candidates.json>",
  "choices": [
    {"record_id": "<exact record_id>", "depth_id": "comments", "reason": "Why this source's actual context merits reading its comments"}
  ],
  "omission_reason": "Why the unselected candidates do not warrant more authorized reads"
}
```

Use `choices: []` when no depth read is justified. Choices validate before reads and then freeze; unknown or unaddressable IDs, repeated targets, changed choices and exceeded caps refuse.

```text
<interpreter> <method>/scripts/acquire.py --plan <output>/plan.json --output <output>/evidence --selection <output>/choices.json
```

## Resume and hand off

Reissue the unchanged plan/output command after interruption; bound choices may be omitted. Completed steps, including empty/refused results, make no more requests. Changed plan/package identity, corrupt/missing checkpoints or completed receipts refuse reuse. A started step without a durable result is uncertain and is not replayed; preserve its reserved budget and gap while independent work may finish. The process lock prevents concurrent invocation. New scope requires a separate plan within the caller's authorization and remaining bounds.

Retain the directory together:

- `packet.json`: evidence records, edges, groups, per-step outcomes and losses.
- `summary.json`: packet SHA-256, counts, timings, limits, advisories and gaps.
- `candidates.json`, `selection.json`: selection evidence and reasons.
- `checkpoint.json` and steps directory: identities, reservations, immutable results and work ledgers needed for resume.

When `timing_complete` is false, active time is only a lower bound; the assignment deadline still applies. Exit 0 means a valid checkpoint: inspect `phase`, because selection or source gaps may remain. Exit 2 refuses invalid input, identity, corruption or lock state; exit 3 means an incomplete packet with uncertain reads or an observation-ceiling violation. Return partial evidence with its gaps.

Offline check: `<interpreter> <method>/scripts/acquire_fixture.py --output <scratch>/admission`. It tests parsing, depth linkage and completed resume without added attempts or changed packet bytes; live access/model decisions remain untested.
