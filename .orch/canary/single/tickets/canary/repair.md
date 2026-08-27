---
id: repair
run: orch-install-catalog-repair-20260825
status: complete
executor: orch-repair
depends_on: []
write_scope:
  - installer/foundation.py
  - tests/test_installer_cases/
mutations:
  - change:installer/foundation.py
  - write:tests/test_installer_cases/
excluded_actions:
  - changing canonical skill contracts, worker profiles, host-block routing, or non-Codex adapters
  - removing or renaming any existing Codex skill redirect
  - reinstalling user-level orchflows before the repository repair passes its checks
independence: checker
isolation: none
bound: <= 120 tool calls
admission: plain-artifact:sha256:08ea59a33094a3fad47a4e943a5ed2aabc162a1d79838607751daaa9f9b8a1ab
ownership_regions: []
root_generation: root:repair:1:sha256:c8b50504b264a3f3a5cdefdeb34f9e4d62973a47c012dc3d9b14aa3253f07183
cut_generation: cut:repair:1:sha256:12c115412192ebaf6457e6cabdbeeb49d6b9a917453beb159535c40e9d70057f
assignment_seal: sha256:4865c276f3c9fec642a767af395fc85a580e1b2d6941068ed6ee2a148a243bef
claimed_by: orch-install-catalog-repair-20260825-repair
claimed_at: 2026-08-25T17:45:59Z
checked_by: orch-install-catalog-repair-20260825-repair-checker
---

## Objective

The canonical installer generates a first-class Codex skill redirect for `orch-investigate` alongside the existing four redirects, guarded by a regression test that fails under the old four-name policy.

## Fixed inputs

- input: {"identity":{"kind":"ticket-section","run":"orch-install-catalog-diagnosis-20260825","section":"Result","sha256":"625ca8aaa7a02c5d41fa1af42b9e605ad336097beadf229d5ff5886eaa496b9e","ticket":"investigate"},"name":"accepted-defect-set","type":"identity"}
- input: {"name":"workspace","type":"literal","value":"C:\\Users\\danhm\\.codex\\worktrees\\2cb3\\orchflows-public"}

## Completion test

- affected installer tests PASS and include a regression assertion that the generated Codex skill targets contain `orch-investigate` while preserving `orch-spec`, `orch-frontier`, `fix`, and `orch-build` | oracle: `uv run --no-project python tools/run_tests.py --scope installer/foundation.py tests/test_installer_cases/` | oracle_class: deterministic | provenance: authored-here
- library validation PASSes after the redirect-policy change | oracle: `uv run --no-project python tools/validate.py` | oracle_class: deterministic | provenance: pre-existing
- installer dry-run PASSes and resolves the updated canonical plan without writing user files | oracle: `uv run --no-project python install.py --dry-run` | oracle_class: deterministic | provenance: pre-existing
- the patch is the smallest coherent repair and changes no behavior outside first-class Codex exposure of `orch-investigate` and its regression expectations | oracle: independent library-lens critique of the diff against the accepted defect set | oracle_class: judged | provenance: authored-here

## Return fields

status; changed_artifacts; per-finding disposition with rerun evidence; result identity; verification; feedback; risks; queued scope

## Result

status: repair implemented; verification pending.

Changed artifacts so far: `installer/foundation.py`, `tests/test_installer_cases/planning/runtime.py`, and `tests/test_installer_cases/planning/scoped_hosts.py`.

Disposition: accepted redirect/catalog-generation omission fixed by keeping the Claude shared-four tuple intact and defining the Codex redirect tuple as those four plus `orch-investigate`. The scoped-host regression asserts the exact generated Codex target set, so the old four-name policy fails it.

Authored-here discrimination record: a faithful `git clone --no-local` of the pre-repair repository had `git rev-list --count HEAD` = 1120. Applying only the two regression-test changes and running `uv run --no-project python tools/run_tests.py --scope installer/foundation.py,tests/test_installer_cases/` exited 1 with runner summary `21 modules, 910 tests: 2 failures, 0 errors, 5 skipped`; the failures were the exact Codex tuple assertion and generated-target assertion, both because `orch-investigate` was absent. This is the executor-owned red required by rules/verification.md §8.

status: complete; repair artifact produced, with independent critique pending the ticket's checker path.

Changed artifacts: `installer/foundation.py`; `tests/test_installer_cases/planning/runtime.py`; `tests/test_installer_cases/planning/scoped_hosts.py`.

