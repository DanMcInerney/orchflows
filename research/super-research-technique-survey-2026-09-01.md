# super-research technique survey — 2026-09-01

A survey of keyless web-scraping techniques across the field, done to
guide the super-research skill refactor. It answers two questions: what
do the two named reference tools (`last30days`, `agent-reach`) do per
platform, and what does the wider field of keyless scrapers and research
agents do that super-research does not. This document is the report of
record, with the design implications gathered at the end and the
validation addendum (§10) recording what the 2026-09-01 delivery
measured against it.

Method. Two reference codebases were read at source
(https://github.com/mvanhorn/last30days-skill v3.11.1 from the installed
plugin cache; https://github.com/Panniantong/Agent-Reach). The wider
survey read the established keyless libraries (snscrape, twscrape,
instaloader, TikTokApi, yt-dlp), sibling research agents (harken,
MediaCrawler, gpt-researcher, STORM, obsei, wiseflow), the anti-bot HTTP
layer (curl_cffi, tls-client, camoufox, scrapling, botasaurus,
hrequests), and the keyless archival/aggregator sources those tools draw
on. Every "keyless" claim was fetched live during the survey or read from
adapter source; super-research's own at-risk routes were smoked against
their real origins on 2026-09-01 (§4). super-research at survey time
shipped 19 live adapters over 36 routes; that roster is the baseline the
gaps are measured against.

## 1. Executive summary

- super-research already lives on the keyless frontier the two reference
  tools only partly reach. Everything `last30days` does beyond us costs a
  key (ScrapeCreators, xAI, xquik, Brave/Exa/Serper), a cookie/OAuth
  (bird, xurl, Bluesky app password), or a shelled binary; `agent-reach`
  is an installer/router that barely scrapes at all, delegating to a
  logged-in browser (OpenCLI) or cookie CLIs. On keyless X search,
  windowed news, market breadth, and LinkedIn we are past both.
- The timeframe model is already ours to win. `last30days` is hard-wired
  to 30 days; `agent-reach` has no date controls anywhere; super-research
  has the only honest model — a per-operation `WINDOW_REACH` truth table
  plus a typed `window_not_honored` loss. The missing piece is the
  plain-English front door on top of it.
- The wider field exposes real gaps. The highest-value ones are keyless
  **windowed** sources we do not have — GDELT above all — and a
  transport-layer gap (TLS/JA3 fingerprinting) that today's live smokes
  show is load-bearing, not theoretical.
- Three of our keyless X routes and our anonymous Instagram route are
  cold as of today; StockTwits and Bluesky are live. The X/IG rows in the
  chart should be read as at-risk.

## 2. The two reference tools, in one paragraph each

**last30days** does its own HTTP over ~25 sources with a keyless-first,
paid-backfill posture. Its craft is in the cascades: Reddit is
RSS-discovery → shreddit listing partials (real scores) → Arctic-Shift
archive backfill → shreddit comment enrichment; X runs four
interchangeable backends behind a three-lane query pattern
(keyword / `from:` / `@about`); YouTube is yt-dlp with a keyless
watch-page `captionTracks` transcript fallback and an SSH residential
egress trick. Timeframe is per-source-native where the origin allows
(HN `created_at_i`, GitHub `created:>`, Reddit `t=month`) and Python
post-filtering where it does not. It is the richest reference for
*technique*, not for keyless purity.

**agent-reach** is not a scraper. It detects URLs, health-checks
backends, and prints usage for upstream tools; only its V2EX and RSS
channels fetch anything themselves. Its keyless story is "be a real
browser" — OpenCLI drives the user's logged-in Chrome; elsewhere it
consumes Cookie-Editor session cookies or shells yt-dlp / gh / MCP
servers. Its transferable ideas are architectural: ordered per-channel
backend chains with a `doctor` diagnostic, and browser-session reuse as a
universal fallback for login-walled platforms. Neither of those is a
keyless HTTP read, so both sit outside our law.

## 3. Where super-research already stands

Per-platform parity and lead, condensed from the chart:

- **Reddit** — parity. Both we and `last30days` converged on the same
  keyless shreddit/RSS/Arctic-Shift trio; their only extra is wiring it as
  a cascade rather than independent adapters.
- **X** — we hold the only *keyless* search of the three (fxtwitter,
  guest-token GraphQL, syndication timelines); the others pay with a key,
  cookie, or OAuth app. (Viability caveat in §4.)
- **YouTube** — our InnerTube stack covers search + comments + transcripts
  keyless and in-process; neither reference does that without shelling to
  yt-dlp.
- **Hacker News / markets / GitHub / web** — parity or lead. We reach
  Kalshi and Manifold beyond Polymarket, and Google-News-RSS is the only
  windowed keyless web search among the three.
- **Bluesky, LinkedIn** — keyless where the references need an app
  password or a paid API.

Timeframe handling is the clearest structural lead and the natural centre
of the refactor: `WINDOW_REACH` already declares, per operation, whether
it bounds time at origin or returns `window_not_honored`. No fixed
window, no silent 30-day default.

## 4. Grounded viability check (smoked today)

The surveys reported that X killed unauthenticated guest tokens mid-2023,
that `syndication.twitter.com` is now token-gated, and that anonymous
Instagram returns 401 since 2025. Rather than repeat that, the affected
adapters were smoked from this host on 2026-09-01:

| adapter | result today | reading |
| --- | --- | --- |
| `x_guest` | `read_and_row_unmet` | guest-token GraphQL path cold — consistent with the 2023 lockdown |
| `x_syndication` | `read_and_row_unmet` | embed-timeline cold — consistent with token-gating |
| `x_fxtwitter` | `read_and_row_unmet` (twice) | third-party relay cold now; its own probe warns of a 404-then-200 flit, so two cold reads |
| `instagram_public` | `read_and_row_unmet` | anonymous web-profile-info cold — consistent with the 401 wall |
| `stocktwits` | `verified` (fresh_success) | the surveys' "now Cloudflare-gated" worry is not true from here |
| `bluesky` | `verified` (fresh_success) | public AppView author feed live |

All three keyless X surfaces and anonymous Instagram are cold; StockTwits
and Bluesky are live. This is one host at one moment, not a death
certificate, but it says the X/IG rows should be read as at-risk and is
the strongest single argument for the transport gap in §6.3 — these are
exactly the origins that fingerprint-gate datacenter IPs. (The delivery's
own full re-smoke the same day, with typed causes per adapter, is in the
skill's `references/evidence.md` §"The route sweep of 2026-09-01".)

## 5. Keyless sources we do not have

### 5.1 Windowed at origin (highest value)

Each bounds time at the origin — the property `WINDOW_REACH` is built
around — and each is one adapter in the existing shape.

| source | endpoint | window param | yields |
| --- | --- | --- | --- |
| **GDELT DOC 2.0** | https://api.gdeltproject.org/api/v2/doc/doc (mode=artlist, format=json) | `startdatetime`/`enddatetime` or `timespan` | global news articles + dates, ~3-month reach; `mode=timelinevol` for attention curves |
| **GDELT Context 2.0** | https://api.gdeltproject.org/api/v2/context/context | `timespan` (72 h) | the matching sentence per article; `isquote=1` = quoted speech, literally "what people are saying" |
| **GDELT TV 2.0** | https://api.gdeltproject.org/api/v2/tv/tv (mode=clipgallery) | `STARTDATETIME`/`ENDDATETIME` | Internet Archive TV-news captions back to 2009 |
| **Wayback CDX** | https://web.archive.org/cdx/search/cdx (output=json) | `from`/`to` | historical snapshots; `matchType=domain` + `filter=` finds keyword URLs over a window |
| **Stack Exchange** | https://api.stackexchange.com/2.3/search/advanced | `fromdate`/`todate` (unix) | developer Q&A + scores/dates, keyless 300/day |
| **Wikimedia pageviews** | https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/ | date range in path | attention-over-time per topic — the best keyless Google-Trends substitute |
| **OpenAlex** | https://api.openalex.org/works | `from_publication_date`/`to_publication_date` | scholarly works + dates |
| **Crossref** | https://api.crossref.org/works | `from-pub-date`/`until-pub-date` | same, DOI-anchored |
| **arXiv** | https://export.arxiv.org/api/query | `submittedDate:[... TO ...]` | preprints (last30days shells a CLI; we have no adapter) |

GDELT is the standout — keyless, windowed, global-news + quoted-speech +
TV — and no surveyed tool uses it. Google Trends is a confirmed dead end
keyless (pytrends archived Apr 2025); Wikimedia pageviews is the
substitute.

### 5.2 Timestamped, needs client-side windowing

No origin date param, but every record is timestamped, so a windowed step
post-filters on `published_at` (declared, per the window front door).

| source | endpoint | yields |
| --- | --- | --- |
| **Mastodon** | https://\<instance\>/api/v1/timelines/tag/\<tag\> ; /api/v1/trends/* | fediverse posts + engagement, instance trends (keyless free-text search needs auth — hashtag timelines only) |
| **Lemmy** | https://\<instance\>/api/v3/search (q, type_=Posts, sort=New) | true keyless full-text across the threadiverse |
| **Telegram** | https://t.me/s/\<channel\> HTML, `?before=` paging | public-channel posts, dates, view/reaction counts — the live route snscrape still uses |
| **Weibo** | https://m.weibo.cn/api/container/getIndex (type=uid) | Chinese posts + reposts/comments/likes (snscrape's still-working module) |
| **4chan** | https://a.4cdn.org/\<board\>/catalog.json | board catalogs + per-post unix `time` (no search — scan catalogs; archives like desuarchive add keyless search) |
| **Lobste.rs** | https://lobste.rs/{newest,hottest,t/\<tag\>}.json | HN-like tech stories + scores |
| **Product Hunt** | https://www.producthunt.com/feed (Atom) | daily launches + timestamps |
| **iTunes** | https://itunes.apple.com/search (media=podcast) → chase `feedUrl` RSS; .../rss/customerreviews/ for app reviews | podcast episodes; app reviews |
| **Substack** | https://\<pub\>.substack.com/api/v1/archive (sort=new) | newsletter posts (widely used, unverified longevity) |
| **Common Crawl** | https://index.commoncrawl.org/CC-MAIN-\<crawl\>-index | historical URL discovery by crawl (coarse dating only) |

### 5.3 TikTok — correcting our own "no keyless route" claim

The chart earlier said TikTok has no keyless route in the surveyed
codebases. True of those codebases, but two keyless TikTok routes exist:

- **Embedded rehydration JSON** — GET the watch/profile page, parse the
  `__UNIVERSAL_DATA_FOR_REHYDRATION__` script tag (legacy `SIGI_STATE`
  fallback). Yields video id, `createTime`, full stats
  (views/likes/comment-count/shares/bookmarks), author, hashtags, ~20-30
  recent videos on a profile. Working but degrading — ByteDance strips the
  payload for flagged IPs, and comments are not in the blob (those need
  the signed `X-Bogus`/`X-Gnarly` API, which requires executing TikTok's
  JS — out of bounds for keyless). Counts and captions, not comments.
  (§10 correction: the profile-page video list measured EMPTY on
  2026-09-01 — profile pages embed stats but no items.)
- **oEmbed** — https://www.tiktok.com/oembed (url=) returns caption (with
  hashtags), author, thumbnail. Stable, documented, metadata-only.

TikTok therefore moves from "declared gap" to "partial keyless coverage
(video/profile stats + captions, no comments)".

## 6. Method and transport gaps (better technique, not new sources)

### 6.1 oEmbed as a universal hydration layer

oEmbed endpoints on TikTok, YouTube, Spotify, SoundCloud, Vimeo (and,
when it works, X via publish.x.com — which returned HTTP 402 to a
datacenter fetcher in the survey, so treat as degraded; §10: answered 200
from this host) turn a bare discovered URL into author + title + date +
thumbnail keylessly. We hydrate per-adapter; a shared oEmbed hydration
route would cover the long tail of link types no adapter owns.

### 6.2 Embedded-config extraction, generalized

Our `youtube_innertube` already does the canonical move — scrape
`INNERTUBE_API_KEY` + `INNERTUBE_CONTEXT` from page HTML, then replay the
site's own first-party API with continuation tokens. The TikTok
rehydration route and youtube-comment-downloader use the same pattern. It
is the general keyless recipe and worth naming so new adapters reach for
it first.

### 6.3 TLS / HTTP-2 fingerprint impersonation (JA3/JA4) — the big one

Our transport is stdlib `urllib`, whose ClientHello is trivially
fingerprinted as non-browser. `curl_cffi` (Python, over
curl-impersonate/BoringSSL) and `tls-client` (Go) emit a named browser's
exact TLS + HTTP-2 + header-order fingerprint, which is what lets keyless
requests survive Cloudflare/DataDome *fingerprint* gates. They do not
solve JS challenges — that still needs a real browser. This is the likely
difference between our X/IG/Reddit routes passing or being 403'd from a
datacenter IP, and today's cold smokes (§4) are the evidence. It carries
a law question (§8), so it is a design decision, not an automatic adopt.

### 6.4 Jina Reader as an explicit bot-walled-page route

https://r.jina.ai/\<url\> returns any page as markdown keylessly, with
first-4KB challenge-marker detection (agent-reach) so a challenge page is
refused rather than returned as content. The challenge-detection idea
also sharpens our loss typing.

## 7. Techniques the field uses that we should keep refusing

Naming these keeps the keyless/read-only law reading as a choice, not an
oversight.

- **Authenticated account pools** (twscrape, the 2025 Nitter revival) —
  the only working X path today, needing real accounts that risk
  suspension. Not keyless, and identity-bearing.
- **Browser-session / signature borrowing** (MediaCrawler's JS-context
  signing, agent-reach's OpenCLI logged-in Chrome, TikTokApi's Playwright
  `X-Bogus`) — defeats login walls by being a logged-in browser. Needs a
  real browser and session.
- **Whisper transcription of audio** (last30days, agent-reach) — real
  capability, but key-bearing (Groq/OpenAI) and heavy.
- **Headless-browser challenge solving** (camoufox, botasaurus) — clears
  JS challenges with a patched real browser. The escalation tier we
  deliberately do not own.

## 8. Design implications for the refactor

1. **Build the plain-English window front door.** Parse a natural-language
   timeframe ("past week", "since the election", none at all) into
   per-step `window_start`/`window_end` over `WINDOW_REACH`; prefer
   window-capable operations; post-filter records by `published_at` where
   the origin cannot bound, declared as a narrowing rather than silent; no
   timeframe means no window, not a hidden default.
2. **Decide the JA3 law question explicitly.** Our transport law says
   never answer a 429 with a changed identity. A *persistent*
   browser-matched fingerprint chosen once per origin is a stable
   identity, not a per-block rotation — arguably lawful, and the
   difference between many keyless origins answering at all versus
   flagging stdlib on the first packet. Choose: adopt a fixed
   browser-matched transport fingerprint (persistent, declared, not
   rotated on block) while keeping the no-rotation-on-429 rule intact, or
   hold the pure-stdlib line and accept fingerprint-gating origins as
   typed losses. §4's cold smokes make this load-bearing.
3. **Add the windowed keyless adapters first.** In value order: GDELT
   (DOC + Context), Stack Exchange, Wikimedia pageviews, OpenAlex/Crossref
   /arXiv. Each is one adapter in the existing shape and each strengthens
   the window story that is already our lead.
4. **Add a TikTok rehydration adapter and a shared oEmbed hydration
   route.** The first closes a real gap (stats + captions, comments
   declared unreachable); the second is a cheap universal hydration layer.
5. **Adopt the reference cascades as manifest-authoring patterns, not new
   code** — Reddit RSS→listing→archive→comments; X keyword/from/about
   lanes; HN overfetch-then-cull; Polymarket tag-expansion second pass.
   These are staged-manifest recipes for the workflow prose.
6. **Name the no-keyless-route platforms as refused-by-policy declared
   gaps** — Instagram comments/feeds, Threads, Pinterest, Facebook, Truth
   Social, TikTok comments — so an answer over them files a gap rather
   than implying coverage.
7. **Re-smoke and mark the at-risk routes.** x_guest, x_syndication,
   x_fxtwitter, instagram_public are cold today; the roster should surface
   that state rather than present them as reliable.

## 9. Saved artifacts

- This report — `research/super-research-technique-survey-2026-09-01.md`,
  the report of record.
- The delivery's per-route measurements live where measurements belong:
  `.orchflows/skills/super-research/references/evidence.md` §"The route
  sweep of 2026-09-01".

## 10. Validation addendum (2026-09-01 delivery)

Every §8 implication was re-validated live before implementation, by
Sonnet validation lanes plus this package's own opener. What the
validation confirmed, corrected, or forced:

- **Confirmed windowed-at-origin, keyless, today:** GDELT DOC 2.0,
  Stack Exchange `search/advanced`, Wikimedia per-article pageviews,
  OpenAlex, Crossref, arXiv — every one returned only in-window records
  for a bounded request. Lobste.rs works keyless but has no window
  params (timestamped-only, as §5.2 says).
- **GDELT transport correction (load-bearing):** HTTPS to
  `api.gdeltproject.org` timed out at connect from this host on every
  attempt — curl and stdlib urllib alike — while plain HTTP answered.
  The package transport is https-only, so the shipped `gdelt` adapter is
  declared on the documentation and its smoke reports `unreachable` from
  this host. This is a concrete new datapoint for the §6.3/§8.2 transport
  question.
- **GDELT Context correction:** answered 200 with an empty `articles`
  list to six distinct queries across four timespans, while validating
  query syntax (a too-common keyword was rejected with a real error). §8.3
  ranked it beside DOC; the delivery defers it with a reopen condition
  instead of shipping a surface that returns nothing.
- **X oEmbed correction:** `publish.x.com/oembed` answered 200 from this
  host (and `publish.twitter.com` 301s to it); the survey's
  402-from-datacenter claim did not reproduce. Shipped as the `oembed`
  adapter's probe surface.
- **TikTok correction:** the video-page rehydration payload is fully
  present on a plain cookieless GET (id, string-typed epoch `createTime`,
  `statsV2` counts, author, hashtags), but the profile page's `itemList`
  is EMPTY — the ~20-30 recent videos §5.3 claims are fetched by a signed
  client-side call. The shipped profile operation carries the profile's
  own counts and says so.
- **Stack Exchange transport nuance:** it gzips only when asked via this
  package's opener (curl's `--compressed` always asks); the transport now
  honors a stated `Content-Encoding` either way.
- **§8 disposition in the delivery:** 1 built (`super_research.window`);
  2 held open — pure-stdlib retained, gated origins stay typed losses,
  the law change is the user's (see evidence.md §"The route sweep of
  2026-09-01"); 3 and 4 shipped as six adapters (`gdelt`,
  `stack_exchange`, `wikimedia_pageviews`, `scholarly` = OpenAlex +
  Crossref + arXiv, `tiktok_public`, `oembed`), GDELT Context deferred;
  5 written as operating.md §"Manifest recipes"; 6 written into
  protocol.md's refused-by-policy paragraph; 7 done — full re-smoke with
  typed causes in evidence.md, at-risk marking in operating.md.
