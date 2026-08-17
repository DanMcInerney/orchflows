# super-research operating surface

The operator's side of [protocol.md](protocol.md): the command line this package
exposes, and the one bounded read each adapter's smoke makes.

## CLI surface

`python3 -m super_research.cli`, with this item's `scripts/` on `PYTHONPATH`.
Three operations, one argument, twenty-one reachable invocations. The parser is built
from the `OPERATIONS` table, so the enumeration a reader checks is the one the
parser was made from.

| operation | argument | reaches an origin | writes | exit |
| --- | --- | --- | --- | --- |
| `adapters` | none | no | nothing | 0 |
| `smoke` | `--adapter <one of nineteen>`, required | one bounded read | one of its two records: the ledger on success, the unmet record on a row the origin answered and did not carry, neither otherwise | 0 / 1 / 3 |
| `status` | none | no | nothing | 0 always |

`python3 -m super_research.cli adapters` prints the nineteen live adapters, the
access class each declares, and the field set its smoke asserts; the offline
`fake` adapter has no smoke and is not on that list. The roster's routes were
measured from one host on 2026-08-10, two sweeps on 2026-08-12 read them
against real origins, and a third sweep on 2026-08-17 measured the routes this
revision adds and reversed three earlier findings; what each of those found is
in [evidence.md](evidence.md) §"Route measurements of 2026-08-10",
§"The two liveness sweeps of 2026-08-12" and §"The route sweep of 2026-08-17". `status` still reports every adapter
`unverified` until `smoke --adapter <id>` makes one bounded read that carries
that adapter's row: the smoke ledger lives in a tempdir and never travels with a
checkout.

No operation takes an address, a route, a path, a manifest, or a command;
`--adapter` is a closed `choices` list of the nineteen live ids. `fake` is refused
with everything else: reading a fixture and printing it as liveness is the one
result this surface must never produce. The carrier, clock, moment, ledger path
and output stream are parameters of `main` with the real defaults and are
unreachable from a command line, which is how the whole path is exercised offline.

Exit codes: `0` the roster row was carried; `1` the origin answered and the row was
not carried; `2` argparse's own usage error, taken by nothing else here; `3` this
host's local network answered, **or nothing answered at all**, so nothing about
the platform was concluded. `1` and `3` are separate doors because they are not
the same news. A refused connection, an unresolvable name, or a TLS failure
raises `TransportError` out of the opener rather than becoming a typed page,
because there was no answer to type; `cli.main` catches it and takes `3`, and
records nothing. Letting it leave as a traceback would take `1` — a cable
nobody plugged in, filed as a row the origin declined to carry.

Two dispositions and no third: `verified` and `unverified`. Rejecting a platform
is not something this package does from one read, so `rejected` is not in the
vocabulary at all and "never degrades to rejected" is structural rather than a
branch someone has to remember. Reasons are `fresh_success`, `never_smoked`,
`read_and_row_unmet`, `stale_success`, `unreadable_last_success`,
`last_success_ahead_of_now`. The window is seven days, because every route here
depends on markup or on a vendor identifier that rotates without notice.

`never_smoked` asserts that no read has ever reached this adapter's origin, and
`read_and_row_unmet` that one did — at the instant it reports — and came back
without the row. It claims no cause: a challenge status, a refused
authorization, a withheld payload and a parser that dropped a field all reach it
alike, and the state stays `unverified` for all of them. Nothing about a
platform is concluded by either.

**Two records, and each holds one fact.** The ledger is one JSON object of
adapter id to ISO stamp at `<tempdir>/super-research/smoke-ledger.json`, holding
the last read that carried an adapter's whole row. Beside it, at
`smoke-ledger-unmet.json`, one more of the same shape, holding the last read
that reached an origin and did not. Both are constants no argument can point
elsewhere: the second is derived from the path handed to `main`, so a caller who
redirects the ledger cannot leave half the state behind in the other directory.

