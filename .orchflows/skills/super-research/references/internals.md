# super-research internals

The maintainer's side of [protocol.md](protocol.md): where the code lives, the
two laws a reader has to be told, and what the package refuses.

## Layout

`scripts/super_research/`, standard library only on the Python 3.9 floor, no I/O
at import time. The module set is not the one the frozen spec's affected surfaces
list: `ledger.py`, `ordering.py` and `pacing.py` were split out of `runner.py`,
`probes.py` and `smoke.py` out of `cli.py`, and `routes.py` out of
`transport.py`, after the spec froze.

| module | owns |
| --- | --- |
| `schema.py` | closed enums, the immutable manifest and artifact values, `parse_manifest` |
| `routes.py` | every route constant and every `K1` public client credential: the closed allowlist of reachable hosts, declarations only |
| `transport.py` | the outbound request — the opener, method admission, the byte cap, refusal parsing, the guest-token store, the captive-portal detector, `route_admissions` |
| `router.py` | one step's route decision, from per-route booleans alone |
| `runner.py` | literal adapter dispatch, and one manifest run to one artifact plus its ledger |
| `pacing.py` | per-route budgets and the rate governor |
| `ledger.py` | the work ledger and the schedule a mode admits |
| `ordering.py` | the five named views |
| `cache.py` | one run's TTL memory of reads it already made |
| `normalize.py` | native pages to immutable records; grouping and provenance edges |
| `project.py` | a pure bounded subset of one artifact |
| `probes.py` | the thirteen liveness probe declarations |
| `smoke.py` | one probe's read, and the standing it leaves an adapter at |
| `cli.py` | three operations, and everything an operator reads |
| `adapters/__init__.py` | `AdapterDescriptor`, `NativeRecord`, `NativePage`, `fetch_one_page` |
| `adapters/<id>.py` | one route's parser, one `DESCRIPTOR`, one `fetch_native_page` |

`runner.py` re-exports every name moved to `ledger`, `ordering` and `pacing`,
`cli.py` every name moved to `probes` and `smoke`, and `transport.py` every name
moved to `routes`, so each name has one definition and one address. Tests are
`tests/`, with `tests/helpers.py` and `tests/fixtures/**`; the whole suite runs
with no network reachable.

## Two laws, each bought with a defect

Neither is derivable from the code by a reader who has not already made the
mistake, so both are stated as law.

### A record's route, not its adapter, identifies the surface that produced it

An adapter id names a parser. A route id names the surface a read actually left
on. Every accounting and every metric lookup keys on the route.

- `StepResult.route_id` and `WorkLedgerEvent.route_id` are `page.route_id` — the
  route the page says answered — and not the route the core routed by. A step
  whose pages disagree on a route falls back to the route it was admitted on,
  because no single route is what it read and each record already carries the
  exact one it came from.
- `ordering._surface_descriptor` resolves a metric name by matching the record's
  `route_id` against the descriptors `runner.surface_descriptors` returns for that
  adapter, and only then falls back to the adapter's own.

Charging to the adapter is invisible until an adapter reads two surfaces. It bills
one origin's budget for the other's read, and it resolves `most_commented` by
adapter id alone — so one surface's rows get ordered by the other surface's metric
name, and half a view goes unordered. Hacker News is where this shows: the item
store calls a story's comment count `descendants` and the index calls the same
quantity `num_comments`, and neither is this package's to rename. `github_rest`
has the same shape, with one anonymous hour counted in two buckets.

### A page is not a call

A page is what an adapter returned. A call is what an origin was asked to spend.
`runner.reached_origin` is the one place that decides, and it is false in **three**
ways: the run's own memory answered (`cache_hit`), the adapter refused before
making a call at all (`outcome == "refused"`), or the read raised and nothing took
it (`unreachable`). The third follows the governor: `_paced_fetch` charges a
route's interval and logs the read only after the carrier returns, so a fetch that
raised spent nothing there, and a ledger billing it would disagree with the
governor's log the suite pins it equal to. Every other outcome, failures included,
describes an answer this host actually got.

Inferring "reached the origin" from "not a cache hit" is indistinguishable from
correct until an adapter can refuse *without* calling — a target it does not
serve costs a page and no read. Once one can, the ledger bills a `calls` delta for
a request that never went out, and every downstream sum is wrong by the number of
refusals. `public_page`'s refusal of an unserved selection is the case that
exposed it.

## How the ladder is enforced

The classes and their three rules are [protocol.md](protocol.md)'s. This is the
machinery behind them.

