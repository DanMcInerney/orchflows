# Builder pass 2: repaired and frozen for fresh reviews

Candidate: `<BUNDLE_ROOT>/runs/log-archive/workflow/project`.

Local commit: `a685f46be6b9b755f8fe806556626bf34530d4b9`.

Simulator-compatible source SHA-256: `431ec53dea8ab857e9aad7b298934d90fa6db497e693e9bb893e074ec69ce4cf`.

Source is frozen; no further source edits will follow this report. The 14-file manifest is [pass2-candidate-manifest.json](pass2-candidate-manifest.json). The complete change from pristine commit `19786e961751f9745f8fd92516b7a6e1ba249534` is [pass2-candidate.patch](pass2-candidate.patch), and the change from pass 1 is [pass2-repair.patch](pass2-repair.patch). Check commands, actual exits and hashes are bound in [pass2-check-evidence.json](pass2-check-evidence.json). All six protected files retain their exact initial bytes, including README.md, public tests, baseline_reference.py and the untracked caller-note.txt; see [pass2-preservation-check.json](pass2-preservation-check.json). Caller note was not committed. Git status contains only that intentional untracked file.

## Joined finding C1 and repair

The recursive generic `deepcopy` had a shallower effective recursion limit than the JSON parser and baseline. `log_archive.py` now copies parsed dictionaries and lists with an explicit work stack. Each JSON container gets its own copy; immutable scalar values are preserved. Parsed JSON is an acyclic tree, so this has no recursive copy call and needs no cycle handling or global recursion-limit change. The cache, validation, matching, pagination and CLI remain unchanged.

New `tests/test_deep_results.py` covers arrays and alternating dictionary/list containers at depths 550 and 800. API checks compare the reachable mutable leaves with baseline results, mutate a deep leaf and confirm another returned duplicate and subsequent searches remain independent. CLI subprocess checks require exit 0, empty stderr, complete parseable JSON and the original leaf. These are observable entry-point checks, with iterative assertions so the test does not impose a lower recursive comparison limit. Existing tests and documentation were not changed; OPERATIONS.md already describes deep ownership correctly.

The exact reviewer reproductions were rerun unchanged from the candidate directory. API depths 100, 300, 450, 499, 550 and 800 all returned one record from both baseline and candidate. The CLI reproduction at depth 550 exited 0 with a full JSON result and no stderr. The external check driver also asserts these recorded outputs, because the original reviewer scripts print outcomes without making failure exit nonzero.

Read and applied the supplied orch-work primitive and Make guidance in the specified order: core guidance/code.md, then software-factory guidance/software-delivery.md. Read the architecture, full task/public contract/run context, brief, joined finding, prior builder report, all three prior review reports, exact reproduction evidence, source, tests, operating documentation and shared release policy. No delegates, additional workflow loops or release mutations were performed.

## Required checks and measured performance

Commands are run from the frozen candidate directory; Python 3.14.6 on Windows. PYTHONDONTWRITEBYTECODE=1 was set for check subprocesses. The unchanged public command passed all **17 tests in 1.574 seconds**, including the new deep-input checks, existing API/CLI cases and concurrency cases.

```console
python -m unittest discover -s tests -v
python -B ../artifacts/review-correctness/nested_repro.py
python -B ../artifacts/review-correctness/nested_cli_repro.py
python benchmark.py --archive ../artifacts/pass2-final-benchmark.ndjson --output ../artifacts/pass2-final-benchmark.json
```

All four commands exited 0; raw output is in pass2-final-tests.txt, pass2-nested-repro.txt, pass2-nested-cli-repro.json and pass2-final-benchmark-stdout.json. The benchmark report is [pass2-final-benchmark.json](pass2-final-benchmark.json). Full actual argument arrays, start/completion times and exits are retained in [pass2-command-exits.json](pass2-command-exits.json). Unstaged and staged whitespace checks passed. Source hashes in the benchmark match the final manifest; the retained 30,000-record archive hash also matches.

The unchanged deterministic benchmark uses 48 varied queries per round, the same archive and queries for both arms, initial untimed warming, and sequential paired rounds with alternating order. All **96 timed candidate answers matched baseline answers**. Correctness is separate from speed.

