# Direct acquisition protocol

Use the [bounded plan](acquisition.md) for normal collection. This reference describes manual manifests and returned records; [source operations](selection-routes.md) own query syntax. Direct runner calls have no plan-wide request/time budget, checkpoint or resume guarantee.

## Manifest

`schema.parse_manifest` rejects invalid or unknown fields before transport. Top-level keys are `manifest_id`, `as_of`, `steps`; identifiers must be nonempty and step IDs unique. Instants use `YYYY-MM-DDTHH:MM:SSZ`. `as_of` is the declared observation ceiling, distinct from source publication time; the bounded CLI enforces it.

Step keys are `step_id`, `kind`, `adapter_id`, `query`, `prior_step_id`, `selected_hits`, `max_items`, `window_start`, `window_end`. `prior_step_id`, when present, names a step in the manifest. `kind` is `discovery` or `hydration`; `max_items` is a positive integer.

- Discovery forbids selected hits and can follow returned cursors, capped at five pages and `max_items` retained records per step.
- Hydration requires hits of `{discovery_locator, target_id}`. Each target gets one call, capped at `max_items`; hydration spends no continuation. The discovery locator is the exact normalized locator the caller retained, not a similarity match.
- Optional window endpoints use the instant spelling above, with start no later than end. Known out-of-window publication times are filtered before counting the cap; unknown dates remain unknown. Origin-side time bounds depend on the selected operation. `window_not_honored` and `window_capability_unmeasured` expose limits that local filtering cannot repair. Selected document depth in the bounded plan deliberately omits the window to retain contradictory original dates.

`runner.run_acquisition(manifest)` returns an artifact; `run_scheduled` returns the artifact and a work ledger. Direct multi-step runs use at most eight adapter lanes, preserving step order within each lane; `lanes=1` serializes them. Inputs are frozen before execution and the governor serializes reads per origin. Ledger scheduling and `fake_makespan_us` are posthoc models, not observed wall time or proof of speed. Use the bounded CLI's measured summary times for run reporting.

## Artifact and provenance

An `AcquisitionArtifact` contains `manifest_id`, `as_of`, `records`, `steps`, `edges`, `groups`, `outcome` and `loss`. Each `StepResult` retains `step_id`, `adapter_id`, first `route_id`, `kind`, `query`, page/received/kept counts, `outcome`, `loss` and `warnings`. Read these before interpreting an empty result. Each record retains its actual answering route.

An `AcquisitionRecord` carries:

| Concern | Fields |
| --- | --- |
| Identity | record/artifact/manifest/step IDs, adapter ID/version, platform, native identity namespace, content kind, item and parent IDs |
| Content | `title`, `body`, `exact_content_hash`, `attributes`, `author`, `community` |
| Address and relation | `canonical_locator`, `normalized_locator`, `discovery_locator`, `representation_kind`, `group_scope` |
| Time and engagement | `published_at`, `observed_at`, `time_confidence`, `usable_basis_time`, `engagement` |
| Provenance | `route_id`, `access_class`, `operator_identity`, `page_index`, `list_index`, `native_position`, `outcome`, `loss` |

Records are immutable. Identity groups hold related records side by side; they never merge content, dates or counts. Strong grouping uses native namespace, item ID and content kind; otherwise a complete weak key uses scope, representation, normalized locator, content kind and content hash. Representations remain separate. A `discovery_hydration` edge ties a selected read to the exact discovery locator; similarity creates no edge. Missing discovery lineage stays visible.

`engagement` contains `EngagementSnapshot(metric_name, value, observed_at)` using exact native integers. Counts must be nonnegative and at most `2^63-1`; only platform `reddit` with metric `score` permits signed 64-bit integers. Booleans, floats and out-of-range values are refused. Metric names are not aliased, combined or compared across platforms. `attributes` holds named string facts, including repeated values where the source repeats them. Missing engagement is not zero, and popularity is not a quality score.

`usable_basis_time` preserves `published_at`. Missing publication gives `time_confidence=unknown`; indexes, feeds and third-party records use `reported` with `published_at_basis` of `index_reported`, `publisher_reported` or `third_party_reported`. Other directly reported dates use `authoritative`, an origin label rather than independent verification. Candidate `date_eligibility` prefixes reported dates with `reported_` and `date_qualification` explains what remains unverified. Keep publication, revision/event time and observation time distinct; a recent index date cannot make an old paper recent.

Access labels describe acquisition, not truth: `K0` keyless official endpoint, `K2` structured public HTML, `K3` third-party operator, `offline` fixture. The schema also reserves `K1` for a public client credential and `K4` for a discovery index; no current route uses either. No route accepts user credentials or performs login.

## Outcomes and losses

Outcomes are `ok`, `empty`, `partial`, `failed`, `refused`, in increasing severity. Losses are additive qualifications, not a second outcome: useful content can coexist with missing fields. A parser failure or refusal is never evidence that the source had no matches. Inspect warnings for the actual cause; routes do not retry or fall back.

| Loss | Meaning |
| --- | --- |
| `third_party_archive` | An independent operator supplied the record; inspect `operator_identity`. |
| `auth_required`, `attestation_required`, `rate_limited` | Origin required authentication, a challenge, or fewer requests. |
| `network_intercepted` | The network, rather than the requested origin, answered. |
| `unreachable` | No admitted usable transport response: connection/TLS/timeout, transport policy, invalid compression, or exhausted plan bounds; inspect the warning. |
| `http_status`, `malformed_json`, `schema_drift` | Unexpected status, invalid JSON, or an unrecognized payload shape. |
| `scope_required`, `unselected_target`, `no_route` | Missing required scope, invalid/unsafe target, or unsupported adapter. |
| `field_omitted`, `engagement_unavailable` | A declared field was absent, or the surface supplies no counts. |
| `unknown_publication_time`, `date_precision_only` | Publication is unknown, or only coarse date precision was supplied. |
| `native_identity_unknown`, `target_not_hydrated` | An index hit lacks native identity or remains a discovery representation; check edges for a separately read target. |
| `discovery_not_recorded` | A read names discovery lineage absent from this artifact. |
| `recall_window_partial` | A cap or available continuation limited collection. |
| `window_not_honored`, `window_capability_unmeasured` | The operation cannot bound time at the origin, or that ability has not been measured. |
| `cache_hit` | This run's memory supplied the response. |

## Transport and direct use

Declared route methods are read-only HTTPS. The transport bounds responses to 8 MiB and checks redirects and open-document addresses. Route ceilings and server `Retry-After`/`X-RateLimit-Reset` govern pacing; server limits may lengthen cooldowns. The run cache holds at most 32 entries of at most 1 MiB (32 MiB of cached bodies), keyed by route and canonical request, with route-specific TTLs. Hits carry `cache_hit` and spend no origin budget; cached bodies do not survive a run. The bounded plan persists refusal/pacing reservations, not this cache.

With the skill's `scripts/` on `PYTHONPATH`, direct callers use `schema.parse_manifest`, `runner.run_acquisition`, then `dataclasses.asdict` to serialize. `coverage.plan_depth` builds steps from already selected records without I/O; `coverage.review_manifest` and `coverage.review_artifact` report anticipated and observed gaps. These checks establish acquisition coverage only. Source access, recall and research quality still require observed evidence.