A `K1` public client credential is a route constant `routes.py` declares and
`transport.py` re-exports. It is attached at send time, never enters a manifest
or an artifact, and is stripped back off the answering address before that
address leaves the transport seam.

The `K3` label has to be on the row rather than on the page:
`normalize.normalize_page` builds a record's loss from that native record's own
and never from the page's, so an archive that labelled only the page would leave
an artifact whose rows all read as the platform speaking.

`AdapterDescriptor.__post_init__` refuses any `access_class` not in
`schema.ACCESS_CLASSES` at construction, because three separate rules read it —
the router admits on it, `time_confidence_for` decides on it, and the artifact
publishes it — and none can tell an unnamed class from a wrong one.

**No route in this package is `K5`, and there is no lawful shape for one.** A
credentialed surface beside a keyless one on the same adapter breaks one class per
adapter; a wholly credentialed adapter breaks rule 1, because the core substitutes
nothing and a caller naming that adapter is simply refused. The ladder's two named
`K5` members, Reddit OAuth and the YouTube Data API, are deferred for that reason
rather than by coincidence.

`transport.route_admissions()` is the only route knowledge the router ever sees:
one boolean per route, true exactly when the route's class is not `K5`. The router
sees no host, path, or credential, and answers `no_route` or `auth_required`
before any I/O.

## Rate budgets, cache, and the work ledger

**Per-route budgets replace a uniform cap.** Each descriptor declares
`min_interval_ms`, `burst` and `cooldown_ms` as measured constants, enforced per
route by `pacing.RateGovernor`. A ceiling belongs to the origin, so two adapters
reading one route declare the same three numbers. An undeclared route takes
`DEFAULT_MIN_INTERVAL_MS=1000`, `DEFAULT_BURST=1`, `DEFAULT_COOLDOWN_MS=60000`: a
limit nobody has measured is not one to spend. The measured extremes are
`reddit_feed`, at one read per 30 000 ms, and `github_rest`, whose anonymous hour
is sixty reads in each of two separately counted buckets — which is why its two
surfaces are two routes rather than one.

**The composition is the default, not an option a caller assembles.**
`runner.run_acquisition(manifest)` and `run_scheduled` name no carrier and get
`pacing.paced_carrier`: a `RateGovernor` over a `RunCache` over a real
`transport.Transport`, all three on the run's own clock. It is the only place in
the package that builds a carrier, which is checkable from outside — a second
one is a second unpaced door. Handing in a carrier is how a caller takes pacing
over deliberately; there is no way to reach an origin unpaced by omission.

That choice is one choice and not three. A caller who hands in a bare
`transport.Transport` gets no pacing, no cache, and **no mint**: the guest-token
activation a `K1` route needs is minted inside `RateGovernor`, because an
activation is a read like any other and belongs in a budget of its own. A bare
carrier's `x_guest` read therefore goes out unauthorized, and the origin's own
401 or 403 is what the run records — never an invented token and never a retry.

An HTTP 429 is typed `rate_limited` on the page, sets that route's cooldown, and
ends the call. It never triggers a second read, another route, or a changed
identity: `transport.USER_AGENT` is one static string, and a rate limit is a
constraint this package respects rather than evades.

**The cooldown is the origin's own interval whenever it states one.**
`Retry-After` in both RFC 7231 spellings and `X-RateLimit-Reset` are read off the
headers `TransportResponse` carries, matched without regard to case and resolved
against that answer's own `observed_at`; `RateGovernor` then holds the route for
the longer of that and the declared `cooldown_ms`. Longer only — a stated
interval that shortened a wait would be evasion wearing the shape of obedience —
so an elapsed deadline, an unreadable value and an absent header alike leave the
declared constant governing, and none of them raises. `transport.rate_refused`
opens a cooldown for one status besides 429: a 403 whose body says the refusal is
about rate, which is how GitHub spells its secondary limit. A 403 about who is
asking opens none, and neither changes how the page is typed.

**The run-local cache is a correctness requirement**, not an optimization: at one
to two reads per thirty seconds, a run that re-reads a Reddit feed starves.
`cache.RunCache` is keyed by `(route_id, canonical_request)`, holds at most
`MAX_ENTRIES=32` bodies of at most `MAX_ENTRY_BYTES=1 MiB`, runs on a monotonic
clock, and dies with the run — `close()` makes a later run's reach for it an error
rather than a quiet hit. Their product, 32 MiB, is what a run's cache can cost
however long the run goes on. Per-route TTLs are declared in `ROUTE_TTL_SECONDS`;
`public_page_control` declares `0.0`, because a channel control answered from
memory would report the network healthy on the strength of a read made before the
appliance woke. A served entry carries `cache_hit` on the page and on every
record, and keeps the transport's own `observed_at` — a cached record states when
the origin was read, never when memory answered.

