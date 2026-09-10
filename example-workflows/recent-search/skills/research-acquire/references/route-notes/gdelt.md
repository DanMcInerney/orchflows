# gdelt draft notes

Working notes from implementing the `gdelt` adapter (K4, `gdelt_doc`). Not
yet folded into `protocol.md` beyond the roster row that was already wired
before this delivery — the loss-vocabulary cells below are new source that
`protocol.md`'s `"named by"` tables do not yet reflect (see "Known open
item" below; several other in-flight adapters have the identical gap).

## Measured facts (2026-09-01, this host)

- HTTPS to `api.gdeltproject.org` times out at connect on every attempt —
  curl and this package's own opener alike (`WinError 10060`). Plain HTTP
  to the same host answers normally. The transport admits https only
  (`transport.urlopen_read` refuses a non-https url), so the live smoke
  from this host types `unreachable` and concludes nothing about the
  platform; every fact below was captured over plain HTTP as test
  evidence only. The shipped module never sends anything but https.
- `GET http://api.gdeltproject.org/api/v2/doc/doc?query=climate&mode=`
  `artlist&format=json&maxrecords=75&startdatetime=20260829000000&`
  `enddatetime=20260901000000` answered keyless 200,
  `Content-Type: application/json; charset=utf-8`, 75 rows in a ~38 KB
  body — `maxrecords` honored exactly.
- Each row: `url`, `url_mobile` (blank on most rows, populated on some —
  an AMP/mobile variant), `title`, `seendate` (`YYYYMMDDTHHMMSSZ`),
  `socialimage` (often blank), `domain`, `language`, `sourcecountry`. No
  native id, no author, no engagement count of any kind.
- **A query matching nothing answers 200 with the literal body `{}`** — no
  `articles` key at all. Reproduced twice, on two distinct nonsense
  queries (one a bare unmatched string, one a real query dated into an
  empty span). This is the origin's own documented way of saying "nothing
  matched," not a reshaped payload — see "Decisions" below for why this
  module reads it as `outcome="empty"` rather than `schema_drift`.
- A `startdatetime` outside the origin's retained span (tried:
  `19900101000000`–`19900102000000`) answered 200,
  `Content-Type: text/html; charset=utf-8`, body exactly
  `Invalid query start date.` — plain text, never JSON.
- `mode=badmode` answered 200, `Content-Type: text/html; charset=utf-8`,
  with its own response headers echoed into the body ahead of the
  complaint (`Content-type: text/html; charset=utf-8\nServer: GDELT API`
  `Server 2.0\n...\n\nInvalid mode.`) — also plain text, never JSON.
- The origin's own stated ceiling, in a plain-text 429 body also measured
  2026-09-01, is one request per five seconds (`DESCRIPTOR.min_interval_ms`
  is set to 5000 accordingly; this was pre-wired in the placeholder
  descriptor and left unchanged).
- Windowed reads: `startdatetime`/`enddatetime` (`YYYYMMDDHHMMSS`, no
  separators, no trailing zone letter) genuinely filter — every `seendate`
  on a bounded read fell inside the requested span.

## Decisions

- **A missing `articles` key is read as `empty`, not `schema_drift`.** The
  task brief that started this delivery specified "JSON without the
  articles list → schema_drift," written before this measurement. Given
  GDELT's own no-match answer is a bare `{}` (measured twice, described
  above), reading a missing `articles` key as drift would mislabel the
  origin's ordinary "nothing matched" answer as a broken parser on every
  query nothing matches. `_articles_page` in `adapters/gdelt.py` instead
  reserves `schema_drift` for three shapes, none observed live: a
  top-level body that is not a JSON object at all, an `articles` key
  present and not a list, and a nonempty `articles` list none of whose
  rows carry a `url`. An explicit `{"articles": []}` (never observed, but
  a plausible variant) is handled the same as the bare `{}` — both read as
  `outcome="empty"`.
- **`malformed_json` covers both measured rejection shapes.** A rejected
  request's body is plain text either way (`Invalid query start date.`,
  and the header-echoing `Invalid mode.` shape), so one `try: json.loads`
  / `except ValueError` branch in `_page_from` types both, the same way
  `stocktwits`/`stack_exchange` type any other 200 this parser cannot read
  as JSON.
