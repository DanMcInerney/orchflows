# Frozen candidate review plan

Each fresh reviewer uses a separate source snapshot inside this run, applies the same resolved Review guidance from brief.md, and records actual evidence in artifacts/reviews/pass-N/LENS/. No reviewer may repair source or delegate a repair. All reviews must bind to the same frozen source manifest and must distinguish tested behavior, static reasoning and missing evidence.

- Correctness: map complete TASK.md acceptance to code/tests, especially validation/error codes, factory and CLI contract, exact size/window limits, raw-byte retry semantics, canonical pagination and simultaneous failure behavior.
- Data: review SQLite schema and lifecycle; atomicity and rollback; exact raw-body/event-ID persistence; per-tenant sequence ordering and pagination; same-ID and cross-tenant concurrency; restart durability and backup/restore expectations.
- Security: review HMAC input and constant-time authentication, missing/duplicate/malformed headers, timestamp replay window, tenant scoping, bearer parsing, raw-body and JSON validation, SQL parameters, credential leakage and failure write effects. Human security decision remains mandatory independent of this review.
- Infrastructure: review create_server and CLI startup/readiness, thread/database resource handling and shutdown/restart, malformed request handling, operating documentation, local-only assumptions, future staged rollout signals and recoverability. No cloud resources or production telemetry exist in this assignment.

Each result must list actionable high-impact issues with concrete file locations/consequences/evidence, resolve common causes before reporting, name missing context explicitly and assign lens risk. A clean result is limited to reviewed context and does not grant release approval.

Required candidate checks before all reviews: unchanged public smoke suite, full unit discovery including authored tests, py_compile, CLI help and git diff --check. Additional reviewer probes must use isolated state and preserve their raw output outside source. No source edits while any review is active.