Per-finding disposition: FIXED — Codex catalog-generation omission. `SHARED_ADAPTER_NAMES` remains exactly `orch-spec`, `orch-frontier`, `fix`, `orch-build` for Claude's four-adapter mode; `CODEX_SKILL_REDIRECT_NAMES` now adds `orch-investigate`. The generated-target regression asserts exactly those five Codex skill targets. Rerun evidence: the corrected-syntax affected-scope oracle exited 0 with `21 modules, 910 tests: 0 failures, 0 errors, 5 skipped` and `OK`; validation and installer dry-run also exited 0, with the dry-run planning five Codex redirect skills including `orch-investigate`.

Frozen result identity: base repository HEAD `cd54dc0c24dbe5183571360e146e71afc56c9aac`; filesystem/raw-byte SHA256 `AB60B61DC666C12B6D7FA26C53D8FA485A0B6ED0182A381980AF5124FA355165` (`installer/foundation.py`), `565600F1ECE418C7CDFAA9053A498CFA7251C4C08BF7116F3F0E31CA48FE21FD` (`tests/test_installer_cases/planning/runtime.py`), and `5090D9D79880E93F25F73305509CAD09CBF14DBDFD75ADDA9F96AA8BCFDC7119` (`tests/test_installer_cases/planning/scoped_hosts.py`).

Queued scope: none. The user-level installation was not run.

Checker pass in progress — identity confirmed at HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac and the three recorded filesystem/raw-byte SHA256 values; tracked diff remains exactly the three in-scope artifacts.

Checker pass by orch-install-catalog-repair-20260825-repair-checker: status PASS; changed_artifacts: []; findings: none; corrections: none; invalidated verification entries: none. The result remains frozen at base HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac with filesystem/raw-byte SHA256 AB60B61DC666C12B6D7FA26C53D8FA485A0B6ED0182A381980AF5124FA355165 for installer/foundation.py, 565600F1ECE418C7CDFAA9053A498CFA7251C4C08BF7116F3F0E31CA48FE21FD for tests/test_installer_cases/planning/runtime.py, and 5090D9D79880E93F25F73305509CAD09CBF14DBDFD75ADDA9F96AA8BCFDC7119 for tests/test_installer_cases/planning/scoped_hosts.py. Per-finding disposition and rerun evidence: not applicable; no finding required correction, all deterministic covers are unchanged, and their executor entries were reused rather than rerun. Fresh judged criterion 4 PASS: the diff is exactly three in-scope tracked files; its sole installer behavior change extends the Codex redirect tuple with orch-investigate while preserving the exact Claude bounded-four tuple, and its test edits replace the now-obsolete tuple-identity assertion plus pin the exact generated five-name Codex set. Queued scope, nonblocking and outside this ticket authority: update install.py line 30 prose that still says Codex writes four redirect stubs.

## Verification

Frozen result identity: base repository HEAD `cd54dc0c24dbe5183571360e146e71afc56c9aac`; filesystem/raw-byte SHA256 `AB60B61DC666C12B6D7FA26C53D8FA485A0B6ED0182A381980AF5124FA355165` (`installer/foundation.py`), `565600F1ECE418C7CDFAA9053A498CFA7251C4C08BF7116F3F0E31CA48FE21FD` (`tests/test_installer_cases/planning/runtime.py`), and `5090D9D79880E93F25F73305509CAD09CBF14DBDFD75ADDA9F96AA8BCFDC7119` (`tests/test_installer_cases/planning/scoped_hosts.py`).

Criterion 1 — PASS, exit 0 using the runner-required equivalent spelling `uv run --no-project python tools/run_tests.py --scope installer/foundation.py,tests/test_installer_cases/`. Summary: `21 modules, 910 tests: 0 failures, 0 errors, 5 skipped`; `OK`. The ticket's literal two-argument spelling was also attempted and rejected before selection with `run_tests: --scope takes one comma-separated value`; that friction is logged. Authored-here discrimination: in a faithful clone of the pre-repair tree, history count 1120, the same corrected-syntax command exited 1 with two assertion failures specifically because `orch-investigate` was absent from the Codex policy and generated targets.

Criterion 2 — PASS, exit 0: `uv run --no-project python tools/validate.py`. Summary: validation completed successfully with existing near-duplicate warnings and no errors.

Criterion 3 — PASS, exit 0: `uv run --no-project python install.py --dry-run`. Summary: `Codex redirect skills (5)` listed `orch-frontier`, `orch-investigate`, `orch-build`, `orch-spec`, and `fix`; `planned entries: 363`; no user files were written.

