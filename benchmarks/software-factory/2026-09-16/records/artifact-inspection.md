# Artifact inspection beyond black-box scores

This is a scoped inspection by the experiment coordinator, who did not implement the candidates. It is not a complete security audit. No findings are sent back for post-evaluation repair. The same checklist applies to both approaches.

## Webhook workflow candidate

Inspected `runs/webhook-inbox/workflow/project/inbox.py`, `inbox_store.py`, `README.md` and `RELEASE_HANDOFF.md` after its pass-1 freeze.

- HMAC signatures and bearer credentials use `hmac.compare_digest`; signature input includes exact timestamp and raw body bytes. Validation and authentication precede storage mutation.
- SQLite persists raw bodies as BLOBs and exact event IDs. A `(tenant, event_id)` uniqueness constraint and immediate transaction enforce idempotency. SQL values are bound parameters, including tenant filters on reads.
- Routine request logging is disabled and application error responses use fixed messages. This source inspection found no routine path that logs credentials; it does not prove secrecy under every possible runtime failure.
- Application imports are standard-library modules plus its own storage module. No external service or package dependency was introduced.
- Operating documentation covers startup/configuration, signing, paging, retries, storage/backup, tests, mandatory human review, and limits of the HTTP server. Release documentation accurately says no deployment occurred and explains why restoring an old database can lose accepted events.
- The completed patch verification records clean application and reconstructed content equality (Git line-ending normalization only). Final audit verifies all 12 source-file hashes and preserved policy, public tests, fixture config and caller note. Independent collection confirms the task/context/note hashes, no release mutation and no source mutation during grading.
- Corrected external evaluation passed 28/28. A separately recorded evaluator connection-cleanup defect caused the first run's teardown error; no application source was repaired between runs.
- A separate coordinator audit applied the delivered patch to a fresh copy of the common starter and reproduced the complete candidate, allowing text line-ending normalization only. Raw commands are in `results/webhook-inbox/workflow/patch-audit/result.json`.

## Log workflow pass-2 candidate

Inspected `runs/log-archive/workflow/project/log_archive.py`, unchanged public `README.md`, and `OPERATIONS.md` after its pass-2 freeze at commit `a685f46be6b9b755f8fe806556626bf34530d4b9`.

- The implementation uses only standard-library modules and performs read-only archive access. It stores private process-local snapshots and replaces them as a unit under a lock. File identity, size and timestamps are checked on calls; same-size preserved-mtime replacement is distinguished by file identity.
- Search uses token/filter indexes and chronological positions; stable sorting preserves source order for ties. An iterative container copy returns independent nested JSON objects, replacing the recursive-copy defect identified during pass 1.
- Operating documentation explicitly distinguishes warmed API throughput from cold CLI startup, documents cache memory and file-change behavior, gives reproducible test/benchmark commands, and describes the synthetic release exercise accurately.
- Independent collection verifies all eight release checks, including halted advancement, baseline restoration and recovery at zero exposure. External evaluation passes 31/31 assertions and measures 374.70x warmed throughput. This inspection does not add the review-discovered nesting example to the fixed external score.
- **Delivered patch defect:** `pass2-candidate.patch` fails direct `git apply --check` against the pristine starter. Its entire exported text uses CRLF, including context for an LF baseline. A separate diagnostic copy normalized to LF applies and exactly reconstructs the candidate; the original patch and application code remain unchanged. This is a handoff-artifact defect, separate from the application's fixed external score. Evidence: `results/log-archive/workflow/patch-audit/result.json` and `line-ending-diagnosis.json`. The candidate's persistent Git commit remains usable.

## Webhook single-agent candidate

Inspected the final `inbox.py`, README and completed handoff. The same scoped source checklist finds standard-library-only imports; `hmac.compare_digest` for signatures and bearer credentials; validation/authentication before mutation; exact body BLOB storage; tenant/ID uniqueness; immediate transactional idempotency; bound SQL parameters and tenant-filtered reads; fixed error messages and disabled routine request logging. Startup, signing, pages, retries, storage, tests and human release review are documented. This is not exhaustive authentication or log-leak assurance.

External evaluation passes 28/28. The independently applied complete patch reconstructs the candidate, allowing text line-ending normalization. Protected files are unchanged and no release mutation occurred.

A possible parser-depth concern in the workflow candidate was explored after source inspection. A 2,410-byte valid JSON request nested 1,200 levels was sent to each actual server. **Both passed** acceptance, readback and idempotent retry. The probe process raised its own recursion limit to validate/read the fixture, but neither server process was altered. This does not demonstrate a webhook defect and is not counted as one. See `results/supplemental-webhook-nesting/result.json`.

## Log single-agent candidate

Inspected final `log_archive.py`, README and handoff. The implementation uses only the standard library, private read-only snapshots, synchronized publication, token/filter indexes, timestamp bisection and file-identity freshness checks. Documentation preserves the API/CLI/acceptance contract while updating the introduction and appending operational guidance; it distinguishes warmed API searches from cold CLI loads and explains memory/reload tradeoffs.

Fixed external evaluation passes 31/31 and measures 620.79x warmed throughput. All eight release checks pass. The delivered patch explicitly covers tracked files only; it applies, but does not reconstruct the new benchmark and added test file. Those files are retained and identified in the full candidate manifest. This is a documented packaging limitation, not a missing application or a falsely claimed complete patch; the log task did not explicitly require a standalone complete patch.

**Confirmed contract defect beyond the fixed suite:** the final implementation uses recursive `deepcopy` for returned items. The review-derived, separately declared depth-550 probe succeeds against the frozen reference and final workflow candidate, including mutation isolation and CLI output. The final single-agent candidate raises `RecursionError` from the API and exits 1 with a CLI traceback for the same valid record. The public contract preserves additional JSON fields and independent caller-owned results. The defect was not repaired after grading. Evidence: `results/supplemental-deep-json/result.json` and raw API/CLI output beside it. This exploratory result is separate from the primary 31/31 score.

## Integrity and scope

`records/final-integrity-audit.json` verifies all four candidates remain unchanged after primary and supplemental evaluation; tasks, contexts, caller notes and original public tests are preserved. Notes remain untracked. The only change among 40 frozen shared input/evaluator/tool files is the documented evaluator-owned SQLite connection cleanup. All application tests ran locally on Windows/Python 3.14.6; Python 3.11 and other operating systems were not executed.
