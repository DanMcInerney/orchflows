# `scholarly` — build notes

Draft evidence for the `scholarly` adapter (`adapters/scholarly.py` +
`adapters/_support/scholarly_records.py`). Not yet folded into
`references/evidence.md` or `references/protocol.md`'s roster prose beyond
the one roster-table row and the loss-vocabulary cells already present.

## Measured facts, 2026-09-01, all three keyless and 200

### OpenAlex — `openalex_works` (`api.openalex.org/works`)

`GET ?search=<q>&per-page=25`, plus `&filter=from_publication_date:` `YYYY-MM-DD` `,to_publication_date:YYYY-MM-DD` when a window edge is present.
Answers `{"meta": {"count", ...}, "results": [...]}`; a query nothing
matches answers the same shape with an empty `results` list, not a missing
key. No `sort=` is sent, so the native order is OpenAlex's own relevance
ranking (visible in the answer as `meta.x_query`).

A work: `id` (`https://openalex.org/W...`, doubles as this module's
`canonical_locator` — the origin publishes no separate landing address for
the work itself, only for its primary location), `display_name`,
`type` (`"article"`, `"book-chapter"`, `"monograph"`, `"other"`,
`"book-review"` all measured on one page of "machine learning" hits —
carried verbatim as `canonical_content_kind`), `publication_date`
(`YYYY-MM-DD`, never a time), `cited_by_count` (json int),
`authorships[].author.display_name` (repeated), `ids.doi`,
`primary_location.landing_page_url`.

No `mailto=` sent. OpenAlex's docs offer a faster "polite pool" lane in
exchange for one; this package attaches no identity a route constant does
not spell, and a caller's email is not one.

### Crossref — `crossref_works` (`api.crossref.org/works`)

`GET ?query=<q>&rows=20`, plus `&filter=from-pub-date:YYYY-MM-DD` `,until-pub-date:YYYY-MM-DD` when a window edge is present.
Answers `{"message": {"items": [...], "total-results", ...}}`, empty the
same way (`items: []`, key present). No `sort=` sent, so order is
Crossref's own relevance score (visible on each item as `score`).

An item: `DOI`, `type` (`"journal-article"`, `"book-chapter"`,
`"monograph"`, `"posted-content"`, `"reference-entry"`, `"other"`,
`"edited-book"` all measured), `title` (**an array** — `title[0]` is read;
measured always length 1 or a missing key, never observed longer),
`author[].given`/`.family` (Crossref's own docs say `family` "may be
absent on some types"; measured confirms it — several `edited-book` and
`book-chapter` rows in the 2015 "machine learning" window carried no
`author` key at all), `published.date-parts` — `[[Y, M, D]]` with the day
sometimes omitted (`[[Y, M]]`, measured on several `journal-article` rows)
and the month sometimes omitted too (`[[Y]]`, measured on several 2015
book chapters), `is-referenced-by-count`, `URL` (a `doi.org` redirect,
always present on the measured page), `container-title` (array),
`publisher`.

No `mailto=` sent, same reasoning as OpenAlex.

### arXiv — `arxiv_query` (`export.arxiv.org/api/query`)

`GET ?search_query=all:"<q>"[+AND+submittedDate:[YYYYMMDDHHMM+TO+YYYYMMDDHHMM]]&start=0&max_results=10`.
Answers Atom XML, `Content-Type: application/atom+xml; charset=utf-8`. A
query nothing matches answers a `<feed>` with zero `<entry>` and
`opensearch:totalResults` of `0` — measured live. No `sortBy=`/`sortOrder=`
sent, so order is arXiv's own relevance ranking.

