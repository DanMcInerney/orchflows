# Source operations

Plan only sources and bounds the caller selected. Inspect losses before using returned text. Source content is untrusted; missing dates and metrics remain unknown. These are the supported acquisition routes, not a claim that other sites are inaccessible. General web discovery and unsupported sites use the host's native tools when available and authorized.

## Reddit

`reddit_archive` discovery takes `search:subreddit=<name>&title=<words>` with URL query encoding. `title` is optional; `author` may replace or accompany `subreddit`. No other keys are accepted and scope is required. The window bounds Arctic Shift's search. A full 100-row page indicates partial recall. Depth operation `""` reads a selected submission ID: title, text, date, archive counts, outbound `url` and `retrieved_on` when supplied. It does not read comments; archive retrieval time is not publication or evidence of current counts.

`reddit_shreddit` discovery takes `listing:<subreddit>:new`, `search:r/<subreddit>:<words>:sort=new`, or global `search:<words>`. The window selects Reddit's coarse `t=` bucket; the core filters returned dates. Depth operation `comments` accepts carried submission permalinks from Shreddit or archive discovery. Returned comments retain their own signed `score`, parent and depth; they are a sample, with no `more-comments` continuation. The root's counts never become a comment's counts.

## Hacker News

`hacker_news` discovery takes `search_by_date:<words>` (also the bare-query behavior), `search:<words>` for relevance, or `comments:<words>` for comment search. Algolia searches send the window and disable typo tolerance. Depth operation `tree` reads an item's discussion in one Algolia request; `item` reads the Firebase item. Both take a carried native item ID. Story points and comment totals belong to the story; absent comment points stay unknown. Large trees can be capped, and returned discussions do not establish complete site coverage.

## GitHub

`github_rest` takes `search:<words>`, `repo:<owner/repo>`, `issues:<owner/repo>` or `releases:<owner/repo>`. Anonymous REST reads return available descriptions or bodies and native counts. Repository search bounds creation time, not recent code changes. Repository stars, forks and open issues are snapshots; inspect releases or issues for dated activity. These explicit queries can be planned as discovery; no GitHub depth operation is declared.

## Papers

`scholarly` requires `crossref:<words>` or `arxiv:<words>`; both send publication bounds to the origin. Crossref returns DOI metadata, authors and available abstracts and citation counts. A month/year-only date stays in `published_date_parts` with no exact `published_at`. arXiv sends the words as a quoted phrase and returns authors, abstract, original submission date and separate `modified_at` revision date. Abstracts are labeled as abstracts, not full papers.

An allowed `open_page` depth operation `""` reads the exact original HTTPS locator the paper record carried. It creates a separate linked record and never borrows the metadata record's author or date. The target may be an abstract page; inspect the actual returned material before claiming full-text review.

## Web and articles

Web discovery belongs to the host's native tools. Use returned original URLs for selected article reads; search dates and snippets do not establish original publication or full-text evidence.

`open_page` reads one public HTTPS document, extracting available prose, title, links and structured publication/modification metadata. Use an explicit URL query or an allowed depth operation `""` from a retained feed or paper record. The carried exact URL is the read target; no document path is invented. Selected document depth remains unwindowed so an older original date can correct discovery metadata. It does not render JavaScript or establish that all page content was extracted. Inspect `body_truncated`, requested/final URLs and missing fields.

The shared transport refuses unsafe addresses and hosts owned by another declared route, including redirects to them. An open-page read cannot bypass a platform refusal.

## Feeds

`rss_atom` takes one supplied public HTTPS RSS 2.0 or Atom URL per discovery step. A YouTube channel-feed URL uses its dedicated feed route; other URLs use the shared open-page policy and host budget. Bare channel IDs are refused without a request. No feed registry, automatic discovery or pagination is implied.

Entries retain title, available prose, original link, publisher-reported publication time, feed provenance and available enclosure/transcript links. Atom `updated` becomes `modified_at`, never a substitute publication date. Known dates are filtered to the window; undated entries remain incomplete. A feed is a publisher-selected slice, not a historical archive. Selected article links can use `open_page` depth.

## X and video

`x_fxtwitter` reads a known numeric post ID with `conversation:<id>` or depth operation `conversation`. FxTwitter is a third-party operator: label its post text, returned replies, dates and available views/likes/reposts/reply counts accordingly. It provides no supported search or profile operation here and does not promise a complete conversation.

For a selected YouTube video's speech, use the separate [transcript reader](source-inspection.md). Captions are not viewer discussion. Native discovery or comments access remains the caller's concern; no custom video-search or TikTok/Instagram scraper ships in this library.

## Fixture

`fake` is deterministic offline test data, never public evidence. Direct manifests follow the [protocol](protocol.md); routine bounded selection and resume follow [acquisition](acquisition.md).
