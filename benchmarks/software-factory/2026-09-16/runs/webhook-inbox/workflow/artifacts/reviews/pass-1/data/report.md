# Data review — pass 1

Outcome: no actionable high-impact data finding identified in the frozen candidate. This is a scoped data review, not production approval or an overall low-risk classification. The mandatory human authentication/security review remains pending.

## Scope and candidate identity

Reviewed snapshot: `review-snapshots/pass-1-data` under the webhook-inbox workflow run. Builder identity: `4f73c55c524e6aba3e05b373baa45d58e8fe895a0aed2a5bbeaea9f85df8a2f7`. Coordinator full-tree identity, including caller note: `93f5ad441ff2ef764f6aaf75f813402a969add20488e74de1e8902b900e67807`. `snapshot-verification.json` verifies every one of the 12 manifest file hashes against this snapshot.

Read TASK.md, AGENTS.md, RUN_CONTEXT.md, README.md, RELEASE_HANDOFF.md, the actual implementation and both test files. Applied the supplied orch-review primitive and the Review sections of core code and software-delivery guidance. Read candidate-specific checks.json and the raw smoke/unittest outputs: the required checks report success, and the raw full suite reports 22 passing tests. Source was not repaired; probes and their disposable databases are confined to this report directory. No delegation or deployment occurred.

## Assessment and evidence

- Schema and identity: `inbox_store.py:13–18` persists exact raw bytes as BLOB, exact IDs as binary-collated text, and a unique tenant/ID pair. Global AUTOINCREMENT sequences provide stable increasing subsequences for each tenant, as the contract permits. SQL values are bound. The read query at lines 53–57 applies tenant and cursor predicates before ordering and limiting.
- Atomicity and concurrent retries: `inbox_store.py:32–49` places the existence check and possible insert in an immediate transaction. The transaction commits before the handler returns success and rolls back on exceptions. Twenty-four simultaneous submissions through two server instances sharing the same database produced exactly one 201, eleven identical-body 200 responses, and twelve different-body 409 responses, leaving one row.
- Exact data and isolation: independent probes persisted whitespace-bearing UTF-8 raw JSON and a SQL-looking ID for two tenants, verified the BLOB bytes directly, and confirmed retry/conflict requests left both bytes and sequence unchanged. Existing tests also exercise malformed request non-effects, case sensitivity and cross-tenant cursors.
- Failure effects: an independent BEFORE INSERT trigger first wrote to a probe table and then raised a SQLite failure. The HTTP response was 503; both the event row and the trigger's intermediate write were absent after rollback. Removing the trigger allowed the same ID to return 201. This exercises rollback beyond a failure before any SQL mutation.
- Durability and recovery: SQLite WAL is configured at `inbox_store.py:11`, FULL synchronous mode is set on every connection at line 27, and connections close in a finally block. A local CLI process was abruptly killed after twenty acknowledged accepts. Restart retained all rows, raw bytes and sequences; identical retry returned 200, changed body returned 409, and a new event received a larger sequence.
- Backup and restore: a backup taken with SQLite's backup API while the service was running passed integrity_check and matched all rows. A server started against that backup retained duplicate/conflict behavior and allocated a larger sequence for a subsequent insertion. This supports README's backup mechanism and same-schema restore procedure.
- Lifecycle and rollback: retention is indefinite and documented. Removing tenant configuration blocks access without destroying stored events. Documentation explicitly warns that restoring an older backup loses later events and idempotency state, and that the starter is not a viable ingestion rollback. No destructive migration or retention job is introduced.

Independent probe command (exit 0):

```text
python -B artifacts/reviews/pass-1/data/probe.py review-snapshots/pass-1-data
```

The actual invocation used absolute paths. `probe.py` contains the complete probe logic; `probe-raw.txt` records five PASS results; `crash-stderr.txt` retains CLI stderr. The script's SQLite files retain the probe/backup/recovered state. The script is a one-shot evidence run and assumes those destination database filenames do not already exist.

## Shared-cause pass, missing context and residual risk

I enumerated potential identity races, partial SQL effects, byte normalization, tenant leakage through shared sequencing, backup loss and restart sequence reuse, then checked them for shared causes. The same transaction boundary and schema constraints address the identity and failure-effect concerns; raw BLOB storage and raw JSON response embedding address byte preservation without floating-point conversion. No remaining concern justified a high-impact defect finding.

No production filesystem, storage hardware, backup schedule, restore objective, deployment topology or pre-existing production database schema was supplied. The abrupt-process test does not simulate host power failure, disk exhaustion, filesystem corruption or unreliable fsync. The SQL-failure probe does not certify every possible storage failure. Durability therefore still depends on the documented local-filesystem and SQLite guarantees; storage capacity monitoring and recovery ownership remain operating decisions. Migration from an unrelated existing schema was not requested or established by the supplied starter context. The tested recovery path is a fresh database or a same-schema SQLite backup.

Data-contract risk is bounded for the supplied local workflow, with positive concurrency, rollback and recovery evidence. Production risk remains subject to operational choices and the mandatory human security gate; this report does not waive them.