Each record only ever gains an entry, and a read lands in exactly one of them. A
read that carried its whole row, from the origin, stamps the ledger; one the
origin answered without the row stamps the unmet record; a read this host's own
network answered stamps neither, because the origin was never reached and that is
not a read of the platform at all. A blocked read is not a finding about the
platform, and a failed read has not undone a success already recorded — the
ledger is never written by a failure, so a reader that only asks whether an
adapter is in it gets the answer it always gave. Expiry happens by the window
passing, never by a later read revoking an earlier one, and it expires a success
rather than the fact of a read: seven days on, a stale success and a read that
went unmet still report different reasons. Either record unreadable reads as
empty, which costs an adapter its evidence and never invents any — `unverified`
where the ledger is lost, `never_smoked` where the unmet record is, both the
safe direction.

## Running a manifest

The CLI runs no manifest, by design; a caller runs one in process, from a
file it wrote, and never from a value it holds in memory — the file is the
guard. Write the manifest, then run exactly this, with `scripts/` on
`PYTHONPATH`, in a lane-private directory (two lanes sharing `step_a.json`
was the 2026-08-17 bakeoff's most expensive accident):

```
python -c "import dataclasses, json, sys
from super_research import runner, schema
manifest = schema.parse_manifest(json.load(open(sys.argv[1], encoding='utf-8')))
print(manifest.manifest_id, manifest.as_of, manifest.mode, len(manifest.steps), 'steps')
artifact = runner.run_acquisition(manifest)
json.dump(dataclasses.asdict(artifact), open(sys.argv[2], 'w', encoding='utf-8'), indent=1)
print(artifact.outcome, artifact.loss, len(artifact.records), 'records')
" manifest.json artifact.json
```

`parse_manifest` is total and reads the file the caller re-reads, so the id,
horizon, mode and step count it prints are the ones about to run: compare them
to what was intended and stop before any transport call if they differ. Read
each `StepResult`'s `outcome`, `loss` and `warnings` before any record.

A `fused` manifest naming several adapters runs them as concurrent lanes; a
`staged` one runs serially. To pin serial execution on a fused manifest —
for a replay whose timing must match — pass `lanes=1` to `run_acquisition`.
Set `window_start`/`window_end` on every step whose question has a window, so
the cap is spent inside it. Order afterwards with `runner.order_records` at an
`as_of` at or after the run's own reads (`ordering.observation_horizon`
gives the smallest such moment), and rank on topic with
`relevance.compile_query` / `relevance.rank` / `relevance.partition`, reading
the dropped list before applying any floor.

## Smoke inventory

One probe per live adapter, in `probes.py`. Each is one ordinary manifest step,
not a private path into an adapter, and its assertion is that **one record of the
named kind carries the whole list** — a row assembled out of several records would
claim a completeness no single answer had. `engagement:` and `attribute:` prefixes
name the two places a route's own vocabulary lands.

