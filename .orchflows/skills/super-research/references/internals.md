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
adapter id alone — so one surface's rows get ranked by the other surface's metric
name, and half a view goes unranked. Hacker News is where this shows: the item
store calls a story's comment count `descendants` and the index calls the same
quantity `num_comments`, and neither is this package's to rename. `github_rest`
has the same shape, with one anonymous hour counted in two buckets.

### A page is not a call

A page is what an adapter returned. A call is what an origin was asked to spend.
`runner.reached_origin` is the one place that decides, and it is false in **two**
ways: the run's own memory answered (`cache_hit`), or the adapter refused before
making a call at all (`outcome == "refused"`). `refused` is the one outcome
meaning the read never left; every other one, failures included, describes
something an origin or the local network actually answered.

Inferring "reached the origin" from "not a cache hit" is indistinguishable from
correct until an adapter can refuse *without* calling — a target it does not
serve costs a page and no read. Once one can, the ledger bills a `calls` delta for
a request that never went out, and every downstream sum is wrong by the number of
refusals. `public_page`'s refusal of an unserved selection is the case that
exposed it.

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
