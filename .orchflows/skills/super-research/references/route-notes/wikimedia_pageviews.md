# wikimedia_pageviews draft notes

Working notes from implementing the `wikimedia_pageviews` adapter (K0,
`wikimedia_pageviews_per_article`). Not yet folded into `protocol.md` beyond
the loss-vocabulary cells and roster row that were already required for the
suite to pass.

## Measured facts (2026-09-01, live)

- `GET .../api/rest_v1/metrics/pageviews/per-article/en.wikipedia/`
  `all-access/all-agents/Python_(programming_language)/daily/2026082100/`
  `2026083100` answers keyless 200 with `{"items": [...]}`, one row per day
  inside the inclusive range: eleven days requested, eleven rows back. Each
  row carries its own `project`, `article`, `granularity`, `access`,
  `agent`, a `timestamp` spelled `YYYYMMDD00`, and an integer `views`.
- **Path quoting.** The ordinary path quoting
  `_support.transport_request.path_segments` already applies
  (`urllib.parse.quote(value, safe="")`) percent-encodes a disambiguated
  title's parentheses (`Python_%28programming_language%29`). Measured live:
  the percent-encoded segment answered 200 with byte-identical `items` to
  the literal-parenthesis request. No special-casing was needed in this
  adapter for the parentheses or underscores a title carries.
- **Sentinel far-future end, measured.** A request ending
  `.../2026082100/2100010100` (year 2100) answered 200 and returned exactly
  the days the origin actually holds (eleven, through `2026083100`, the
  latest day loaded when this was measured) rather than erroring or
  returning nothing past the last real day. This is what
  `FAR_FUTURE_END = "2100010100"` spends for a `window_start` with no
  `window_end`: deterministic, never derived from the wall clock, so the
  same open-ended window builds byte-identical requests every time.
- **404, with a JSON detail sentence.** A title/range combination the
  origin holds no data for (tried: a nonexistent article) answered 404
  with `{"detail": "The date(s) you used are valid, but we either do not
  have data for those date(s), or the project you asked for is not loaded
  yet...", "method": "get", "status": 404, "title": "Not Found", ...}`.
  This adapter reads `detail` and rides it as part of the `http_status`
  warning, the same shape `open_page`/`reddit_shreddit` warnings carry the
  origin's own words where the origin sent one.
- **Cold 429, then 200.** A first request from a fresh address answered 429
  once, then 200 on the very next attempt (recorded in the task brief that
  seeded this build; not independently re-measured in this session beyond
  the fact that no read in this session's measurements above needed a
  retry). The package's own pacing and cooldown default
  (`DEFAULT_COOLDOWN_MS`, unchanged from the placeholder's declared
  `min_interval_ms=1000, burst=1`) are read as covering this; nothing in
  `fetch_native_page` retries.
- **`de.wikipedia:Berlin` grammar**, measured live: `GET .../de.wikipedia/`
  `all-access/all-agents/Berlin/daily/2026082900/2026083100` answered 200
  with `project: "de.wikipedia"` on every row — the `<project>:<article>`
  prefix reaches a non-default project cleanly.

## Design decisions

- **The window is the path, not a parameter.** `start`/`end` are two of the
  route's seven declared `path_params`
  (`_support/route_contracts.py:WIKIMEDIA_PAGEVIEWS_ROUTE`), so there is no
  valid URL to build without both. A hydration naming no `window_start` is
  refused in `fetch_native_page` before any call — `outcome="refused"`,
  `loss=("unselected_target",)` — mirroring `open_page`'s pre-call refusal
  of an address its policy will not read. This is the one adapter in the
  roster (checked: `gdelt` and `stack_exchange`, the roster's other two
  `WINDOW_REACH[...] == True` origins already shipped, both degrade an
  unwindowed call gracefully by omitting optional query parameters — their
  grammar has an unwindowed shape at all) whose grammar has none.
- **`smoke.probe_step` only ever sets `window_start`, never `window_end`**
  (`_support/smoke_plan.probe_window_start`), confirmed by reading it before
  writing this adapter. That is why the sentinel path
  (`FAR_FUTURE_END` on a `window_start`-only call) is load-bearing: without
  it, every liveness smoke of this adapter would refuse on its own
  `window_end`-less step and report `wikimedia_pageviews` unreachable
  forever, which would be wrong — the live read above is genuinely healthy.
