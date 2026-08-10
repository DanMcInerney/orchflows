"""K0 Reddit freshness probe over the one Reddit surface that answers.

Measured 2026-08-10 (findings.md §1, "Reddit"): ``www.reddit.com/r/<sub>.rss``
answered 200 with 32 KB in 1.4 s, carrying a title, a link, an author and an
updated stamp per entry. Every ``.json`` form answered **403** — on ``www.``,
``old.`` and ``api.`` alike, to a curl User-Agent, a custom app User-Agent and a
browser User-Agent alike. Three unrelated identities getting identical bodies is
IP-class blocking, not a header problem, so there is no ``.json`` route in this
package, no host alias to try, and nothing here to fall back to. A refusal on
this route is an outcome; it is never a reason to become a different client.

**This route is why the run-local cache exists.** Its measured ceiling is one to
two requests per ~30 s per IP — four back-to-back requests answered once and
then refused three times — which is the tightest in the roster by a factor of
thirty. A run that re-reads what it just read here does not run slowly, it
starves, so the descriptor declares the floor of that measured range and the
cache holds the answer for longer than the interval that paces it.

**Four fields, and no fifth.** The roster row is title, link, author and
updated, and this route publishes no count of any kind. Every other Reddit
surface in the roster carries ``score``, ``num_comments`` and ``upvote_ratio``,
which is exactly why the absence has to be said out loud rather than filled: a
zero here would be indistinguishable from a post nobody has voted on, and a
caller ranking on it would be ranking on a number this package invented. The
descriptor declares neither engagement metric and every record carries
``engagement_unavailable``.

The parser is :mod:`html.parser` rather than an XML reader, which is the same
choice every other markup-reading adapter here makes and it is load-bearing for
one more reason: acquired text is untrusted, and this parser expands no
document-defined entity, so a feed cannot ask it to allocate a gigabyte.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Dict, List, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="reddit_feed",
    adapter_version="1",
    access_class="K0",
    route_id=transport.REDDIT_FEED_ROUTE,
    platform="reddit",
    native_identity_namespace="reddit",
    # A syndication feed is its own representation, and the closed enum has had
    # a name for it all along. It is deliberately not `native`: this is four
    # fields about a post, not the post as the platform holds it, and calling it
    # native would let a feed entry group with a hydrated record as though the
    # two carried the same thing.
    representation_kind="feed",
    operator_identity="reddit",
    # True of every entry this route will ever return rather than of some of
    # them, which is what makes it standing rather than per-record.
    standing_loss=("engagement_unavailable",),
    # findings.md §1: four requests back to back answered 1x 200 then 3x 429;
    # after a thirty-second cooldown, paced one per six seconds, it answered
    # 2x 200 and then refused again; a custom UA changed none of it. The
    # effective ceiling is 1–2 per ~30 s per IP, and a client that respects a
    # limit takes the floor of a measured range rather than its ceiling. The
    # cooldown is the window the same measurement saw service return in.
    min_interval_ms=30000,
    burst=1,
    cooldown_ms=30000,
    # Declared by omission, which is a statement: this route publishes no count
    # of comments and no count of replies, so it has no eligible metric and the
    # two engagement orders skip it rather than ranking it on a zero.
)

NATIVE_ORDER = "reddit_feed_recency_order"
CONTENT_KIND = "post"

# The Atom document this route answers with, and what one entry of it is.
# Declared, never searched for: the value of a typed drift is that it says the
# document changed shape rather than that the community went quiet.
FEED_TAG = "feed"
ENTRY_TAG = "entry"
AUTHOR_TAG = "author"
LINK_TAG = "link"
HREF_ATTRIBUTE = "href"

# The four fields findings.md §1 records this route returning, plus the entry's
# own identifier. `id` is not in the measured field list and is read anyway: it
# is required of every Atom entry, and without it a record can be grouped with
# nothing. It is not engagement, which is the one thing this row forbids.
TITLE_FIELD = "title"
UPDATED_FIELD = "updated"
ID_FIELD = "id"
NAME_FIELD = "name"
LINK_FIELD = "link"

# Text between tags, captured only inside an entry. `title`, `updated` and `id`
# all appear at feed level too, and a feed's own title is not a post's.
ENTRY_TEXT_TAGS = (TITLE_FIELD, UPDATED_FIELD, ID_FIELD)
ENTRY_KEYS = (TITLE_FIELD, UPDATED_FIELD, ID_FIELD, NAME_FIELD, LINK_FIELD)

# Every field a record must have for the roster row to be complete. The entry's
# id is absent from this list on purpose: a row short of it is not a row of this
# kind at all, and it is dropped rather than marked.
ROSTER_FIELDS = (TITLE_FIELD, LINK_FIELD, NAME_FIELD, UPDATED_FIELD)

# Reddit spells one thing two ways across its own surfaces, and the rule for
# which prefix survives is whether it is an identity or an address. `t3_` is
# part of how Reddit names a submission — wrong_merge_law rule 6 — so it stays,
# and it is the same spelling the archive adapter produces. `/u/` is the path a
# user's page lives at, not the handle who wrote the post, so it goes.
AUTHOR_PATH_PREFIX = "/u/"

# The stamp this feed emits, and the one an artifact record holds.
ROUTE_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SCHEMA_DRIFT = "schema_drift"
HTTP_STATUS = "http_status"

# Declared here and produced nowhere in this module, which is the statement: no
# status this route can answer with is a report that a credential was needed.
# The surface is documented keyless, and Reddit's own refusal for a community it
# will not serve publicly is that community's setting rather than this package's
# missing account.
AUTH_REQUIRED = "auth_required"


class _AtomEntryParser(HTMLParser):
    """Collect this document's feed element and the entries inside it."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.feed_seen = False
        self.entries: List[Dict[str, str]] = []
        self._in_entry = False
        self._in_author = False
        self._field = ""

    def handle_starttag(self, tag, attrs):
        if tag == FEED_TAG:
            self.feed_seen = True
            return
        if tag == ENTRY_TAG:
            self.entries.append(dict.fromkeys(ENTRY_KEYS, ""))
            self._in_entry = True
            return
        if not self._in_entry:
            return
        if tag == AUTHOR_TAG:
            self._in_author = True
        elif tag == LINK_TAG:
            # The entry's own address, as the feed published it, and the first
            # one wins: Reddit states one per entry and a document that states
            # two has not said which is the post.
            if not self.entries[-1][LINK_FIELD]:
                self.entries[-1][LINK_FIELD] = dict(attrs).get(HREF_ATTRIBUTE) or ""
        elif tag == NAME_FIELD and self._in_author:
            self._field = NAME_FIELD
        elif tag in ENTRY_TEXT_TAGS:
            self._field = tag

    def handle_endtag(self, tag):
        if tag == ENTRY_TAG:
            self._in_entry = False
            self._field = ""
        elif tag == AUTHOR_TAG:
            self._in_author = False
        elif tag == self._field:
            self._field = ""

    def handle_data(self, data):
        if self._field and self._in_entry:
            self.entries[-1][self._field] += data


