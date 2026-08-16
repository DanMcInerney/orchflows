"""Transport seam: the outbound request, and the one address for the routes.

The two tables of per-platform data this module used to hold — the route
constants and the vendor-published public client credentials — were moved to
one read-size sibling, :mod:`.routes`, and are re-exported below under the
names they have always had. Each name still has exactly one definition; this
module stays the one address the suite, the adapters and the CLI reach it at.
What is left here is mechanism: the opener, the method admission, the byte cap,
the refusal parsing and the captive-portal detector.

Nothing outside this module and :mod:`.routes` may name a host, a path, or a
vendor-published public client credential. Callers that need to know whether a
route is reachable ask :func:`route_admissions`, which answers in booleans only.

This module also owns the captive-portal detector. Every response it returns
names the party that answered it — the origin, or a local network appliance —
so a caller can never record this network's block as a platform gap.

Reliability bar: read-only. The default opener refuses any URL that is not
``https://`` and any method outside :func:`admitted_methods` — reads
everywhere, plus two closed exceptions named by route id: minting an anonymous
guest token, and asking a question InnerTube only takes in a JSON body. Both
are POSTs that create nothing at the origin. PUT, PATCH and DELETE are admitted
nowhere, no code path here can mutate a remote resource, and the offline
``fake`` route can never leave the process.
"""

from __future__ import annotations

import email.utils
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .routes import (
    ARCTIC_SHIFT_POSTS_ROUTE,
    CREDENTIAL_PLACEMENTS,
    DDG_HTML_ROUTE,
    FAKE_OFFLINE_ROUTE,
    GITHUB_REST_ROUTE,
    GITHUB_SEARCH_ROUTE,
    HEADER_PLACEMENT,
    HN_ALGOLIA_SEARCH_ROUTE,
    HN_FIREBASE_ITEM_ROUTE,
    INSTAGRAM_WEB_APP_ID,
    INSTAGRAM_WEB_PROFILE_ROUTE,
    JSON_CONTENT_TYPE,
    LINKEDIN_JOBS_GUEST_SEARCH_ROUTE,
    LINKEDIN_PUBLIC_PROFILE_ROUTE,
    PUBLIC_CLIENT_CREDENTIALS,
    PUBLIC_PAGE_ARTICLE_ROUTE,
    PUBLIC_PAGE_CONTROL_ROUTE,
    QUERY_PLACEMENT,
    REDDIT_FEED_ROUTE,
    REDDIT_SITE_ORIGIN,
    ROUTE_CONSTANTS,
    PublicClientCredential,
    RouteConstant,
    X_GUEST_ACTIVATE_ROUTE,
    X_GUEST_GRAPHQL_ROUTE,
    X_GUEST_PUBLIC_BEARER,
    X_SYNDICATION_TIMELINE_ROUTE,
    YOUTUBE_CHANNEL_FEED_ROUTE,
    YOUTUBE_INNERTUBE_ROUTE,
    YOUTUBE_INNERTUBE_WEB_KEY,
)

# One static identity. Never rotated: a rate limit is an observed constraint
# this package respects, not one it evades.
USER_AGENT = "super-research/0.1 (keyless read-only acquisition)"
REQUEST_TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
READ_METHODS = ("GET", "HEAD")

# The status an origin answers with when it wants fewer requests, and the typed
# loss a caller records for it. Named here once each, because the scheduler that
# waits it out and the record that reports it must be talking about the same
# thing. A refusal is an outcome, never a reason to become a different client.
RATE_LIMITED_STATUS = 429
RATE_LIMITED = "rate_limited"

# Where an origin states how long it wants to be left alone, named here for the
# same reason the status is. Both are matched without regard to case: HTTP
# header names are case-insensitive and origins do not agree on the spelling,
# so a lookup that matched one casing would read a stated interval as an absent
# one — which is how a limit gets evaded by accident rather than by intent.
RETRY_AFTER_HEADER = "Retry-After"
RATE_LIMIT_RESET_HEADER = "X-RateLimit-Reset"

