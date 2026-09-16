# Data review — pass 2

Status: **complete**. Actionable high-impact findings: **none**. The data-lens risk is **low for the documented local read-only archive workload and update model**, subject to the coordinator joining the other reviews and release prerequisites. This report does not authorize release.

## Frozen artifact

Persistent candidate: <BUNDLE_ROOT>/runs/log-archive/workflow/project

Isolated review snapshot: <BUNDLE_ROOT>/runs/log-archive/workflow/review-data-p2

Commit: `a685f46be6b9b755f8fe806556626bf34530d4b9`.

Source SHA-256: `431ec53dea8ab857e9aad7b298934d90fa6db497e693e9bb893e074ec69ce4cf`.

All 14 manifest file hashes matched the isolated snapshot before and after targeted checks. Final verification also matched every persistent-candidate file to the same manifest. Git status retained only the intentional untracked caller-note.txt. Evidence: [final-identity.json](final-identity.json). No source edits, repairs, delegates, release mutations, external services, other build arms, or held-out evaluation inputs were used.

Read and applied the supplied orch-review primitive, then the Review sections of core guidance/code.md and example-workflows/software-factory/guidance/software-delivery.md in that order. Read TASK.md, the entire README.md contract, RUN_CONTEXT.md, architecture, brief, joined pass-one review, builder pass-two report, prior data/correctness reports and reproductions, final manifest/check evidence/preservation/tests/benchmark data, implementation, baseline, repair patch, new deep tests, operating documentation and benchmark procedure. The supplied core root directly contains skills/ and guidance/; the initial redundant core/ lookup was corrected. The full public contract is README.md; no separate fullREADME.md exists or is needed.

## C1 and independent deep/broad checks

The previous shared cause was recursive result copying. In log_archive.py:163, `_copy_record` now shallow-copies each JSON dictionary/list and walks child containers using an explicit stack. Every nested container gets a new owner while immutable JSON scalars retain their values. This requires no cycle handling because parsed JSON forms a tree; no record is skipped, no recursion limit is changed, and no cached container is returned directly. The call at line 200 uses this copy only for the selected page.

The fresh independent [deep_broad_checks.py](deep_broad_checks.py) exercised six structures: list, dictionary and alternating mixed spines at depths 550 and 800, with broad list/dictionary side branches at every level. Each archive contained two duplicate complete records. Each item had 12,655 mutable containers at depth 550 or 18,405 at depth 800. Iterative whole-tree signatures matched baseline output, including every key, scalar type/value, dictionary/list shape and empty container. Container identity sets were disjoint between duplicates and separate API calls. Every mutable container in one returned item was mutated; the other duplicate, a previously obtained independent result, and subsequent searches remained unchanged. All six CLI calls exited 0, emitted complete parseable equivalent JSON, and had empty stderr. Archive hashes remained unchanged. This independently supports that C1 is resolved across deep and broad trees, beyond the builder's deep-leaf regression tests.

Evidence: [deep-broad-raw.txt](deep-broad-raw.txt), [deep-broad-checks.json](deep-broad-checks.json). Commands, from the isolated snapshot with PYTHONDONTWRITEBYTECODE=1:

```console
python -B ../artifacts/review-data-p2/data_checks.py
python -B ../artifacts/review-data-p2/deep_broad_checks.py
python -B -m unittest discover -s tests -v
```

All passed. The unchanged discovery suite ran **17 tests in 1.320 seconds**, exit 0, including API/CLI deep-result regressions, concurrent cold loads and reloads, completed updates, and replacement between stat and open. Raw output: [public-tests.txt](public-tests.txt).

## Full data contract and freshness

The prior independent data script was read, adapted only in this outside-source evidence directory to the pass-two manifest/output location, and rerun against this final artifact. All six groups passed; the retained source and raw/structured results are [data_checks.py](data_checks.py), [data-checks-raw.txt](data-checks-raw.txt), and [data-checks.json](data-checks.json).

- Schema/calendar checks used 50 invalid lines plus five valid records, covering malformed/nonobject input, required fields/types/empty strings, valid year extremes, invalid calendar dates and timestamp formats, leap years, complete extras, duplicate IDs/records, physical-order ties, and half-open bounds.
- A deterministic direct oracle checked 350 varied queries over 500 records, including ASCII token matching and Unicode separators, exact filters, bounds, totals, ordering and huge/zero pagination values. Ordinary nested mutation and outer result mutation did not affect later results.
- Twenty archive paths exceeded the eight-entry cache, with 60 interleaved reads. Every path then underwent completed append, truncation, rewrite, and same-size atomic replacement preserving the exact old modification timestamp; each next search reflected the completed operation.
- Eight readers made 2,400 searches while a writer completed 150 equal-size atomic replacements preserving modification time. Every result matched a complete 150-record old or new version. Every completed replacement received an immediate freshness check. All 2,400 reader results were independently mutated without contaminating subsequent reads.
- Durable archive hashes were unchanged by searches. Final candidate/snapshot source identity was unchanged.

Static inspection supports these observations: a read-only single file handle supplies each version; validation precedes indexing; stable chronological sorting preserves physical ties and duplicates; file identity participates in every freshness check; cache publication/eviction is locked; published snapshots remain private; result copying owns each mutable container. The repair did not modify indexing, fingerprints or cache synchronization. There is no persistent data index, migration, rewrite, deletion or backfill. Discarding the process-local cache or reverting the implementation requires no archive-data recovery.

## Supplied evidence and risk

The review verified all **21 supplied evidence hashes**, benchmark source hashes and retained archive hash against the final artifact. The benchmark implementation uses the same 30,000-record archive and 48 varied queries per paired round, initial untimed warming, sequential arms, alternating order, and equality checks for all 96 timed answers. Recorded per-query timings recompute to **262.473429x** total warmed throughput, independently of correctness. No full benchmark was rerun during concurrent reviews. These verifications are included in deep-broad-checks.json.

Findings were enumerated and a second pass checked shared causes across schema/ordering, mutable ownership, path fingerprints/eviction, and snapshot publication. No evidence-backed high-impact contract violation remained. The source and tests have coherent bounded responsibilities; no structural split or test-order coupling was substantiated.

Missing required context: **none** for this data review. Executed evidence is Windows/Python 3.14.6; Python 3.11 and POSIX were not executed. The JSON parser's own resource limits were not expanded by this repair. Concurrent partial in-place writes remain outside the explicit public contract. Documented memory growth with retained records/postings and large-page copying remains a capacity characteristic, with no durable mutation or irreversible data operation. The coordinator retains the joined-risk and release decisions.
