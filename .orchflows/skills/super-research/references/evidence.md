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