# The other status an origin uses to ask for fewer requests, and how it says
# so. A 403 is normally about who is asking rather than how often — an authwall
# and a private repository are both 403 — so the status alone decides nothing:
# it is a rate refusal only when the answer says the refusal is about rate.
# GitHub's secondary limit is the roster's measured case, and it says it in the
# body rather than in a status of its own.
SECONDARY_RATE_LIMITED_STATUS = 403
SECONDARY_RATE_LIMIT_MARKERS = ("secondary rate limit",)

# The moment format `observed_at` is written and read in. One name, because an
# absolute interval an origin states is measured against that field.
OBSERVED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# What an origin sent back, in the order it sent it. Named once because three
# places pass it around: the opener reports it, the response holds it, and
# :func:`header_value` answers questions about it.
AnsweredHeaders = Tuple[Tuple[str, str], ...]

# The first closed exception to reads-only, named by route id: minting an
# anonymous guest token needs a POST, and that POST creates no account,
# session, or content at the origin.
TOKEN_ACTIVATION_ROUTES = (X_GUEST_ACTIVATE_ROUTE,)
TOKEN_ACTIVATION_METHODS = ("POST",)

# The second, and the last. InnerTube takes its query as a JSON body and has
# no GET form, so this is a read spelled in an awkward verb rather than a write
# — it asks a question and creates nothing. What keeps that true is not the
# verb but the body: it is rendered from the route's own `body_params` and from
# nothing else, so a caller supplies values into a shape this module declares
# and can never choose the shape. A route absent from both sets above reaches
# no method outside `READ_METHODS` by any path, and no route anywhere reaches
# PUT, PATCH or DELETE.
QUERY_BODY_ROUTES = (YOUTUBE_INNERTUBE_ROUTE,)
QUERY_BODY_METHODS = ("POST",)

# What an activation route issues, and where the route that needs it carries
# it. A guest token is not a vendor-published constant: the origin mints a new
# one on request, it names no user, and it lives in memory for as long as the
# process reading with it does.
GUEST_TOKEN_FIELD = "guest_token"
GUEST_TOKEN_HEADER = "x-guest-token"

# Which party answered a request. `network_intercepted` is also the typed
# loss code a caller attaches, so an intercepted route is reported as
# unverified rather than as a platform gap.
ORIGIN_CONTENT = "origin_content"
ORIGIN_FAILURE = "origin_failure"
NETWORK_INTERCEPTED = "network_intercepted"
CHANNEL_VERDICTS = (ORIGIN_CONTENT, ORIGIN_FAILURE, NETWORK_INTERCEPTED)

# The one measured captive-portal signature (findings.md §0, 2026-08-10):
# this host's appliance answered tiktok.com and ecosia.org with HTTP 503 and
# a body carrying this marker, while example.com and wikipedia.org returned
# genuine 200 origin content. Widening this set requires a new measurement:
# a marker an origin also emits would record platform behavior as a local
# block, which is the mirror of the error §0 forbids.
CAPTIVE_PORTAL_MARKERS = ('<base href="/login/">',)


class TransportError(RuntimeError):
    """An outbound request was refused or could not be completed."""


# The typed loss a read that raised :class:`TransportError` leaves on its page.
# It is declared beside the exception and loaded nowhere here, because the two
# modules that spell it are the two that meet the failure rather than raise it:
# `runner` attaches it to the step it ends, `smoke` reads it to decide which
# party answered.
UNREACHABLE = "unreachable"


@dataclass(frozen=True)
class TransportRequest:
    """One read, spelled completely, before any credential is attached.

    ``body`` is the JSON a query-body route asks its question in, rendered from
    that route's declared ``body_params``. Every other route carries none, and
    no caller can put anything in one: the shape is the route's and only the
    values are the caller's.
    """

    route_id: str
    method: str
    url: str
    headers: Tuple[Tuple[str, str], ...] = ()
    body: str = ""


