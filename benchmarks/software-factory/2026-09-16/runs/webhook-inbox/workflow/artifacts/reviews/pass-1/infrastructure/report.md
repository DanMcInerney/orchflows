# Infrastructure review, pass 1

Disposition: no actionable high-impact infrastructure finding for the specified local-only product. This is a scoped review result, not approval to deploy or a determination that the authentication change is low risk. Mandatory human security review remains pending.

Reviewed snapshot: `review-snapshots/pass-1-infrastructure`.

Builder identity: `4f73c55c524e6aba3e05b373baa45d58e8fe895a0aed2a5bbeaea9f85df8a2f7`.

Coordinator full-tree identity: `93f5ad441ff2ef764f6aaf75f813402a969add20488e74de1e8902b900e67807`.

The probe verified all 12 source/configuration/documentation file hashes against the coordinator manifest, including the preserved caller note. Reviewed TASK.md, AGENTS.md, RUN_CONTEXT.md, README.md, RELEASE_HANDOFF.md, implementation and tests, shared release policy, and supplied check manifests/raw smoke and unittest output. Applied the supplied orch-review primitive and Review sections of code.md and software-delivery.md. No repairs, dependency changes, delegation, simulator operations or live deployment were performed.

## Findings and cause consolidation

No high-impact finding to report. A second pass considered shared resource exhaustion causes (unbounded request threads, slow partial clients, SQLite contention and oversized read pages), shutdown ordering, process restart durability and rollback assumptions. The unbounded connection/admission behavior is real but explicitly documented and scoped to a loopback local service. It is a prerequisite for separate review before public exposure, rather than an unreported capability or a violation of this local runtime contract.

## Evidence and concrete behavior

`probe.py` and `output.txt` beside this report contain the independent executable probes and raw output. Command, run from the assigned snapshot:

```text
python -B <run>/artifacts/reviews/pass-1/infrastructure/probe.py
```

The command exited 0 with a final PASS record. It used isolated temporary SQLite/configuration files, loopback listeners, and short-lived local subprocesses; all were closed and removed.

- Factory and CLI readiness: `inbox.py:252-258` initializes configuration/storage before binding, and `inbox.py:269` flushes the actual bound address before serving. Two independent CLI startups with port 0 emitted valid loopback readiness and served authenticated traffic. No extra stdout/stderr was observed during these runs.
- Contention and resource cleanup: `inbox_store.py:23-30` closes each operation's connection; `inbox_store.py:32-49` uses one immediate transaction for identity and write. Holding an external SQLite write transaction caused the request to return JSON 503 after 10.891 seconds. The ID was absent afterward, health stayed responsive, and releasing the lock allowed the same ID to return 201. This supports the advertised contention failure/retry behavior without assuming a strict total ten-second deadline.
- Graceful shutdown: `inbox.py:247-249` uses non-daemon request workers. While an already accepted POST waited for its remaining body, shutdown plus server_close waited for it; completing the body produced 201, then close and the serving thread completed. The factory subsequently bound the same port, preserved both stored events and returned 200 for the authenticated duplicate.
- Real process restart: a CLI subprocess acknowledged a third event, was forcibly killed, and was restarted using the same database. The authenticated page was unchanged, including sequences and payloads; the exact retry returned 200 and a changed-body retry returned 409. This is direct process-stop evidence, not a power-loss/filesystem durability certification.
- Recovery: the documented SQLite backup API produced an integrity-check result of `ok` and exactly matching event rows. `README.md:126-137` explains WAL-aware backup, separate-path restore, and the data-loss/idempotency implications of restoring an older copy.
- Supplied check evidence: the frozen candidate's checks.json records successful smoke, full unittest, compilation, CLI help, whitespace and cached patch-applicability checks. Inspected raw output confirms 22 passing discovered tests, including concurrency and restart, and both unchanged public smoke tests. These provided checks were not rerun without cause.

## Operating and release preparedness

`README.md:139-147` accurately limits the implementation: no TLS, global connection cap, rate limiting or process supervisor; the socket timeout is an idle timeout and slow trickling can extend total request/shutdown time. Read pages can hold roughly 6.5 MB of raw event data plus overhead. Retention is indefinite. These limits must inform any future exposure/capacity decision; the current evidence establishes local functional behavior, not production load capacity.

RELEASE_HANDOFF.md keeps the candidate frozen for review, identifies human security approval, and proposes loopback canary validation, authenticated isolation/idempotency/restart checks, status/latency/storage signals and stop gates. Those are future acceptance proposals, not existing production telemetry or observed deployment results. The supplied release policy explicitly excludes webhook simulator release as well as live release; preparation does not override it.

Rollback guidance avoids treating the nonfunctional starter as a usable fallback, preserves the latest database/idempotency state, prefers a previously approved compatible artifact, and otherwise keeps ingestion stopped while repairing forward. That is an honest supported recovery posture for this new local service. No prior approved artifact is claimed or verified.

## Missing context and residual risk

There is no provider infrastructure, remote CI, production traffic/latency baseline, approved public serving boundary, supervisor configuration, deployment authorization or real production telemetry in this case. No such evidence was invented or substituted with simulator observations. Operating ownership, production admission limits, disk alerting/retention policy, a previously approved compatible rollback artifact and human security approval remain future release decisions.

The probes do not establish behavior under disk exhaustion, filesystem/power failure, sustained overload or adversarial slow trickling; Windows console Ctrl+C was inspected in code but not generated in a real interactive console. Existing source documentation identifies the material local resource limits. These gaps do not establish a local contract failure, but they preclude claiming unrestricted operational readiness or blanket low risk. Authentication and tenant isolation remain subject to the separate review and mandatory human gate.
