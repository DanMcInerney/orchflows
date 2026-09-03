# oembed draft notes

Working notes from implementing the `oembed` adapter (K0, six route surfaces:
`youtube_oembed`, `vimeo_oembed`, `spotify_oembed`, `soundcloud_oembed`,
`tiktok_oembed`, `x_publish_oembed`). Not folded into `protocol.md` beyond
the six loss-vocabulary cells and the roster row that were already required
for the suite to pass.

## Measured facts (2026-09-01, live, all keyless 200 from this host)

- `GET https://www.youtube.com/oembed?url=<video url>&format=json` answers
  `author_name`, `author_url`, `title`, `thumbnail_url`, `provider_name`,
  `html`, `width`/`height`, and `type: "video"`. No `embed_product_id` and
  no date of any kind.
- `GET https://vimeo.com/api/oembed.json?url=<video url>` answers `title`,
  `author_name`, `author_url`, `provider_name`, `html`, and `type: "video"`
  on a public id. A deleted or private id (probed against an id one digit
  short of any assigned range) answers plain 404, not a 200 with an empty
  or error-shaped body.
- `GET https://open.spotify.com/oembed?url=<track url>` answers `title`,
  `thumbnail_url`, `iframe_url`, `html`, and `type: "rich"`. It never
  answers `author_name` on a track — probed against a well-known public
  track id, confirmed absent rather than a fetch failure: the response is
  200 and every other field is present.
- `GET https://soundcloud.com/oembed?url=<track url>&format=json` answers
  `title` (`"Flickermood by Forss"`), `author_name`, `author_url`,
  `thumbnail_url`, `description`, `html`, and `type: "rich"`.
- `GET https://www.tiktok.com/oembed?url=<video url>` answers `title` (the
  clip's own caption, hashtags and all), `author_name`, `author_unique_id`,
  `author_url`, `thumbnail_url`, `embed_product_id` (the video id restated
  as a string, byte-identical to the id in the item url), `html`, and
  `type: "video"`.
- `GET https://publish.x.com/oembed?url=<status url>` answers `author_name`,
  `author_url`, `html`, `cache_age`, `provider_name: "X"`, and
  `type: "rich"`. It never answers a `title` — the payload states none, and
  the response is otherwise a normal 200. Probed against `jack`'s original
  tweet (`https://x.com/jack/status/20`), chosen because it can never be
  deleted or made private the way a newer id could.
- `publish.twitter.com/oembed?url=...` answers this host with a bare
  `301 Moved Permanently` onto `publish.x.com/oembed?url=...` (`Location`
  header, empty body) — no 402, no login wall. A separately reported survey
  from a datacenter IP range claimed `publish.twitter.com` answers 402
  there; that did not reproduce from this host at any point in this
  delivery, on either the old or the new hostname, keyless.
- None of the six answers a structured publication date in any field, and
  none answers an engagement count of any kind (likes, views, plays,
  comments) under any name. Both are standing absences of the surface
  itself, not something one particular read happened to omit.
- Response `Content-Type` measured: `application/json` on YouTube and X,
  `application/json; charset=utf-8` on SoundCloud — all read as JSON
  regardless of the exact parameter, matching the `PROBE_PAYLOADS` entry
  already wired in `tests/test_cli_cases/_support.py` for the X route.
- `format=json` was sent on every YouTube and SoundCloud call made while
  building this module and both answered JSON either way when re-probed
  without it during evidence-gathering; it is kept as a declared,
  deliberate parameter on those two surfaces rather than dropped, because
  the measured fact this module was built against names it as necessary
  and a `Content-Type` that happens to agree on one further read is not
  proof the origin never varies by content negotiation, only that it did
  not on this host today.

## Decisions

- **Hydration-shaped, one url in.** Unlike every other multi-surface
  adapter in this roster (`stocktwits`, `prediction_markets`), there is no
  default surface an unprefixed argument falls back to: a bare string is
  not any platform's item id in a shape this module could guess, so an
  unprefixed or unrecognised target is refused before any call is made,
  mirroring `public_page`'s closed-selection refusal rather than
  `stocktwits`'s "defaults to the primary surface" rule.
- **`canonical_content_kind` is the payload's own `type`, verbatim.**
  Never mapped, aliased or folded into a fixed enum — a seventh oEmbed
  provider this module has never read would still report its own kind
  rather than being forced into `video` or `rich`.
- **`canonical_locator` is the caller's own url, not the payload's.** Every
  provider echoes a `url` field of its own (X's is even the same string
  back, percent-decoded); this module ignores it and carries the address
  the caller actually asked to hydrate, so the record's locator is exact
  provenance rather than whatever normalization the provider applied.
- **`html` is deliberately not carried.** Every one of the six answers a
  ready-to-embed blob (an iframe or a script-and-blockquote pair), and it
  is markup for a browser, not a fact about the item. Carrying it would
  put one provider's whole rendering surface into `attributes` next to
  five providers that carry none of their own; a caller that wants an
  embed can build one from `canonical_locator`.
- **Two standing losses on every record.** `unknown_publication_time` and
  `engagement_unavailable` — the same two codes `web_search` stands on
  every index hit — are declared once as `STANDING_LOSS` and set as each
  of the six descriptors' `standing_loss`, then read back onto every record
  this module returns. Neither is derived from what one particular answer
  happened to omit; both are true of the surface itself, on every provider,
  every time.
- **Absent `title` (X) and absent `author_name` (Spotify) carry no loss
  code of their own.** Both are payload absences this module's own
  docstring documents as measured facts about the surface, not a read that
  went wrong — the roster row and this draft are where that documentation
  lives, not a per-record `field_omitted`.
- **Six routes, one budget each, even where a host is shared.** YouTube,
  Vimeo and TikTok's oEmbed endpoints share a host with another declared
  route this roster already reaches (the YouTube channel feed, and no
  Vimeo/TikTok sibling yet, respectively) — same "different endpoint,
  different route" shape `youtube_channel_feed` and `youtube_innertube`
  already hold on YouTube's own site.
- **No measured throttle, so no invented one.** Nothing about this
  surface's rate ceiling was measured beyond "it answered"; every
  descriptor keeps the protocol's conservative default (`min_interval_ms`,
  `burst`, `cooldown_ms`) rather than a number this module made up.

## Deferrals

- **The other providers oEmbed's own discovery directory lists** (Flickr,
  Reddit's own oEmbed, Twitch clips, and the rest of oembed.com's
  registry) are not shipped. Six were pre-wired by the roster row this
  delivery fills in; a seventh reopens as its own route constant, its own
  descriptor, and its own line in `OEMBED_OPERATIONS`, not as a change to
  this module's parsing — the parser already reads any provider's
  `type`/`title`/`author_name`/`author_url`/`thumbnail_url`/`provider_name`/
  `author_unique_id`/`description` generically.
- **No caption or transcript surface.** oEmbed is a hydration of a single
  item's author/title/thumbnail, never its content; a caller wanting a
  YouTube transcript already has `youtube_innertube`'s `transcript`
  operation, not this module.
- **No retry across a provider's own transient 5xx.** A single 404 was the
  only non-200 measured live (Vimeo, on a plainly unassigned id); no 5xx
  or 429 was observed from any of the six during this delivery, so the
  generic `rate_limited`/`network_intercepted` handling `fetch_one_page`
  already gives every adapter is what this module relies on, untested
  against a live 429 from any of the six specifically.
