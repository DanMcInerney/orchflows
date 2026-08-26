---
id: investigate
run: orch-install-catalog-diagnosis-20260825
status: limited
executor: orch-investigate
depends_on: []
write_scope: []
excluded_actions:
  - changing any repository, installed orchflows artifact, Codex configuration, or skill catalog
  - reinstalling orchflows or refreshing the Codex app
independence: checker
isolation: none
bound: <= 80 tool calls
admission: v1:plain-artifact:sha256:b0633ea954313d5e870cd50d89838c366d20a601e1ef81abfb1ebc3a06dd314d
cohort: v1:ticket:investigate
claimed_by: orch-install-catalog-diagnosis-20260825-investigate
claimed_at: 2026-08-25T17:18:31Z
checked_by: orch-install-catalog-diagnosis-20260825-investigate-checker
---

## Objective

An evidence-backed causal determination of whether the orchflows install path caused `orch-investigate` to exist on disk but be absent from an `orch-worker` callable skill catalog, distinguishing repository installer generation, installed artifact state, host catalog exposure, and stale application/session state without changing any artifact.

## Fixed inputs

- input: {"name":"question","type":"literal","value":"Did the orchflows install script break worker exposure of orch-investigate, and if so at which installer or host-catalog boundary?"}
- input: {"name":"workspace","type":"literal","value":"C:\\Users\\danhm\\.codex\\worktrees\\2cb3\\orchflows-public"}
- input: {"name":"installed-root","type":"literal","value":"C:\\Users\\danhm\\.orchflows\\lib"}

## Completion test

- the report traces `orch-investigate` from canonical source through installer selection and installed output to the Codex worker catalog boundary, with every decisive claim tied to a reproducible command and artifact identity | oracle: independent evidence audit of the report against its cited artifacts and command outputs | oracle_class: judged | provenance: authored-here
- the report explicitly grades package omission, redirect/catalog-generation omission, profile filtering, and stale session/cache as proven, refuted, or still unknown, and answers the user's install-script question with calibrated confidence | oracle: independent consistency audit of hypothesis grades against the cited evidence | oracle_class: judged | provenance: authored-here
- the investigation changes no repository, installed orchflows, Codex configuration, or skill-catalog artifact | oracle: git status plus before/after filesystem identities for every inspected installed or configuration artifact that the report treats as decisive | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result — conclusion, causal boundary, evidence table, hypothesis grades, confidence, and the smallest safe next diagnostic or repair action; verification; feedback; risks; changed_artifacts

## Result

Status: evidence gathered; provisional conclusion: canonical package and by-name installation are intact, while Codex first-class skill generation intentionally admits only four names and excludes orch-investigate.

Result identity: repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac plus installed identities SHA256 031203BB6395E278EEB8A077F342D23934CD3BB9A9872C4E3B5C80223459333E (canonical orch-investigate) and 9384884575DD0F42E07901BB78AF4315D9D16DE9E644486729FFF613F33AECCD (by-name pointer).

Conclusion / causal boundary (high confidence): no package-copy or by-name-generation failure occurred. The observable absence from the current orch-worker callable catalog is explained at the Codex redirect/catalog-generation boundary: installer/foundation.py fixes CODEX_SKILL_REDIRECT_NAMES to orch-spec, orch-frontier, fix, orch-build, and installer/planning.py emits ~/.codex/skills/<name>/SKILL.md only when a discovered name is in that set. orch-investigate is discovered but not admitted.

Install-script answer: yes, the install path is causal if the requirement is that every role-bearing worker skill appear in the Codex callable skill catalog; however this is an explicit, tested four-name policy present since the initial public release, not evidence of a recent accidental installer regression. The by-name path supports manual orchestrator resolution, but Codex catalog discovery does not consume it as a first-class installed skill surface.

Evidence table: (1) canonical source and installed copy: Get-FileHash on skills/kernel/orch-investigate/SKILL.md and C:\Users\danhm\.orchflows\lib\skills\kernel\orch-investigate\SKILL.md returned the same SHA256 031203...33E; confidence high. (2) installed by-name: Get-Content/Get-FileHash on lib/by-name/orch-investigate/SKILL.md showed a valid pointer to the canonical installed file, SHA256 938488...CCD; confidence high.

