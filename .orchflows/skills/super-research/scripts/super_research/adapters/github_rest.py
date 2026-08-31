"""K0 GitHub reads, anonymous, under the tightest hourly ceiling in the roster.

Measured 2026-08-10 (Carry-over routes): `api.github.com`
answered anonymously, `api.github.com/search/repositories` answered 200 with no
credential, and `api.github.com/rate_limit` reported the anonymous ceiling as
**60/hr for core and 60/hr for code_search** — two buckets, measured apart. Two
buckets are two routes here, each with its own declared budget, so a search
never spends a repository read's hour.

**This is the one origin in the roster with a large, well-known write
surface, and none of it is reachable.** Not because no test tries it, but
because the set of operations this module can perform is enumerated: four,
listed in ``OPERATION_SURFACES``, each a GET on one of the two declared read
routes. There is no other path from :func:`fetch_native_page` to the carrier,
this module names no HTTP verb at all — the verb is the route's — and
``transport.admitted_methods`` returns reads and nothing else for both routes,
so a hand-built POST is refused in the opener before a socket exists. T07
widened that gate by one closed set for a route with no GET form; neither of
these is in it.

**A 403 here is never ``auth_required``.** GitHub answers an anonymous client
that has spent its hour with 403 and a message about rate limits, and waiting
fixes that where a credential need not. Reporting it as a missing credential
would record the roster's tightest budget as a capability this package does not
have, which is the false claim the measured access ladder exists to prevent. So
every refusal here is the status it is, and the warning names what GitHub
documents the status as.

Pagination is the caller's: GitHub states how many repositories matched and
never how many pages it split them into, so no next page is derived from a
total and a row count. A caller that wants page two says so.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from .. import transport
from ._support.github_rest_records import (
    ID_KEY,
    id_text,
    issue_record,
    release_record,
    repository_record,
)
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

# The `core` bucket: a repository and the two collections under it. This is the
# adapter's primary descriptor because a request naming a target reads a
# repository, which is what an unprefixed `owner/repo` means.
DESCRIPTOR = AdapterDescriptor(
    adapter_id="github_rest",
    adapter_version="1",
    access_class="K0",
    route_id=transport.GITHUB_REST_ROUTE,
    platform="github",
    native_identity_namespace="github",
    representation_kind="native",
    operator_identity="github",
    # The 2026-08-10 probes: `rate_limit` reported 60/hr anonymous. GitHub spends an
    # hour as one bucket, so sixty reads may leave at once and one refills per
    # minute; a refusal costs the window the bucket resets in. T04 seeded these
    # three numbers as a replay constant before this route existed.
    min_interval_ms=60000,
    burst=60,
    cooldown_ms=3600000,
    # An issue reports an exact count of its own comments. Nothing on these
    # routes reports a count of replies, and neither name is inferred.
    comment_count_metric="comments",
)

# The `code_search` bucket: the same origin, a different hour.
SEARCH_DESCRIPTOR = AdapterDescriptor(
    adapter_id="github_rest",
    adapter_version="1",
    access_class="K0",
    route_id=transport.GITHUB_SEARCH_ROUTE,
    platform="github",
    native_identity_namespace="github",
    representation_kind="native",
    operator_identity="github",
    min_interval_ms=60000,
    burst=60,
    cooldown_ms=3600000,
    comment_count_metric="comments",
)

SURFACE_DESCRIPTORS = (DESCRIPTOR, SEARCH_DESCRIPTOR)

# The four operations the roster row names, spelled once each.
REPO_OPERATION = "repo"
ISSUES_OPERATION = "issues"
RELEASES_OPERATION = "releases"
SEARCH_OPERATION = "search"
GITHUB_OPERATIONS = (
    REPO_OPERATION,
    ISSUES_OPERATION,
    RELEASES_OPERATION,
    SEARCH_OPERATION,
)

# Every read this module can perform: which route it goes to, and which
# collection it names on that route. This table is the reachable operation set
# — nothing else in this file reaches the carrier, and no value here is
# composed from a caller's argument. A write on GitHub's API is a verb on paths
# like these, and the verb belongs to the route, which declares a read.
OPERATION_SURFACES = {
    REPO_OPERATION: (DESCRIPTOR, ""),
    ISSUES_OPERATION: (DESCRIPTOR, "issues"),
    RELEASES_OPERATION: (DESCRIPTOR, "releases"),
    SEARCH_OPERATION: (SEARCH_DESCRIPTOR, "repositories"),
}

NATIVE_ORDERS = {
    REPO_OPERATION: "github_repository_order",
    ISSUES_OPERATION: "github_issue_list_order",
    RELEASES_OPERATION: "github_release_list_order",
    SEARCH_OPERATION: "github_search_relevance_order",
}

# Where a search answer keeps its rows. Declared, never searched for: a payload
# that no longer carries this is a shape change and not a search that matched
# nothing.
ITEMS_KEY = "items"

# The manifest's own instant spelling, parsed here rather than imported from
# `ordering`: each origin-adjacent adapter module owns its own tiny parser of
# the same name, rather than reaching into a shared one.
RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
# GitHub's search qualifiers read a day, never a finer instant — measured live
# 2026-08-31: `created:>=2026-08-24` and `created:2026-08-01..2026-08-15` both
# answered with every `created_at` inside the named day boundary.
GITHUB_SEARCH_DATE_FORMAT = "%Y-%m-%d"

# Every key these payloads publish that this module reads, under GitHub's own
# names.
SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"
FIELD_OMITTED = "field_omitted"

# Declared here and produced nowhere in this module, which is the statement:
# no answer either of these routes can give is a report that a credential was
# needed. Both are documented keyless, and the one refusal GitHub documents for
# an anonymous client is a spent hour. A count of zero reads of this name is
# how that stays checkable from outside.
AUTH_REQUIRED = "auth_required"

# The status GitHub documents for a spent anonymous hour, and the ceiling that
# spends it. Named together because the warning has to say both.
BUDGET_REFUSAL_STATUS = 403
ANONYMOUS_HOURLY_CEILING = 60


RECORD_BUILDERS = {
    REPO_OPERATION: repository_record,
    ISSUES_OPERATION: issue_record,
    RELEASES_OPERATION: release_record,
    SEARCH_OPERATION: repository_record,
}


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


def _refusal_warning(response: transport.TransportResponse, operation: str, route_id: str) -> str:
    """What the origin's own status says, and what GitHub documents it as."""

    said = "http status {0} from {1} on {2}".format(response.status, route_id, operation)
    if response.status != BUDGET_REFUSAL_STATUS:
        return said
    return (
        "{0}: GitHub answers an anonymous client with this status both when the"
        " {1}/hr ceiling for this bucket is spent — which waiting clears — and"
        " when the resource is not public. Neither is a credential this package"
        " is missing, so it is recorded as the status it is.".format(
            said, ANONYMOUS_HOURLY_CEILING
        )
    )


