diff --git a/README.md b/README.md
index 8db8ae0..cd01c2f 100644
--- a/README.md
+++ b/README.md
@@ -1,4 +1,4 @@
-# Support log archive starter
+# Support log archive
 
 Python 3.11+; standard library only. Run from this directory:
 
@@ -7,7 +7,7 @@ python -m unittest discover -s tests -v
 python log_archive.py --file sample.ndjson --query "gateway timeout" --limit 10
 ```
 
-The starter delegates to a deliberately slow, complete full-scan implementation. `baseline_reference.py` is a frozen reference; leave it unchanged. Implement the production API and CLI in `log_archive.py` (additional modules are allowed).
+`log_archive.py` provides the production API and CLI using a reusable in-process index. `baseline_reference.py` is the frozen full-scan reference; leave it unchanged.
 
 ## Python API
 
@@ -42,3 +42,31 @@ Correctness checks cover the contract above with held-out data: tokens, punctuat
 Performance uses a deterministic 30,000-record UTF-8 archive, varied token/filter/time/pagination queries, an untimed initial search for warming, and two sequential paired rounds against the pristine full-scan baseline. Both arms receive identical queries; round order alternates baseline/candidate then candidate/baseline. The reported throughput ratio is total baseline query time divided by total candidate query time. All timed answers must also be correct. The target is at least 5x; a speed result never overrides failed correctness. Setup and initial warming are excluded. The public check is `python -m unittest discover -s tests -v`; include a reproducible benchmark command and record measured results in your handoff.
 
 The shared run context supplies the local release simulator and policy for contract `log-archive`. Follow its staged checks, observations, hold/rollback rules, and evidence requirements. Do not claim live production deployment.
+
+## Operation and verification
+
+Reuse the Python API in a long-lived process to benefit from warm searches. Each process keeps up to eight recently used archive snapshots. The first search and every detected file change rebuild the affected index; there are no sidecar files or invalidation calls. One-shot CLI invocations each build a fresh index. CLI JSON uses ASCII escapes so Unicode records survive legacy terminal encodings unchanged after JSON decoding.
+
+Snapshots contain complete records in stable timestamp order and inverted indexes for message tokens, service and level. Every call checks device, file identity, size and nanosecond modification time (plus change time on POSIX). This detects completed appends, truncations and atomic replacements, including replacements with preserved size/mtime. Loads read one opened file version and publish a completed snapshot under a lock; active queries retain their existing snapshot. Returned records are deep copies. Windows sharing conflicts get bounded retries before an OS error propagates.
+
+Memory grows with archive size and token memberships; the eight-file cache bounds file count, not bytes. Rebuilds are serialized, including across archive paths, while searches use snapshots outside the lock. A rebuild can temporarily retain both old and new versions. Concurrent partial in-place writes remain outside the public contract. Local filesystems must expose stable file identity and fresh metadata; network filesystem cache semantics have not been validated.
+
+Run correctness and the reproducible benchmark separately:
+
+```console
+python -m unittest discover -s tests -v
+python benchmark.py --output ../artifacts/benchmark.json
+git diff --check
+```
+
+The benchmark generates 30,000 deterministic records, warms both implementations, then times the same 24 varied queries in two sequential paired rounds: baseline/candidate, then candidate/baseline. It compares every timed answer outside the timed loops and reports correctness separately from total baseline time / total candidate time. Both correctness and the 5x target must pass. `--records` is available for exploration; acceptance uses the default 30,000. Save stdout/stderr and failed attempts outside the source directory.
+
+## Local release and handoff
+
+Read `RUN_CONTEXT.md` and its shared policy before releasing. This change only reads local archives and builds process-local indexes; it has no migrations, external writes, network calls or new dependencies. Classify risk for the specific environment; the supplied isolated `log-archive` simulation permits unattended low-risk release after checks and self-review pass. High or unknown risk requires a handoff.
+
+Before the first stage, save the baseline simulator status, successful check output, benchmark results, review findings and candidate file hashes. Keep the candidate directory persistent and stop editing its source. Use only the supplied simulator/state file; never reinitialize or edit state directly. Have its `rollback --reason ...` command ready to restore the recorded baseline.
+
+Deploy at 10%, then 50%, then 100% only after three consecutive healthy observations at the preceding stage. Observe every stage. Each synthetic observation must have error rate <=1% and p95 <=200 ms. On any breach, stop, invoke rollback, then observe once to verify recovery. The supplied simulation deliberately breaches at 50%; a correct exercise ends rolled back, not fully released. These observations are synthetic ten-second windows, not elapsed real monitoring or live traffic.
+
+Write the actual final exposure, operation IDs, signals, candidate identity, check commands, failed checks and repairs, benchmark ratio, residual risks and remaining decisions in `../artifacts/HANDOFF.md`; write the required machine-readable result beside it. Preserve raw output and the caller-owned note. A stopped rollout needs a new authorized decision before any future release attempt.
