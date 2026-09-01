# tiktok_public draft notes

Working notes from implementing the `tiktok_public` adapter (K2,
`tiktok_video_page` + `tiktok_profile_page`). Unlike the other in-flight
adapters' drafts in this directory, `references/protocol.md`'s loss-vocabulary
tables were edited directly as part of this delivery (see "Loss vocabulary"
below) rather than left as an open item, because the task's own definition of
done required no `loss_vocabulary` failure mentioning this module.

## The package-UA measurement (load-bearing)

**The package's own honest `User-Agent`
(`super-research/0.1 (keyless read-only acquisition)`) is served the full
payload — on a first-touch request.** Measured 2026-09-01, plain GET, no
cookie, no script run:

- `https://www.tiktok.com/@nba/video/7606907506589207838` -> 200, 406 KB,
  `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">`
  present, `__DEFAULT_SCOPE__["webapp.video-detail"].itemInfo.itemStruct`
  fully populated (`id`, `createTime`, `desc`, `statsV2`, `stats`, `author`,
  `textExtra`).
- `https://www.tiktok.com/@nba` -> 200, 368 KB, same script id,
  `__DEFAULT_SCOPE__["webapp.user-detail"].userInfo` fully populated (`user`,
  `stats`, `statsV2`, and an **empty** `itemList`).

**Then it changed, within the same session, after roughly ten live requests
to `www.tiktok.com` over about fifteen minutes (this module's own
measurement traffic — both fixture captures, several ad hoc probes, and one
CLI smoke run).** Every later request — to the *same* video address, and to
a *different, never-before-touched* profile address (`@cristiano`) — still
answered 200 with the same script id present, but the rehydration payload's
`__DEFAULT_SCOPE__` had shrunk to
`['seo.abtest', 'webapp.a-b', 'webapp.app-context', 'webapp.biz-context',
'webapp.i18n-translation']`: no `webapp.video-detail`, no
`webapp.user-detail`, on *any* address tried, first-touch or not. None of
the six challenge markers (see "Decisions" below) appeared in this reduced
page either — it is not a login/verification wall, and this module correctly
reads it as `schema_drift` rather than misreporting `auth_required`.

**Reading:** this is not a per-URL or per-video state (the never-touched
`@cristiano` profile was degraded too), and it is not a wall. The shape of it
— same status, same script id, a payload that quietly stopped carrying the
one container this module reads — is consistent with an origin-side adaptive
throttle keyed on request velocity from this IP/UA pair rather than on
identity or on the specific resource, but that is a reading, not a measured
mechanism: nothing here inspected response headers, timing, or retried after
a cooldown to confirm it, and no other explanation was ruled out. **Reopen
condition:** re-run the same first-touch probe after a substantial idle
period (hours, not the minutes tried here) and from a distinct source
address if possible; if the full payload returns, the throttle theory holds
and a documented minimum inter-read interval could be derived from how long
recovery takes. This is exactly the finding
`super-research-superset-2026-08-17`'s sibling investigations have been
watching for on other K2 surfaces, and is the reason it is called out
prominently here for the coordinator's JA3/transport-identity write-up: **the
identity that was refused nothing on the first read can still be throttled
into a degraded one shortly after, on this platform, under this package's
own honest transport** — a fact about request pacing, not about the
`User-Agent` string.

## Path-quoting: no route correction needed

Both `%40`-encoded and literal `@` forms of the handle segment answered 200
with the full payload in the pre-throttle measurement:
`https://www.tiktok.com/%40nba/video/7606907506589207838` and
`https://www.tiktok.com/@nba/video/7606907506589207838` both worked.
`_support/transport_request.path_segments` calls
`urllib.parse.quote(value, safe="")` on every path segment, which encodes
`@` to `%40` unconditionally — exactly the form proved live. The two
pre-wired route entries in `_support/route_catalog_k1_k4.py`
(`tiktok_video_page`: `path_params=("handle", "resource", "video_id")`;
`tiktok_profile_page`: `path_params=("handle",)`) needed no edit. The
adapter builds `handle` as `"@" + <bare handle>` so the composed address is
`origin + "/%40<handle>/video/<id>"` for a video and `origin + "/%40<handle>"`
for a profile, matching both measurements.

## Measured payload shapes

