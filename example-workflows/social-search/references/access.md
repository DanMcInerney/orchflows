# Public access

Keyless routes that answered on 2026-09-23. Origins change, throttle and block. Throttled origins often answer again after a pause of tens of seconds; when one keeps refusing, record the gap instead of hammering it. Native web search finds leads on any site; these routes read the discussion itself, with dates and engagement.

## Hacker News

- Search, newest first: `https://hn.algolia.com/api/v1/search_by_date?query=<q>&tags=(story,comment)&numericFilters=created_at_i><start>,created_at_i<<end>&hitsPerPage=100`, with Unix-second bounds. `/search` ranks by relevance instead; add `points>N` to `numericFilters` to find the most-voted stories.
- Whole thread with nested comments, one request: `https://hn.algolia.com/api/v1/items/<story-id>`.
- Permalink: `https://news.ycombinator.com/item?id=<id>`.

## Reddit

reddit.com's `.json` endpoints and Claude Code's fetch tool refuse keyless reads.

- The Arctic Shift archive serves JSON with date filters and stays current within hours: `https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=<sub>&title=<q>&after=YYYY-MM-DD&before=YYYY-MM-DD&limit=100`, `/api/comments/search?subreddit=<sub>&body=<q>&after=…&before=…`, whole threads through `/api/comments/tree?link_id=<post-id>&limit=<n>`, and items through `/api/posts/ids?ids=` or `/api/comments/ids?ids=`. Its scores are archive snapshots, not live counts. Text search needs a subreddit or author and cannot sort by score: find the communities carrying a topic through web search and the topic's own communities, then rank each subreddit's results locally. Broad queries time out or throttle; narrow the window and pace requests.
- reddit.com answers a browser User-Agent on `https://www.reddit.com/svc/shreddit/community-more-posts/top/?name=<sub>&t=month` (a subreddit's most-voted posts; each `<shreddit-post>` element carries `score`, `comment-count`, `created-timestamp`, `post-title` and `permalink`), `https://www.reddit.com/r/<sub>/search.rss?q=<q>&restrict_sr=on&sort=new&t=month` and `https://www.reddit.com/svc/shreddit/comments/r/<sub>/t3_<post-id>` (HTML thread), then rate-limits after a few requests. Its sitewide search returns unrelated filler to scripts.

## GitHub

Use `gh search issues|prs|repos` or `gh api` when `gh` is authenticated. Otherwise the REST search `https://api.github.com/search/issues?q=repo:<owner>/<repo>+created:>=YYYY-MM-DD` allows about ten keyless searches a minute.

## X

There is no keyless search. Find post URLs through web search, then read `https://api.fxtwitter.com/status/<id>`, a third-party relay returning text, author, date and like, repost, reply and view counts.

## YouTube

- Find: `yt-dlp "ytsearch20:<q>" --flat-playlist --print "%(id)s %(title)s"`. Flat results carry no dates.
- Metadata: `yt-dlp --skip-download --print "%(upload_date)s %(view_count)s %(like_count)s %(comment_count)s %(channel)s" <url>`.
- Captions: `yt-dlp --skip-download --write-auto-subs --sub-langs en --sub-format vtt -o "<dir>/%(id)s" <url>`. Automatic captions are machine speech recognition.
- After repeated reads from one address, YouTube may demand sign-in from `yt-dlp`; then `https://www.youtube.com/oembed?url=<url>&format=json` still confirms title and channel, without dates.

## Polymarket

`https://gamma-api.polymarket.com/public-search?q=<q>&events_status=active` matches loosely; confirm each market's question. Events carry outcome prices, volume, liquidity and end dates.

## Lemmy

The instance comes from the caller. For v0.19 instances exposing API v3, `https://<instance>/api/v3/search?q=<q>&type_=Posts&sort=New&limit=<n>` and `https://<instance>/api/v3/comment/list?post_id=<local-id>&sort=New&limit=<n>` are public; v3 search has no date parameter, so filter locally. [API documentation](https://join-lemmy.org/docs/contributors/04-api.html) distinguishes v3 and v4.
