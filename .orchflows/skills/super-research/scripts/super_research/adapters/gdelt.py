"""K4 GDELT DOC 2.0: a global news index with an origin-side time bound.

Measured 2026-09-01, this host. HTTPS to ``api.gdeltproject.org`` times out
at connect (curl and this package's own opener alike) while plain HTTP
answers, and the transport admits https only — so a live smoke here types
``unreachable`` and concludes nothing about the platform. The fixture below
and every fact in this docstring were captured over plain HTTP as test
evidence; the shipped module never sends anything but https, through the
same declared route every other K4 adapter uses.

``api.gdeltproject.org/api/v2/doc/doc?query=<q>&mode=artlist&format=json&
maxrecords=75`` answered 200 with ``{"articles": [...]}``, seventy-five rows
on an unbounded "climate" query — the origin's own stated ceiling. Adding
``startdatetime``/``enddatetime`` (``YYYYMMDDHHMMSS``, both edges) returned
only rows whose ``seendate`` fell inside them. Each row carries ``url``,
``url_mobile`` (blank on most rows), ``title``, ``seendate``
(``YYYYMMDDTHHMMSSZ``), ``socialimage`` (often blank), ``domain``,
``language`` and ``sourcecountry`` — no native id, no author, no counts.
The origin's own stated ceiling, in a plain-text 429 body also measured
2026-09-01, is one request per five seconds.

**A missing ``articles`` key is not schema drift.** A query matching
nothing answered 200 with the literal body ``{}`` — no ``articles`` key at
all — reproduced on two distinct nonsense queries, one bare and one dated
into an empty span. Reading that shape as `schema_drift` would mislabel the
origin's own "nothing matched" answer as a broken parser on every query
nothing matches; it is read here as `outcome="empty"` instead.
`schema_drift` stays for a body that is not a JSON object at all, an
``articles`` that is present and not a list, and a nonempty ``articles``
none of whose rows carry a ``url`` — none of the three observed, all three
a payload this parser no longer recognizes. A request the origin itself
rejects — a ``startdatetime`` outside its retained span, an unrecognized
``mode`` — answered 200 with a plain-text line naming the problem
(``Invalid query start date.``, and for `mode=badmode`, its own echoed
response headers followed by ``Invalid mode.``), never JSON; both read here
as `malformed_json`, the same code any other 200 this parser cannot parse
carries.

**mode=timelinevol and mode=context are deliberately not shipped.** Neither
is this module's ``mode``; `mode=context` answered 200 with an empty
``articles`` list on every query tried 2026-09-01 and `timelinevol` was not
tried. See ``references/route-notes/gdelt.md`` for the reopen condition.

Every record stands on the same three losses `web_search` attaches to an
index hit, minus the one GDELT does not deserve: this surface states a
publication time on every measured row, so `unknown_publication_time` never
stands here. It states no native id (`native_identity_unknown`), no engagement
count of any kind (`engagement_unavailable`), and a hit this artlist call
never hydrates (`target_not_hydrated`) — the same reading `web_search`
gives its own index hits, attached the same way: unconditionally, on every
record this parser keeps.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Mapping, Tuple

from .. import schema, transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

# Every code this module can attach, spelled once each. The first three
# stand on every record this parser keeps, unconditionally — the same
# reading `web_search` gives its own index hits, minus
# `unknown_publication_time`: the module docstring states why GDELT does
# not carry that one.
NATIVE_IDENTITY_UNKNOWN = "native_identity_unknown"
ENGAGEMENT_UNAVAILABLE = "engagement_unavailable"
TARGET_NOT_HYDRATED = "target_not_hydrated"
SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"

DESCRIPTOR = AdapterDescriptor(
    adapter_id="gdelt",
    adapter_version="1",
    access_class="K4",
    route_id=transport.GDELT_DOC_ROUTE,
    platform="gdelt",
    native_identity_namespace="gdelt",
    representation_kind="index",
    operator_identity="gdelt",
    # The origin's own stated ceiling, in a plain-text 429 body measured
    # 2026-09-01: one request per five seconds.
    min_interval_ms=5000,
    burst=1,
    cooldown_ms=60000,
    standing_loss=(NATIVE_IDENTITY_UNKNOWN, ENGAGEMENT_UNAVAILABLE, TARGET_NOT_HYDRATED),
    page_size=75,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR,)

CONTENT_KIND = "web_hit"
NATIVE_ORDER = "gdelt_doc_artlist_order"

# The origin's own grammar, spelled once each. `MAX_RECORDS_PER_PAGE` is the
# descriptor's own `page_size`, sent explicitly so the page a call reads is
# a stated size rather than whatever the origin defaults to.
QUERY_PARAM = "query"
MODE_PARAM = "mode"
FORMAT_PARAM = "format"
MAXRECORDS_PARAM = "maxrecords"
STARTDATETIME_PARAM = "startdatetime"
ENDDATETIME_PARAM = "enddatetime"
ARTLIST_MODE = "artlist"
JSON_FORMAT = "json"
MAX_RECORDS_PER_PAGE = 75

# Where the answer keeps what it returned, and the four fields a kept row
# carries onto a record. Declared, never searched for.
ARTICLES_KEY = "articles"
URL_KEY = "url"
TITLE_KEY = "title"
SEENDATE_KEY = "seendate"
DOMAIN_KEY = "domain"
LANGUAGE_KEY = "language"
SOURCECOUNTRY_KEY = "sourcecountry"

DOMAIN_ATTRIBUTE = "domain"
LANGUAGE_ATTRIBUTE = "language"
SOURCECOUNTRY_ATTRIBUTE = "sourcecountry"

# The origin's own instants, and the artifact's. `seendate` is
# ``YYYYMMDDTHHMMSSZ``; `startdatetime`/`enddatetime` take
# ``YYYYMMDDHHMMSS``, no separators and no trailing zone letter.
ORIGIN_SEENDATE_FORMAT = "%Y%m%dT%H%M%SZ"
ORIGIN_WINDOW_FORMAT = "%Y%m%d%H%M%S"
RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _origin_instant(seendate: Any) -> str:
    """One row's ``seendate`` as an artifact instant, or nothing at all.

    A row this parser cannot read as the documented shape carries no
    publication time on its record rather than a guessed one; nothing here
    attaches a loss code for it; the module docstring states why.
    """

    text = _text(seendate)
    if not text:
        return ""
    try:
        moment = datetime.strptime(text, ORIGIN_SEENDATE_FORMAT)
    except ValueError:
        return ""
    return moment.strftime(RECORD_INSTANT_FORMAT)


def _origin_window_datetime(instant: str) -> str:
    """One manifest instant as the origin's own ``YYYYMMDDHHMMSS``, or nothing."""

    try:
        moment = datetime.strptime(instant, RECORD_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.strftime(ORIGIN_WINDOW_FORMAT)


def _record_for(position: int, row: Mapping[str, Any], url: str) -> NativeRecord:
    attributes: List[Tuple[str, str]] = []
    domain = _text(row.get(DOMAIN_KEY))
    if domain:
        attributes.append((DOMAIN_ATTRIBUTE, domain))
    language = _text(row.get(LANGUAGE_KEY))
    if language:
        attributes.append((LANGUAGE_ATTRIBUTE, language))
    sourcecountry = _text(row.get(SOURCECOUNTRY_KEY))
    if sourcecountry:
        attributes.append((SOURCECOUNTRY_ATTRIBUTE, sourcecountry))
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        canonical_locator=url,
        title=_text(row.get(TITLE_KEY)),
        published_at=_origin_instant(row.get(SEENDATE_KEY)),
        attributes=tuple(attributes),
        native_position=position,
        loss=DESCRIPTOR.standing_loss,
    )