- **Standing loss: three of `web_search`'s four, not all four.** GDELT
  states a time on every measured row, so `unknown_publication_time` never
  stands here — the module docstring and `probes.SmokeProbe`'s asserted
  `published_at` field both depend on this. `native_identity_unknown`,
  `engagement_unavailable` and `target_not_hydrated` stand on every kept
  record, attached via `DESCRIPTOR.standing_loss` and read off it in
  `_record_for`, mirroring how `web_search.DESCRIPTOR.standing_loss` feeds
  its own `_record_for`.
- **`request.target_ids` is never read.** This module mirrors
  `web_search`'s own omission: `fetch_native_page` reads `request.query`
  alone. A hydration-shaped request (its `AdapterRequest.query` the empty
  string a hydration step's `planned_calls` always builds) is served as an
  empty-query discovery would be — the empty `query` param is then dropped
  entirely before the request reaches the wire
  (`_support.transport_request.build_transport_request` drops any
  parameter whose value is `""`), so the origin sees a plain
  `mode=artlist&format=json&maxrecords=75` request and, per the measured
  fact above, answers `{}`. Covered by
  `tests/test_gdelt.py::FixedShapeAndQueryTest`.
- **No `field_omitted`.** The task brief's field list (`title`,
  `canonical_locator`, `published_at`, `attribute:domain`,
  `attribute:language`, `attribute:sourcecountry`) does not mention this
  code, and every field this module reads was present on every row of the
  measured 75-row page; language/sourcecountry are omitted from the
  attribute tuple per-row when absent rather than triggering a code, the
  same "only when present" rule the task brief states for those two.
- **`native_position` keeps the origin's own array index, gaps included.**
  A row skipped for carrying no `url` leaves a gap in `native_position`
  rather than being renumbered out — the same convention `web_search`'s
  `_DuckDuckGoResultParser`-derived records use (`enumerate(parser.hits)`,
  filtered afterward), chosen over the compacted `len(records)` convention
  `stocktwits`/`stack_exchange` use, because GDELT is the other declared
  index/K4 surface `native_position` fidelity to the origin's own ordinal
  matters most for.

## Probe / window-reach state

No change was needed to either file:

- `probes.py`'s `SmokeProbe(adapter_id="gdelt", ...)` already declared
  `target="climate"`, `window_days=3`, and the exact field set this
  delivery ships (`title`, `canonical_locator`, `published_at`,
  `attribute:domain`) before this delivery began — the measurement above
  confirms it is satisfiable by a live 200.
- `_support/window_reach.WINDOW_REACH["gdelt"] = {"": True}` already
  declared before this delivery began, and the measured fact above (a
  bounded read returning only in-window `seendate`s) confirms it.
  `tests/test_window_reach_roster.py` and `tests/test_gdelt.py::WindowTest`
  both prove it off the wire.

## Known open item (not this module's to fix)

`tests/test_dependency_boundary_cases/loss_vocabulary.py`'s
`LossVocabularyIsReadOffTheSourceTest` checks `protocol.md`'s
`"named by"` cells against what the package's source actually spells, and
this delivery adds `gdelt` as a speller of `schema_drift`, `malformed_json`,
`http_status`, `native_identity_unknown`, `engagement_unavailable` and
`target_not_hydrated` — six cells `protocol.md` does not yet list it under.
Fixing this means editing `references/protocol.md`'s loss-vocabulary
tables, which is outside this delivery's file ownership (several other
adapters landing in this same tree concurrently — `oembed`,
`wikimedia_pageviews`, `stack_exchange` were all observed in the same red
state during this run) and reads as a single consolidated pass once every
adapter in the batch has landed, rather than one this module's own PR
should take alone.

## Deferrals

- **`mode=timelinevol` not shipped.** Not tried live during this delivery;
  no measurement exists either way. Reopens on a request for GDELT's time-
  series/volume surface rather than its article index.
- **`mode=context` not shipped.** Tried live 2026-09-01: every query tried
  answered 200 with an empty `articles` list — GDELT's own documentation
  describes this mode as returning contextual snippets around a match, and
  nothing tried here produced one. Reopens if a later measurement finds a
  query that returns nonempty context rows, or if GDELT's own docs are
  read closely enough to explain the empty answer (a paid-tier gate, a
  different required parameter, etc.) — neither was investigated further
  here since `artlist` alone satisfies this delivery's roster row.
- **`sourcelang`, `sourcecountry`, `timezoom`, `timespan` and other artlist
  query parameters are not exposed.** Only `query`, `mode`, `format`,
  `maxrecords`, `startdatetime` and `enddatetime` are sent. Reopens if a
  caller needs to filter by source language/country at the origin, or
  needs a relative `timespan` window instead of absolute
  `startdatetime`/`enddatetime` edges.
