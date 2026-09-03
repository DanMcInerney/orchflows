"""K0 scholarly works over three origins: OpenAlex, Crossref, arXiv.

Measured 2026-09-01, all three keyless and 200. ``api.openalex.org/works``
``?search=<q>&filter=from_publication_date:...,to_publication_date:...``
``&per-page=25`` answers ``{"meta": {...}, "results": [...]}``, empty the
same way — an empty list, never a missing key. A work: ``id`` (an
``https://openalex.org/W...`` locator, doubled as this module's
``canonical_locator``), ``display_name``, ``publication_date`` (a day, never
a time), ``cited_by_count``, ``type`` (the origin's own classification,
carried verbatim as ``canonical_content_kind``), ``authorships[].author.``
``display_name``, ``ids.doi``, ``primary_location.landing_page_url``.

``api.crossref.org/works?query=<q>&filter=from-pub-date:...,until-pub-date:``
``...&rows=20`` answers ``{"message": {"items": [...], ...}}``, empty the
same way. An item: ``DOI``, ``title`` (an array — ``title[0]`` is read),
``author[].given``/``.family`` (Crossref's own docs say ``family`` "may be
absent on some types", and measured rows confirm it), ``published.``
``date-parts`` — ``[[Y, M, D]]`` with the day sometimes omitted and the
month sometimes omitted too (``[[Y]]``, measured) — ``is-referenced-by-``
``count``, ``URL``, ``container-title``, ``publisher``.

``export.arxiv.org/api/query?search_query=all:"<q>"[+AND+submittedDate:[``
``YYYYMMDDHHMM+TO+YYYYMMDDHHMM]]&start=0&max_results=10`` answers Atom XML,
a ``<feed>`` with zero or more ``<entry>``. An entry: ``id`` (a versioned
``http://arxiv.org/abs/`` address — measured as ``http``, never used as
``canonical_locator`` for that reason), ``title``, ``published`` (a full
``...Z`` instant, authoritative), repeated ``<author><name>``, ``summary``,
and two ``<link>``: ``rel="alternate" type="text/html"`` is the item's own
address, ``rel="related" type="application/pdf"`` its PDF. An unquoted
multi-word query reads as an OR of its words — measured live — so this
module always quotes the caller's argument as one phrase.

**Every origin bounds publication time at the origin, in its own grammar,
so ``WINDOW_REACH["scholarly"]`` declares ``True`` once.** A caller naming
one edge still narrows OpenAlex's and Crossref's filter to that one clause;
arXiv's range grammar takes two, so a missing edge is filled with a
measured sentinel — ``ARXIV_FAR_FUTURE``/``ARXIV_FAR_PAST`` — rather than
left unsent. The naive floor, year 1, answered 500 live; year 1900 and year
2100 both answered 200, so those are the measured sentinels, not the
calendar's own.

**The documented ``mailto`` etiquette is deliberately not sent**, on either
JSON origin: this package attaches no identity a route constant does not
spell, and a caller's email is not one.

**One adapter, three origins, one call each.** A caller names the operation
with a prefix; a bare query defaults to OpenAlex. Record construction and
the Atom parser are extracted to ``_support.scholarly_records``.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .. import schema, transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)
from ._support.scholarly_records import (
    ArxivFeedParser,
    arxiv_records,
    crossref_records,
    openalex_records,
)

DATE_PRECISION_ONLY = "date_precision_only"

DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.OPENALEX_WORKS_ROUTE,
    platform="openalex",
    native_identity_namespace="openalex",
    representation_kind="native",
    operator_identity="openalex",
    # OpenAlex states a publication day and never a time of day, on every
    # work this route will ever answer — standing, the same reasoning
    # `linkedin_jobs.DESCRIPTOR.standing_loss` carries for its own route.
    standing_loss=(DATE_PRECISION_ONLY,),
    min_interval_ms=1000,
    burst=1,
    page_size=25,
)

CROSSREF_DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.CROSSREF_WORKS_ROUTE,
    platform="crossref",
    native_identity_namespace="crossref",
    representation_kind="native",
    operator_identity="crossref",
    min_interval_ms=1000,
    burst=1,
    page_size=20,
)

ARXIV_DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.ARXIV_QUERY_ROUTE,
    platform="arxiv",
    native_identity_namespace="arxiv",
    representation_kind="native",
    operator_identity="arxiv",
    # arXiv's own API terms ask for one request every three seconds.
    min_interval_ms=3000,
    burst=1,
    page_size=10,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR, CROSSREF_DESCRIPTOR, ARXIV_DESCRIPTOR)

OPENALEX_OPERATION = "openalex"
CROSSREF_OPERATION = "crossref"
ARXIV_OPERATION = "arxiv"
SCHOLARLY_OPERATIONS = (OPENALEX_OPERATION, CROSSREF_OPERATION, ARXIV_OPERATION)

OPERATION_SURFACES = {
    OPENALEX_OPERATION: DESCRIPTOR,
    CROSSREF_OPERATION: CROSSREF_DESCRIPTOR,
    ARXIV_OPERATION: ARXIV_DESCRIPTOR,
}

NATIVE_ORDERS = {
    OPENALEX_OPERATION: "openalex_relevance_order",
    CROSSREF_OPERATION: "crossref_relevance_order",
    ARXIV_OPERATION: "arxiv_relevance_order",
}

# --- Request grammar --------------------------------------------------

RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT

OPENALEX_SEARCH_PARAM = "search"
OPENALEX_PER_PAGE_PARAM = "per-page"
OPENALEX_PER_PAGE_VALUE = "25"
OPENALEX_FILTER_PARAM = "filter"
OPENALEX_FROM_PUBLICATION_DATE_KEY = "from_publication_date"
OPENALEX_TO_PUBLICATION_DATE_KEY = "to_publication_date"
OPENALEX_RESULTS_KEY = "results"

CROSSREF_QUERY_PARAM = "query"
CROSSREF_ROWS_PARAM = "rows"
CROSSREF_ROWS_VALUE = "20"
CROSSREF_FILTER_PARAM = "filter"
CROSSREF_FROM_PUB_DATE_KEY = "from-pub-date"
CROSSREF_UNTIL_PUB_DATE_KEY = "until-pub-date"
CROSSREF_MESSAGE_KEY = "message"
CROSSREF_ITEMS_KEY = "items"

ARXIV_SEARCH_QUERY_PARAM = "search_query"
ARXIV_START_PARAM = "start"
ARXIV_START_VALUE = "0"
ARXIV_MAX_RESULTS_PARAM = "max_results"
ARXIV_MAX_RESULTS_VALUE = "10"
# Measured live 2026-09-01: a range query needs both ends, so a missing edge
# is filled with a spelled sentinel rather than left unsent. Year 2100 and
# year 1900 both answered 200; year 1 (`000101010000`) answered 500, so 1900
# — decades before arXiv existed — is the measured floor, not the calendar's.
ARXIV_FAR_PAST = "190001010000"
ARXIV_FAR_FUTURE = "210001010000"
ARXIV_STAMP_FORMAT = "%Y%m%d%H%M"

SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"


def _parsed_instant(instant: str) -> Optional[datetime]:
    """One manifest instant parsed, or nothing a bound this module can send.

    A bound this cannot read is a bound not sent — the core's own window
    filter still holds on every row that comes back — rather than a bound
    sent wrong.
    """

    if not instant:
        return None
    try:
        return datetime.strptime(instant, RECORD_INSTANT_FORMAT)
    except ValueError:
        return None


def instant_to_date(instant: str) -> str:
    """One manifest instant as the day OpenAlex's and Crossref's filters take."""

    moment = _parsed_instant(instant)
    return moment.strftime("%Y-%m-%d") if moment else ""


def instant_to_arxiv_stamp(instant: str) -> str:
    """One manifest instant as the ``YYYYMMDDHHMM`` arXiv's range takes."""

    moment = _parsed_instant(instant)
    return moment.strftime(ARXIV_STAMP_FORMAT) if moment else ""


