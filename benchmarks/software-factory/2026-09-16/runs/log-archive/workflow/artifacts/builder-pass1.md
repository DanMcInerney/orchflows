# Builder pass 1: frozen candidate, ready for independent review

Candidate: `<BUNDLE_ROOT>/runs/log-archive/workflow/project`

Commit: `0a7fc516fe94417187ee8efa208bf971c07476ff` (local only).

Simulator-compatible source identity: `7127fda5b79af7fcaeb1b2808cdd9733e0163968a135d460a0cb83953665e2b9`.

The complete per-file manifest is [pass1-candidate-manifest.json](pass1-candidate-manifest.json); the reproducible change from pristine commit `19786e961751f9745f8fd92516b7a6e1ba249534` is [pass1-candidate.patch](pass1-candidate.patch). Source is frozen. No edits will follow this handoff. Only `caller-note.txt` remains untracked, intentionally; its exact original bytes are preserved and it was not committed. All six protected baseline files (including README.md and public tests) are byte-for-byte unchanged; see [preservation evidence](pass1-preservation-check.json).

## Implementation

- `log_archive.py` owns validation, private snapshot loading, indexed query matching, result copying and JSON CLI. ASCII words are extracted before case normalization. Stable chronological sorting retains physical ties and duplicate records. The complete original objects are kept and returned as independent deep copies.
- A synchronized eight-entry process-local cache checks device/file identity, size, mtime and a platform-consistent extra timestamp on every call. Windows uses birthtime when available (zero fallback on older Python); POSIX uses ctime. One file handle provides each snapshot; publication is atomic and readers never modify it. Permission contention caused by Windows rename replacement has a bounded retry. OS path resolution is preserved for actual reads; absolute normalization is only used for cache keys.
- `tests/test_contract.py` and `tests/test_concurrency_cli.py` cover malformed input, timestamps/calendar extrema, token boundaries/punctuation/Unicode separators, exact filters, stable ties/duplicates, nested mutation, pagination and errors, separate paths/eviction, append/truncate/preserved-mtime replacement, simultaneous first load/reload, replacement during stat/open, concurrent complete-version reads, and process-level CLI success/help/errors.
- `benchmark.py` generates the deterministic 30,000-record archive, 48 varied queries and two sequential paired rounds. Both arms receive the same file and query list; all timed answers are compared. `OPERATIONS.md` documents use, verification, cache scope, measurement and recovery. The public README contract is untouched.

## Required checks and measurements

Run all commands with the candidate project as current directory.

```console
python -m unittest discover -s tests -v
python benchmark.py --archive ../artifacts/pass1-final-benchmark.ndjson --output ../artifacts/pass1-final-benchmark.json
```

The unchanged public discovery command passed all 15 tests in 1.406 seconds on Python 3.14.6 / Windows. Raw output: [pass1-final-tests.txt](pass1-final-tests.txt). This includes CLI success, help and useful nonzero error exits without traceback. The final benchmark exited 0 and every one of the 96 timed candidate answers equaled the full-scan baseline. Raw report: [pass1-final-benchmark.json](pass1-final-benchmark.json), with [stdout](pass1-final-benchmark-stdout.json). Its source hashes match the frozen manifest.

| Round | Order | Baseline seconds | Candidate seconds |
| --- | --- | ---: | ---: |
| 1 | baseline, candidate | 13.263616700 | 0.017333300 |
| 2 | candidate, baseline | 11.368461500 | 0.019788600 |
| Total | sequential paired | 24.632078200 | 0.037121900 |

Measured warmed throughput ratio: **663.55x**, exceeding the 5x target. Setup and one full initial search per arm were untimed; equality checks and report serialization were untimed. The final measurement ran without the builder's other test workload concurrently. Throughput is reported separately from correctness and is specific to this measured workload. [pass1-check-evidence.json](pass1-check-evidence.json) binds commands, status, benchmark hashes and evidence hashes to the exact commit and manifest.

## Actual failures and repairs before freeze

The first expanded race test exposed a transient Windows `PermissionError` when opening during atomic replacement. It is retained in [pass1-contract-tests.txt](pass1-contract-tests.txt); the bounded sharing retry fixed it. Ten repeated concurrency/CLI runs on the metadata-corrected implementation passed ([pass1-final-concurrency-repeats.txt](pass1-final-concurrency-repeats.txt)); the exact final bytes were subsequently tested again by the full suite above.

