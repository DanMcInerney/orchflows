# stack_exchange draft notes

Working notes from implementing the `stack_exchange` adapter (K0,
`stackexchange_search_advanced`). Not yet folded into `protocol.md` beyond
the three loss-vocabulary cells and the roster row that were already
required for the suite to pass.

## Measured facts (2026-09-01, live)

- `GET https://api.stackexchange.com/2.3/search/advanced?site=stackoverflow`
  `&q=python&pagesize=30&order=desc&sort=creation` answers keyless 200.
- Body: `{"items": [...], "has_more": bool, "quota_max": 300,`
  `"quota_remaining": N}`. `quota_remaining` was 293 immediately after one
  read that started at 300 that day — one read costs one point.
- Every item carried `question_id` (int), `title` (HTML-entity-escaped —
  `Can&#39;t get virtual environment to activate...` was one of thirty),
  `owner.display_name`, `is_answered` (bool), `view_count`, `answer_count`,
  `score` (signed — several items on the same page answered `-3` through
  `-10`), `creation_date`/`last_activity_date` (unix seconds), `link`,
  `tags` (list of strings). `last_edit_date`, `content_license`,
  `closed_date`, `closed_reason` and `accepted_answer_id` were present on
  some rows and absent on others; none of the five is read by this adapter.
- `page=2` returned thirty different `question_id`s with its own `has_more`;
  the origin never states which page answered, only whether another exists.
- `fromdate=1735689600&todate=1738368000` (unix seconds) returned only rows
  whose `creation_date` fell inside that range — genuinely filters.
- `site=serverfault&q=reverse+proxy` returned `serverfault.com` links —
  `site` genuinely selects the origin's per-site index.
- A query nothing matches answers 200 with `{"items": [], "has_more": false,`
  `"quota_max": ..., "quota_remaining": ...}"` rather than an error status.
- Via this package's own opener (`urllib`, no `Accept-Encoding` header sent)
  the answer still arrived `Content-Encoding: gzip` — `transport.decoded_body`
  already handles this generically (built for this route specifically,
  per its own docstring) and needed no adapter-side change.
- Response `Content-Type` measured: `application/json; charset=utf-8`,
  matching the `PROBE_PAYLOADS` entry that was already wired in
  `tests/test_cli_cases/_support.py`.

## Decisions

- **Title unescaping.** `html.unescape` is applied to `title` because the
  route documents its titles as HTML-entity-encoded for embedding
  (confirmed live: `&#39;` for an apostrophe). Reading that back out is
  reading the route's own stated encoding, the same move `rss_atom` makes
  on its feed text, not an invented transform.
- **Sort choice: `creation` over relevance.** Stack Exchange's `search/`
  `advanced` supports a `relevance` sort, deliberately not taken. Relevance
  is not a metric this roster can snapshot and later re-derive the same way
  twice, and — more concretely — a windowed read on `creation` order spends
  the origin's own recency ordering *inside* the caller's window, where
  `fromdate`/`todate` narrow what the origin returns rather than trimming
  what this adapter discards afterward. `order=desc&sort=creation` is sent
  on every call, unconditionally, so the shape is one deterministic request
  rather than one that varies by caller intent.
- **`site:<name> ` grammar.** Measured live against `site:serverfault`. A
  bare `site:` with no following space is read as an ordinary query rather
  than a malformed selection, since nothing here infers a selection from
  characters that only look like one (`site_and_query`'s own docstring
  states the same rule `hacker_news.operation_for` and `stocktwits.`
  `operation_for` already follow for their own prefixes).
- **Negative `score` is dropped, not carried.** Not anticipated in the
  original task brief. `normalize.engagement_snapshots` raises
  `NormalizeError` on any negative int — the artifact's engagement family
  admits only non-negative exact integers — and Stack Exchange's `score`
  is genuinely signed (several items in the captured fixture answer with
  `-3` through `-10`). `exact_count` here returns `None` for a negative
  value, the same shape it already uses for a bool or a non-int, so a
  downvoted question's `answer_count` and `view_count` still carry while
  its `score` is absent rather than the read crashing the whole page.
  Found live: the CLI smoke's field-set assertion crashed with
  `NormalizeError: engagement metric score is out of range` before this
  guard was added, because the captured thirty-item page genuinely
  contains negative scores.
- **Cursor discipline.** The origin states only `has_more`, never which
  page answered. `_next_page` derives the page just spent from the inbound
  `request.cursor` itself (absent means page one) and adds one; `cursor_out`
  is that number, surfaced and never followed by this module, mirroring
  `stocktwits`' `next_max` and `hacker_news`'s `next_page_of`.
- **No `field_omitted`.** Unlike `stocktwits`/`hacker_news`, this adapter
  does not emit `field_omitted` — `protocol.md`'s vocabulary table does not
  list `stack_exchange` under that code, and every field this module reads
  (`title`, `link`, `owner.display_name`, `creation_date`) was present on
  every row of the measured page, so no per-record omission signal was
  wired.

## Quota

The anonymous daily quota (`quota_max`/`quota_remaining`) rides in every
response body. This adapter reads neither field into a record or a
warning — it is not a roster field this route's smoke asserts, and no
lower-severity signal (e.g. "close to exhausted") is derived from it. If a
caller needs to budget across many `stack_exchange` reads in one run, that
would read `quota_remaining` off the raw response, which this module does
not expose today.

## Deferrals

- **Answer hydration.** `/2.3/questions/{id}/answers` is not shipped. This
  route only ever discovers questions; `answer_count` is the exact native
  count already carried, but the answer bodies themselves are not fetched.
  Reopens if a caller needs answer text or per-answer `score` rather than
  the question-level `answer_count` this search already states.
- **Non-`stackoverflow` sites beyond the `site:` override.** No adapter
  code enumerates or validates site names — any string after `site:` is
  sent verbatim as the `site` query parameter, and an invalid site name is
  whatever `http_status` or `schema_drift` the origin's own answer types
  it as. No live probe covers a second site's error shape.