- `itemStruct.id`, `itemStruct.createTime`, `author.id` are all
  **decimal-string** (`"7606907506589207838"`, `"1771121181"`,
  `"134941634731003904"`), not JSON numbers — confirmed by explicit
  `repr()`/`type()` inspection, not inferred from how they print.
- `itemStruct.statsV2` publishes every count (`diggCount`, `shareCount`,
  `commentCount`, `playCount`, `collectCount`, `repostCount`) as a decimal
  string. `itemStruct.stats` publishes the same names, mostly as `int`, with
  one measured exception: `collectCount` arrived as the *string* `"2480"`
  inside `stats` on the one row read, even though its four siblings in the
  same object were plain `int`. This is the fact behind the "statsV2 primary,
  a `statsV2` key that is present but not all-digits is dropped rather than
  falling back" rule in `tiktok_public_records.video_engagement` — `stats`
  is not a trustworthy fallback for type either, only for presence.
- `itemStruct.textExtra` carries the video's hashtags *and* its `@mentions`
  in one list, told apart only by `type` (`1` = hashtag, `0` = mention seen
  here) and by the mention's `hashtagName` being the empty string. Read as
  "`type == 1` and a nonempty `hashtagName`" — both conditions, not either.
- `userInfo.itemList` was empty on the one profile measured, on every read
  including the pre-throttle one — never observed nonempty. The video-shaped
  entries it would hold are unverified in structure past "presumed to match
  `itemStruct`'s own shape," because TikTok's own web client evidently reads
  them the same way a video page's `itemStruct` reads (same field names
  throughout the surface); `ProfileNonemptyItemListTest` in
  `tests/test_tiktok_public.py` proves the parsing branch against a
  constructed payload, not a captured one.
- Both pages carry a `statusCode`/`statusMsg` pair one level above
  `itemInfo`/`userInfo` (`0` and `""` on every read here). Not read by this
  module: the task's typed-page rules name only the `__DEFAULT_SCOPE__` path
  check, and no measurement exists of what a nonzero `statusCode` means (a
  removed video, a private account, something else) — inventing that
  semantics would be a guess dressed as a typed distinction.

## Decisions

- **The `auth_required` wall-marker heuristic is unverified on its true-positive
  side.** No login or verification wall was ever observed live — not on the
  original measurement, and not on the throttled/degraded pages described
  above (checked explicitly; see the measurement section). The six markers
  in `CHALLENGE_MARKERS` (`tiktok_public.py`) are TikTok's publicly
  documented anti-bot interstitial container ids/classes, chosen because
  none of them appears anywhere in either a healthy *or* a throttled
  ordinary page — including the embedded `webapp.i18n-translation`
  dictionary, which repeats the literal text "Log in" dozens of times on
  every page regardless of state, confirmed by direct `grep`, and is exactly
  the false-positive trap the task brief warned about (`captcha-ttp.*.js`
  asset filenames are the same category of trap: present on every healthy
  page, meaningless as a signal). **Reopen condition:** capture a genuine
  wall/challenge page and confirm at least one marker fires on it; until
  then this branch is honest about being unreachable-from-a-status-code and
  best-effort about being reachable-from-a-body at all.
- **`statsV2` is read key-by-key, not container-by-container, for the
  primary/fallback choice.** `video_engagement` checks `name in stats_v2`
  per metric name, not `bool(stats_v2)` once: a `statsV2` key present but
  not an all-digit string is read as "a count nobody reported" and dropped,
  never falling through to `stats`'s value for that same name. Only a name
  `statsV2` does not carry at all falls through. This is the literal reading
  of the task brief's "a non-digit string is a count nobody reported" clause
  applied at the per-metric level.
- **Profile engagement reads `stats`, not `statsV2`.** The task brief names
  "exact ints" for `followerCount`/`heartCount`/`videoCount` with no
  primary/fallback rule the way the video roster's does, and the measured
  profile `stats` object already carries all three as plain `int` — reading
  it directly is both what was asked and the simpler, already-typed source.
  `friendCount` and `followingCount` are on the payload and named by neither
  the roster nor this module.
- **`native_item_id` on a profile is TikTok's numeric id when present, the
  handle otherwise** — the literal task-brief rule, implemented as
  `numeric_id or unique_id` in `tiktok_public_records.profile_record`.