**The work ledger** is additive per-operation deltas in one causal order, keyed
`(dispatch_ordinal, operation_ordinal, operation_kind_ordinal, metric_ordinal,
operation_id)`. This core schedules one operation kind, `native_page`, and emits
`calls`, `pages`, `items` and `fake_duration`, plus one zero-delta `stop` marker
per dispatch naming why the run ended. `pages` is emitted exactly once per
operation, because one native page per adapter call is the law. `fake_makespan_us`
is derived over the schedule and is deliberately not a metric: two operations the
model places overlapping count once between them, which is the only quantity that
tells `fused` from `staged`. It is a counterfactual over a placement, not a
measurement of a run — nothing in this package executes two operations at once.

## What the package refuses

Threat oracles T01–T16 are retained from the superseded spec with applicability
remapped from `A0`–`A5` to `K0`–`K5` by the rule the old mapping used: a threat
applies to a class when that class has the machinery the threat is about. The
remap table is `test_transport.THREAT_REMAP` and is itself checked — every threat
named once, every class one the ladder declares, and every class the roster
answers at covered by at least one threat. `offline` is not on the ladder; nothing
about `fake` is a claim about a route.

The sixteen rows below are that remap and not a second copy of it:
`test_transport.ThreatTableIsReadOffTheDocumentTest` parses **both** columns out
of this file and compares each against `THREAT_REMAP`, so a row corrected here
and left there is a red test rather than two statements nobody compared.

| threat | applies to | form here |
| --- | --- | --- |
| T01 | `K1`, `K5` | no credential id or value reaches a request, a response, a call log, or an artifact |
| T02 | `K1`, `K5` | an echoed credential — the address a query-placed key was appended to — comes back stripped |
| T03 | `K1`, `K5` | a credential is attached at send time from the route's own constant, so it reaches that origin and no other |
| T04 | `K0`–`K5` | no route admits a state-changing verb: PUT, PATCH and DELETE nowhere, POST only for two named reads |
| T05 | no class | no process is launched, because none can be: nothing here imports one or spells a command |
| T06 | `K0`–`K5` | a caller cannot escape a route's admitted method set, and a body is the route's shape with the caller's values |
| T07 | no class | there is no session state to export: the one token a run mints lives in memory and nowhere else |
| T08 | no class | nothing navigates, clicks or submits: the only outbound operation is one bounded read |
| T09 | `K0`–`K5` | acquired text is `untrusted_content`: it changes no plan, no grant, and no write set |
| T10 | `K1`, `K5` | a `K1` credential names no user, so there is no principal to mismatch; the operator that answered is declared |
| T11 | `K0`–`K5` | a refusal is typed `rate_limited` on one call, and no identity changes because of it |
| T12 | `K0`–`K5` | a route the run cannot reach is refused with a typed reason and never probed |
| T13 | `K4` | an index surface declares itself an index, and it is the only surface in the roster that does |
| T14 | `K0`–`K5` | the package has no delete primitive: its only stores are in memory and clearing one is all there is |
| T15 | `K0`–`K5` | a refusal costs the origin nothing: it is decided before any call is made |
| T16 | `K0`–`K5` | no fallback: a failed read is a typed failure, never a second read somewhere else |

T05, T07 and T08 apply to no class because the `K0`–`K5` ladder has neither an
ambient-identity CLI nor an exported browser session; they are answered by absent
machinery rather than by a behaviour, and recording that is the remap.

**Zero writes are reachable.** `transport.admitted_methods` returns `GET` and
`HEAD` for every route but two named exceptions, both POSTs that create nothing:
minting an anonymous guest token, and asking InnerTube a question it publishes no
GET form for. A query-body route's body is rendered from that route's declared
`body_params` and from nothing else, so a caller supplies values into a shape this
module owns and can never choose the shape — the point at which a route would
become the generic HTTP primitive the spec's non-goals refuse. PUT, PATCH and
DELETE are admitted by no route, unconditionally. The opener also refuses any URL
that is not `https://`.

**Everything acquired is untrusted content.** A snippet, a body, an attribute
value, or a profile description is data. It never alters a manifest, a route, a
cap, or a write set, however it is phrased, and the calling lane owes it the same
treatment.