def openalex_filter(window_start: str, window_end: str) -> str:
    """OpenAlex's own ``filter=`` clause for this window, or nothing.

    Only the edges present are sent — an origin that takes independent
    bounds is narrowed by whichever ones the caller named, never invented on
    the caller's behalf.
    """

    clauses = []
    start = instant_to_date(window_start)
    if start:
        clauses.append(OPENALEX_FROM_PUBLICATION_DATE_KEY + ":" + start)
    end = instant_to_date(window_end)
    if end:
        clauses.append(OPENALEX_TO_PUBLICATION_DATE_KEY + ":" + end)
    return ",".join(clauses)


def crossref_filter(window_start: str, window_end: str) -> str:
    """Crossref's own ``filter=`` clause for this window, or nothing."""

    clauses = []
    start = instant_to_date(window_start)
    if start:
        clauses.append(CROSSREF_FROM_PUB_DATE_KEY + ":" + start)
    end = instant_to_date(window_end)
    if end:
        clauses.append(CROSSREF_UNTIL_PUB_DATE_KEY + ":" + end)
    return ",".join(clauses)


def arxiv_window_clause(window_start: str, window_end: str) -> str:
    """arXiv's own ``AND submittedDate:[... TO ...]`` clause, or nothing.

    arXiv's range grammar takes two ends; a caller naming only one still
    gets a genuinely narrowed read rather than an unsent bound, because the
    missing edge is filled with the measured sentinel rather than left out
    of a grammar that has no open-ended form.
    """

    start = instant_to_arxiv_stamp(window_start)
    end = instant_to_arxiv_stamp(window_end)
    if not start and not end:
        return ""
    return " AND submittedDate:[{0} TO {1}]".format(
        start or ARXIV_FAR_PAST, end or ARXIV_FAR_FUTURE
    )