def _rows_of(payload: Any, operation: str) -> Optional[Sequence[Any]]:
    """The rows this answer carries, or None when its container is not there.

    Three shapes, one per surface: a repository answers with itself, a
    collection answers with a bare list, and a search answers with its rows
    under the key it declares. Each is read where the endpoint puts it rather
    than found by looking for something list-shaped.
    """

    if operation == REPO_OPERATION:
        return (payload,) if isinstance(payload, Mapping) else None
    if operation == SEARCH_OPERATION:
        items = payload.get(ITEMS_KEY) if isinstance(payload, Mapping) else None
        return items if isinstance(items, list) else None
    return payload if isinstance(payload, list) else None


def _page_from(
    response: transport.TransportResponse, operation: str, argument: str
) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    descriptor, _ = OPERATION_SURFACES[operation]
    native_order = NATIVE_ORDERS[operation]
    if response.status != 200:
        return _failed(
            descriptor,
            response,
            native_order,
            HTTP_STATUS,
            _refusal_warning(response, operation, descriptor.route_id),
        )
    try:
        payload = json.loads(response.body)
    except ValueError:
        return _failed(
            descriptor,
            response,
            native_order,
            MALFORMED_JSON,
            "{0} answered 200 with no json body".format(operation),
        )

    rows = _rows_of(payload, operation)
    if rows is None:
        return _failed(
            descriptor,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with a body this adapter cannot read as {1}: the"
            " payload has changed shape".format(operation, operation),
        )

    build = RECORD_BUILDERS[operation]
    records = []
    for row in rows:
        # A row with no id is not a row: it can be neither identified nor
        # grouped, and a record naming nothing is worse than one fewer record.
        if isinstance(row, Mapping) and id_text(row.get(ID_KEY)):
            records.append(build(len(records), row, FIELD_OMITTED))
    if records:
        return _answered(descriptor, response, native_order, records=tuple(records))
    if rows:
        # The container is present and holds rows, and not one of them names an
        # id. That is the payload reshaping, not an answer with nothing in it:
        # a search stating `total_count: 2` over two rows this adapter cannot
        # identify would otherwise be reported as "this query has none", which
        # is the one thing a caller cannot tell from a real absence.
        return _failed(
            descriptor,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with {1} row(s) and no {2} on any of them: the"
            " payload has changed shape".format(operation, len(rows), ID_KEY),
        )
    return _answered(
        descriptor,
        response,
        native_order,
        outcome="empty",
        warnings=(
            "{0} answered 200 with nothing under {1}: this repository or query"
            " has none".format(operation, argument or operation),
        ),
    )


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation, because one adapter serves four. Absent a
    name, the step's own shape decides: a step naming a target reads that
    repository, and a step naming only a query searches. Neither is inferred
    from the characters in the argument, so a query containing a slash stays a
    query.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in GITHUB_OPERATIONS:
        return (kind, argument)
    return (REPO_OPERATION if request.target_ids else SEARCH_OPERATION, named)