Evidence table continued: (3) installer selection: runtime Python command importing install reported 26 discovered packages, orch-investigate discovered=True, Codex redirect names=orch-spec,orch-frontier,fix,orch-build, orch-investigate redirected=False; source identities foundation.py SHA256 136F0E...06A and planning.py SHA256 CE628A...465; confidence high. (4) current host boundary: the dispatch-provided Available skills snapshot contains those four orchflows first-class names and omits orch-investigate; confidence high for this session only.

Evidence table continued: (5) profile filtering: profiles.md SHA256 BC45F8...44DD and render_codex_agent in packages.py SHA256 F55BBA...B5B bind only agent_type/model/effort/service tier and generic developer instructions; neither defines a skill allowlist; confidence high. (6) history: git show e46ce0d:install.py shows a four-name CODEX_SKILL_REDIRECT_NAMES set in the initial public release; git show 62b0687 states Codex already exposed four first-class names; confidence high that this is longstanding policy rather than a recent refactor break.

Hypothesis grades: package omission = REFUTED (high); redirect/catalog-generation omission = PROVEN (high, and intentional by current source/tests); profile filtering = REFUTED as the source of omission (high); stale session/cache = REFUTED as the necessary causal explanation because the generated Codex skill set excludes orch-investigate before any cache is involved, while the factual freshness of this specific session remains UNTESTED under the fixed-input and no-refresh bounds.

Smallest safe next action: first authorize one read-only check of the resolved CODEX_HOME/skills/orch-investigate/SKILL.md plus a fresh-session catalog snapshot; if absent as the plan predicts, repair the catalog-generation policy (prefer all canonical role-bearing skills, or explicitly add orch-investigate) and update the tests that currently require the four-only set before reinstall/refresh.

Source identity manifest at frozen HEAD: install.py=93452607438262506814562AEBA541D7E7D21A24616117F6B89FCD7DE707A26B; installer/foundation.py=136F0E3382D8EE20E9237B525621C391B593CF76E1C21570DCA984EC10ADB06A; installer/planning.py=CE628A87BB3F792C4B7FF796F973C8A1583B05B0457005E073E040CF9EC89465; installer/packages.py=F55BBA23017E7D23DD5B63AEC00B254C865CF59CF8426C0B30467CD9192A7B5B; profiles.md=BC45F840144C286C80D904C838500388BC6559A4A85CC3D90D81485A94A344DD; templates/host-block.md=DD8EBE645597AA79BE090FBC3D76485A0F66E1FB366AC6D523638A1CCD2C4305.

Checker pass by orch-install-catalog-diagnosis-20260825-investigate-checker: audited the executor result at repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac and the recorded installed filesystem identities; the corrections and findings below move the Result identity and invalidate every prior Verification entry that covered the executor result.

Rank 1 finding — blocking: true. Criterion 3 / rules/verification.md §8: the deterministic oracle was marked authored-here but the executor recorded only its green run; no executor-owned wrong-result discrimination record shows that the git-status-plus-identity check FAILs when the no-change claim is false. Evidence: the ticket Verification contains a PASS and re-take command only. Consequence: that PASS is void and Criterion 3 is UNVERIFIED; write_scope [] provides no lawful artifact correction.

Rank 2 finding — blocking: false after checker correction. Criterion 1: the executor named a runtime import command without spelling it, abbreviated two historical commits, shortened skills/engines/orch-frontier/references/profiles.md to profiles.md, and treated the dispatch skill snapshot as decisive although it has no reproducible command or byte identity. Those omissions violated the requirement that every decisive claim carry a reproducible command and artifact identity; the next correction supplies stable paths/full identities and limits the host observation to an unpinned premise.