def openalex_params(argument: str, window_start: str, window_end: str) -> Dict[str, str]:
    params = {
        OPENALEX_SEARCH_PARAM: argument,
        OPENALEX_PER_PAGE_PARAM: OPENALEX_PER_PAGE_VALUE,
    }
    clause = openalex_filter(window_start, window_end)
    if clause:
        params[OPENALEX_FILTER_PARAM] = clause
    return params


def crossref_params(argument: str, window_start: str, window_end: str) -> Dict[str, str]:
    params = {
        CROSSREF_QUERY_PARAM: argument,
        CROSSREF_ROWS_PARAM: CROSSREF_ROWS_VALUE,
    }
    clause = crossref_filter(window_start, window_end)
    if clause:
        params[CROSSREF_FILTER_PARAM] = clause
    return params


def arxiv_params(argument: str, window_start: str, window_end: str) -> Dict[str, str]:
    search_query = 'all:"{0}"{1}'.format(argument, arxiv_window_clause(window_start, window_end))
    return {
        ARXIV_SEARCH_QUERY_PARAM: search_query,
        ARXIV_START_PARAM: ARXIV_START_VALUE,
        ARXIV_MAX_RESULTS_PARAM: ARXIV_MAX_RESULTS_VALUE,
    }


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation with a prefix; absent one — or on an
    unrecognized prefix — a bare query defaults to OpenAlex, unchanged: a
    query that happens to contain a colon stays a query, the same rule
    `prediction_markets.operation_for` states for its own three origins.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in SCHOLARLY_OPERATIONS:
        return (kind, argument)
    return (OPENALEX_OPERATION, named)


# --- Response reading ---------------------------------------------------


def _answered(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    records: Tuple[NativeRecord, ...] = (),
    outcome: str = "ok",
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        descriptor,
        records,
        observed_at=response.observed_at,
        native_order=native_order,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _failed(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    loss: str,
    warning: str,
) -> NativePage:
    return _answered(
        descriptor, response, native_order, outcome="failed", warnings=(warning,), loss=(loss,)
    )


def _json_payload_of(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    operation: str,
) -> Tuple[Any, Optional[NativePage]]:
    """One JSON origin's answer, or the typed page that says why there is none."""

    if response.status != 200:
        return (
            None,
            _failed(
                descriptor,
                response,
                native_order,
                HTTP_STATUS,
                "http status {0} from {1}".format(response.status, descriptor.route_id),
            ),
        )
    try:
        return (json.loads(response.body), None)
    except ValueError:
        return (
            None,
            _failed(
                descriptor,
                response,
                native_order,
                MALFORMED_JSON,
                "{0} answered 200 with no json body".format(operation),
            ),
        )


def _resolved(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    records: List[NativeRecord],
    row_count: int,
    unidentified: int,
    unidentified_message: str,
    drift_message: str,
    empty_message: str,
) -> NativePage:
    """The shared tail every origin's page assembly ends on, once rows are read.

    Three origins, one shape past this point: rows that named an id become
    records and a page reporting them, in the origin's own count, unless not
    one of them named an id — the payload reshaping, not a search with
    nothing in it — and no rows at all is a query or scope that matched
    nothing. Each origin supplies its own wording because the noun
    (work/item/entry) and the identifying field (id/DOI/id) are its own.
    """

    if records:
        warnings = (unidentified_message,) if unidentified else ()
        return _answered(descriptor, response, native_order, records=tuple(records), warnings=warnings)
    if row_count:
        return _failed(descriptor, response, native_order, SCHEMA_DRIFT, drift_message)
    return _answered(descriptor, response, native_order, outcome="empty", warnings=(empty_message,))


def _openalex_page(response: transport.TransportResponse, argument: str) -> NativePage:
    native_order = NATIVE_ORDERS[OPENALEX_OPERATION]
    payload, refused = _json_payload_of(DESCRIPTOR, response, native_order, OPENALEX_OPERATION)
    if refused is not None:
        return refused
    rows = payload.get(OPENALEX_RESULTS_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(rows, list):
        return _failed(
            DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1} list: the payload this adapter reads has"
            " changed shape".format(OPENALEX_OPERATION, OPENALEX_RESULTS_KEY),
        )
    records, unidentified = openalex_records(rows, DESCRIPTOR.standing_loss)
    return _resolved(
        DESCRIPTOR,
        response,
        native_order,
        records,
        len(rows),
        unidentified,
        "{0} answered 200 with {1} work(s) naming no id: they are not rows this"
        " adapter can identify".format(OPENALEX_OPERATION, unidentified),
        "{0} answered 200 with {1} work(s) and no id on any of them: the payload"
        " has changed shape".format(OPENALEX_OPERATION, len(rows)),
        "{0} answered 200 with an empty {1} list: nothing matched {2!r}".format(
            OPENALEX_OPERATION, OPENALEX_RESULTS_KEY, argument
        ),
    )


def _crossref_rows(payload: Any) -> Optional[List[Any]]:
    message = payload.get(CROSSREF_MESSAGE_KEY) if isinstance(payload, Mapping) else None
    items = message.get(CROSSREF_ITEMS_KEY) if isinstance(message, Mapping) else None
    return items if isinstance(items, list) else None


def _crossref_page(response: transport.TransportResponse, argument: str) -> NativePage:
    native_order = NATIVE_ORDERS[CROSSREF_OPERATION]
    payload, refused = _json_payload_of(
        CROSSREF_DESCRIPTOR, response, native_order, CROSSREF_OPERATION
    )
    if refused is not None:
        return refused
    rows = _crossref_rows(payload)
    if rows is None:
        return _failed(
            CROSSREF_DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1}.{2} list: the payload this adapter reads"
            " has changed shape".format(CROSSREF_OPERATION, CROSSREF_MESSAGE_KEY, CROSSREF_ITEMS_KEY),
        )
    records, unidentified = crossref_records(rows)
    return _resolved(
        CROSSREF_DESCRIPTOR,
        response,
        native_order,
        records,
        len(rows),
        unidentified,
        "{0} answered 200 with {1} item(s) naming no DOI: they are not rows this"
        " adapter can identify".format(CROSSREF_OPERATION, unidentified),
        "{0} answered 200 with {1} item(s) and no DOI on any of them: the payload"
        " has changed shape".format(CROSSREF_OPERATION, len(rows)),
        "{0} answered 200 with an empty {1} list: nothing matched {2!r}".format(
            CROSSREF_OPERATION, CROSSREF_ITEMS_KEY, argument
        ),
    )