def repository_params(target: str) -> Dict[str, str]:
    """One `owner/repo` target as the two segments the route declares.

    Split once, so a target naming more than a repository spends only the two
    segments this route has. A target naming no repository leaves the segment
    empty, the path stops there, and the origin answers for the path it was
    actually asked — which is a 404 this adapter reports as the status it is.
    """

    owner, _, repository = target.partition("/")
    return {"owner": owner, "repo": repository}


def _instant_seconds(stamped: str) -> Optional[int]:
    """One manifest instant as whole UTC seconds, or nothing unparseable."""

    if not stamped:
        return None
    try:
        moment = datetime.strptime(stamped, RECORD_INSTANT_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return int(moment.timestamp())


def _search_date(stamped: str) -> str:
    """One manifest instant as the day GitHub's search qualifiers read."""

    seconds = _instant_seconds(stamped)
    if seconds is None:
        return ""
    return datetime.fromtimestamp(seconds, tz=timezone.utc).strftime(GITHUB_SEARCH_DATE_FORMAT)


def origin_created_qualifier(window_start: str, window_end: str) -> str:
    """The `created:` qualifier `search`'s `q` should carry, or nothing.

    Measured live 2026-08-31: `created:>=2026-08-24` moved `total_count` from
    1,244,282 to 6,725 and every returned `created_at` after the named day;
    `created:2026-08-01..2026-08-15` (both edges) put every returned
    `created_at` inside that exact span. The one-sided `<=` form is the same
    qualifier grammar mirrored, not independently re-measured. A pure
    function of the step's two instants, day-precision because that is what
    was measured, returning nothing when neither edge is usable.
    """

    start = _search_date(window_start)
    end = _search_date(window_end)
    if start and end:
        return "created:" + start + ".." + end
    if start:
        return "created:>=" + start
    if end:
        return "created:<=" + end
    return ""


def origin_since_param(window_start: str) -> str:
    """The `since` value `issues` should carry, or nothing.

    Measured live 2026-08-31: `since=<a few minutes in the future>` on an
    active repository's issue list answered zero rows where the same call
    without it answered a full page, so `since` genuinely filters by
    `updated_at` rather than being silently ignored (as `releases`' own
    `since` is — measured the same way, unchanged). No `until`/`before`
    exists on this route (undocumented, unmeasured): the far edge stays the
    core's own post-filter, exactly as an adapter with no window reach at all
    already leaves it.
    """

    return window_start


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one of the four declared operations and return exactly one NativePage.

    One call on one route. Which route is the operation's own, declared in
    ``OPERATION_SURFACES``, and the two are paced apart because GitHub counts
    them apart.
    """

    operation, argument = operation_for(request)
    descriptor, collection = OPERATION_SURFACES[operation]
    if operation == SEARCH_OPERATION:
        qualifier = origin_created_qualifier(request.window_start, request.window_end)
        params = {"index": collection, "q": (argument + " " + qualifier) if qualifier else argument}
    else:
        params = repository_params(argument)
        params["resource"] = collection
        if operation == ISSUES_OPERATION and request.window_start:
            params["since"] = origin_since_param(request.window_start)
    if request.cursor:
        # The page the core froze. No next one is derived here: GitHub states a
        # total and not a page count, and inventing one from the rows returned
        # would make this adapter the thing that decides there is more.
        params["page"] = request.cursor

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, operation, argument)

    return fetch_one_page(
        descriptor,
        carrier,
        params=params,
        parse=parse,
        native_order=NATIVE_ORDERS[operation],
    )