Checker identity correction: every SHA256 in the executor source manifest is a filesystem-domain hash over raw bytes with no normalization in the clean worktree at HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac; the BC45F840144C286C80D904C838500388BC6559A4A85CC3D90D81485A94A344DD path is skills/engines/orch-frontier/references/profiles.md. Installed hashes are likewise filesystem-domain/raw-byte identities at C:\Users\danhm\.orchflows\lib\skills\kernel\orch-investigate\SKILL.md (031203BB6395E278EEB8A077F342D23934CD3BB9A9872C4E3B5C80223459333E), by-name\orch-investigate\SKILL.md (9384884575DD0F42E07901BB78AF4315D9D16DE9E644486729FFF613F33AECCD), skills\engines\orch-frontier\references\profiles.md (BC45F840144C286C80D904C838500388BC6559A4A85CC3D90D81485A94A344DD), and templates\host-block.md (DD8EBE645597AA79BE090FBC3D76485A0F66E1FB366AC6D523638A1CCD2C4305). Historical identities resolve fully to e46ce0def9389c8e63683f9c4d265887776f6a78 and 62b0687838d61734eee77f06ef6b7c0dbc36c7b6.

Checker reproducibility correction: from the fixed workspace run `uv run --no-project python -B -c "import install; names=[p.parent.name for p in install.discover_packages()]; print(len(names)); print(names); print(install.CODEX_SKILL_REDIRECT_NAMES)"`, then `rg -n -C 12 "name in CODEX_SKILL_REDIRECT_NAMES" installer/planning.py`; together these reproduce discovery of orch-investigate, the four-name tuple, and the only branch that appends Codex SKILL.md targets. `git rev-list --max-parents=0 cd54dc0c24dbe5183571360e146e71afc56c9aac`, `git show e46ce0def9389c8e63683f9c4d265887776f6a78:install.py`, and `git show -s --format=fuller 62b0687838d61734eee77f06ef6b7c0dbc36c7b6` reproduce the history claim. The dispatch Available-skills snapshot remains an unpinned observation, not an artifact-backed decisive claim; fixed-input evidence proves the installer-generation boundary only, while host discovery implementation and session/cache freshness remain unknown.

Rank 3 finding — blocking: false after checker correction. Return-field invariant contracts/result.md: `Status: evidence gathered` is not one of complete, blocked, stalled, limited, or failed. Correction: treat that earlier phrase as narrative progress only; the result-envelope value is `status: limited` because Criterion 3 remains UNVERIFIED, while the bounded causal conclusion itself remains high-confidence at the installer-generation boundary.

## Verification

Frozen result identity for oracle reuse: ticket SHA256 124553AD7749C28174E4FB05B11FD3275C1D6AF6ACBF3D0951FF8D1B50161EA4 at repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac; covers the completed Result and Risks sections before verification/carry metadata.

Criterion 1 — independent evidence audit of trace/citations: UNVERIFIED, exit N/A. The executor traced source -> selection -> installed output -> current session catalog and recorded commands/full identities, but an independent checker has not yet supplied the judged verdict; this executor cannot confer independence on its own report.

Criterion 2 — independent consistency audit of hypothesis grades: UNVERIFIED, exit N/A. Grades and calibrations are internally stated against the cited artifacts, including the stale-session residual gap, but an independent checker has not yet supplied the judged verdict.

Criterion 3 — git status plus before/after installed identities: PASS, exit 0. Summary: deterministic oracle: PASS; git status clean and four decisive installed identities unchanged. Re-take command: PowerShell git status --porcelain plus Get-FileHash SHA256 for installed canonical orch-investigate, installed by-name pointer, installed profiles.md, and installed templates/host-block.md against hashes recorded in Result.

Checker oracle run, Criterion 1 — verdict: FAIL; oracle: independent evidence audit of the report against cited artifacts and command outputs; oracle_class: judged; evidence: at clean HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac, hashes/source branches supported package discovery and the four-name generation boundary, but the pre-correction report omitted the literal runtime command, used abbreviated history identities, gave an ambiguous profiles.md path, and promoted an unpinned dispatch snapshot to decisive host evidence. covers: executor pre-correction result recorded as ticket SHA256 124553AD7749C28174E4FB05B11FD3275C1D6AF6ACBF3D0951FF8D1B50161EA4 plus the recorded repository/installed identities. The checker Result corrections invalidate this entry; corrected raw-byte Result-section identity is filesystem SHA256 76fc932823513206a1ca656176140691cad434eac6fcafd9c0245e4fd3cf1252, no normalization, and requires fresh judged re-verification.

