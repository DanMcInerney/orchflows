# Bounded acquisition

[acquire.py](../scripts/acquire.py) runs discovery, pauses for the worker's semantic choices, then acquires selected depth. The [offline fixture](../scripts/acquire_fixture.py) is an executable example. Resolve `<method>` to the loaded skill directory and `<interpreter>` to the caller's Python 3.9+ interpreter, normally the orchflows home runtime. Resolve plan, selection and output arguments to absolute task paths. The acquisition backend is standard-library only.

## Plan and run

Write a plan in the task workspace, with output outside the package:

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

Replace the example dates and sources with the resolved request. `window: null` means explicitly chosen all-time. The window propagates to discovery and depth; put its dates here, not in query operators. Freeze `as_of` as an observation ceiling at or after the permitted reads, tied to the assignment's finite deadline; stop reads when it expires. It is distinct from publication/event dates, completed observation times and any forecast horizon.

The validator requires worst-case steps/records to fit plan limits. Discovery has at most five pages per step; `max_targets` bounds depth choices and `max_items` bounds each result. Request reservations are charged before I/O and shared across stages/resumes, including guest activation; internal redirect hops are not separate attempts. `max_seconds` bounds active work and new read/pacing admission, while an in-flight read retains its transport timeout. These are ceilings, not completeness or wall-time guarantees.

Allocate caller budgets across plans: enforcement is per plan. One plan shares paced/cache state and serializes each origin; serialize separate plans sharing an origin. Only explicitly permitted adapters may run; supply no credentials. An origin that refuses (`auth_required`, `attestation_required`, `rate_limited`) refuses every later read in the plan with that same code, before any budget is spent; refusals and reserved pacing state survive resume; there is no retry and no substitute stage.

## Select and deepen

At `selection_required`, read step outcomes/losses and the complete capped batch in `candidates.json`. Choose exact record/depth IDs from retained text and context, with reasons grounded in relevance, credibility, disagreement and likely value. Engagement or a generic daily title is insufficient. Inspect hydrated text before final inclusion; selection is provisional, and omissions/caps remain visible.

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

Preserve the output directory together:

- `packet.json`: evidence records, edges, groups, per-step outcomes and losses.
- `summary.json`: packet SHA-256, counts, timings, limits, advisories and gaps.
- `candidates.json`, `selection.json`: selection evidence and reasons.
- `checkpoint.json` and steps directory: identities, reservations, immutable results and work ledgers needed for resume.

When `timing_complete` is false, active time is only a lower bound; the assignment deadline still applies. Exit 0 means a valid checkpoint: inspect `phase`, because selection or source gaps may remain. Exit 2 refuses invalid input, identity, corruption or lock state; exit 3 means an incomplete packet with uncertain reads or an observation-ceiling violation. Return partial evidence and gaps accurately.

For an offline backend check, run `<interpreter> <method>/scripts/acquire_fixture.py --output <scratch>/admission`. It checks adapter parsing, selected-depth linkage and completed resume with no added attempts and identical packet bytes; it does not test live access or model decisions.
