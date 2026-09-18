# Independent dogfood audit

Audited the completed `dynamic-small`, `dynamic-medium`, `dynamic-large`, and `software-factory` native runs under `C:/Users/danhm/orchflows-dogfood-20260917`. This assessment used installed instructions, actual task inputs and outputs, native session traces and fresh checks. The root's `audit.json` and native final summaries were not accepted as proof. Original trial files were not changed.

The four runs demonstrate flat dispatch and distinct reviewers. Three delivered the requested local outcomes in the checks performed. The larger dynamic run delivered a useful tool but failed an additional malformed-timestamp case. These runs do not establish perfect output correctness or adaptive parallel maker staffing.

## Observed execution

| Trial | Actual structure | Outcome |
| --- | --- | --- |
| Dynamic small | Root → one notice maker → one separate reviewer | Notice contains every supplied operational fact, is 52 whitespace-separated words including its heading, and adds no promise. No repair. |
| Dynamic medium | Root does analysis and writing → one separate reviewer | Independently recomputed all six vendor/scenario totals: Aster $2,096/$5,416; Birch $2,040/$2,560; Cedar $2,650/$7,720. Recommendation preserves eligibility and provisional-price qualifications. No repair. |
| Dynamic large | Root → one maker → one separate reviewer → root repairs UTF-8 handling and reruns checks | A real review found a defect and caused one repair. A separate timestamp-validation defect remains, below. |
| Software Factory | Root → one builder → one correctness reviewer → checked handoff | One of two allowed candidate passes. Correctness was the only applicable lens, with explicit reasons for omitting others. No release was attempted. |

All seven native children have depth 1 and the trial root as their parent. Child-own calls contain no agent spawning, sibling task assignment or agent CLI launch. Child messages found in the larger dynamic and Factory runs target `/root`. Reviewers are distinct from makers and do not repair candidate source. No second review was added to the dynamic repair cycle. Factory correctly retains its own pass/lens contract rather than silently substituting the generic pattern.

The installed core architecture file has SHA-256 `2e57b6c49813a37212438975bc1c08cce5cec934b08626f2d1adaf6b871aef2a`, matching the checkout file inspected during this audit. I also read installed dynamic/work/review instructions and Factory's installed workflow/run contract.

## Finding: generated ticket tool accepts invalid offset minutes

**Candidate output defect; moderate impact.** In `C:/Users/danhm/orchflows-dogfood-20260917/dynamic-large/workspace/ticket_report.py`, `TIMESTAMP_RE` accepts any two offset-minute digits. `datetime.fromisoformat` then normalizes `+00:99`, so a malformed timestamp is accepted and existing reports are overwritten. The request expressly requires rejecting malformed timestamps and preserving output files for invalid input.

Fresh CLI reproduction produced exit **0**, empty stderr, and replaced both sentinel files. The same failure occurs when `+00:99` is supplied through `--as-of`. This does not show a flaw in flat orchestration; it shows a generated validation error missed by the trial's checks and review. The original reviewer explicitly listed malformed offset timestamps among coverage gaps.

Reproduce without changing the original workspace:

```python
from pathlib import Path
import subprocess, sys, tempfile

script = Path("C:/Users/danhm/orchflows-dogfood-20260917/dynamic-large/workspace/ticket_report.py")
with tempfile.TemporaryDirectory(prefix="ticket-audit-") as scratch:
    root = Path(scratch)
    source, output = root / "input.csv", root / "out"
    output.mkdir()
    source.write_text(
        "id,priority,status,created_at,resolved_at,due_at\n"
        "x,low,open,2026-09-01T00:00:00+00:00,,2026-09-02T00:00:00+00:99\n",
        encoding="utf-8",
    )
    for name in ("summary.json", "report.md"):
        (output / name).write_text("sentinel", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), str(source), "--out", str(output),
         "--as-of", "2026-09-03T00:00:00Z"],
        capture_output=True, text=True,
    )
    print(result.returncode, repr(result.stderr))  # observed: 0, ''
    print(all((output / name).read_text() == "sentinel"
              for name in ("summary.json", "report.md")))  # observed: False
```

The native final says “No known unresolved issues” and omits the reviewer's explicit coverage gaps. It correctly says the review occurred and the encoding finding was repaired; it does not claim that the revised candidate received another passing review. Still, its handoff conveys less uncertainty than its evidence supports. This is a reporting weakness in that execution, not evidence that another review stage should be added to the architecture.

## Review timing and evidence limits