@dataclass(frozen=True)
class TransportResponse:
    """One answer, and everything a caller needs to know about how it got here.

    ``cache_hit`` says a run's own memory answered rather than the origin.
    Nothing in this module ever sets it: only a caller holding a cache knows,
    and it says so by copying the response with the flag raised — which is why
    ``observed_at`` stays the moment the origin was really read.

    ``final_url`` is the address the origin actually answered from, which is
    one hop's worth of truth and **not** a redirect chain: it says "I asked
    ``url`` and read the document at ``final_url``", and a caller that needs
    every intermediate hop needs a redirect handler nobody has asked for. An
    opener that reports no address answered from the one it was asked, which is
    what every offline stand-in in the suite does and what a read that never
    left the process means.

    ``headers`` is what the origin sent back, in the order it sent it. It is
    the only place an origin can say how long it wants to be left alone, so a
    scheduler that never saw it could wait no interval but the one this package
    guessed. An opener that reports none sent none. Names are asked for through
    :func:`header_value` and never indexed, because origins do not agree on
    casing.
    """

    route_id: str
    url: str
    status: int
    body: str
    content_type: str
    observed_at: str
    channel_verdict: str
    cache_hit: bool = False
    final_url: str = ""
    headers: AnsweredHeaders = ()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime(OBSERVED_AT_FORMAT)


def channel_verdict(status: int, body: str) -> str:
    """Name the party that answered: the origin, or a local network appliance.

    An interception needs both halves of the measured signature — a failure
    status and a portal marker. A success is never one: this host's control
    probes show a 2xx is genuine origin content, and an origin's own login
    page must stay platform behavior. A failure without the marker is the
    origin's own, so a real platform gap is still recordable as one.
    """

    if 200 <= status < 300:
        return ORIGIN_CONTENT
    lowered = body.lower()
    for marker in CAPTIVE_PORTAL_MARKERS:
        if marker in lowered:
            return NETWORK_INTERCEPTED
    return ORIGIN_FAILURE


def rate_refused(status: int, body: str) -> bool:
    """Whether this answer is the origin asking for fewer requests.

    A 429 always is. A 403 is one only when the answer says the refusal is
    about rate: read the way the portal marker is read — the origin's own
    words, case folded — and only on the refusing status, so a page that
    quotes the sentence is still content rather than a limit.
    """

    if status == RATE_LIMITED_STATUS:
        return True
    if status != SECONDARY_RATE_LIMITED_STATUS:
        return False
    lowered = body.lower()
    for marker in SECONDARY_RATE_LIMIT_MARKERS:
        if marker in lowered:
            return True
    return False


def header_value(headers: AnsweredHeaders, name: str) -> str:
    """One header off an answer, matched without regard to case.

    The first match wins and a header nobody sent reads as an empty string, so
    a caller asks a question rather than indexing a mapping whose keys it would
    have to spell exactly the way this origin happened to.
    """

    wanted = name.lower()
    for held, value in headers:
        if held.lower() == wanted:
            return value
    return ""