- **The itemList warning is unconditional, and drops only when the list is
  nonempty on that specific page** — never once-per-run, never inferred from
  whether a caller asked for recent videos. `_profile_page_from` branches on
  `videos` (the parsed, `Mapping`-filtered `itemList`) after building the
  profile record, so the warning and the extra video records are mutually
  exclusive on one page's own answer, matching the task brief exactly ("say
  it whether or not itemList is empty... if it is ever non-empty... drop the
  warning for that page").
- **`video:` and `profile:` both refuse before touching the carrier.**
  `video_target` requires the full `handle/id` pair (partition on the first
  `/`, both halves nonempty) and refuses everything else — a bare handle, a
  bare id, an empty argument — as `unselected_target`, unseeded-carrier-proof
  in `VideoOperationRefusesWithoutThePairTest`. `profile:` with an empty (or
  `@`-only) handle refuses the same way. Neither refusal is `AdapterError`:
  both return a typed `NativePage` with `outcome="refused"`, mirroring
  `public_page`'s `_refused` rather than raising, so a malformed target in a
  manifest reads as a step result and not a crash.
- **Loss-vocabulary tables in `references/protocol.md` were edited as part
  of this delivery**, not left open: `tiktok_public` was added to the
  `auth_required`, `schema_drift`, `field_omitted`, `malformed_json`,
  `http_status` and `unselected_target` rows'
  `"named by"` cells, matched exactly against what
  `tests/test_dependency_boundary_cases/loss_vocabulary.py` scans the source
  for (verified green for every `tiktok_public`-attributable cell — the
  suite's remaining loss-vocabulary failures are all attributable to
  `gdelt`, landing concurrently in this same tree, and are not this
  module's to fix). One authoring bug caught by that same suite along the
  way: backtick-quoting `` `video:` `` and `` `profile:` `` inside the
  `unselected_target` cell's prose made the table's own parser
  (`backticked()`, which treats every backtick span in a "named by" cell as
  a module reference) read them as two more module names nothing declares —
  fixed by dropping the backticks around those two words.

## Probe / window-reach state

No change was needed to either file:

- `probes.py`'s `SmokeProbe(adapter_id="tiktok_public", kind="hydration",
  target="video:nba/7606907506589207838", ...)` was already pre-wired with
  exactly the field set this delivery ships
  (`native_item_id`, `body`, `author`, `canonical_locator`, `published_at`,
  three `engagement:` fields) before this delivery began, and it is
  satisfiable by the pre-throttle live 200 and by the offline fixture alike.
- `_support/window_reach.WINDOW_REACH["tiktok_public"] = {"": False}` was
  already declared before this delivery began. Confirmed correct: neither
  operation's route takes any query parameter beyond its path segments
  (`_support/route_catalog_k1_k4.py`'s two entries have no window-shaped
  param, and this module sends nothing beyond `handle`/`resource`/
  `video_id`), so there is nothing for a window to act on either way.

## Refused by policy (not deferred — no keyless route exists)

- **TikTok comments.** Reading a video's comment list requires TikTok's
  mobile API under the signed `X-Bogus`/`X-Gorgon` request-signing scheme —
  a signed client challenge, one of the three techniques the access ladder
  exists to refuse (`protocol.md`'s existing "Refused by policy" list
  already names "TikTok comments and search" for this reason; this delivery
  does not change that classification, only implements the two surfaces
  that were reachable).
- **TikTok search.** No keyless web-servable search endpoint was found or
  tried; the only surfaces this delivery reads are a video by exact id and a
  profile by exact handle, both hydrations rather than discovery.

## Deferrals

- **Profile `itemList` videos beyond the roster's own fields.** If a future
  live read ever returns a nonempty `itemList` (never observed here), the
  additional video records it produces carry exactly the same roster fields
  a `video:` hydration does — nothing in the shape is expected to differ,
  but nothing here proves it either, since `ProfileNonemptyItemListTest` is
  necessarily a constructed-payload test.
- **A documented minimum inter-read interval for this route.** The
  descriptor's `min_interval_ms=2000, burst=1` are the placeholder's
  pre-wired conservative defaults, unchanged by this delivery. The
  throttling behavior described above suggests the true safe pacing may be
  markedly more conservative than that for sustained reads, but no
  measurement here established a number — reopens once the reopen condition
  above (a fresh first-touch probe after an extended idle period) is run and
  a recovery time is observed.
