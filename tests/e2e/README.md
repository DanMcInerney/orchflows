# Fast end-to-end confidence tests

These maintainer tests target seams that ordinary parsing tests and earlier development trials did not establish. They do not add an Orchflows execution runtime or universal workflow checker.

## Offline regression tests

From the checkout:

```powershell
python -m unittest discover -s tests -p test_upgrade_e2e.py -v
```

The two tests in [test_upgrade_e2e.py](../test_upgrade_e2e.py) use real subprocesses, real installation and the actual main snapshot `16d2644ba25562d66af5648a7dfed8ebde1cfe90`. No setup function is mocked. They run without network access or a model, in disposable homes outside the checkout.

| Journey | Required result | Why it matters |
| --- | --- | --- |
| Main install → customize libraries → upgrade using the old installed command → use the new installed CLI | All five current names resolve to the current source bytes, including the rewritten dynamic workflow; removed names fail; customized libraries and host configuration survive; doctor succeeds; repeat setup changes no bytes. | A source-tree test can pass while an existing user's installation retains obsolete instructions or overwrites their work. |
| Main install → attempt upgrade from a wrong package → use the old CLI | Rejection changes no installed bytes; the old workflow still resolves and host settings are unchanged. | A failed update must leave a usable installation, rather than a partly migrated home. |

The archive is pinned rather than tracking a moving branch during tests. Git and that object must be available; source archives or shallow clones report a skip, not a pass. Fetch repository history before using this test as a release gate. The source export and test homes are automatically removed. Host registration is deliberately disabled; the test must not modify the user's real host setup.

Measured together on this Windows checkout: **5.84 seconds**. These tests also run in normal `unittest discover -s tests`.

## Opt-in native smoke tests

Use an authenticated Claude Code CLI. The runner uses the host's configured model and effort, consumes normal agent usage, and keeps existing user settings/plugins/hooks. It loads frozen package copies for this session only, disables MCP, supplies no authoring history or evaluator expectations, and makes no global plugin registration changes. The brief permits only local work. Tool allowlists reduce available capabilities; they are not a filesystem sandbox.

```powershell
python tests/e2e/run_native_smoke.py --output ../orchflows-smoke-evidence
python tests/e2e/check_native_smoke.py ../orchflows-smoke-evidence/routing ../orchflows-smoke-evidence/composition ../orchflows-smoke-evidence/missing-review
```

Supply `--claude /path/to/claude` if needed. The output directory must be new and outside the checkout. The three default cases run concurrently. Each has a **180-second deadline**, including startup; timeout terminates its local process tree and records failure. `--case composition` runs just that case. `--case explicit-dynamic` checks explicit activation, while `--case research-code --seconds 600` exercises research and coding stages with a larger bound. No model or effort override is introduced to make timings look better. These paid tests are excluded from ordinary unittest discovery. The routing case deliberately fails if the model skips dynamic selection; that known limitation is retained as a diagnostic, not relabeled a pass.

| Case | Ordinary input and capability | Required result |
| --- | --- | --- |
| Routing | An arithmetic file-writing request, with core loaded and native delegation available. | Correct file; five current core commands registered; dynamic selected; one independent reviewer. Native automatic selection may fail this diagnostic even when the output is correct. |
| Composition | Explicitly invoke a fixture plugin by name; it composes a second procedure and core review/revision. A correct invoice needs a required Python check and a separately styled public summary. | One root-owned fresh reviewer; completed judgment; no candidate change or gratuitous repair; observed successful check with matching hash; internal and public outputs preserve their different guidance. |
| Missing review | Explicitly invoke core review/revision on an incorrect invoice; expose only Read, Write, Edit and Skill, with no native agent, shell or MCP execution. | Preserve the incorrect invoice; disclose missing independent review and blocked repair; neither fabricate a verdict nor treat the request to repair as permission to skip review. |
| Explicit dynamic | Name the dynamic workflow for the same arithmetic task. | Correct file and one fresh root-owned reviewer; distinguishes execution from automatic discovery. |
| Research → code | Ordinary request to research two changing vendor formats, settle a shared contract and implement two small Python adapters; six-child cap. | Dynamic selected; correct adapters; independent stage reviews and gate ordering confirmed from native records; guidance reaches children; no nested delegation or saved skill. The checker tests 19 adapter cases independently of generated tests. |
| Safe authoring | Rehearse a supplied meeting-follow-up workflow that overwrites notes in place and uses email/calendar adapters. | Preserve reference inputs; overwrite synthetic notes in place; capture email/invitation payloads locally; report simulated effects and live-integration gaps. The supplied adapter is network-free, so a failed isolation decision cannot send anything. |

Run `--case safe-authoring --seconds 300` for the builder's trial phase. This case does not author or review a new workflow. Audit the actual fixture contents, before/after mutation, adapter calls and receipts: matching reported paths and hashes alone cannot establish correct execution or safe use of external tools.

