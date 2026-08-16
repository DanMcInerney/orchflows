"""K0 LinkedIn job postings from the guest search surface.

Measured 2026-08-10 (LinkedIn): the jobs-guest search route
answered 200 in 0.7 s with 27 KB carrying ten postings, each with a
``jobPosting`` URN id, a title, a company and a ``datetime``, and ``start=``
paginating. No account, no token, and no vendor-published credential — the
plainest ``K0`` surface in the roster.

The route answers with a bare results list rather than a document, so the
container this module reads is declared once and never searched for. Three
answers then have to stay apart, because each costs an operator something
different. A list holding no card is a search that matched nothing. A body
with no markup at all is the route declining to send a list, which is the same
fact reached by paging past the last result. Markup holding neither the list
nor a single card is the page having changed shape, and only that one is
``schema_drift`` — a parser that typed every cardless answer as drift would
send someone hunting a markup change every time a query came up short.

LinkedIn reports a posting's date at day precision and the artifact's instant
carries seconds, so every record from this route declares
``date_precision_only``: midnight UTC is this package's form for a day, and
not a time anyone observed.
"""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Tuple

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
    adapter_id="linkedin_jobs",
    adapter_version="1",
    access_class="K0",
    route_id=transport.LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
    platform="linkedin",
    native_identity_namespace="linkedin",
    representation_kind="native",
    operator_identity="linkedin",
    # True of every card this route will ever return rather than of some of
    # them, which is what makes it standing rather than per-record.
    standing_loss=("date_precision_only",),
    # The 2026-08-10 probes: 0.7 s per request. Nothing on this route was measured
    # refusing, so `burst` and `cooldown_ms` keep the protocol's conservative
    # defaults rather than a ceiling nobody observed.
    min_interval_ms=700,
    # A job posting carries no comment count and no reply count, and neither
    # name is inferred here. An unset metric is a stated absence; a guessed one
    # would let `most_commented` rank postings on a number nobody reported.
)

NATIVE_ORDER = "linkedin_jobs_search_order"
CONTENT_KIND = "job_posting"

# Where this fragment keeps its postings, and what one posting is. Declared,
# never searched for: the whole value of a typed drift is that it says the page
# changed rather than that the search found nothing.
RESULTS_LIST_TAG = "ul"
RESULTS_LIST_CLASS = "jobs-search__results-list"
CARD_URN_ATTRIBUTE = "data-entity-urn"
JOB_URN_PREFIX = "urn:li:jobPosting:"
TITLE_CLASS = "base-search-card__title"
COMPANY_CLASS = "base-search-card__subtitle"
# The posting's own address, as the card publishes it. It is taken from the
# card rather than assembled here for two reasons: a host belongs to
# `routes.py` and to nothing else, and an address the origin published is a
# better claim than one this module composed. Its query string is dropped —
# and only its query string — because LinkedIn hangs per-response tracking
# parameters off it, so two reads of one posting would otherwise normalize to
# two locators and never group.
FULL_LINK_CLASS = "base-card__full-link"
LINK_ATTRIBUTE = "href"
# The posted day is read from the time element's own attribute. LinkedIn adds a
# `--new` class to a recent posting's listdate, so a parser keyed to the class
# name would lose the date on exactly the postings a caller most wants dated.
LISTDATE_TAG = "time"
LISTDATE_ATTRIBUTE = "datetime"

# The two card fields that are text between tags, and the tag each capture ends
# at. Everything else on a card is an attribute.
CARD_TEXT_CLASSES = (("title", TITLE_CLASS), ("company", COMPANY_CLASS))
CARD_KEYS = ("urn_id", "title", "company", "posted_at", "locator")

# Every field the 2026-08-10 probes record this route returning per card. A record
# missing one says so, because a caller comparing postings needs to know which
# rows were incomplete rather than which were undated.
ROSTER_FIELDS = ("urn_id", "title", "company", "posted_date")