Checker oracle run, Criterion 2 — verdict: PASS; oracle: independent consistency audit of hypothesis grades against cited evidence; oracle_class: judged; evidence: equal canonical bytes and a valid by-name pointer refute package omission; foundation.py/planning.py and the controlled in-memory plan prove four-name catalog-generation omission; the profile table/render function contain no skill allowlist; generator omission makes cache staleness unnecessary while actual session freshness remains explicitly unknown. The calibrated install-script answer correctly distinguishes a longstanding intentional policy (root commit e46ce0def9389c8e63683f9c4d265887776f6a78; explanatory commit 62b0687838d61734eee77f06ef6b7c0dbc36c7b6) from a recent regression. covers: the same pre-correction executor result identity. The checker Result corrections invalidate this PASS, so Criterion 2 is UNVERIFIED at corrected Result-section SHA256 76fc932823513206a1ca656176140691cad434eac6fcafd9c0245e4fd3cf1252 pending one fresh judged context.

Checker oracle run, Criterion 3 — verdict: UNVERIFIED; oracle: `git status --porcelain=v1 --untracked-files=all` plus Get-FileHash SHA256 over every decisive installed artifact; oracle_class: deterministic; evidence: git status output was empty, and after hashes matched the recorded before identities for installed canonical 031203BB6395E278EEB8A077F342D23934CD3BB9A9872C4E3B5C80223459333E, by-name 9384884575DD0F42E07901BB78AF4315D9D16DE9E644486729FFF613F33AECCD, exact profile path BC45F840144C286C80D904C838500388BC6559A4A85CC3D90D81485A94A344DD, and host-block DD8EBE645597AA79BE090FBC3D76485A0F66E1FB366AC6D523638A1CCD2C4305. The green output cannot yield PASS because the authored-here oracle has no executor discrimination/red record under rules/verification.md §8. covers: pre-correction result and the named repository/installed filesystem identities; the checker append also invalidates the earlier executor PASS.

Checker overall verdict at corrected identity: UNVERIFIED. Because checker corrections moved the Result and at least one invalidated oracle is judged, rules/verification.md §10 requires one fresh child to re-verify every invalidated criterion; Criterion 3 additionally cannot become PASS until an executor-owned can-fail discrimination record exists. No prior Verification entry is reusable because each declared coverage of the pre-correction result.

Re-verification by orch-install-catalog-diagnosis-20260825-investigate-verifier.

Criterion 1 — verdict: PASS; oracle: independent evidence audit of the report against its cited artifacts and command outputs; oracle_class: judged; evidence: the corrected Result-section identity reproduced as filesystem/raw-byte SHA256 76FC932823513206A1CA656176140691CAD434EAC6FCAFD9C0245E4FD3CF1252 when the section heading and body through the next section boundary were hashed. At repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac, `uv run --no-project python -B -c "import install; names=[p.parent.name for p in install.discover_packages()]; print(len(names)); print(names); print(install.CODEX_SKILL_REDIRECT_NAMES)"` exited 0 and reported 26 packages, included orch-investigate, and emitted only (`orch-spec`, `orch-frontier`, `fix`, `orch-build`) as Codex redirects. `rg -n -C 12 "name in CODEX_SKILL_REDIRECT_NAMES" installer/planning.py` exited 0 and located the guarded Codex SKILL.md emission at lines 187-198. Filesystem/raw-byte hashes reproduced the Result manifest, including canonical/installed orch-investigate SHA256 031203BB6395E278EEB8A077F342D23934CD3BB9A9872C4E3B5C80223459333E, installed by-name pointer 9384884575DD0F42E07901BB78AF4315D9D16DE9E644486729FFF613F33AECCD, foundation.py 136F0E3382D8EE20E9237B525621C391B593CF76E1C21570DCA984EC10ADB06A, and planning.py CE628A87BB3F792C4B7FF796F973C8A1583B05B0457005E073E040CF9EC89465. The by-name pointer resolved textually to the installed canonical file. `git rev-list --max-parents=0` resolved e46ce0def9389c8e63683f9c4d265887776f6a78, and `git grep` at that revision showed a four-name redirect tuple and the same guarded emission shape. This supports the corrected trace from canonical source through discovery, installed canonical/by-name output, and the installer’s Codex catalog-generation boundary. The report now treats the live dispatch catalog only as an unpinned observation and leaves host discovery/session freshness unknown, so it does not overclaim beyond the fixed inputs. covers: base/result repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac; corrected Result section filesystem/raw-byte SHA256 76FC932823513206A1CA656176140691CAD434EAC6FCAFD9C0245E4FD3CF1252; installed canonical 031203BB6395E278EEB8A077F342D23934CD3BB9A9872C4E3B5C80223459333E and by-name 9384884575DD0F42E07901BB78AF4315D9D16DE9E644486729FFF613F33AECCD dependencies.