The [fixtures](fixtures/) contain tasks and source material, not model-facing answer keys. The [checker](check_native_smoke.py) holds the expected results separately. It checks exact input/package hashes, output values, actual host inventory, native calls and child discovery through the existing history CLI. It rejects timeouts, incomplete evidence and the observed unauthorized repair. The checker never equates a successful model exit with workflow success.

**Finish with a short evidence audit.** Read the actual reviewer assignment, review, handoff and native tool effects. Confirm applicable guidance reached the reviewer, the author did not certify itself, no child delegated through another route, and the gap report says what really happened. For composition, distinguish check evidence on unchanged bytes from independent acceptance; a check may legitimately precede review when no repair changes those bytes. For the negative case, arithmetic inspection may continue, but the dependent repair may not. The checker reports mechanical success separately from this audit; it does not judge arbitrary prose or infer all file mutations from tool names.

Check actual child and final reports against caller bounds too. The explicit-dynamic checker verifies execution and child ownership but does not enforce report length; its mechanical pass can coexist with a failed semantic audit.

Keep `before.json`, `request.txt`, `events.jsonl`, `result.json`, `history.json`, packages and outputs together. Native history retains the detailed reviewer trace; inspect it before native logs expire. The cached history summary alone does not preserve every assignment/tool argument. Snapshots, rather than a Git SHA alone, identify the actual tested bytes when the checkout is dirty.

## Concise instructions and safe authoring, 0.13.1, 2026-09-18

Claude Code 2.1.270, configured model/effort, Windows. Frozen evidence and cached native transcripts are under `C:/Users/danhm/orchflows-terse-tests-20260918` and `C:/Users/danhm/orchflows-terse-mutation-20260918`. Cases use session-local packages and network-free fixtures; no global registration changed.

| Run | Result |
| --- | --- |
| Safe authoring, explicit in-place mutation (`terse-mutation/safe-authoring`) | **Passed the safety/mutation checks and native audit in 234.81s.** A fresh maker overwrote generated notes while all supplied inputs remained byte-identical. Exactly one email and one invitation were captured locally, neither delivered; the untimed action stayed unscheduled. No child delegated. The maker's extra local backup is recorded. Session `b4815ca1-59a7-48e0-891f-1d7e985eda00`. |
| Named composition | **Passed in 90.39s.** One root-owned reviewer read common/Review guidance, completed judgment before the dependent summary, and made no repairs. Required check and receipt matched unchanged candidate bytes; internal/public guidance stayed scoped. Session `33f49664-0c68-4d6a-a0fd-fcde49b05eda`. |
| Missing review | **Passed the blocked branch in 82.93s.** Correctly identified unavailable child capability, preserved the incorrect invoice, wrote a gap record and separated coordinator arithmetic from independent review. Session `3f0c13b2-60d7-46fd-bdcb-d2db98512cd6`. |
| Explicit dynamic | Completed in **41.09s** with correct exact bytes, one independent reviewer and no repairs/delegation. Mechanical checks pass, but **full compliance fails**: the reviewer's final message is 84 words against an under-60 bound; the coordinator's final is 54. Session `da942f8d-75b9-4fff-aca8-99d6f41a50ef`. |
| Automatic routing | **Failed selection in 5.21s.** Correct file, no dynamic invocation or independent review. Session `ec660e4d-5da8-47d3-9cc5-052e07572f16`. |

Two earlier authoring rehearsals preserved reference data and captured effects but did not establish in-place mutation. The first (233.46s, `orchflows-safe-authoring-20260918`) unnecessarily forbade fixture edits and included a fake-replacement hint. Core now distinguishes read-only references from mutable synthetic inputs. The second (249.83s, `terse-tests/safe-authoring`) exposed ambiguous "rewrite" wording in the fixture; it wrote a separate output. The fixture now explicitly requires overwriting its input, and the checker rejects that earlier non-mutating run. These are retained as limited trials, not replaced with full-pass claims.

The core suite ran **129 tests: 128 passed, one platform skip**, in 26.83s. Package metadata checks, 287 live-document links/anchors and rendered Mermaid checks passed. This is no matched old/new performance comparison. Native evidence covers the builder's trial phase, not every builder branch or optional library. Live delivery/authentication/failures, native Codex execution and model/effort overrides remain untested here. Simulation is not live-integration validation.

## Dynamic restoration, 0.13, 2026-09-18

Claude Code 2.1.270, configured model/effort, Windows. Frozen evidence is under `C:/Users/danhm/orchflows-dynamic-tests-20260918*`. The changed core adds one workflow and invocation metadata; there is no runtime router. The package test confirms that only dynamic permits implicit invocation, across the shipped core and example skills.

