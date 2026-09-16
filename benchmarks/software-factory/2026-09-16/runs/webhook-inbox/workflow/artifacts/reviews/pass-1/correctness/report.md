# Correctness review — pass 1

Disposition: no actionable high-impact correctness findings. This is a scoped automated review, not production or security approval. The mandatory human review of authentication, signatures and tenant authorization remains pending.

## Reviewed candidate and guidance

- Snapshot: `review-snapshots/pass-1-correctness` under this workflow run.
- Builder candidate identity: `4f73c55c524e6aba3e05b373baa45d58e8fe895a0aed2a5bbeaea9f85df8a2f7`.
- Coordinator full-tree identity: `93f5ad441ff2ef764f6aaf75f813402a969add20488e74de1e8902b900e67807`.
- Independently verified every snapshot file hash against the coordinator manifest, including the preserved caller note.
- Applied the supplied `orch-review` primitive and the Review sections of core `guidance/code.md` and library `example-workflows/software-factory/guidance/software-delivery.md`.
- Read TASK.md, AGENTS.md, RUN_CONTEXT.md, README.md, RELEASE_HANDOFF.md, both implementation modules and both test modules. Read candidate/check manifests and raw smoke, full-suite and CLI-help output.

## Evidence and contract assessment

Independent `python -B -m unittest discover -v` in the snapshot passed all 22 tests in 5.598 seconds. Raw evidence: `unittest-review.txt`. The supplied checks record also reports successful smoke tests, compilation, CLI help, whitespace validation and checked patch application against the stated baseline, all tied to the builder identity.

The independent `probes.py` completed successfully with 29 passing assertions; raw evidence is `probes.txt`. These checks cover snapshot identity; exactly 65,536 bytes containing multibyte UTF-8; oversize rejection without insertion; validated raw JSON containing quoting, whitespace and a large exponent; raw-byte conflict detection; canonical decoded query values; malformed percent escapes and repeated decoded keys; invalid UTF-8 and numeric JSON; failed IDs remaining reusable; a 10,000-digit cursor; JSON errors from unsupported methods; and exact stored body bytes.

The initial probe invocation passed all behavioral assertions but failed its own temporary-directory cleanup because its direct SQLite inspection connections were not explicitly closed. Only the reviewer-owned harness was corrected to use `contextlib.closing`; the full rerun passed with exit code 0. Initial evidence is preserved in `probes-initial-harness-cleanup-error.txt`. This was not a candidate failure.

Source review and observable checks support the following:

- Factory returns a compatible threaded server with loopback and ephemeral-port defaults; the CLI supplies help and flushed actual-bound-address readiness.
- Header parsing preserves values needed to reject duplicate, folded or malformed authentication/framing fields. Signature verification and timestamp checks precede every insert/duplicate decision.
- Body validation requires UTF-8 JSON objects, rejects non-JSON constants and preserves valid numeric lexemes without floating-point conversion on reads.
- EventStore owns durability, uniqueness and ordering. Parameterized SQL and an immediate transaction protect tenant/ID identity, exact-byte retry/conflict behavior and concurrent insertions. Read limits and cursor filtering use tenant predicates and stable increasing sequences.
- Error paths before insertion do not reserve IDs; concurrent, cross-tenant and restart behavior are covered by independently passing tests. Unsupported methods and ordinary errors return JSON objects.
- Required public smoke tests remain present, and tests use independent fixtures. The implementation split is coherent and does not duplicate storage ownership.

I enumerated potential issues and made a second pass for shared causes across framing, authentication, JSON conversion, transaction ordering and pagination. No issue met the instruction's high-impact reporting threshold.

## Missing context and residual risk

No external caller or production topology was supplied beyond the task, fixture config and operating documentation. This review used the available Windows Python 3.14 runtime; Python 3.11 was not separately executed. The documented standard-library JSON nesting limit remains an input limitation; exhaustive nesting/resource behavior was not established here. Clean restart is tested, while forced process/power loss, disk-full recovery and filesystem durability were not experimentally validated in this lens. No live traffic, production deployment or release simulation was performed.

Functional correctness evidence is strong for the supplied local contract. An overall low-risk or release-ready judgment would be inappropriate: authentication is explicitly high risk under project policy, human security approval is missing, and operational exposure/resource/recovery decisions remain as described in the handoff. No candidate source was repaired or changed by this reviewer, and no review was delegated.
