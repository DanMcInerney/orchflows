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
