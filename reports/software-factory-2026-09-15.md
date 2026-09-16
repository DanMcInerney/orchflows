# Software factory implementation and validation

The example library lives in `example-workflows/software-factory/`. It exposes delivery, production observation and incident investigation through three manual-only workflows. It adds guidance, shared context/evidence contracts, host manifests and portable trial briefs; no core runtime or external service adapter changes.

## Source and adaptation

The author inspected the user's diagram and the publicly accessible sections of [Inside OpenAI's agentic software factory](https://newsletter.pragmaticengineer.com/p/openai-software-factory), September 15, 2026. The web reader could not open the URL, but a normal HTTP request returned the public article through its factory section. No subscriber-only continuation was used.

The source supplies the build/check/review feedback cycle, risk routing, observed rollout and production feedback paths. The example adds finite candidate passes, exact candidate evidence, operation reconciliation and explicit host/project dependencies to make those ideas portable. Existing project policies and the caller's request determine authority; article content does not grant permission to deploy or mitigate an incident.

Delivery uses one builder per candidate pass, up to five applicable independent reviewers, and an optional release worker: at most `6P + 1` children, with P=3 by default. Observation and incident investigation each use one child. Follow-up implementation and recurring scheduling require a request; they are not hidden extra work.

## Package checks

- `python -B -m unittest discover -s tests`: 61 tests run, 60 passed and one skipped.
- Real `setup --example software-factory --skip-host-config` into a disposable home succeeded. `doctor` returned ready; `resolve software-factory --skill software-factory` returned the installed entrypoint.
- After the scheduling clarification, a second fresh home installed all 15 library files byte-for-byte; source hashes are retained in `final-package-hashes.json` under the scratch root.
- Root/Codex manifest identity and shared Claude metadata checked. All three skills have Claude `disable-model-invocation: true` and Codex `allow_implicit_invocation: false`, as required by repository architecture.
- All 16 package-local Markdown links resolved inside the library. `git diff --check` passed.
- The bundled skill validator rejects the Claude frontmatter field; the bundled plugin validator requires that field to be false. Those assumptions conflict with this repository's required manual-only policy. The actual validators were run and their failures retained as a compatibility limitation; direct YAML, manifest and portable-install checks verified the repository's intended policy instead. No validator or invocation policy was weakened.

Installation and trial scratch root: `C:/Users/danhm/AppData/Local/Temp/orchflows-factory-66d1c9ab86c94ec79fd4487942f4f7b1/`. The real home, host registration and user settings were not changed. Native discovery by name in the user's active host is not claimed.

## Trial preparation

The author prepared two unrelated disposable fixtures. The code fixture has a committed Python duration formatter, one existing unittest and an untracked caller note. Its ordinary request asks for nonnegative integer seconds formatted as HH:MM:SS, unlimited hours, rejection of negatives/non-integers/booleans, P=2 and a local-only release handoff.

The operations fixture has an offline JSON telemetry export with equal baseline/current traffic, release labels, duplicate latency alerts, elevated errors, a deployment timeline and an unavailable CPU signal. Its context describes possible contributing changes without establishing causality. The ordinary requests ask for a bounded observation and then incident explanation/mitigation proposals, without authorization to execute a mitigation.

Separate fresh trial coordinators received the candidate skills, declared absolute package roots and ordinary requests. Each was instructed to let the workflow supply orchestration and to confine side effects to its disposable workspace. No expected findings or repair strategy were passed. The author reminded both coordinators to keep the trials minimal; no desired findings or implementation fixes were supplied.

## Delivery trial

The workflow completed the local checked-change/handoff endpoint in one of the two allowed passes. It used one builder and one independent correctness reviewer, with isolated candidate and review worktrees. The builder produced commit `a2c942d286225606c1ff008f65c1be77906d0d48`; all six acceptance tests passed, and the reviewer independently ran those tests and checked reverse-patch applicability without finding an actionable issue.

The coordinator correctly returned ready for human review, with no automatic-review opt-in, integration or release. The original tracked source and untracked caller note matched their baseline hashes. One baseline test invocation left Python bytecode residue in the disposable original project; subsequent checks suppressed it and the residue was excluded from snapshots.

Evidence under the scratch root: `delivery-run/trial-result.md`, `checkpoint.md`, `builder-report.md`, `correctness-review.md`, `preservation-audit.json`, `candidate.patch` and `release-handoff.md`. This validates the successful local path with one applicable lens, not the repair loop or concurrent specialist reviews.

## Operations trial

Observation and incident investigation each used one fresh worker, sequentially, without nested work. Both consumed the offline fixture and preserved its source hashes. Observation measured p95 latency 100 to 260 ms and error rate 0.1% to 2.0%; it grouped the two overlapping latency alerts, retained the distinct error signal, and reported unavailable CPU telemetry as a gap. It produced one proposed performance brief with a fingerprint, comparison plan and explicitly proposed acceptance criteria.

Incident investigation reused the existing fingerprint and brief. It separated observed impact from the unproven cache/pool hypotheses and ranked recovery options with their conditions and checks. It did not execute a mitigation, create a repair task, contact an incident channel or claim recovery. Evidence is in `operations-run/observation.md`, `incident.md`, `checkpoint.md`, `instruction-identities.json` and `trial-result.md` under the scratch root.

After the one-off observation finished, the author clarified the unexercised recurring-scheduling paragraph: later invocations advance windows from saved coverage, preserve gaps/late overlap, and carry fingerprints forward. The trial coordinator retained original instruction hashes and recorded that this later wording was not exercised. The observed one-off path and incident workflow were unchanged.

## Limits and final review

These trials use four workflow children plus two trial coordinators. They establish local implementation/check/review/handoff and offline observation/investigation behavior only. No model or effort overrides were supplied.

Unexercised paths include failed checks, repair passes, conflicting/incomplete reviews, multiple concurrent specialists, bound exhaustion, interruption/resume, stale candidate evidence, automated low-risk review, human approval consumption, integration, hosted CI, publication, deployment, staged rollout, rollback, real telemetry, mitigation execution and recurring scheduling. No live deployment or persistent monitoring was performed, and no general reliability improvement is claimed.

One fresh independent reviewer inspected the package, core ownership/invocation contracts and actual trial records, without editing or delegating repairs. It found no substantive issues and confirmed that the validation claims match the inspected local evidence and disclose the untested paths. Its report is `final-review.md` under the scratch root. No repair pass or additional review was needed.