# The stamp this route emits, and the one an artifact record holds.
ROUTE_DATE_FORMAT = "%Y-%m-%d"
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class _JobCardParser(HTMLParser):
    """Collect this fragment's results list and the postings inside it."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.results_list_seen = False
        self.cards: List[Dict[str, str]] = []
        self._field = ""
        self._field_tag = ""

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == RESULTS_LIST_TAG and RESULTS_LIST_CLASS in classes:
            self.results_list_seen = True
        urn = attributes.get(CARD_URN_ATTRIBUTE) or ""
        if urn.startswith(JOB_URN_PREFIX):
            card = dict.fromkeys(CARD_KEYS, "")
            card["urn_id"] = urn[len(JOB_URN_PREFIX):]
            self.cards.append(card)
            self._field = ""
            return
        if not self.cards:
            return
        for field, class_name in CARD_TEXT_CLASSES:
            if class_name in classes:
                self._field = field
                self._field_tag = tag
                return
        if tag == LISTDATE_TAG:
            self.cards[-1]["posted_at"] = attributes.get(LISTDATE_ATTRIBUTE) or ""
        elif FULL_LINK_CLASS in classes:
            self.cards[-1]["locator"] = attributes.get(LINK_ATTRIBUTE) or ""

    def handle_endtag(self, tag):
        if self._field and tag == self._field_tag:
            self._field = ""

    def handle_data(self, data):
        if self._field and self.cards:
            self.cards[-1][self._field] += data


def route_day_to_utc_iso(posted_at: Any) -> str:
    """This route's day as the artifact's instant, or nothing.

    Only the exact form the route emits is read. A stamp in any other shape is
    a missing date rather than an approximated one: a posting dated from the
    moment it was found would look exactly as fresh as the search that found
    it, which is the kind of wrong that survives review.
    """

    if not isinstance(posted_at, str) or not posted_at.strip():
        return ""
    try:
        moment = datetime.strptime(posted_at.strip(), ROUTE_DATE_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def untracked_locator(href: str) -> str:
    """One posting's published address with its tracking parameters dropped."""

    if not href:
        return ""
    parts = urllib.parse.urlsplit(href.strip())
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def roster_row_of(card: Dict[str, str]) -> Dict[str, str]:
    """One card's roster row, named as the 2026-08-10 probes name it."""

    return {
        "urn_id": card["urn_id"].strip(),
        "title": card["title"].strip(),
        "company": card["company"].strip(),
        "posted_date": route_day_to_utc_iso(card["posted_at"]),
    }


def _record_for(position: int, card: Dict[str, str]) -> NativeRecord:
    roster = roster_row_of(card)
    missing = tuple(name for name in ROSTER_FIELDS if not roster[name])
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        canonical_locator=untracked_locator(card["locator"]),
        native_item_id=roster["urn_id"],
        title=roster["title"],
        # The company is the party that posted; a job posting has no individual
        # author. The card's location is deliberately not carried: it is not in
        # the roster row, and no record field means "where a job is offered" —
        # putting it in `community` would make that field a subreddit on one
        # adapter and a city on another.
        author=roster["company"],
        published_at=roster["posted_date"],
        native_position=position,
        loss=DESCRIPTOR.standing_loss + (("field_omitted",) if missing else ()),
    )


def _page(
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...],
    warnings: Tuple[str, ...],
    outcome: str,
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


def _page_from(response: transport.TransportResponse) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        return _page(
            response,
            (),
            ("http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),),
            "failed",
            ("http_status",),
        )

    parser = _JobCardParser()
    parser.feed(response.body)
    parser.close()

    records = tuple(_record_for(position, card) for position, card in enumerate(parser.cards))
    if records:
        return _page(response, records, (), "ok")
    if parser.results_list_seen:
        # The one empty this route answers with most often, and it is said out
        # loud: an empty nobody explained cannot be told apart at a glance from
        # the drift below, which is the whole distinction this branch keeps.
        return _page(
            response,
            (),
            (
                "route {0} answered 200 with a {1} holding no {2} card: this"
                " search matched nothing".format(
                    DESCRIPTOR.route_id, RESULTS_LIST_CLASS, JOB_URN_PREFIX
                ),
            ),
            "empty",
        )
    if not response.body.strip():
        return _page(
            response,
            (),
            (
                "route {0} answered 200 with no markup at all: this search"
                " matched nothing, or start= is past the last result".format(
                    DESCRIPTOR.route_id
                ),
            ),
            "empty",
        )
    return _page(
        response,
        (),
        (
            "route {0} answered 200 with markup carrying neither a {1} nor a"
            " {2} card: the fragment this adapter reads has changed shape".format(
                DESCRIPTOR.route_id, RESULTS_LIST_CLASS, JOB_URN_PREFIX
            ),
        ),
        "failed",
        ("schema_drift",),
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one page of guest job search and return exactly one NativePage.

    ``start=`` is the caller's: pagination is the core's to own, so a cursor it
    froze is spent here and no next offset is derived. This fragment states
    none, and inventing one from the count returned would make the adapter the
    thing that decides there is another page. Nothing in this release freezes
    one — ``runner.planned_calls`` sets no cursor — so the parameter is the
    seam and every call starts at the top.
    """

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"keywords": request.query, "start": request.cursor},
        parse=_page_from,
        native_order=NATIVE_ORDER,
    )
