# Release preparation — human approval pending

The starter's placeholder routes are replaced with tenant-authenticated HMAC
ingestion, bearer-authenticated reads, durable SQLite transactions, exact-body
idempotency and sequence pagination. `inbox.py` retains the factory and CLI;
`inbox_store.py` owns storage. Tests and operating instructions are included.

The supplied public smoke test is unchanged. Candidate-specific check output,
source hashes and checked patch are retained outside source under
`../artifacts/pass-1/`. The coordinating workflow records independent review
outcomes and the final disposition in `../artifacts/HANDOFF.md`.

## Decision required

Authentication, signatures and tenant authorization are high-risk changes under
`AGENTS.md`. A human security reviewer must approve the final frozen candidate
before any live release. Shared release policy also forbids simulator deployment
for this webhook task. Local implementation and checks do not imply deployment
approval. No deployment, production observation or rollback has been performed.

Review the exact header grammars, timestamp window, constant-time comparisons,
cross-tenant isolation, retained payload access, configuration permissions,
credential rotation/restart plan, and the exposure boundary described in README.
Choose a TLS/proxy, resource limits, operational ownership and retention policy
before a production release. No automatic retention deletion is implemented.

## Proposed rollout after separate authorization

1. Freeze the reviewed candidate hash/patch and retain the previously approved
   artifact. Provision isolated configuration and a durable local database path.
   Back up any existing database using SQLite backup and verify its integrity.
2. Start on loopback with port 0 and verify the readiness line and `/health`.
   Run authenticated tenant A/B checks using controlled test events: accept,
   duplicate, conflict, unauthorized cross-tenant read/write, and pagination.
   Restart and confirm bodies, IDs and sequence ordering survive.
3. Put a limited canary behind the reviewed serving boundary. Before routing real
   traffic, establish counts of response status by route and tenant, accepted
   events, duplicate/conflict rates, storage failures, request latency and disk
   space. Exclude tokens, secrets, signatures, bodies and raw request headers.
   No new telemetry service or dashboard was created by this task.
4. Do not advance if any unauthorized read/write succeeds, integrity verification
   fails, accepted events disappear, storage 503 responses recur, or canary error
   rate exceeds 1% or p95 latency exceeds 200 ms in three consecutive 10-second
   windows. These are proposed gates, not measurements or synthetic observations.
   Compare legitimate duplicate/conflict/401 rates with the preapproved baseline;
   do not treat ordinary client validation errors as server incidents.

## Rollback preparation

On an isolation or integrity violation, stop accepting traffic immediately and
preserve the database, WAL/SHM if present, configuration version and evidence.
After stopping the process, preserve a recovery copy and verify SQLite integrity
before switching binaries. Prefer reverting to a previously reviewed compatible
artifact while retaining the latest database; this schema introduces only a new
events table and index and does not require a destructive down migration.

The pristine starter is not a functional ingestion fallback. If no approved
compatible artifact exists, keep ingestion disabled and use sender retries while
repairing forward. Do not silently restore an older backup, delete accepted
events or drop idempotency state to make a rollback appear successful. Any backup
restore requires an explicit data-loss/reconciliation decision and validation of
tenant isolation, sequence stability and idempotency before reopening traffic.
