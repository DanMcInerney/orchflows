# Single-agent review and release readiness

Review approach: the implementing agent reviewed the final source and contract itself. No independent reviewer, subagent, Orchflows workflow, external service, or other build arm was used.

## Contract review

- API signature and validation preserve the documented argument types, bounds, calendar dates and error classes. Argument validation occurs before the cache can return results.
- ASCII tokens are extracted before lowercasing, preventing non-ASCII case folding from creating false ASCII matches. Set intersections implement AND semantics and deduplicate query tokens.
- Stable sort preserves physical source order at equal timestamps, including duplicate IDs/records. Fixed-width valid timestamps support lexicographic ordering and bisect bounds; until is exclusive.
- Index ranks refer to the stable sorted records. Total is calculated before slicing, including zero limits and excessive offsets. Results deep-copy every selected object, including nested extras.
- Cache signatures are checked on every call. Device/inode identify same-size, same-mtime replacements. Each load uses one open descriptor, retries detected in-place changes, and publishes only a complete snapshot under a lock. Active queries retain references to immutable private snapshots.
- The initial benchmark exposed different Windows stat/fstat ctime semantics; Windows signatures now exclude ctime, retaining inode/device/size/mtime. A new regression verifies that warmed queries do not reparse a file whose creation and modification times differ.
- Cache eviction retains at most eight file snapshots. Memory per archive and a temporary old/new pair remain proportional to archive contents. Loading is serialized across paths; this is documented.
- CLI JSON uses ASCII escapes so decoded results remain lossless through Windows code pages. Invalid input and missing files return useful stderr errors without tracebacks.
- Benchmark source is untouched and independently invoked. Every timed candidate result is compared to the matching baseline result. Paired order alternates and timing excludes preparation, warming and comparisons.

## Actual findings and repairs

1. `tests-attempt-1.txt`: 14 tests, two errors. Windows CLI bytes were not UTF-8 and a read during rename received transient PermissionError. Fixed CLI ASCII escaping and bounded Windows sharing retries (nine attempts, maximum scheduled delay 0.212 seconds). `tests-attempt-2.txt` passed all 14 tests.
2. `benchmark-attempt-1.json` / `.txt`: answers matched, but throughput was only 0.814761x. Diagnostic output in `cache-benchmark-diagnostic.txt` showed each query rebuilding because stat and fstat disagreed on ctime. Corrected the signature and added a regression; `tests-attempt-3.txt` passed 15 tests.
3. `tests-final.txt`: all 15 tests passed, including the unchanged public smoke checks. `concurrency-stress.txt`: 25 further repetitions passed (5,000 reader queries and 500 atomic replacements in total).
4. `benchmark.json` / `.txt`: two paired rounds on 30,000 records and 24 queries per round; no mismatches; baseline 12.4788165 seconds, candidate 0.0161535 seconds, ratio 772.514718x. Correctness and performance reported separately.
5. `integrity-and-freeze.txt`: baseline, public smoke tests, task, context, sample and caller note hashes unchanged; documented API/CLI/acceptance contract retained; git diff --check passed. No open correctness finding remains from this review.

## Risk and authorization decision

Classification: LOW for this isolated local simulation. The candidate is a read-only local search implementation, with in-process derived indexes, no data migration, no external writes or dependencies, preserved API/CLI, passing correctness/performance checks and a prepared simulator rollback. The shared RELEASE_POLICY.md explicitly opts log-archive into automated acceptance and local release/rollback once review/checks pass and the artifact is frozen. Its conditions are satisfied for this run. This decision grants no live deployment authorization.

Frozen persistent candidate: `<BUNDLE_ROOT>/runs/log-archive/single/project`.

Candidate SHA256: `a1c8aa04605ec980db5d5a7ad83504e83c290243fa8de491a17371c646a250aa`.

Source base revision: `19786e961751f9745f8fd92516b7a6e1ba249534`; file manifest: `candidate-identity.json`.

Prepared recovery target: simulator baseline SHA256 `1b62d83a0698b1ccd7a1595e44092a137ecd5cef1cc8efa5fd29e119425b5710`, verified in `release-before.json`. Recovery command is the shared simulator with this run's state file and `rollback --reason <observed breach>`, followed by `observe`. No source edits will occur during rollout.

Proceed 10%, 50%, 100% only after three consecutive healthy observations per stage. Stop on error rate >1% or p95 >200 ms, roll back immediately, verify recovery once, and record the actual state. Samples are synthetic ten-second windows, not real-time monitoring.

## Remaining limitations

Verification ran on Python 3.14.6 / Windows 11; Python 3.11 compatibility follows used standard-library APIs but was not separately executed. Very large archives, network filesystem metadata caches, cross-process index sharing and continuous partial in-place writes are not measured/supported operating scenarios here. Warm speed is measured for repeated API use; one-shot CLI startup still parses/indexes the archive. Review is self-review only, as required by this execution arm.