Criterion 4 — UNVERIFIED, exit N/A: the required independent library-lens critique cannot be supplied by the executor that authored the repair. The diff is three in-scope files, 14 insertions and 10 deletions, and is queued for the ticket's checker path.

Overall executor verification: UNVERIFIED pending independent judged critique; all deterministic criteria are green at the frozen identity.

Checker verification at the confirmed frozen identity: Criterion 1 PASS by reuse — unchanged covers and executor evidence 21 modules, 910 tests, 0 failures, 0 errors, 5 skipped, plus its recorded pre-repair red with the exact Codex tuple and generated-target failures; Criterion 2 PASS by reuse — unchanged covers and executor validation exit 0; Criterion 3 PASS by reuse — unchanged covers and executor dry-run exit 0 listing five Codex redirect skills including orch-investigate and 363 planned entries; Criterion 4 PASS fresh judged oracle — independent diff review found one shared cause, one behavior-line tuple extension, exact preservation of SHARED_ADAPTER_NAMES, exact five-target generated-plan regression coverage, and no tracked change outside the three granted artifacts. Overall checker verdict: PASS; weakest oracle class: judged.

## Feedback

The first completion-test command needs one comma-separated `--scope` value: `--scope installer/foundation.py,tests/test_installer_cases/`. Its current two-argument spelling is rejected by `tools/run_tests.py` before test selection. The equivalent corrected spelling was used for both the red discrimination and final green run, and the friction was logged for the contract owner.

Mechanism answer for the user: CODEX_SKILL_REDIRECT_NAMES is the curated allowlist used in both discover_packages and discover_templates loops in installer/planning.py; every discovered name gets a host-agnostic library pointer at the lib/by-name/name/SKILL.md path and, when Codex is enabled, a Codex prompt, but only allowlisted names are appended to Plan.codex_skills at the CODEX_HOME/skills/name/SKILL.md first-class catalog path, which installer/application.py writes and receipts as codex-skill. The by-name pointer is therefore resolution infrastructure, not a Codex catalog registration. Claude has a configurable analogue: CLAUDE_ADAPTER_SETS selects all by default, or four; only four mode gates through SHARED_ADAPTER_NAMES in _mints_claude_adapter and writes CLAUDE_CONFIG_DIR/skills/name/SKILL.md adapters. After this repair, the Claude bounded allowlist remains orch-spec, orch-frontier, fix, orch-build, while the Codex allowlist is that tuple plus orch-investigate.

## Risks

Checker risks: the authorized work proves plan generation, validation, and dry-run behavior only; the user-level Codex catalog is intentionally unchanged until a separately authorized reinstall or refresh. The top-level install.py module prose still enumerates four Codex redirect stubs, a nonbehavioral documentation follow-up outside this ticket write scope.

## Carry

1. Decision: keep `SHARED_ADAPTER_NAMES` as Claude's exact four and define Codex redirects as those four plus `orch-investigate`; no canonical skill contract, profile, routing, or non-Codex adapter changed.

2. Landed identity: base HEAD `cd54dc0c24dbe5183571360e146e71afc56c9aac`; repaired filesystem hashes are recorded in Result and Verification. Only `installer/foundation.py` and two installer regression files are modified.

3. Hazard: the ticket's affected-test oracle is misspelled for this runner. Re-take it with `uv run --no-project python tools/run_tests.py --scope installer/foundation.py,tests/test_installer_cases/`; the literal space-separated form exits 1 before selection.

4. Measurement: the corrected scoped command ends `21 modules, 910 tests: 0 failures, 0 errors, 5 skipped` / `OK`; `uv run --no-project python tools/validate.py` and `uv run --no-project python install.py --dry-run` both exit 0, and the dry-run lists five Codex redirect skills including `orch-investigate`.

5. Acceptance: deterministic criteria are green with an executor-owned red discrimination record; one fresh independent library-lens critique of this frozen diff remains required.

Checker carry: no code correction and no invalidated oracle entry. Reuse the three deterministic PASS entries at the recorded hashes; accept the fresh judged PASS. For follow-up communication, distinguish the universal by-name pointer surface from host catalog surfaces: CODEX_SKILL_REDIRECT_NAMES controls only CODEX_HOME/skills first-class redirects, while Claude defaults to all adapters and uses SHARED_ADAPTER_NAMES only under --claude-adapters four.

## Handoff

[]