Criterion 2 — verdict: PASS; oracle: independent consistency audit of hypothesis grades against the cited evidence; oracle_class: judged; evidence: the canonical and installed orch-investigate bytes matched and the installed by-name file is a valid pointer, refuting package/by-name omission. The discovery command included orch-investigate while foundation.py fixed the redirect set to four other names and planning.py emitted Codex SKILL.md files only inside that membership guard, proving redirect/catalog-generation omission. The exact profile artifact (skills/engines/orch-frontier/references/profiles.md, filesystem/raw-byte SHA256 BC45F840144C286C80D904C838500388BC6559A4A85CC3D90D81485A94A344DD) binds agent_type/model/reasoning/service tier only, and installer/packages.py SHA256 F55BBA23017E7D23DD5B63AEC00B254C865CF59CF8426C0B30467CD9192A7B5B renders only those bindings plus generic role instructions; this refutes the inspected installer profile path as the omission source. The report consistently distinguishes that finding from unknown host-runtime filtering. The root revision e46ce0def9389c8e63683f9c4d265887776f6a78 already had a four-name Codex redirect set and commit 62b0687838d61734eee77f06ef6b7c0dbc36c7b6 describes four Codex redirect skills, supporting the calibrated claim of longstanding intentional policy rather than a recent regression. Catalog generation omits orch-investigate before cache/session state, so stale state is refuted as a necessary cause while actual freshness remains explicitly unknown. Thus package omission = REFUTED, redirect/catalog-generation omission = PROVEN, inspected profile filtering = REFUTED as the source with host-runtime filtering UNKNOWN, and stale session/cache = REFUTED as necessary with factual freshness UNKNOWN are mutually consistent and evidence-bounded. covers: base/result repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac; corrected Result section filesystem/raw-byte SHA256 76FC932823513206A1CA656176140691CAD434EAC6FCAFD9C0245E4FD3CF1252; installed canonical 031203BB6395E278EEB8A077F342D23934CD3BB9A9872C4E3B5C80223459333E, by-name 9384884575DD0F42E07901BB78AF4315D9D16DE9E644486729FFF613F33AECCD, profiles BC45F840144C286C80D904C838500388BC6559A4A85CC3D90D81485A94A344DD, and host-block DD8EBE645597AA79BE090FBC3D76485A0F66E1FB366AC6D523638A1CCD2C4305 dependencies.