| adapter | route | probe | field set asserted |
| --- | --- | --- | --- |
| `web_search` | `ddg_html` | discovery `rate limiting` | web_hit: title, canonical_locator, body |
| `public_page` | `public_page_article` | hydration `article:Rate_limiting` | web_page: body, exact_content_hash, observed_at, attribute:content_type, attribute:link, attribute:requested_url, attribute:final_url |
| `reddit_archive` | `arctic_shift_posts_ids` | hydration `z1c9z` | post: title, author, community, canonical_locator, published_at, engagement:score, engagement:num_comments |
| `reddit_feed` | `reddit_feed` | discovery `programming` | post: title, author, canonical_locator, published_at |
| `x_syndication` | `x_syndication_timeline` | hydration `simonw` | post: body, published_at, native_parent_id, engagement:favorite_count, engagement:retweet_count, engagement:reply_count, engagement:quote_count |
| `x_guest` | `x_guest_graphql` | hydration `user:simonw` | profile: native_item_id, title, author, canonical_locator, published_at, engagement:followers_count |
| `linkedin_public` | `linkedin_public_profile` | hydration `williamhgates` | profile: title, body, attribute:jobTitle, attribute:addressLocality, attribute:worksFor, attribute:alumniOf |
| `linkedin_jobs` | `linkedin_jobs_guest_search` | discovery `reliability engineer` | job_posting: native_item_id, title, author, published_at |
| `youtube_innertube` | `youtube_innertube` | hydration `dQw4w9WgXcQ` | video: title, published_at, engagement:viewCount |
| `instagram_public` | `instagram_web_profile` | hydration `instagram` | profile: title, author, body, engagement:edge_followed_by.count; **and** post: native_item_id, published_at, engagement:edge_liked_by.count, engagement:edge_media_to_comment.count |
| `hacker_news` | `hn_algolia_search` | discovery `python` | story: title, author, published_at, engagement:points, engagement:num_comments |
| `github_rest` | `github_rest` | hydration `python/cpython` | repository: title, body, author, published_at, engagement:stargazers_count, engagement:forks_count, engagement:open_issues_count |
| `rss_atom` | `youtube_channel_feed` | discovery `UC_x5XG1OV2P6uZZ5FSM9Ttw` | feed_entry: native_item_id, title, author, canonical_locator, published_at |
| `reddit_shreddit` | `reddit_shreddit_listing` | discovery `listing:programming` | post: native_item_id, title, author, community, canonical_locator, published_at, engagement:score, engagement:comment-count |
| `open_page` | `web_page_open` | hydration `https://www.iana.org/help/example-domains` | web_page: title, body, exact_content_hash, observed_at, attribute:content_type, attribute:requested_url, attribute:final_url, attribute:link |
| `prediction_markets` | `polymarket_gamma` | discovery `polymarket:SpaceX` | market: native_item_id, title, canonical_locator, attribute:outcomes, attribute:outcomePrices |
| `stocktwits` | `stocktwits_symbol_stream` | discovery `stream:AAPL` | post: native_item_id, body, author, canonical_locator, published_at |
| `bluesky` | `bluesky_author_feed` | discovery `author:bsky.app` | post: body, author, canonical_locator, published_at, engagement:likeCount, engagement:replyCount, attribute:did, attribute:cid |
| `x_fxtwitter` | `fxtwitter_api` | discovery `search:spacex` | post: body, author, canonical_locator, published_at, engagement:likes, engagement:reposts, engagement:replies, attribute:lang, attribute:created_at |

Instagram's is the only row describing two content kinds, which is why a field set
is declared per kind at all: no single record carries both the profile's follower
count and a post's like count. Seven adapters read more than one surface and a smoke
makes one call, so each probe names the surface it takes — Algolia search for
`hacker_news`, the repository surface for `github_rest`, the article surface for
`public_page`, DuckDuckGo for `web_search`, the subreddit listing for
`reddit_shreddit` (the one surface that names both counts as its own
attributes), Polymarket for `prediction_markets`, and the symbol stream for
`stocktwits`.

Three probes are worth reading twice. `bluesky`'s names the **author feed**
rather than the search its primary descriptor declares: the search method
answered 403 from the CDN in front of the public AppView on this host, and a
smoke on it would report a working adapter dead. `open_page`'s target is a document on a host
no other route declares, because an open read that landed on a declared host is
refused by policy and a refusal is not a liveness answer. And
`prediction_markets`' target is a subject somebody is actually trading: a query
matching nothing there is an honest empty answer and a useless liveness check,
which is the same reason `stocktwits` smokes a ticker whose stream never goes
quiet.

A probe target can rot without the route changing, and a removed target and a
broken route both come back with no row. Every probe whose target is a named item,
slug, channel, or handle therefore declares `target_recovery`: how to obtain a
current one. A query never goes stale and declares none.