def _answered(
    response: transport.TransportResponse,
    records: Tuple[NativeRecord, ...] = (),
    outcome: str = "ok",
    warnings: Tuple[str, ...] = (),
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


def _failed(response: transport.TransportResponse, code: str, warning: str) -> NativePage:
    return _answered(response, outcome="failed", warnings=(warning,), loss=(code,))


def _articles_page(response: transport.TransportResponse, payload: Any, query: str) -> NativePage:
    if not isinstance(payload, Mapping):
        return _failed(
            response,
            SCHEMA_DRIFT,
            "route {0} answered 200 with a body that is not a json object: the"
            " payload this adapter reads has changed shape".format(DESCRIPTOR.route_id),
        )
    articles = payload.get(ARTICLES_KEY)
    if articles is None:
        # The origin's own "nothing matched" shape, measured twice: a bare
        # ``{}`` with no `articles` key at all. See the module docstring —
        # this is deliberately not `schema_drift`.
        return _answered(
            response,
            outcome="empty",
            warnings=(
                "route {0} answered 200 with no {1}: no article matched {2}".format(
                    DESCRIPTOR.route_id, ARTICLES_KEY, query
                ),
            ),
        )
    if not isinstance(articles, list):
        return _failed(
            response,
            SCHEMA_DRIFT,
            "route {0} answered 200 with a non-list {1}: the payload this adapter"
            " reads has changed shape".format(DESCRIPTOR.route_id, ARTICLES_KEY),
        )

    records: List[NativeRecord] = []
    unidentified = 0
    for position, row in enumerate(articles):
        if not isinstance(row, Mapping):
            unidentified += 1
            continue
        url = _text(row.get(URL_KEY))
        if not url:
            unidentified += 1
            continue
        records.append(_record_for(position, row, url))

    if records:
        warnings = (
            (
                "route {0} answered 200 with {1} row(s) naming no {2}: they are"
                " not rows this adapter can identify".format(
                    DESCRIPTOR.route_id, unidentified, URL_KEY
                ),
            )
            if unidentified
            else ()
        )
        return _answered(response, records=tuple(records), warnings=warnings)
    if articles:
        # Rows present and not one of them identified: the payload
        # reshaping, not an index that matched nothing.
        return _failed(
            response,
            SCHEMA_DRIFT,
            "route {0} answered 200 with {1} row(s) and no {2} on any of them:"
            " the payload has changed shape".format(
                DESCRIPTOR.route_id, len(articles), URL_KEY
            ),
        )
    return _answered(
        response,
        outcome="empty",
        warnings=(
            "route {0} answered 200 with an empty {1} list: no article matched"
            " {2}".format(DESCRIPTOR.route_id, ARTICLES_KEY, query),
        ),
    )


def _page_from(response: transport.TransportResponse, query: str) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        return _failed(
            response,
            HTTP_STATUS,
            "http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),
        )
    try:
        payload = json.loads(response.body)
    except ValueError:
        # Covers both measured shapes of a rejected request: a plain-text
        # line (`Invalid query start date.`) and `mode=badmode`'s echoed
        # response headers ahead of `Invalid mode.` — 200, never JSON.
        return _failed(
            response,
            MALFORMED_JSON,
            "route {0} answered 200 with a body this parser could not read as"
            " json".format(DESCRIPTOR.route_id),
        )
    return _articles_page(response, payload, query)


def _params(request: AdapterRequest) -> Mapping[str, str]:
    params = {
        QUERY_PARAM: request.query,
        MODE_PARAM: ARTLIST_MODE,
        FORMAT_PARAM: JSON_FORMAT,
        MAXRECORDS_PARAM: str(MAX_RECORDS_PER_PAGE),
    }
    if request.window_start:
        start = _origin_window_datetime(request.window_start)
        if start:
            params[STARTDATETIME_PARAM] = start
    if request.window_end:
        end = _origin_window_datetime(request.window_end)
        if end:
            params[ENDDATETIME_PARAM] = end
    return params


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Fetch one artlist page and return exactly one NativePage.

    One surface, one call: this adapter reads `request.query` alone, the
    same way `web_search` reads its own — a hydration-shaped request (its
    `target_ids` populated, its `query` the empty string a hydration step's
    `AdapterRequest` always carries) is served exactly as an empty-query
    discovery would be, not specially refused, because this module never
    reads `target_ids` at all.
    """

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, request.query)

    return fetch_one_page(
        DESCRIPTOR, carrier, params=_params(request), parse=parse, native_order=NATIVE_ORDER
    )