- **Identity and locator are composed from the row's own fields, not
  request echoes.** `native_item_id = project + "/" + article + "/" +
  timestamp` and `canonical_locator = "https://" + project + ".org/wiki/" +
  article` both read the origin's own answer rather than the parsed
  request, so an origin-side title normalization (capitalization, etc.)
  would still be reflected correctly. No full host literal is spelled in
  the adapter source — `tests/test_transport_cases/route_ownership.py`
  bans the exact `route.origin` string (`https://wikimedia.org`) outside
  the declared route-owning modules, so the docstring above avoids writing
  the measured URLs with their scheme+host prefix.
- **`date_precision_only` is standing loss**, declared once on
  `DESCRIPTOR.standing_loss` rather than attached per record: every row
  this route will ever answer is day-precision, the same shape
  `linkedin_jobs` uses for its own always-a-day fact.
- **`views` is omitted, never zeroed, when the row's own value is not a
  clean non-negative int** — the same "a count nobody reported is not
  zero" rule `reddit_archive`/`stocktwits` already hold to, and a defensive
  guard against `normalize.engagement_snapshots` raising on a value outside
  its admitted range (not observed live; `stack_exchange`'s draft notes
  record hitting exactly this failure mode for a different adapter's
  negative `score`, which is why this adapter filters proactively rather
  than trusting the origin never to send something `normalize` would
  reject).

## Known cross-cutting test conflicts (not this adapter's files to fix)

Three shared test files build a **windowless** `AdapterRequest` for every
adapter in the roster and assert exactly one origin call resulted. Because
this route's grammar has no windowless shape at all (see above), those three
assertions fail specifically for `wikimedia_pageviews`, and no code change
inside this adapter's own owned files can satisfy them without abandoning
the refuse-before-call design the task brief specifies verbatim (and which
`protocol.md`'s roster row already commits to in prose: "a step here with no
window is refused rather than defaulted"):

1. `tests/test_adapters_cases/unrecognized_and_roster.py::RosterIsCompleteTest`
   `.test_every_listed_adapter_resolves_to_a_descriptor_and_to_a_call` — asserts
   `len(opener.opened) == 1` for a windowless `AdapterRequest` built straight
   from each adapter's `SmokeProbe`, ignoring the probe's own `window_days`.
2. `tests/test_pipeline_cases/failure.py::AdapterBranchTest` — the same shape.
3. `tests/test_window_reach_roster.py::DeclarationMatchesBehaviorAcrossTheRosterTest`
   `.test_every_declared_can_sends_a_different_request_when_windowed` — for
   every probe whose declared operation is `WINDOW_REACH[...] == True`, forces
   `window_days=0` (i.e. no `window_start`) for the "unwindowed" half of its
   comparison and indexes `opener.opened[0]`, which is empty here.

None of these three files is in this task's "files you own" list, so they
were left unedited. A minimal fix for all three would be the same shape:
special-case (or generalize) the assertion so an adapter's windowless call
is allowed to be a typed, no-call refusal rather than requiring exactly one
transport call — likely a `_support/window_reach.py`-keyed exemption list,
or reading each probe's own `window_days` instead of forcing zero. Reopens
whoever reconciles the windowed-adapter batch (`gdelt`, `stack_exchange`,
`wikimedia_pageviews`, `scholarly` all share `WINDOW_REACH[...] == True`, and
`wikimedia_pageviews` is the only one of the four with no windowless shape).

## Deferrals

- **`top-viewed-articles` and other pageviews endpoints not shipped.** Only
  `per-article` is wired. The Wikimedia REST API also serves per-project
  and top-N endpoints under the same `metrics/pageviews` family; none of
  those is measured or declared. Reopens if a caller needs "what was
  trending" rather than "how much attention did this one article get."
- **`access`/`agent` are not caller-selectable.** Every call sends the
  fixed `all-access`/`all-agents` pair (`ACCESS`, `AGENT` constants) rather
  than exposing `desktop`/`mobile-web`/`mobile-app` or `user`/`spider`
  splits the origin also serves. Reopens if a caller needs a device- or
  bot-filtered count rather than the combined total.
- **Hourly granularity not shipped.** `GRANULARITY` is fixed to `"daily"`;
  the origin also serves `"monthly"`. Both would need a different
  `date_precision_only` story (monthly is coarser still) and are out of
  scope for the "attention over time" roster row as specified.