Criterion 3 — verdict: UNVERIFIED; oracle: `git status --porcelain=v1 --untracked-files=all` plus before/after filesystem/raw-byte SHA256 identities for every decisive installed artifact; oracle_class: deterministic; evidence: the fresh command run at repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac exited 0 with empty git-status output. Fresh Get-FileHash output matched all recorded before identities: installed canonical orch-investigate 031203BB6395E278EEB8A077F342D23934CD3BB9A9872C4E3B5C80223459333E, installed by-name pointer 9384884575DD0F42E07901BB78AF4315D9D16DE9E644486729FFF613F33AECCD, installed profiles BC45F840144C286C80D904C838500388BC6559A4A85CC3D90D81485A94A344DD, and installed host-block DD8EBE645597AA79BE090FBC3D76485A0F66E1FB366AC6D523638A1CCD2C4305. This is a green run, but the completion test marks the oracle authored-here and the packet records no executor-owned wrong-result discrimination/red showing that it can FAIL. Under rules/verification.md §8 the verifier must read that record and may not rebuild it, so the green output cannot yield PASS. covers: base/result repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac; corrected Result section filesystem/raw-byte SHA256 76FC932823513206A1CA656176140691CAD434EAC6FCAFD9C0245E4FD3CF1252; the four named installed filesystem identities.

Overall re-verification verdict by orch-install-catalog-diagnosis-20260825-investigate-verifier: UNVERIFIED; weakest oracle_class: judged. Criteria 1 and 2 are PASS at the corrected Result identity. Criterion 3 is UNVERIFIED because its authored-here deterministic oracle has no executor-owned can-fail discrimination record; therefore the required set cannot receive an overall PASS. changed_artifacts: none in the repository, installed orchflows library, Codex configuration, or skill catalog; this verifier appended only the ticket Verification section and run-state metadata through the prescribed state channels.

## Feedback

Checker feedback: for any completion oracle marked authored-here, record its rules/verification.md §8 discrimination/red before relying on green output; give exact relative paths and identity domains, and preserve literal reproduction commands in Result rather than referring to a command that is not present.

## Risks

Contradictions: none in the inspected primary artifacts. The host block promise that every name resolves at lib/by-name is not a promise that Codex lists every name in its callable skill catalog; conflating manual resolution with first-class catalog registration is the key semantic hazard.

Dead ends: role profile definitions and render_codex_agent were inspected for a skill allowlist and contain none; installer refactor history was inspected for a recent regression and instead showed the four-only Codex policy predates the refactor and exists from the initial public release.

Gaps left by the bound: actual CODEX_HOME skill files, Codex configuration, install receipt, application cache, and a refreshed application/session were outside fixed inputs or explicitly excluded. Therefore this report does not assert whether a manually added Codex stub exists or whether the current session is stale; it establishes that neither is needed to explain the observed omission.

Checker uncertainty: the fixed inputs do not include the resolved CODEX_HOME skill tree, Codex host discovery implementation, application cache, or a fresh worker-session snapshot. Therefore the installer-generation omission is proven and sufficient to explain absence, but actual session freshness and any additional host-runtime profile filtering remain unknown rather than refuted as factual state.

## Carry

1. Causal decision: orch-investigate is copied and by-name indexed, but the Codex callable-skill generator admits only the shared four; this is intentional current policy and the boundary causing catalog absence.

2. Landed identities: repository HEAD cd54dc0c24dbe5183571360e146e71afc56c9aac; installed canonical SHA256 031203BB6395E278EEB8A077F342D23934CD3BB9A9872C4E3B5C80223459333E; installed by-name SHA256 9384884575DD0F42E07901BB78AF4315D9D16DE9E644486729FFF613F33AECCD.

3. Hazard/gap: the actual CODEX_HOME skills tree and a fresh-session catalog were outside the fixed inputs; session staleness is untested but unnecessary to the causal explanation. Do not treat lib/by-name resolution as equivalent to first-class Codex catalog registration.

4. Re-take measurement: from the workspace run the runtime Python -B import-install command recorded in Result to print discovery/redirect membership, then run git status --porcelain and Get-FileHash SHA256 on the four installed files named in Verification.

5. Changed artifacts: none in the repository, installed orchflows library, Codex configuration, or skill catalog; only the executor-owned ticket sections and run-state records were written through the prescribed channels.

6. Checker carry: corrected Result-section identity is filesystem/raw-byte SHA256 76fc932823513206a1ca656176140691cad434eac6fcafd9c0245e4fd3cf1252. A fresh judged context must reverify all three invalidated criteria, but Criterion 3 remains structurally UNVERIFIED until the missing executor red/discrimination record is supplied; do not reuse the prior PASS.

## Handoff

[]

