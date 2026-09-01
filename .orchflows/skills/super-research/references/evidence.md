# Measured evidence behind this package

Three records, distilled. Their full form belongs to the runs that produced them
and is not tracked; this file holds exactly what a tracked document in this item
cites of them, and stops. No credential value appears below.

## Route measurements of 2026-08-10

One macOS host, unauthenticated, no credential supplied to any route. Every row
of that record was a real HTTP response — status, latency, and the key names the
payload actually carried — never a documentation claim. It predates this
package, so every ceiling, field list and route constant this item declares
traces to that one host at that one moment.

What this item cites of it:

- **`linkedin.com/in/<slug>` answered 200 with a complete `ld+json` Person
  block** — `name`, `jobTitle[]`, `addressLocality`, `description`,
  `worksFor[]`, `alumniOf[]`. **`linkedin.com/company/<slug>` answered 200 with
  a marker name and no field set**, so a company parser would be inferred rather
  than measured.
- **Brave and Bing both answered 200 and both resisted extraction** — Brave with
  obfuscated class names, Bing with markup no clean title/locator/snippet triple
  came out of. DuckDuckGo's HTML endpoint answered 200 with ten clean triples,
  which is why one web-index route ships and no second provider does.
- **The two playability statuses.** Across `WEB`, `MWEB`, `TVHTML5`, `ANDROID`
  and `IOS` clients on three videos, the YouTube player answered 200 with
  `UNPLAYABLE` or `ERROR`, and an empty caption track list every time, after the
  first successful metadata read. That is an attestation this package does not
  perform, and those two statuses are what `attestation_required` was named for.

## The captive-portal caveat

The measuring host sits behind a network appliance that intercepts some domains
and answers HTTP 503 with a body containing `<base href="/login/">`. Control
probes confirmed it: `example.com` and `wikipedia.org` returned genuine origin
content, `tiktok.com` and `ecosia.org` returned the portal. Every such row is
network-local and never platform behaviour — the route is unverified, never
rejected. A read that comes back `network_intercepted` is a statement about the
asking network. It never degrades an adapter and never becomes a platform gap.

## The two liveness sweeps of 2026-08-12

Two sweeps, thirteen bounded smoke reads each, one per adapter in roster order,
no retry and no reorder. With one single-read capture taken between them they
spent thirty authorized requests — fifteen, one, fourteen. Same macOS host,
`python3` 3.9.6. These were the first reads any parser in this package had made
against a real origin.

**First sweep.** All thirteen adapters reached a real origin and none was
intercepted. Nine carried their whole roster row and stood `verified`:
`public_page`, `reddit_archive`, `reddit_feed`, `linkedin_public`,
`linkedin_jobs`, `instagram_public`, `hacker_news`, `github_rest`, `rss_atom`.
Four reached an origin and failed their row — `web_search` on a 202 challenge,
`x_guest` on a 401, `youtube_innertube` on a non-`OK` playability typed
`attestation_required`, and `x_syndication` on the one package defect the sweep
found: the origin sent `created_at` on all 100 entries and the package carried
`published_at` on none.

**Second sweep**, after every fix that run made. Nine carried their whole roster
row again, `x_syndication` among them with that defect repaired and measured
against the same live route. Three reached an origin and failed their row and
none of the three was a package defect. `github_rest` reached no one: a
condition of the asking connection, reported as such rather than as a platform
gap, so this sweep neither re-proves nor disproves it. None was intercepted.

**What the sweeps do not cover.** No read touched `hn_firebase_item`,
`github_search`, `public_page_control`, or the `search` and `next` operations of
`youtube_innertube`, so the sweeps say nothing about them. Every row is one
host, one network, two moments.

## The route sweep of 2026-08-17

One Windows 11 host, unauthenticated, the package identity unless a row says
otherwise, one bounded read per surface, made after the bakeoff review of that
date recorded the roster reading competitively and hydrating almost nothing.
Every row was a real HTTP response. Three of them reverse a claim above.

- **DuckDuckGo answers 202 to a browser identity as well as to this one**, on
  `html.duckduckgo.com/html/` and `lite.duckduckgo.com/lite/` alike: the
  challenge is not about the identity, so a second identity would buy nothing
  and none is tried. **Bing's RSS forms answer 200** — `www.bing.com/search?q=&format=rss`
  with ten clean title/link/description/pubDate items and `first=` paging, and
  `www.bing.com/news/search?q=&format=rss` with items whose links are wrapped
  in `news/apiclick.aspx?…&url=` — and so does **Google News RSS**,
  `news.google.com/rss/search?q=<q>+when:30d&hl=en-US&gl=US&ceid=US:en`, 131 KB
  of press items whose links redirect to the publisher when read. Three index
  routes ship as parallel planned routes; Brave answered 429, Mojeek a
  challenge.
