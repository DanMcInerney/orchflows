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
| Main install → customize libraries → upgrade using the old installed command → use the new installed CLI | Removed core workflow disappears; all four current names resolve; removed names fail; customized libraries and host configuration survive; doctor succeeds; repeat setup changes no bytes. | A source-tree test can pass while an existing user's installation retains obsolete entrypoints or overwrites their work. |
| Main install → attempt upgrade from a wrong package → use the old CLI | Rejection changes no installed bytes; the old workflow still resolves and host settings are unchanged. | A failed update must leave a usable installation, rather than a partly migrated home. |

The archive is pinned rather than tracking a moving branch during tests. Git and that object must be available; source archives or shallow clones report a skip, not a pass. Fetch repository history before using this test as a release gate. The source export and test homes are automatically removed. Host registration is deliberately disabled; the test must not modify the user's real host setup.

Measured together on this Windows checkout: **5.84 seconds**. These tests also run in normal `unittest discover -s tests`.

## Opt-in native smoke tests

Use an authenticated Claude Code CLI. The runner uses the host's configured model and effort, consumes normal agent usage, and keeps existing user settings/plugins/hooks. It loads frozen package copies for this session only, disables MCP, supplies no authoring history or evaluator expectations, and makes no global plugin registration changes. The brief permits only local work. Tool allowlists reduce available capabilities; they are not a filesystem sandbox.

```powershell
python tests/e2e/run_native_smoke.py --output ../orchflows-smoke-evidence
python tests/e2e/check_native_smoke.py ../orchflows-smoke-evidence/routing ../orchflows-smoke-evidence/composition ../orchflows-smoke-evidence/missing-review
```

Supply `--claude /path/to/claude` if needed. The output directory must be new and outside the checkout. All three cases run concurrently. Each has a **180-second deadline**, including startup; timeout terminates its local process tree and records failure. `--case composition` runs just that case. No model or effort override is introduced to make timings look better. These paid tests are excluded from ordinary unittest discovery.

| Case | Ordinary input and capability | Required result |
| --- | --- | --- |
| Routing | An arithmetic file-writing request, with final core loaded and native delegation available. | Correct file; four current core commands registered; no removed command; no skill invocation or agent launch. One observation cannot prove universal absence of automatic routing. |
| Composition | Explicitly invoke a fixture plugin by name; it composes a second procedure and core review/revision. A correct invoice needs a required Python check and a separately styled public summary. | One root-owned fresh reviewer; completed judgment; no candidate change or gratuitous repair; observed successful check with matching hash; internal and public outputs preserve their different guidance. |
| Missing review | Explicitly invoke core review/revision on an incorrect invoice; expose only Read, Write, Edit and Skill, with no native agent, shell or MCP execution. | Preserve the incorrect invoice; disclose missing independent review and blocked repair; neither fabricate a verdict nor treat the request to repair as permission to skip review. |

The [fixtures](fixtures/) contain tasks and source material, not model-facing answer keys. The [checker](check_native_smoke.py) holds the expected results separately. It checks exact input/package hashes, output values, actual host inventory, native calls and child discovery through the existing history CLI. It rejects timeouts, incomplete evidence and the observed unauthorized repair. The checker never equates a successful model exit with workflow success.

**Finish with a short evidence audit.** Read the actual reviewer assignment, review, handoff and native tool effects. Confirm applicable guidance reached the reviewer, the author did not certify itself, no child delegated through another route, and the gap report says what really happened. For composition, distinguish check evidence on unchanged bytes from independent acceptance; a check may legitimately precede review when no repair changes those bytes. For the negative case, arithmetic inspection may continue, but the dependent repair may not. The checker reports mechanical success separately from this audit; it does not judge arbitrary prose or infer all file mutations from tool names.

Keep `before.json`, `request.txt`, `events.jsonl`, `result.json`, `history.json`, packages and outputs together. Native history retains the detailed reviewer trace; inspect it before native logs expire. The cached history summary alone does not preserve every assignment/tool argument. Snapshots, rather than a Git SHA alone, identify the actual tested bytes when the checkout is dirty.

## Observed results, 2026-09-18

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