The first benchmark compared all answers correctly but achieved only 0.666x: this Python/Windows runtime reports deprecated `st_ctime_ns` differently through `stat` and `fstat`, preventing cache hits. Platform-consistent timestamp selection fixed it. The failed attempt remains in [pass1-initial-benchmark-failed.json](pass1-initial-benchmark-failed.json). Intermediate passing measurements are separately retained; only `pass1-final-benchmark.json` is acceptance evidence for the frozen bytes. Final source whitespace was normalized before the final checks, and `git diff --check` and staged diff checks passed. No public check was weakened.

## Concrete rollout and rollback plan

Builder release actions: **none**. A read-only simulator `status` snapshot is [pass1-release-status.json](pass1-release-status.json): phase `baseline`, exposure 0, pristine baseline identity `1b62d83a0698b1ccd7a1595e44092a137ecd5cef1cc8efa5fd29e119425b5710`. The state is preinitialized; do not reinitialize or manually edit it.

The shared policy opts this log-archive exercise into automatic review acceptance and local simulated release/rollback only after all checks and applicable independent reviews pass, the candidate is frozen and software-delivery's low-risk conditions hold. The coordinator must complete correctness, data and infrastructure reviews and risk routing. No publication or live deployment is authorized. There is no data migration or archive modification to undo.

Let TOOL be `<BUNDLE_ROOT>/tools/release_simulator.py`, STATE be `../artifacts/release-state.json`, PROJECT be the absolute frozen candidate above, and CHECKS be `../artifacts/pass1-final-tests.txt`.

```text
python TOOL --state STATE status
python TOOL --state STATE deploy --project PROJECT --exposure 10 --evidence CHECKS
python TOOL --state STATE observe
python TOOL --state STATE observe
python TOOL --state STATE observe
python TOOL --state STATE deploy --project PROJECT --exposure 50 --evidence CHECKS
python TOOL --state STATE observe
```

Before mutation, verify the source identity above, unchanged policy, baseline state, stored rollback identity, available observation/rollback commands, and check/review gates. Persist every operation ID and its actual exposure before advancing. Require three consecutive healthy synthetic observations at each stage: error rate <= 0.01 and p95 <= 200 ms. Each observation represents synthetic 10 seconds, not wall-clock production monitoring. Stage order is 10%, 50%, 100%; advancement stops at the first breached signal or unavailable observation. The policy deliberately injects a breach at 50%, so do not blindly execute later stages.

On the first observed breach, execute the already-authorized recovery:

```text
python TOOL --state STATE rollback --reason "Observed error rate/p95 values breached the policy threshold at the recorded exposure"
python TOOL --state STATE observe
python TOOL --state STATE status
```

Use the actual numeric values and operation IDs in the rollback reason/evidence. Confirm restored exposure 0, phase `rolled-back`, and a healthy recovery observation with `recovery_verified`. Record rollback identity, remaining decisions and that these are synthetic signals. A missing signal means hold; an uncertain operation must be reconciled with status before retry. A rolled-back exercise must be reported as rolled back, never fully released.

## Risks, limits and remaining work

The change is bounded to a local read-only archive API/CLI and adds no dependency, network surface, authorization change, destructive operation or contract change. Recovery is supported by the supplied simulator. This supports a prospective low-risk classification, but independent reviews are still required and the builder does not grant its own approval.

Runtime evidence is Windows/Python 3.14.6; Python 3.11 and POSIX were not exercised in this run. The implementation uses 3.11-compatible standard-library APIs; those environments need static compatibility review and can run the same suite. Cache memory grows with valid records and token postings for up to eight archives, and cold loads serialize. Large result pages cost deep-copy time. CLI processes start cold, so the measured repeat-query throughput applies to long-lived API processes. Simultaneous partial in-place writes are outside the public contract. Ordinary persistent resource/permission errors propagate.

No unresolved functional failure remains in observed required checks. Remaining work belongs to the coordinator: independent reviews, joined risk decision, eligible fresh release worker, final outcome/handoff and RESULT.json. This builder created no delegates and performed no release mutation.
