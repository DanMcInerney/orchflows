# Evolve implementation and verification

The new example library lives in `example-workflows/evolve/` and exposes `evolve:evolve`. It adds one composing skill, evaluation and state contracts, portable package context, research notes, three host/root manifests, and reusable trial briefs. It adds no execution runtime, scheduler, database or core primitive.

## Original material inspected

The author read `C:/Users/danhm/tools/orchflows/skills/workflows/orch-evolve/SKILL.md` and `compositions/evolve.md` (last affecting commit `93f0248`, July 18, 2026), the earlier skill and judging/journal references in `C:/Users/danhm/tools/orchflows-launch-video-codex/`, and the later `C:/Users/danhm/tools/orchflows-public/example-workflows/references/evolve-generation.md` (last affecting commit `dbfa899e`, August 31, 2026).

The implementation was written afresh for orchflows-light's two native delegation primitives. It retains comparison against a stable evaluator and preservation of verified results. It replaces the old required goal threshold, fixed panels and plateau termination with inferred evaluation, inexpensive challenger comparisons, and resumable continuation. Working-harness revisions may be admitted after downstream trials; the coordinating promotion rules stay outside candidate authority.

The [research report](evolve-research-2026-09-13.md) documents the requested four systems, latest available revisions, newer related work and limitations. The package carries its own shorter source notes, so installation does not depend on this report.

## Package and core checks

- `python -B -m unittest discover -s tests`: 65 tests run; 64 passed and the Windows-inapplicable POSIX permission test skipped.
- An actual `setup --example evolve --skip-host-config` into a fresh disposable home installed all 15 package files byte-for-byte. The installed CLI resolved `evolve`/`evolve`; `doctor` returned `ready`. A repeat setup preserved an added user file and reported the library preserved. No real home or host settings were changed.
- Root, Codex and Claude manifests match. All package-local Markdown links resolve without leaving the library.
- Initial core verification caught a new README link into examples, which are omitted from the shipped core. The README now names the library without creating a broken shipped link; the complete core suite then passed.

Installation evidence: `C:/Users/danhm/AppData/Local/Temp/evolve-install-ww_ad7hf/`. After the trial-driven evaluator edits, a fresh install again passed; exact source hashes and the result are in `C:/Users/danhm/AppData/Local/Temp/evolve-final-install-vtx8rvh3/verification.json`. The package was not registered or installed into the user's active host; availability by native name is not claimed.

## Behavioral trials and revisions

The workflow-building skill requires actual bounded use before final independent review. Separate native trial supervisors prepare unrelated disposable projects; their fresh coordinators receive ordinary requests and declared dependencies. Each report distinguishes preparation from workflow behavior:

- [Runnable artifact](evolve-trial-code-2026-09-13.md): duplicate finder, no supplied metric or evaluator, two rounds. The workflow authored and calibrated an evaluator, confirmed a 9.598x geometric-mean speedup across six generated workloads and rejected the second candidate. The same independent reviewer completed the corrected measurement audit. Four workflow agents plus one reviewer follow-up were used; all 12 final project tests passed.
- [Visual artifact](evolve-trial-visual-2026-09-13.md): community event poster, no supplied quality criteria or judge prompt. One maker and two task-only judges produced a confirmed ordinal preference with all event facts preserved. Both actual renders were also inspected by the workflow author. A fresh coordinator then resumed on a continuous request, removed the former cap and dispatched another experiment. A simulated user stop interrupted the additional maker and left a stopped checkpoint, no in-flight work and the verified incumbent unchanged.
- [Harness and continuation](evolve-trial-harness-2026-09-13.md): synthetic interrupted writing campaign. A fresh coordinator reconciled a saved decision once, proposed a one-sentence harness change and generated six real outputs under matched work allowances. Two anonymous judges disagreed on a fresh case, so h1 was retained and explicitly passed to the next maker. That ordinary challenger received one preference and one tie, so the original notice stayed best. The completed checkpoint retains a0/h1/v1, has no in-flight work and counts two actual resumed rounds separately from the synthetic fixture round. The two resumed rounds used 12 native children.

During trial preparation, the evaluator contract was clarified to require task-only judge contexts and neutral artifact paths: fresh children alone do not hide an inherited transcript. Reserved examples must stay out of proposer development context; a shared filesystem does not establish secrecy. Trial supervisors were notified, and their reports record whether the new contract was read before evaluation.

The code trial's first reviewer qualified its audit because the handoff omitted the generated timing harness. The metric-review contract now explicitly includes scoring code, workload inputs, commands/environment and raw samples. The same independent trial reviewer was asked to finish that audit, and later review handoffs use the corrected contract. This is a trial-driven revision, not a claim the initial handoff was complete.

The second code candidate failed screening but received an unnecessary timing confirmation while the coordinator interpreted author verification advice too broadly. The author clarified that the advice was conditional; no second reviewer was dispatched. The package now explicitly stops confirmation and judging once screening disqualifies a candidate. The trial records the already-spent timing work instead of presenting it as efficient execution from the outset.

Native agent status inspection confirmed no trial work remained running. One fresh independent reviewer found no substantive issues after checking the package, primary research claims, scoring source/audit, actual poster renders, resume/stop evidence and final harness judgments/checkpoint. It requested only closing this report's pending status text; that closure is complete. No implementation repair or additional review was needed.

Accepted-new-harness propagation and rollback, unknown-child recovery, wide tournaments and long-duration operation remain unexercised. No RSI Level 1, indefinite-gain or general multimodal-performance claim is made.