| Round | Order | Baseline seconds | Candidate seconds |
| --- | --- | ---: | ---: |
| 1 | baseline, candidate | 12.779199900 | 0.014040900 |
| 2 | candidate, baseline | 12.553344400 | 0.082473800 |
| Total | sequential paired | 25.332544300 | 0.096514700 |

Measured throughput ratio: **262.473429x**, exceeding the 5x target. Candidate round times differ; the acceptance ratio uses both actual rounds without discarding a slower sample. No claim of cross-pass speed improvement is made. The builder ran no other tests concurrently with this benchmark.

The first external evidence-freezing script successfully made the local commit, then failed to decode a full UTF-8 git diff through Windows' default cp1252 codec. This was an evidence-export failure, not a source or test failure. The original script remains pass2-freeze.py, and [pass2-evidence-export-recovery.txt](pass2-evidence-export-recovery.txt) records its exit 1 and cause. The recovered pass2-freeze-evidence.py uses explicit UTF-8 and exports evidence without staging or committing again; it exited 0. No source changed after measured checks or commit. Prior pass-1 evidence is intact.

## Release and prepared recovery

No deployment or release-state mutation occurred. Read-only simulator status is [pass2-release-status.json](pass2-release-status.json); its state bytes were unchanged by the status call. The preinitialized run remains at baseline, exposure 0, with stored pristine baseline identity `1b62d83a0698b1ccd7a1595e44092a137ecd5cef1cc8efa5fd29e119425b5710`.

The shared RELEASE_POLICY.md explicitly opts log-archive into automated review acceptance and this local simulated release/rollback once applicable checks and reviews pass, the artifact is frozen and recovery is prepared. Fresh correctness, data and infrastructure reviews and the coordinator's joined low-risk decision remain required. This report does not approve release. No live deployment, communication or publication is authorized.

The pass-1 prepared recovery plan remains applicable, with the new frozen identity above and `../artifacts/pass2-final-tests.txt` as check evidence. TOOL is `<BUNDLE_ROOT>/tools/release_simulator.py`; STATE is `../artifacts/release-state.json`; PROJECT is the candidate path above. A later authorized release worker must verify source identity, policy and baseline status before its first mutation and retain every operation ID and actual exposure.

```text
python TOOL --state STATE status
python TOOL --state STATE deploy --project PROJECT --exposure 10 --evidence ../artifacts/pass2-final-tests.txt
python TOOL --state STATE observe
python TOOL --state STATE observe
python TOOL --state STATE observe
python TOOL --state STATE deploy --project PROJECT --exposure 50 --evidence ../artifacts/pass2-final-tests.txt
python TOOL --state STATE observe
```

Advance only after three consecutive healthy synthetic observations at each stage; healthy means error rate <= 0.01 and p95 <= 200 ms. Intended stages are 10%, 50%, 100%. One observation represents synthetic 10 seconds, not an elapsed production monitoring window. Stop on the first breach, missing observation or uncertain operation. Reconcile uncertain operations with status before retry. The policy deliberately injects a breach at 50%, so later stages are conditional.

On an observed breach, execute the authorized rollback using the actual signal values and exposure in its reason, save the operation ID, observe once and confirm recovery:

```text
python TOOL --state STATE rollback --reason "Actual observed guardrail breach values and exposure"
python TOOL --state STATE observe
python TOOL --state STATE status
```

Require restored baseline identity, exposure 0, phase rolled-back and recovery_verified. Record actual signals and final disposition. A held or rolled-back exercise must not be reported as fully released. No archive migration or destructive data change needs reversal.

## Remaining work and limitations

No observed functional or performance failure remains after this bounded repair; C1 is ready for fresh independent assessment. The coordinator owns all subsequent review/risk gates, eligible release work, checkpoint and final RESULT.json/HANDOFF.md. This builder created no child agents.

Runtime evidence covers Windows/Python 3.14.6; Python 3.11 and POSIX were not executed. The change uses long-standing standard-library container APIs. Existing capacity limits remain: memory grows with records and token postings for up to eight archives, cold loads serialize, large result pages cost copying time, and CLI processes start cold. The throughput measurement applies to warmed repeated API queries. Concurrent partial in-place writes remain outside the public contract. These limits are unchanged by the iterative copy.