def atom_instant_to_utc_iso(stamped: str) -> str:
    """One Atom stamp as the artifact's instant, or nothing.

    Only the shape this feed emits is read — an offset-bearing RFC 3339 instant,
    with a bare ``Z`` admitted as the offset it means. A stamp in any other form
    is a missing time rather than an approximated one: an entry dated from the
    moment it was found would look exactly as fresh as the read that found it,
    which is the one thing a freshness probe must never say.
    """

    text = stamped.strip()
    if not text:
        return ""
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.strptime(text, ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.astimezone(timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def author_handle(name: str) -> str:
    """The handle who wrote a post, out of the path this feed writes it inside."""

    stripped = name.strip()
    return stripped[len(AUTHOR_PATH_PREFIX):] if stripped.startswith(
        AUTHOR_PATH_PREFIX
    ) else stripped


def roster_row_of(entry: Dict[str, str]) -> Dict[str, str]:
    """One entry's roster row, named as findings.md §1 names it."""

    return {
        TITLE_FIELD: entry[TITLE_FIELD].strip(),
        LINK_FIELD: entry[LINK_FIELD].strip(),
        NAME_FIELD: author_handle(entry[NAME_FIELD]),
        UPDATED_FIELD: atom_instant_to_utc_iso(entry[UPDATED_FIELD]),
    }


def _record_for(position: int, entry: Dict[str, str]) -> NativeRecord:
    roster = roster_row_of(entry)
    missing = tuple(name for name in ROSTER_FIELDS if not roster[name])
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        canonical_locator=roster[LINK_FIELD],
        # The fullname Reddit identifies a submission by, carried exactly as the
        # feed spells it. No body travels with it: this route publishes an
        # entry's rendered chrome rather than the post's own text, and a body
        # made of chrome would hash to something no other surface can match.
        native_item_id=entry[ID_FIELD].strip(),
        title=roster[TITLE_FIELD],
        author=roster[NAME_FIELD],
        published_at=roster[UPDATED_FIELD],
        native_position=position,
        # No engagement, ever. The absence is standing rather than per-record
        # because it is true of every entry this route can return.
        loss=DESCRIPTOR.standing_loss + (("field_omitted",) if missing else ()),
    )


def _page(
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...] = (),
    warnings: Tuple[str, ...] = (),
    outcome: str = "ok",
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _page_from(response: transport.TransportResponse, subreddit: str) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        return _page(
            response,
            warnings=(
                "http status {0} from {1} for r/{2}: this is the status Reddit"
                " answered with, and not a credential this package is"
                " missing".format(response.status, DESCRIPTOR.route_id, subreddit),
            ),
            outcome="failed",
            loss=(HTTP_STATUS,),
        )

    parser = _AtomEntryParser()
    parser.feed(response.body)
    parser.close()

    if not parser.feed_seen:
        return _page(
            response,
            warnings=(
                "route {0} answered 200 with a body carrying no <{1}> element:"
                " the document this adapter reads has changed shape".format(
                    DESCRIPTOR.route_id, FEED_TAG
                ),
            ),
            outcome="failed",
            loss=(SCHEMA_DRIFT,),
        )

    # An entry with no identifier is not an entry: it can be grouped with
    # nothing and addressed as nothing, and a record naming nothing is worse
    # than one fewer record.
    records = tuple(
        _record_for(position, entry)
        for position, entry in enumerate(
            entry for entry in parser.entries if entry[ID_FIELD].strip()
        )
    )
    if records:
        return _page(response, records=records)
    return _page(
        response,
        warnings=(
            "route {0} answered 200 with a <{1}> holding no entry: r/{2} has"
            " published nothing this feed reports".format(
                DESCRIPTOR.route_id, FEED_TAG, subreddit
            ),
        ),
        outcome="empty",
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one subreddit's feed once and return exactly one NativePage.

    One call, one route, no pagination: this feed states no next page and none
    is derived, and at one read per thirty seconds a caller that wanted to walk
    one would be asking for something the origin has already said it will not
    give.
    """

    subreddit = request.target_ids[0] if request.target_ids else request.query

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, subreddit)

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"subreddit": subreddit},
        parse=parse,
        native_order=NATIVE_ORDER,
    )