def observed_moment(observed_at: str) -> Optional[datetime]:
    """The moment an answer says it was read, or None when it says nothing usable."""

    try:
        return datetime.strptime(observed_at, OBSERVED_AT_FORMAT).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def http_date_moment(stated: str) -> Optional[datetime]:
    """One RFC 7231 HTTP-date, or None for anything this module cannot read.

    A date without a zone is read as UTC, which is the only zone RFC 7231
    admits and the only one an origin obeying it can mean.
    """

    try:
        moment = email.utils.parsedate_to_datetime(stated)
    except (TypeError, ValueError, OverflowError):
        return None
    if moment is None:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def epoch_moment(stated: str) -> Optional[datetime]:
    """One UTC epoch second — how `X-RateLimit-Reset` states a window's end."""

    held = stated.strip()
    if not held:
        return None
    try:
        return datetime.fromtimestamp(int(held), timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def remaining_seconds(deadline: Optional[datetime], read_at: Optional[datetime]) -> float:
    """Seconds from when an answer was read until an absolute moment it named.

    Zero when either moment is unreadable, and zero when the deadline has
    already passed: an interval that ran out states no remaining wait, and a
    negative one would shorten a local budget rather than lengthen it.
    """

    if deadline is None or read_at is None:
        return 0.0
    return max(0.0, (deadline - read_at).total_seconds())


def retry_after_seconds(stated: str, read_at: Optional[datetime]) -> float:
    """`Retry-After` in either spelling RFC 7231 gives it, as seconds remaining."""

    held = stated.strip()
    if not held:
        return 0.0
    # The two spellings are marked by nothing: whole seconds is `1*DIGIT`, and
    # anything else the origin meant as an absolute date.
    if held.isascii() and held.isdigit():
        return float(held)
    return remaining_seconds(http_date_moment(held), read_at)


def stated_cooldown_seconds(response: TransportResponse) -> float:
    """How long this origin itself asked to be left alone, in seconds.

    Zero when it asked for nothing and never negative. Nothing here raises: a
    header this module cannot read is a header the origin did not state, and
    the local budget still governs — which is the only safe direction, because
    a wait this function shortened would be a limit evaded rather than read.

    Two headers can state an interval and an origin may send both. It gets the
    longest of what it said: deciding between them by precedence would let this
    package read the shorter of two stated waits, which is evasion wearing the
    shape of obedience.

    An absolute moment is measured against ``observed_at``, the moment this
    very answer was read, and never against a clock read now: the two are
    different moments, and the difference would come off the wait.
    """

    read_at = observed_moment(response.observed_at)
    return max(
        retry_after_seconds(header_value(response.headers, RETRY_AFTER_HEADER), read_at),
        remaining_seconds(
            epoch_moment(header_value(response.headers, RATE_LIMIT_RESET_HEADER)), read_at
        ),
    )


def route_constant(route_id: str) -> RouteConstant:
    route = ROUTE_CONSTANTS.get(route_id)
    if route is None:
        raise TransportError("unknown route " + route_id)
    return route


def route_admissions() -> Dict[str, bool]:
    """Per-route booleans — the only route knowledge the router ever sees.

    A route is admitted when it needs no user credential. ``K5`` is the one
    credentialed class, so it is the one class that can answer False here.
    """

    return {
        route_id: route.access_class != "K5"
        for route_id, route in sorted(ROUTE_CONSTANTS.items())
    }


def admitted_methods(route_id: str) -> Tuple[str, ...]:
    """Every method this route may use: reads, plus the two closed exceptions.

    A route named in neither exception set reads and nothing else, and no
    route in either one gains a verb that could change anything at an origin:
    both exceptions are the same POST, on a named route, for an operation that
    creates nothing.
    """

    if route_id in TOKEN_ACTIVATION_ROUTES:
        return READ_METHODS + TOKEN_ACTIVATION_METHODS
    if route_id in QUERY_BODY_ROUTES:
        return READ_METHODS + QUERY_BODY_METHODS
    return READ_METHODS


def origin_locator(route_id: str, published: str) -> str:
    """One address on a route's own origin, resolved where hosts are spelled.

    Both `K1` platforms in the roster publish an item's address relative to
    themselves — a ``/watch?v=`` path — or not at all, leaving a caller to
    address a post by the shortcode the payload carries. An adapter may name no
    route host, so either the resolution happens here or every record on those
    routes carries no address. An address that is already absolute is handed
    back untouched: resolving one somebody else resolved would be this module
    rewriting what an origin said.
    """

    if not published:
        return ""
    if urllib.parse.urlsplit(published).scheme:
        return published
    return urllib.parse.urljoin(route_constant(route_id).origin, published)


def route_credential(route_id: str) -> Optional[PublicClientCredential]:
    """The public client credential this route needs, or None for a keyless one."""

    credential_id = route_constant(route_id).credential_id
    if not credential_id:
        return None
    credential = PUBLIC_CLIENT_CREDENTIALS.get(credential_id)
    if credential is None:
        raise TransportError("unknown public client credential " + credential_id)
    return credential


def credentialed_url(url: str, credential: Optional[PublicClientCredential]) -> str:
    """Apply a query-placed credential. Called at send time, never before."""

    if credential is None or credential.placement != QUERY_PLACEMENT:
        return url
    separator = "&" if "?" in url else "?"
    return url + separator + urllib.parse.urlencode(((credential.name, credential.value),))


def credentialed_headers(
    headers: Tuple[Tuple[str, str], ...], credential: Optional[PublicClientCredential]
) -> Tuple[Tuple[str, str], ...]:
    """Apply a header-placed credential. Called at send time, never before."""

    if credential is None or credential.placement != HEADER_PLACEMENT:
        return tuple(headers)
    return tuple(headers) + ((credential.name, credential.value),)


def path_segments(route: RouteConstant, params: Dict[str, str]) -> str:
    """Spend this route's declared path params, in order, removing them from ``params``.

    Segments stop at the first one the caller left empty: a later segment
    appended past a missing earlier one would name a different endpoint, and
    guessing which is not this module's to do. A declared ``path_suffix``
    follows the last segment, and only a complete path takes one — for the
    same reason, and it is the same mistake one character further along.
    """

    values = [params.pop(name, "") for name in route.path_params]
    spent = ""
    for value in values:
        if not value:
            return spent
        spent = spent + "/" + urllib.parse.quote(value, safe="")
    return spent + route.path_suffix


def json_body(route: RouteConstant, params: Dict[str, str]) -> str:
    """Spend this route's declared body params into the JSON it asks in.

    The keys are the route's, taken from ``body_params`` and from nothing else,
    so a param the endpoint never declared cannot reach the body — it stays an
    ordinary query parameter, in the open, on a url the run records. A route
    that declares none carries no body whatever it is handed, which is what
    keeps this from being a generic HTTP primitive.

    Serialized with sorted keys and no spaces, so one request is one string and
    two identical reads are identical bytes.
    """

    if not route.body_params:
        return ""
    body: Dict[str, Any] = {}
    for name, key_path in route.body_params:
        value = params.pop(name, "")
        if not value:
            continue
        held = body
        for key in key_path[:-1]:
            held = held.setdefault(key, {})
        held[key_path[-1]] = value
    return json.dumps(body, separators=(",", ":"), sort_keys=True) if body else ""


def mint_guest_token(
    fetch: Callable[["TransportRequest"], "TransportResponse"], token_route_id: str
) -> str:
    """One activation request, returning the token it issued or nothing at all.

    The request goes out through the caller's own ``fetch`` rather than through
    an opener reached from here, which is what makes an activation a call the
    run can see: recorded in that carrier's log, answered by whatever opener it
    holds, and charged against this route's own budget by whoever paces it.
    Nothing in this module calls this function — a caller holding only a bare
    :class:`Transport` has chosen a carrier that does not mint, and its reads
    go out unauthorized.

    A mint that does not produce a token yields an empty string rather than an
    exception: the read that needed it then goes out unauthorized and the
    origin answers 401 or 403, which the adapter records as the platform's own
    refusal. Inventing a token, or turning a failed mint into a retry of the
    read, are the two wrong answers.
    """

    try:
        response = fetch(build_transport_request(token_route_id))
    except TransportError:
        return ""
    if response.status != 200:
        return ""
    try:
        payload = json.loads(response.body)
    except ValueError:
        return ""
    token = payload.get(GUEST_TOKEN_FIELD) if isinstance(payload, dict) else None
    return token if isinstance(token, str) else ""


class GuestTokenStore:
    """Anonymous guest tokens, held in memory for as long as the process reads.

    One token per activation route, minted once above this store and spent on
    every later read: a run that minted per read would spend two requests where
    the origin expects one, and one that persisted a token would carry state
    across runs. There is no file, no environment variable, and no artifact
    field here — a token exists only in this object.

    Lookup only. Nothing here reaches an origin, because a store that minted on
    lookup would mint wherever it was first read from — which is below the seam
    that records a request and below the one that paces it, and out of sight of
    both. The mint lives at the governor; this holds what it issued.
    """

    def __init__(self) -> None:
        self._tokens: Dict[str, str] = {}

    def token_for(self, token_route_id: str) -> str:
        """The token this process holds for a route, or nothing. Never a mint."""

        return self._tokens.get(token_route_id, "")

    def claim(self, token_route_id: str) -> bool:
        """Take this route's one activation, or report that it is already taken.

        Claimed before the activation goes out rather than after it comes back,
        which is what makes two rules one line. A refused mint is remembered as
        a refusal, so the read that needed a token goes out unauthorized once
        instead of paying for an activation the origin already declined; and an
        activation route that named a token route of its own finds this route
        claimed when it re-enters, so the mint cannot recurse without end.
        """

        if token_route_id in self._tokens:
            return False
        self._tokens[token_route_id] = ""
        return True

    def remember(self, token_route_id: str, token: str) -> None:
        """Hold what one activation issued, empty answer included."""

        self._tokens[token_route_id] = token

    def clear(self) -> None:
        self._tokens.clear()


GUEST_TOKENS = GuestTokenStore()


def tokened_headers(
    headers: Tuple[Tuple[str, str], ...], token_route_id: str
) -> Tuple[Tuple[str, str], ...]:
    """Attach this route's guest token, when the process is holding one.

    An attach, never a mint: a process holding none sends the read
    unauthorized, which is the outcome :func:`mint_guest_token` already names
    as the honest one.
    """

    if not token_route_id:
        return tuple(headers)
    token = GUEST_TOKENS.token_for(token_route_id)
    if not token:
        return tuple(headers)
    return tuple(headers) + ((GUEST_TOKEN_HEADER, token),)


def build_transport_request(
    route_id: str, params: Optional[Mapping[str, str]] = None
) -> TransportRequest:
    route = route_constant(route_id)
    supplied = dict(params or {})
    path = route.path + path_segments(route, supplied)
    body = json_body(route, supplied)
    pairs = [(key, value) for key, value in sorted(supplied.items()) if value != ""]
    url = route.origin + path
    if pairs:
        url = url + "?" + urllib.parse.urlencode(pairs)
    headers = (("User-Agent", USER_AGENT), ("Accept", route.accept))
    if body:
        headers = headers + (("Content-Type", JSON_CONTENT_TYPE),)
    return TransportRequest(
        route_id=route_id, method=route.method, url=url, headers=headers, body=body
    )


def without_query_credential(
    url: str, credential: Optional[PublicClientCredential]
) -> str:
    """Take a query-placed credential back off an address before it leaves here.

    :func:`credentialed_url` puts it on at send time, and an origin answers
    from the address it was asked at — so the address that comes back is the
    only string in this module that can carry a ``K1`` key past its own seam.
    That matters because it does not stop here: ``final_url`` is a field every
    caller sees and one adapter publishes onto a record.

    Only this route's own credential name is dropped, and only where it is
    actually present, so an address nobody credentialed is handed back
    untouched rather than re-encoded.
    """

    if credential is None or credential.placement != QUERY_PLACEMENT:
        return url
    split = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(split.query, keep_blank_values=True)
    if not any(name == credential.name for name, _ in pairs):
        return url
    kept = [(name, value) for name, value in pairs if name != credential.name]
    return urllib.parse.urlunsplit(
        (split.scheme, split.netloc, split.path, urllib.parse.urlencode(kept), split.fragment)
    )


def answering_address(response: Any, request: TransportRequest) -> str:
    """Where the read was actually answered from, or the address it was asked at.

    urllib has already followed whatever redirect there was and records the
    result on the response it hands back; discarding it is what used to make a
    redirect invisible to every caller above this module. An answer that states
    no address states it came from the one that was asked for, which is what a
    read that was not redirected means.

    Whatever it says, it says it without the credential. A route constant is
    this module's to hold and nobody else's to see, and an address is the one
    place a query-placed one could ride out.
    """

    answered = getattr(response, "url", "") or request.url
    return without_query_credential(answered, route_credential(request.route_id))


def answered_headers(carried: Any) -> AnsweredHeaders:
    """What an answer carried, as the ordered pairs a request's headers are in.

    Read out rather than held, because what urllib hands over differs between
    the branch that returns and the branch that raises, and an error response
    can carry nothing at all.
    """

    if not carried:
        return ()
    return tuple((str(name), str(value)) for name, value in carried.items())


def urlopen_read(request: TransportRequest) -> Tuple[int, str, str, str, AnsweredHeaders]:
    """Default opener: one bounded HTTPS read on an admitted method, no redirect games.

    Credentials are attached here and nowhere earlier, which is why a
    ``TransportRequest`` a caller holds can never carry one. A route that
    declares a ``token_route_id`` gets its guest token attached here too, from
    whatever the process is already holding — the mint itself happens above, at
    the governor that records and paces it. A process holding none sends the
    read unauthorized.

    The fifth value is what the origin sent back. It is reported on both
    branches: `Retry-After` rides on a 429, urllib raises every non-2xx, so
    headers read only off the returning branch would be absent from the one
    status a scheduler exists to answer.
    """

    if not request.url.startswith("https://"):
        raise TransportError("refusing a non-https url for route " + request.route_id)
    if request.method not in admitted_methods(request.route_id):
        raise TransportError(
            "refusing a write-capable method {0} on route {1}".format(
                request.method, request.route_id
            )
        )

    credential = route_credential(request.route_id)
    outbound = urllib.request.Request(
        credentialed_url(request.url, credential),
        data=request.body.encode("utf-8") if request.body else None,
        method=request.method,
    )
    headers = tokened_headers(
        credentialed_headers(request.headers, credential),
        route_constant(request.route_id).token_route_id,
    )
    for name, value in headers:
        outbound.add_header(name, value)
    try:
        with urllib.request.urlopen(outbound, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return (
                response.status,
                response.read(MAX_RESPONSE_BYTES).decode("utf-8", errors="replace"),
                response.headers.get("Content-Type", ""),
                answering_address(response, request),
                answered_headers(response.headers),
            )
    except urllib.error.HTTPError as error:
        # A status-bearing error is data, not a tool failure: `channel_verdict`
        # separates a local block from the origin's own failure, and the
        # adapter types the result.
        return (
            error.code,
            error.read(MAX_RESPONSE_BYTES).decode("utf-8", errors="replace"),
            error.headers.get("Content-Type", "") if error.headers else "",
            answering_address(error, request),
            answered_headers(error.headers),
        )
    except OSError as error:
        raise TransportError("transport failed for " + request.route_id) from error


def urlopen_response(request: TransportRequest) -> Tuple[int, str, str]:
    """The three-value view of :func:`urlopen_read`, for callers that ask nowhere else.

    Most reads do not care which address answered or what else it said, and
    the two forms exist so that adding a fourth value, and then a fifth,
    changed no caller that did not want them.
    """

    return urlopen_read(request)[:3]


class Transport:
    """One run's outbound channel. Every attempt is recorded, in order."""

    def __init__(
        self,
        opener: Optional[Callable[[TransportRequest], Tuple[int, str, str]]] = None,
        now: Optional[Callable[[], str]] = None,
    ) -> None:
        self._opener = opener if opener is not None else urlopen_read
        self._now = now if now is not None else utc_now_iso
        self.calls: List[TransportRequest] = []

    def fetch(self, request: TransportRequest) -> TransportResponse:
        # Recorded before the opener runs, so a raising opener still leaves the
        # attempt visible: "an adapter never retries" is checked against this log.
        self.calls.append(request)
        answered = self._opener(request)
        status, body, content_type = answered[:3]
        # An opener that reports no address answered from the one it was asked
        # for. That is what an offline stand-in means and what a read that never
        # left the process means, and it keeps the three-value opener contract
        # every caller here was written against.
        final_url = answered[3] if len(answered) > 3 else request.url
        # And an opener that reports no headers received none, which is the
        # same courtesy the address gets and for the same reason: the four-value
        # opener contract every stand-in here was written against still holds.
        headers = answered[4] if len(answered) > 4 else ()
        return TransportResponse(
            route_id=request.route_id,
            url=request.url,
            status=status,
            body=body,
            content_type=content_type,
            observed_at=self._now(),
            channel_verdict=channel_verdict(status, body),
            final_url=final_url,
            headers=headers,
        )