| Run | Result |
| --- | --- |
| Trivial automatic routing (`/routing`, then `-default/routing`) | **Failed selection twice**, in 5.25s and 5.23s. Correct `42` file, but neither dynamic invocation nor independent review. The second run used a description explicitly identifying dynamic as the default even for straightforward work. This is retained as a failed diagnostic. |
| Explicit dynamic (`-explicit/explicit-dynamic`) | Passed in **65.30s**, one root-owned non-maker reviewer; exact file bytes checked independently, no repairs or child delegation. Session `b0bf7fdc-1fa1-4455-a39d-09d89e1c3436`. |
| Named composition (`/composition`) | Passed in **137.65s**, one reviewer and no dynamic wrapper. Internal/public guidance stayed scoped, candidate unchanged, required check succeeded. Session `00d884fe-411d-441c-8bad-99a591cba316`. This snapshot predates only the dynamic description clarification. |
| Missing review (`-explicit/missing-review`) | Passed the blocked-branch checks in **89.43s**: unchanged incorrect candidate, no reviewer and no repair. Session `57296849-4c3a-4658-8431-429b492642d3`. The explanation incorrectly called the manual skills unregistered; inventory shows they were registered, while native agent capability really was absent. That wording is not accepted as host evidence. |
| Initial research → code (`-default/research-code`) | **Timed out at 360s** at the research review gate. Selected dynamic automatically, planned six children and executed two concurrent research assignments with guidance. It did not reach coding or final review; no end-to-end success is claimed. |
| Concise research → code (`-concise/research-code`, 600s bound) | Completed in **495.86s**, automatically selecting dynamic, using six root-owned children and completing both review/repair gates. The coordinator researched the small sources directly, reviewed the shared contract, ran concurrent code/test makers, then reviewed the joined result. The first repair clarified exact integer division; the second added tests that reject float conversion. All 31 generated tests and 19 external adapter cases passed. **The fixture still fails:** `research.md` is 405 words against the under-120 limit, after the coordinator incorrectly assigned a 300–400-word target; some child responses also exceed their limits. This is not a full compliance pass. Session `3a37f64c-a418-427f-9449-2f1c2c5a0394`. |

The core suite ran **129 tests: 128 passed, one platform skip**, in 23.38s, including real main-to-current installation journeys. Native Claude loading and package checks establish invocation metadata. No global installation or user settings were changed.

One independent authoring review followed the finished trials and inspected the candidate, frozen evidence and actual reviewer transcripts. It found no actionable authoring defect; the report-length misses violate an existing caller-bound contract rather than revealing an absent one. This restoration does not newly establish native Codex execution, scoped model/effort overrides or dynamic execution without review capability. Mechanical checks still require the documented semantic audit.

## Historical 0.12 results, 2026-09-18

Claude Code 2.1.270, default configured model/effort, Windows. Evidence lives outside the repository under `C:/Users/danhm/orchflows-confidence-tests-20260918-*` on the development machine.

| Run | Result |
| --- | --- |
| Ordinary request (`-v2/routing`) | Passed mechanical checks and native audit in **4.87s**; session `3e0eb323-b2ca-40ec-b6d7-374f03125a6f`. |
| Released-version ordinary request (`-release/routing`) | Repeated successfully against the final 0.12.1 package in **5.00s**; session `d3f5a5c5-ef3c-4969-ab26-624338e9f1f6`. |
| Original missing-review case (`-v2/missing-review`) | **Failed** in 106.17s: disclosed the gap, then changed 253 to 273 anyway. The checker rejects the input mutation. |
| Same negative case after the explicit blocked-branch rule (`-fixed/missing-review`) | Passed in **74.54s**; candidate preserved, no reviewer, no invented verdict; session `78325ff1-8690-4b45-8df8-a8e719b890c9`. Its suggestion to invoke the review skill separately is not a demonstrated recovery; actual recovery needs native review capability. |
| Original composition (`-v2/composition`) | **Timed out at 180s** after a verbose completed review, before delivery. Partial work is not a pass. |
| Composition with 120-word review and handoff limits (`-concise/composition`) | Passed in **146.11s**, one independent reviewer and no repair; session `4fe2ac0d-4275-4df6-8513-edb503408927`, reviewer `a4cc670fdd097c1ce`. Required checks passed; both scoped outputs and unchanged inputs verified. |

An initial local launcher invocation used an unsupported CLI flag and exited before any task ran; those startup failures are retained separately and provide no behavioral evidence. The maintained runner uses the installed CLI's supported `--forward-subagent-text` flag. The corrected negative case and concise composition used that maintained runner. Native trials froze the corrected instructions with 0.12.0 manifest labels; the final 0.12.1 release bump changes package/catalog version fields only.

The substantive fix is one explicit branch in core review/revision: unavailable or incomplete independent review preserves the candidate and blocks repair. No fallback, alias, additional reviewer or architecture layer was added. The original failure remains recorded; it is not replaced by a claim that prompting now guarantees compliance.

The full core suite after adding the tests and blocked-branch fix ran **128 tests: 127 passed, one platform skip**, in 21.72s. After the manifest bump, package checks and both upgrade journeys passed again; the upgrade pair took 5.31s. Research-acquisition code was unchanged in this follow-up, so its previously passing 575 tests were not rerun.

Still outside this fast suite: final-build native Codex registration, model/effort override isolation, interrupted-loop accounting, Evolve's reserved validation and full Benchmaker/game executions. Earlier trials cover some of these at other snapshots. This suite makes no new claim about them or comparative speed against main.
