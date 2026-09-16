# Correctness review, pass 1

Status: **complete**, with one unresolved actionable finding that blocks correctness acceptance. No repairs, delegation, source changes, release mutations, external services, or other-arm inspection were performed.

Reviewed snapshot: `<BUNDLE_ROOT>/runs/log-archive/workflow/review-correctness`.
Persistent candidate: sibling `project` directory.
Commit: `0a7fc516fe94417187ee8efa208bf971c07476ff`.
Expected source identity: `7127fda5b79af7fcaeb1b2808cdd9733e0163968a135d460a0cb83953665e2b9`.
All 13 source-manifest file hashes, including the untracked caller note, independently match the frozen candidate. All seven check-evidence hashes and all three benchmark source hashes match; benchmark archive hash matches. Evidence is in `independent_checks.json`.

The reviewer read TASK.md, the entire README.md contract, RUN_CONTEXT.md, brief.md, review-dispatch-plan.md, builder-pass1.md, implementation/tests/benchmark/reference/operations files, final checks and benchmark, and the supplied orch-review primitive plus both guidance Review sections.

## Finding C1 — [P2] Result copying rejects valid nested extras and crashes the CLI

Location: `log_archive.py:185` (the `deepcopy(snapshot.records[position])` call; `main` reaches the same failure at line 200).

The public contract accepts additional JSON fields and requires complete independent caller-owned results without declaring an extra-field nesting restriction. The loader successfully parses a valid record whose extra field has 550 nested arrays, but `deepcopy` consumes multiple Python stack frames per level and raises `RecursionError`. The frozen baseline returns that same record. This is a 1,212-byte input, so the observed failure does not require a large archive or exhausted machine memory. Any search whose returned page includes the record fails in full, and the CLI exits 1 with an unhandled traceback rather than producing the required JSON result. A zero-size page can still succeed, so cache loading/record validation does not surface the limitation before a later result page requests the record.

Reproduce from the review snapshot directory:

```console
python -B ../artifacts/review-correctness/nested_repro.py
python -B ../artifacts/review-correctness/nested_cli_repro.py
```

The first script creates valid UTF-8 NDJSON records in a temporary directory, each with required fields and `extra` equal to `'[' * depth + '0' + ']' * depth`. Its retained `nested_repro.txt` shows baseline success at depths 100, 300, 450, 499, 550, and 800; candidate failure at 499, 550, and 800 on Python 3.14.6. The exact threshold depends on the caller stack; depth 550 is a robust standalone reproduction. `nested_cli_repro.json` retains the process result: exit code 1, empty stdout, and traceback through line 185 ending in `RecursionError: maximum recursion depth exceeded`.

Required outcome: clone every JSON container accepted by the loader without introducing the smaller Python-recursion limit, while preserving independent nested ownership. A nonrecursive JSON-container copy is one bounded solution. Merely catching this exception, skipping the valid record, sharing its nested objects, or changing the published contract would not satisfy the request. Add observable API and CLI coverage with a successfully parsed deep extra structure and verify mutation of its leaf does not affect future results.

Second pass for shared causes: the API exception and CLI traceback are consequences of the same result-copy operation; they are intentionally one finding. No additional high-impact issue was substantiated.

## Evidence and coverage

- `python -B -m unittest discover -s tests -v`: all 15 tests passed in 1.037 seconds; complete output in `public-tests.txt`. `PYTHONDONTWRITEBYTECODE=1` was set, including for subprocesses. This reran the unchanged required discovery suite against the frozen review snapshot.
- `python -B ../artifacts/review-correctness/independent_checks.py`: passed 1,000 deterministic combined-query comparisons against a separate oracle that tokenizes one character at a time with an explicit ASCII alphabet. Cases include Unicode separators and Kelvin/dotted-I boundaries, duplicate tokens, exact case-sensitive filters, year 0001/year 9999, half-open bounds, physical ties, duplicate IDs, zero/large limits and offsets, malformed lines, and nested result mutation. Output in `independent_checks.json`; script retained.
- The same independent script passed 100 complete atomic replacements retaining the original modification timestamp, with equal-size records across versions, and confirmed current-runtime `stat` and `fstat` fingerprints agree. It also checked process CLI success with year 0001 and a limit of `10**100`.
- Reviewed cache synchronization and publication, single-handle reads, permission retry, Windows metadata normalization, POSIX change-time use, path separation/eviction, completed append/truncation, coherent overlapping replacement, timestamp validation, ASCII-before-normalization extraction, stable sorted position filtering, exact totals, and pagination. The existing concurrency suite passed simultaneous first loads/reloads and complete-version replacement checks. No substantiated finding in those mechanisms.
- Reviewed the actual benchmark procedure and retained final report. It uses 30,000 deterministic records, 48 varied identical queries per round, initial untimed warming of both arms, sequential baseline/candidate then candidate/baseline order, and checks all 96 timed answers for equality. Only search calls are timed. The reported totals (baseline 24.632078200 seconds; candidate 0.037121900 seconds) and ratio **663.545729x** recompute exactly from recorded per-query measurements. This satisfies the stated 5x measured workload target independently of the correctness failure. No full performance measurement was rerun concurrently with other reviews.
- Production source is 207 lines with coherent validation/loading/query/CLI responsibilities. The tests use independent temporary directories and verify observable behavior; no oversized-file split or shared-state structural problem was established.

## Missing context and lens risk

No missing task, contract, source identity, test, or benchmark context prevented completion. Dynamic evidence is Windows/Python 3.14.6. Python 3.11 and POSIX were not available as exercised runtimes in this review; static inspection found no obvious incompatible API, and those platform coverage limits remain explicit.

Correctness lens risk for this candidate is **not low while C1 is unresolved**: a documented valid input deterministically fails both public entry points. Scope is otherwise bounded to a local read-only archive tool; no data mutation, new external surface, or broader structural failure was identified. Repair C1, rerun affected acceptance evidence, freeze the revised source, and obtain the prescribed fresh review before a low-risk release decision. This review does not grant release authority.