def _arxiv_page(response: transport.TransportResponse, argument: str) -> NativePage:
    native_order = NATIVE_ORDERS[ARXIV_OPERATION]
    if response.status != 200:
        return _failed(
            ARXIV_DESCRIPTOR,
            response,
            native_order,
            HTTP_STATUS,
            "http status {0} from {1}".format(response.status, ARXIV_DESCRIPTOR.route_id),
        )

    parser = ArxivFeedParser()
    parser.feed(response.body)
    parser.close()

    if not parser.root:
        return _failed(
            ARXIV_DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "route {0} answered 200 with a document not rooted in <feed>: it is not"
            " an Atom feed this adapter can read".format(ARXIV_DESCRIPTOR.route_id),
        )

    records, unidentified = arxiv_records(parser.entries)
    return _resolved(
        ARXIV_DESCRIPTOR,
        response,
        native_order,
        records,
        len(parser.entries),
        unidentified,
        "{0} answered 200 with {1} entry(ies) naming no id: they are not rows"
        " this adapter can identify".format(ARXIV_OPERATION, unidentified),
        "{0} answered 200 with {1} entry(ies) and no id on any of them: the"
        " payload has changed shape".format(ARXIV_OPERATION, len(parser.entries)),
        "{0} answered 200 with a <feed> holding no <entry>: nothing matched"
        " {1!r}".format(ARXIV_OPERATION, argument),
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one of the three declared operations and return exactly one NativePage.

    One call on one route: which route is the operation's own, declared in
    ``OPERATION_SURFACES``, and the three are paced apart because they are
    three origins.
    """

    operation, argument = operation_for(request)
    descriptor = OPERATION_SURFACES[operation]

    if operation == OPENALEX_OPERATION:
        params = openalex_params(argument, request.window_start, request.window_end)

        def parse(response: transport.TransportResponse) -> NativePage:
            return _openalex_page(response, argument)

    elif operation == CROSSREF_OPERATION:
        params = crossref_params(argument, request.window_start, request.window_end)

        def parse(response: transport.TransportResponse) -> NativePage:
            return _crossref_page(response, argument)

    else:
        params = arxiv_params(argument, request.window_start, request.window_end)

        def parse(response: transport.TransportResponse) -> NativePage:
            return _arxiv_page(response, argument)

    return fetch_one_page(
        descriptor,
        carrier,
        params=params,
        parse=parse,
        native_order=NATIVE_ORDERS[operation],
    )