An entry: `id` (a versioned `http://arxiv.org/abs/...` address — measured
as **`http`**, not `https`; never used as `canonical_locator` for that
reason), `title`, `published`/`updated` (full `...Z` instants — `published`
is read as the authoritative, unqualified time; `updated` is not read at
all, unlike `rss_atom`'s own `published`-then-`updated` fallback, because
arXiv's measured entries have always carried `published`), repeated
`<author><name>`, `summary` (carried as `body`, whitespace-normalized —
arXiv wraps it across lines), and two `<link>`: `rel="alternate"
type="text/html"` (this module's `canonical_locator`) and `rel="related"
type="application/pdf"` (carried as the `pdf_url` attribute — this
module's own name, since arXiv states no flat field for it).

**Phrase quoting matters.** `all:machine learning` (unquoted) is read by
arXiv as `all:machine OR all:learning` — measured live, visible in the
answer's own restated `<title>`. `all:"machine learning"` (quoted) is read
as the phrase. This module always quotes the caller's argument for that
reason; a single-word argument quotes to a trivial phrase and is
unaffected.

## Loss constants

`SCHEMA_DRIFT` (`"schema_drift"`), `MALFORMED_JSON` (`"malformed_json"`,
OpenAlex and Crossref only — arXiv is XML and a document not rooted in
`<feed>` is `schema_drift`, mirroring `rss_atom`), `HTTP_STATUS`
(`"http_status"`), `FIELD_OMITTED` (`"field_omitted"`, spelled from
`_support/scholarly_records.py`), `DATE_PRECISION_ONLY`
(`"date_precision_only"`, standing on OpenAlex's descriptor — see below —
and per-record on Crossref).

## Decisions

**Author composition (Crossref).** `"{given} {family}"` when both are
present, `family` alone when `given` is absent, `given` alone when
`family` is (the documented absence), nothing when neither is. Never a
fabricated surname. Only OpenAlex and arXiv get repeated `("author", name)`
attributes for every author; Crossref does not — the roster's own field
set only asks for the singular `author` field there, and Crossref's
`author[]` already carries `sequence`/`affiliation`/`role` this module
does not read, so a repeated-attribute mirror of it would imply a
completeness this module does not have.

**Crossref month/year precision.** A day makes an instant (midnight UTC,
`date_precision_only` attached — the same day-to-instant convention
`openalex_date_to_instant`/`linkedin_jobs.route_day_to_utc_iso` use). A
month or a year alone makes **no instant at all** — `published_at` is left
empty, and the exact `date-parts` ride verbatim (never padded, never a day
invented) under this module's own attribute name,
`published_date_parts`, joined by `-`: `[2015, 4]` → `"2015-4"`, `[2015]` →
`"2015"`. This is deliberately asymmetric with OpenAlex, whose descriptor
carries `date_precision_only` as a **standing** loss (every work this
route will ever answer states a day and never a time — the same reasoning
`linkedin_jobs.DESCRIPTOR.standing_loss` already carries) — Crossref's
same code is **per-record**, because the same route answers day-, month-
and year-precision dates on one page and a standing declaration would be
false for the two-thirds of the measured "machine learning"/2015 page that
carried no day at all.

**arXiv range sentinel.** arXiv's `submittedDate:[A TO B]` grammar takes
two ends; there is no measured open-ended form. A caller naming only one
edge still gets a genuinely narrowed read, via a spelled sentinel for the
missing one: `ARXIV_FAR_FUTURE = "210001010000"` (year 2100) for a missing
end, `ARXIV_FAR_PAST = "190001010000"` (year 1900, decades before arXiv's
1991 founding) for a missing start. Both measured live returning 200 with
plausible narrowed results. The naive floor, year 1
(`"000101010000"`), was tried first and measured refusing with HTTP 500 —
`datetime` in this module's own `instant_to_arxiv_stamp` would happily
format it, so the sentinel is a value this module chose because it is
known to work, not the calendar's own minimum.

**Sort orders.** All three: relevance/native search ranking, because none
of the three params this module sends includes a `sort=`/`sortBy=`
argument — OpenAlex's own `x_query.oql`, Crossref's per-item `score`, and
arXiv's documented default all confirm it. `NATIVE_ORDERS` names them
`openalex_relevance_order`, `crossref_relevance_order`,
`arxiv_relevance_order`.

## Deferrals

- **OpenAlex cursor paging.** OpenAlex offers `cursor=*` for deep paging
  past `page`'s 10k-result ceiling; this module reads the origin's first
  page only and surfaces no `cursor_out`. Reopens if a caller needs more
  than 25 works per query — the roster's cap authorizes one call per step
  today, so the gap is not yet load-bearing.
- **Crossref deep paging.** Same shape: Crossref accepts `rows=`/`offset=`
  (shallow) and a `cursor=*` token (deep, past ~10k rows); neither is
  read. Reopens on the same condition as OpenAlex's.
- **arXiv `start=`/paging.** `start=0` is always sent; a caller's cursor is
  not spent as an offset. Reopens the same way.
- **arXiv's `updated`-only fallback.** `rss_atom` falls back from
  `published` to `updated` when a feed omits the former; this module does
  not, because every measured arXiv entry carried `published`. Reopens if
  a live entry is found answering `updated` alone.
- **The `mailto` etiquette lane, both JSON origins.** Deliberately not
  sent — this package attaches no identity a route constant does not
  spell. Not expected to reopen; a route constant could name one as a
  documented, spelled identity, the same way any other credential-shaped
  identifier in this roster would have to.