- **Reddit's `/svc/shreddit/` HTML partials answer 200 with native counts, on
  a bucket of two hundred reads per window** (`x-ratelimit-remaining: 199.0`
  after the first read, `x-ratelimit-reset` a countdown in seconds), where the
  `.rss` surface answers one read per minute (`remaining 0.0`, `reset 47`) and
  every `.json` form still answers 403 to every identity. `community-more-posts/
  <sort>/?name=<sub>&t=month` carried 24 `<shreddit-post>` elements stating
  `score`, `comment-count`, `post-title`, `author`, `created-timestamp` and
  `permalink`; `search?q=&type=posts&sort=&t=` and `r/<sub>/search?…` carried
  seven posts per page with a `faceplate-number` pair and a continuation
  token; `comments/r/<sub>/t3_<id>?sort=top` carried 25 `<shreddit-comment>`
  elements with `score`, `depth`, `author`, `created`, `permalink`, the body
  under `id="<thingid>-post-rtjson-content"`, `total-comments="93"`, and a
  `more-comments` continuation. This is the platform's own client surface and
  it is `K2`, and it is what makes Reddit search and Reddit comments reachable
  at all. **Arctic Shift** answered 200 to `posts/search?subreddit=&after=&limit=&sort=`,
  `comments/search?link_id=` and `comments/tree?link_id=` with scored bodies,
  and 422 `"Timeout. Maybe slow down a bit"` twice to a full-text `title=` on
  one subreddit — measured and left undeclared, because the shreddit partials
  answer the same questions from the platform itself and a route no adapter
  reads is a route nobody paced. **PullPush** answered 429 with the sentence that it does not
  serve agents; it is not declared, out of respect for the operator's stated
  wish rather than for want of a route.
- **YouTube's InnerTube `player` answers `OK` with caption tracks to the
  `ANDROID` client** (`clientName ANDROID`, `clientVersion 20.10.38`, no other
  context field, no extra header), carrying `videoDetails.viewCount` as an exact
  digit string, `lengthSeconds`, `channelId`, `author`, and
  `captions.playerCaptionsTracklistRenderer.captionTracks[]` with a signed
  `baseUrl` on `www.youtube.com/api/timedtext`; that address, rebuilt through
  the transport's own sorted `urlencode`, answered 200 with 109 KB of `srv3`
  XML, and `fmt=json3` and `tlang=` answered too. `IOS 20.10.4` also answered
  `OK`; `WEB` still answers `UNPLAYABLE`. This reverses the 2026-08-10 row
  above for the `ANDROID` client, and the caption capability the roster
  deferred is shipped on it. `ANDROID` carries no `microformat`, so
  `publishDate` is absent from that read.
- **Hacker News**: `hn.algolia.com/api/v1/items/<id>` answered 200 with a
  story and its whole comment tree, 259 nodes in one 135 KB call, comment
  `points` null throughout; `search_by_date?…&numericFilters=created_at_i>…`
  answered 200.
- **Prediction markets**: `gamma-api.polymarket.com/public-search?q=`,
  `/events` and `/markets` (200; volumes and prices are decimals and JSON
  strings; `commentCount` an integer), `api.elections.kalshi.com/trade-api/v2/
  markets` and `/events` (200; dollar and fixed-point fields as strings; no
  search endpoint), `api.manifold.markets/v0/search-markets?term=` (200;
  `uniqueBettorCount` an integer).
- **Stocktwits** `api.stocktwits.com/api/2/streams/symbol/<SYM>.json` answered
  200 with 30 messages, `likes.total`, `created_at`,
  `entities.sentiment.basic` (`Bullish`/`Bearish`) and a `cursor.max` for the
  next page; `search/symbols.json?q=` answered 200. Keyless.
- **FxTwitter** `api.fxtwitter.com/2/search?q=&feed=latest`, `/2/profile/
  <handle>/statuses`, `/2/profile/<handle>` and `/2/conversation/<id>` answered
  200 with the platform's own counts — a third-party operator reading X on
  this package's behalf, `K3`, and the one keyless path to an X search.
  `syndication.twitter.com/srv/timeline-profile` answered 429 from this host
  that day; the guest GraphQL `UserByScreenName` answered 401.
- **Bluesky** `public.api.bsky.app/xrpc/app.bsky.feed.searchPosts` answered 403
  from the CDN in front of it ("Request forbidden by administrative rules") to
  every identity, while `getProfile` and `getAuthorFeed` answered 200 — the
  feed at a hundred rows with a cursor. A per-host administrative block on the
  search method, which is why the smoke names the feed.
- **FxTwitter's v2 API answered 200 to the package identity on every surface**
  — `/2/search?feed=latest` and `?feed=top` at twenty records, `/2/profile/
  <handle>/statuses` at nineteen, `/2/profile/<handle>`, and `/2/conversation/
  <id>` at thirty-six. No browser identity was used anywhere, and the earlier
  finding that the v1 path refuses this identity does not hold for v2. One
  caveat, reproduced deterministically: this origin answers 404 to a read it
  answers 200 to seconds later, so a 404 here is typed `http_status` and
  nothing retries.
- **A press page** (`www.cnbc.com`) answered 200 with 2 MB of HTML to the
  package identity, which is what the open document route reads.

What this sweep does not cover: no read touched TikTok or Instagram search
(TikTok's `oembed` answered 400; Instagram's hashtag pages are login-walled),
Mastodon's status search (empty without a credential), or Lemmy, and none of
those ships. Every row is one host, one network, one moment.

