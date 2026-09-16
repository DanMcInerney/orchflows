# Security review — pass 1

Disposition: no actionable high-impact security finding identified in the reviewed snapshot. This is an automated review result, not human approval or release authority. Authentication, signature verification, and tenant authorization remain high-risk changes requiring human security review under AGENTS.md.

Reviewed candidate:
- Builder identity: 4f73c55c524e6aba3e05b373baa45d58e8fe895a0aed2a5bbeaea9f85df8a2f7.
- Coordinator tree identity: 93f5ad441ff2ef764f6aaf75f813402a969add20488e74de1e8902b900e67807.
- Snapshot: <BUNDLE_ROOT>/runs/webhook-inbox/workflow/review-snapshots/pass-1-security.
- All 12 snapshot files listed in coordinator-manifest.json independently matched their SHA-256 values before probes.
- No candidate files were changed. Probes and their transient databases were confined to this report directory. No delegation or deployment was performed.

## Evidence and security assessment

Read TASK.md, AGENTS.md, RUN_CONTEXT.md, README.md, RELEASE_HANDOFF.md, both implementation files, and both test files. Applied the supplied orch-review primitive and Review sections of guidance/code.md and software-delivery.md.

The candidate-specific checks.json and raw smoke/unittest logs show passing required checks, including 22 discovery tests. They are tied to the builder identity above. This review additionally ran probes.py against the frozen snapshot; probe-output-passing.txt records 31 passing checks and probe-results.json records individual outcomes.

- inbox.py:219–237 validates canonical timestamps and lowercase 64-digit signatures, computes HMAC-SHA256 over the exact ASCII timestamp plus period plus raw bytes using the selected tenant's UTF-8 secret, and uses hmac.compare_digest. Timestamp and signature checks precede every store operation, including retries. Independent probes rejected raw-body tampering, stale/future identical-body retries, invalid-signature retries, and another tenant's signature with no stored-row effects.
- inbox.py:86–109 and 128–132 preserve header bytes and require one occurrence of each required field; inbox.py:207–229 rejects transfer encoding, malformed/duplicate lengths, and incomplete bodies. Raw-socket probes exercised duplicate required headers, duplicate authorization, folded headers, whitespace before a colon, extra value whitespace, transfer encodings, and truncated framing. Malformed authenticated JSON and invalid UTF-8 were rejected without changing rows.
- inbox.py:167–172 compares bearer-token bytes in constant time against the selected tenant's token. Wrong-tenant credentials, token whitespace/control-byte variants, and duplicate authorization failed. Successful beta reads exposed no alpha rows.
- inbox_store.py:13–18 and 32–57 bind tenant, event ID, body, cursor and limit as SQL values, enforce unique tenant/ID identities, and serialize the existing-body decision with BEGIN IMMEDIATE. Both insert and read predicates include tenant. SQL-looking event IDs remained literal data; failed probes preserved the entire existing row set, including bodies and sequences.
- inbox.py:116–130, 147–158, and 243–244 return bounded error objects and disable routine request logging. Probe error responses did not echo fixture credentials or submitted signatures. Validated stored raw JSON is embedded in pages only after tenant authorization and tenant-filtered selection.
- Source inspection and supplied tests support inclusive size limits, exact-body idempotency, concurrent writes, sequence isolation, pagination, restart durability, and non-disclosing health responses.

## Finding consolidation

The initial finding inventory contained no confirmed high-impact defect. A second pass considered shared causes across header parsing/framing, authentication-before-storage, and tenant-scoped SQL; no common bypass or partial-write path was identified. No repair is requested from this review.

Two early probe runs exposed reviewer-test issues, not candidate defects. The first incorrectly assumed a particular valid nesting depth must be rejected; nesting tolerance is runtime-dependent, and the contract does not prohibit valid nested objects. It was replaced by malformed nested JSON. The second retained a SQLite connection in the probe's row-reading helper, causing Windows temporary-directory cleanup to fail; that helper now explicitly closes connections. The original logs are retained as probe-output.txt and probe-output-final.txt; only probe-output-passing.txt and probe-results.json represent the corrected completed run.

## Remaining risk and missing context

- Human security approval is mandatory. No production deployment topology, actual credentials, OS permissions, TLS/proxy configuration, rate limits or operational ownership was supplied or verified. Those decisions remain pending, as documented in README.md and RELEASE_HANDOFF.md.
- The specified MAC does not cover event ID. A captured valid signature/body can be replayed under different IDs within its valid window; this is inherent in the requested signing contract and is documented. A human reviewer must accept the contract and protect credential/signature traffic through the serving boundary.
- The implementation defaults to loopback but has no TLS, global admission cap, or total request deadline; the documented per-socket timeout does not stop slow trickle clients. Public exposure needs the separately reviewed boundary already called for in the handoff.
- This bounded review is not exhaustive protocol fuzzing or a resource-exhaustion assessment. Runtime probes used the available Python 3.14 installation; compatibility across every supported Python 3.11+ version was not independently exercised. Host clock, filesystem crash durability, and file access controls were not tested.
- Network failure after a committed insert can leave the client uncertain; retry/idempotency handling and the operating documentation address that uncertainty. The no-effect assertions here concern rejected malformed/authentication requests.

No live release, simulated deployment, or production approval is implied by this report.