For dynamic-large, an intermediate reviewer message reached the root at `00:09:32 UTC`; the root announced repair at `00:09:37`. The reviewer completed its final answer locally at `00:09:39`. The root called the patch tool at `00:09:46.844`, and its transcript received the reviewer's final at `00:09:46.955`. Actual editing therefore followed reviewer completion, and no concurrent candidate editing is demonstrated. However, the repair decision began before the full final report was visibly gathered. The earlier message payload is encrypted, so this evidence cannot establish whether that message already contained a complete assessment. Do not label this a proven premature-repair violation or a clean proof of the gather boundary.

Exact native trace locations:

- Dynamic root: `C:/Users/danhm/orchflows-dogfood-20260917/dynamic-large/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-06-04-01a0b1d5-a8a8-70f3-97bb-6c2e75cec8de.jsonl`, lines 67–78.
- Dynamic reviewer: `C:/Users/danhm/orchflows-dogfood-20260917/dynamic-large/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-08-46-01a0b1d8-21d2-7473-aecd-460a578f3486.jsonl`, lines 47–55.

Forked histories are present in child logs, including replayed parent commentary and patch events stamped near the fork. I used the child metadata/assignment boundary and actual child tool calls rather than counting those replayed events as child actions. Assignment bodies are encrypted, which limits direct prompt-scope inspection.

## Additional independent checks

Factory's saved patch applied cleanly to files read from its recorded Git baseline in a fresh temporary directory. The reconstructed files match the delivered source after normalizing line endings, all five reconstructed unit tests pass, and a separate 14-case matrix passes, including very large hours, boundary values, negative values, booleans and non-integers. Patch SHA-256 is `395cdbb0829cbbad82e770ab1e170db405bf82ba8d16d54f8718fd14cfdbd0f8`; preserved caller-note SHA-256 is `20c1ee75d44cfafedf6d23b1fd95071755e2c552eca32ec9d3bc7886576e8341`, matching recorded evidence. The checkpoint accurately says human review/release handoff, with no project opt-in for automatic release.

Factory initially reported that its explicit skill was absent from the native catalog, discovered it in the isolated installed home, and read the exact workflow before dispatching implementation. Its eventual process followed Factory, but this run does not prove smooth native catalog invocation. That is a host/discovery observation, not a demonstrated workflow-process defect.

These trials chose zero or one maker each; none tests concurrent maker fan-out or integration of several independently made artifacts. Unspecified model/effort choices also mean they do not validate scoped overrides. No external release, remote CI, continuation, exhausted-pass path or multi-lens Factory review was exercised. Preserve these limits rather than converting the four successful process exits into an unconditional “all workflows pass.”

## Follow-up: export phase ordering

The parent requested an additional read-only inspection of the still-running `export-workflow` trial. Its first standalone trial was in progress at inspection, so this section does not judge eventual artifact quality or claim completion.

**Supported process failure.** The installed `C:/Users/danhm/orchflows-dogfood-20260917/export-workflow/orchflows-home/libraries/export-workflow/skills/export-workflow/SKILL.md` first requires a bounded fresh top-level representative trial, then standard review and repair of the export against the source, guidance **and trial evidence**, then at most one affected trial repeat. The actual order was:

1. Export draft produced at `00:13:43 UTC`.
2. Export reviewer launched at `00:13:48`, before any representative trial.
3. Root announced repair at `00:14:51` and applied the first repair at `00:15:04`.
4. Reviewer final completed at `00:15:14`, explicitly identifying the absence of trial evidence and the sibling export report as a high-priority finding.
5. Root applied another change within that repair pass at `00:15:19`.
6. The first fresh top-level trial launched at `00:15:45`.

Thus the mandatory export review lacked trial evidence. Later running a trial cannot retroactively make that review assess its results. Unlike the dynamic-large timing ambiguity, the first export repair also indisputably changed the candidate before the reviewer finished. Intermediate messages at `00:14:46` and `00:15:03` did not end the review; its later final included additional findings.

Evidence:

- Root trace: `C:/Users/danhm/orchflows-dogfood-20260917/export-workflow/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-12-47-01a0b1db-cec0-7570-ac9b-95f74d03ec6e.jsonl`, lines 40, 47, 70–96.
- Reviewer trace: `C:/Users/danhm/orchflows-dogfood-20260917/export-workflow/codex-home/sessions/2026/09/17/rollout-2026-09-17T20-13-48-01a0b1dc-bd10-7a80-890d-42e5fa0d9271.jsonl`, lines 54–68.

This is execution noncompliance with the current process, not a need for an additional architecture layer or review. The existing standard pattern already says to wait for review before repairs. A minimal source clarification, if desired, is to change “Apply core's standard review and repair…” to “After the trial finishes, apply core's standard review and repair…”. That makes the evidence dependency explicit while keeping the existing stages and bounds. Do not duplicate the core gather/repair rules across the export library or add another review to compensate for this misordered run.