## The player metadata measurement of 2026-08-31

One Windows 11 host, unauthenticated, through this package's own transport,
after the `youtube_innertube` smoke reported its video row missing
`published_at`. Bounded player reads of one held video (`dQw4w9WgXcQ`) across
nine clients, and one read of an eleven-character id the origin does not hold.
Two rows here supersede claims above.

- **Every client answered `OK` with caption tracks has lost `microformat`.**
  `ANDROID 20.10.38` (the pinned version), `ANDROID 20.34.42`, `IOS 20.10.4`
  and `ANDROID_VR 1.62.27` all answered 200 `OK` with `videoDetails`, six
  caption tracks, and no `microformat` key; a whole-body scan of the `ANDROID`
  answer found no `publishDate`, no `uploadDate`, and no date value anywhere in
  its 247 KB. The publish date is gone from the app-client player surface
  entirely, not moved within it.
- **`WEB` and `MWEB` still carry the date, and now as a full instant.**
  Both answered 200 `UNPLAYABLE`, reason `Video unavailable`, **with** the
  complete `videoDetails` (`title`, exact `viewCount`, `author`,
  `shortDescription`) and `microformat.playerMicroformatRenderer` —
  `publishDate: 2009-10-24T23:57:33-07:00`, an offset instant where the
  2026-08-10 era wrote a bare day — and no caption track and no
  `streamingData`. The origin serves the row and withholds the playback.
  `WEB_REMIX` answered `UNPLAYABLE` without `microformat`; `TVHTML5`,
  `WEB_EMBEDDED_PLAYER`, `TVHTML5_SIMPLY_EMBEDDED_PLAYER` and `WEB_CREATOR`
  refused with no `videoDetails` at all. No client carries both halves: date
  and captions now live on disjoint client families, which is why the `player`
  metadata operation presents `WEB` and the transcript's player read presents
  `ANDROID`.
- **The unheld side of the 2026-08-12 axis is now measured.** The unheld id
  answered 200 `ERROR` with no `videoDetails` and no `microformat`; the held
  video's refusal carried both. The reason string was byte-identical on the
  two sides, so the reason and the status still decide nothing — the served or
  unserved row beside them is the discriminator, and it is the one
  `_player_page` branches on.

Every row is one host, one network, one moment.

## The route sweep of 2026-09-01

The survey-validation sweep behind the six-adapter expansion, plus a full
re-smoke of the nineteen-adapter roster the same day. One host, one network,
one moment, as always.

**The re-smoke.** Fourteen of nineteen carried their row. The five that did
not, each with the typed cause the smoke reported: `web_search` (DDG answered
202, the challenge it has answered every identity since 2026-08-17),
`x_syndication` (429, `rate_limited`), `x_guest` (401, `auth_required` — the
guest activation refused), `instagram_public` (429, `rate_limited`), and
`x_fxtwitter` (404, its measured answer-then-refuse flit). None exited 3:
every read reached its origin. The keyless X surfaces and anonymous
Instagram are at-risk rows, and a caller should read their smoke before
planning on them.

**The new-source validation.** Each endpoint the expansion declares was read
live before it was declared. Keyless 200 with the origin honoring its date
bound: Stack Exchange `search/advanced` (`fromdate`/`todate`, the 300/day
anonymous quota reported in the body), Wikimedia per-article pageviews (the
range is two path segments; one cold 429, then 200), OpenAlex, Crossref
(month-precision dates on some items) and arXiv (`submittedDate` range in
`search_query`). GDELT DOC 2.0 honored `startdatetime`/`enddatetime` and
stated its one-request-per-five-seconds ceiling in a plain-text 429 body —
over plain HTTP, because **port 443 to `api.gdeltproject.org` timed out from
this host on every attempt**, curl and this package's own opener alike, while
port 80 answered; the transport admits https only, so the GDELT smoke here
reports `unreachable` and concludes nothing about the platform. GDELT
Context 2.0 answered 200 with an empty article list to six different queries
and is deferred, not declared. All six oEmbed endpoints answered 200,
including `publish.x.com` — the survey's 402-from-datacenter report did not
reproduce from here. A TikTok video page served the full rehydration payload
to a plain cookieless GET; a profile page served the profile's counts and an
empty `itemList`. Stack Exchange compressed its answer only when asked
(`Accept-Encoding` sent: gzip; not sent: identity), which is why
`transport.decoded_body` honors a stated encoding rather than assuming one.

**The transport-identity question, held open.** The 2026-09-01 survey
(`research/super-research-technique-survey-2026-09-01.md`, §6.3 and §8.2)
argues the cold X/Instagram surfaces are fingerprint-gated at the TLS layer,
and that a browser-matched ClientHello — chosen once, never rotated on a
block — might be a lawful persistent identity where stdlib's is flagged on
the first packet. This delivery holds the pure-stdlib line: the identity
stays `super-research/0.1` over urllib's own handshake, the gated origins
stay typed losses, and the law change is the user's call, not a sweep's.
