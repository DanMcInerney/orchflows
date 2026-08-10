"""K2 X profile timelines from the structured data a public page embeds.

Measured 2026-08-10 (findings.md §1, "X"): the syndication profile route
answered 200 in 2.5 s with 378 KB carrying 100 timeline entries, each with
``full_text``, ``created_at``, ``favorite_count``, ``retweet_count``,
``reply_count``, ``quote_count``, ``conversation_id_str``, ``lang``, and an
author with ``followers_count``. That is the platform's own engagement, at
zero cost and with no account.

A ``K2`` route is structured data inside a page the vendor is free to
rewrite, so the container this module reads is declared once and never
searched for. A page that no longer holds it is ``schema_drift`` — naming
what changed — and never an empty timeline, which is what a parser that went
hunting for a familiar-looking list would eventually report.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Mapping, Sequence, Tuple

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
    adapter_id="x_syndication",
    adapter_version="1",
    access_class="K2",
    route_id=transport.X_SYNDICATION_TIMELINE_ROUTE,
    platform="x",
    native_identity_namespace="x",
    representation_kind="native",
    operator_identity="x",
    # findings.md §1: 2.5 s per request. Nothing on this route was measured
    # refusing, so `burst` and `cooldown_ms` keep the protocol's conservative
    # defaults rather than a ceiling nobody observed.
    min_interval_ms=2500,
    # X reports one metric for replies and none named for comments. Declaring
    # this number under both names would make `most_commented` and
    # `most_replied` silently identical on a count the platform reported once.
    reply_count_metric="reply_count",
)

NATIVE_ORDER = "x_syndication_timeline_order"
X_ORIGIN = "https://x.com"
CONTENT_KIND = "post"

# Where this page keeps its timeline, and what one entry of it is. Declared,
# never searched for: a parser that hunts for a familiar-looking list is
# inferring by similarity, and the whole point of a typed drift is to say that
# the page changed rather than that the profile went quiet.
NEXT_DATA_SCRIPT_ID = "__NEXT_DATA__"
TIMELINE_PATH = ("props", "pageProps", "timeline", "entries")
TWEET_ENTRY_TYPE = "tweet"
TWEET_PATH = ("content", "tweet")

# Every field findings.md §1 records this route returning per entry. A record
# missing one says so, because a caller comparing a timeline needs to know
# which rows were incomplete rather than which were zero.
ROSTER_FIELDS = (
    "full_text",
    "created_at",
    "favorite_count",
    "retweet_count",
    "reply_count",
    "quote_count",
    "conversation_id_str",
)
ENGAGEMENT_FIELDS = ("favorite_count", "retweet_count", "reply_count", "quote_count")

# The stamp this route emits, and the one an artifact record holds.
ROUTE_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%S"
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class _NextDataParser(HTMLParser):
    """Collect the one embedded script this route keeps its timeline in."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.payload = ""
        self._capturing = False

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == NEXT_DATA_SCRIPT_ID:
            self._capturing = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._capturing = False

    def handle_data(self, data):
        if self._capturing:
            self.payload += data


def embedded_payload(body: str) -> str:
    """The page's ``__NEXT_DATA__`` script, or an empty string when it has none."""

    parser = _NextDataParser()
    parser.feed(body)
    parser.close()
    return parser.payload


def dig(payload: Any, path: Sequence[str]) -> Any:
    """Follow one declared path of mapping keys, or return None at the first gap."""

    found = payload
    for key in path:
        if not isinstance(found, Mapping):
            return None
        found = found.get(key)
    return found


def route_instant_to_utc_iso(created_at: Any) -> str:
    """This route's ISO-8601 stamp as the artifact's instant, or nothing.

    Fractional seconds and a trailing ``Z`` are the two shapes the route emits.
    Anything else is unparseable rather than approximated: a time nobody can
    read is a missing time, and every ordering downstream is entitled to know
    the difference.
    """

    if not isinstance(created_at, str) or not created_at:
        return ""
    text = created_at.strip()
    if text.endswith("Z"):
        text = text[:-1]
    text = text.split(".")[0]
    try:
        moment = datetime.strptime(text, ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def _engagement_of(tweet: Mapping[str, Any]) -> Tuple[Tuple[str, int], ...]:
    # Only exact native integers are admitted; anything else is not a snapshot.
    return tuple(
        (name, tweet[name])
        for name in ENGAGEMENT_FIELDS
        if isinstance(tweet.get(name), int) and not isinstance(tweet.get(name), bool)
    )


def _locator_for(screen_name: str, tweet_id: str) -> str:
    if not screen_name or not tweet_id:
        return ""
    return "{0}/{1}/status/{2}".format(X_ORIGIN, screen_name, tweet_id)


def _record_for(position: int, tweet: Mapping[str, Any]) -> NativeRecord:
    author = tweet.get("user") or {}
    screen_name = author.get("screen_name") or "" if isinstance(author, Mapping) else ""
    tweet_id = tweet.get("id_str") or ""
    missing = tuple(name for name in ROSTER_FIELDS if tweet.get(name) is None)
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        canonical_locator=_locator_for(screen_name, tweet_id),
        native_item_id=tweet_id,
        # X names the thread a post belongs to `conversation_id_str`: its own
        # id for a root, the root it answers for a reply. Both are the
        # platform's own statement, and both are carried as reported.
        native_parent_id=tweet.get("conversation_id_str") or "",
        body=tweet.get("full_text") or "",
        author=screen_name,
        published_at=route_instant_to_utc_iso(tweet.get("created_at")),
        engagement=_engagement_of(tweet),
        native_position=position,
        loss=("field_omitted",) if missing else (),
    )


def _tweets_of(entries: Sequence[Any]) -> Tuple[Mapping[str, Any], ...]:
    """Every timeline entry that is a post, in the order the page listed them."""

    found = []
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("type") != TWEET_ENTRY_TYPE:
            continue
        tweet = dig(entry, TWEET_PATH)
        if isinstance(tweet, Mapping):
            found.append(tweet)
    return tuple(found)


def _drifted(response: transport.TransportResponse, detail: str) -> NativePage:
    return build_native_page(
        DESCRIPTOR,
        (),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=(
            "route {0} answered {1} and {2}: the page this adapter reads has"
            " changed shape".format(DESCRIPTOR.route_id, response.status, detail),
        ),
        outcome="failed",
        loss=("schema_drift",),
    )


def _page_from(response: transport.TransportResponse) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
            warnings=("http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),),
            outcome="failed",
            loss=("http_status",),
        )

    embedded = embedded_payload(response.body)
    if not embedded.strip():
        return _drifted(response, "embedded no " + NEXT_DATA_SCRIPT_ID + " script")
    try:
        payload = json.loads(embedded)
    except ValueError:
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
            warnings=(NEXT_DATA_SCRIPT_ID + " was not a json object",),
            outcome="failed",
            loss=("malformed_json",),
        )

    entries = dig(payload, TIMELINE_PATH)
    if not isinstance(entries, list):
        return _drifted(response, "kept no timeline at " + ".".join(TIMELINE_PATH))

    records = tuple(
        _record_for(position, tweet) for position, tweet in enumerate(_tweets_of(entries))
    )
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        outcome="ok" if records else "empty",
    )


def screen_name_of(request: AdapterRequest) -> str:
    """The handle this route reads, and the one form it is written in.

    A hydration step names the profile in ``target_ids``; a discovery step
    names it in ``query``. A leading ``@`` is X's display form rather than part
    of the handle.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    return named[1:] if named.startswith("@") else named


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one profile timeline page and return exactly one NativePage."""

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"screen_name": screen_name_of(request)},
        parse=_page_from,
        native_order=NATIVE_ORDER,
    )
