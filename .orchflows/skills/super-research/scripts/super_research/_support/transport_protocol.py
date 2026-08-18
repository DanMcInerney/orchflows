"""Private transport protocol values and read-only admission policy."""

from __future__ import annotations

import email.utils
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Mapping, Optional, Tuple

from ..routes import X_GUEST_ACTIVATE_ROUTE, YOUTUBE_INNERTUBE_ROUTE, RouteConstant


USER_AGENT = "super-research/0.1 (keyless read-only acquisition)"
READ_METHODS = ("GET", "HEAD")

RATE_LIMITED_STATUS = 429
RATE_LIMITED = "rate_limited"
RETRY_AFTER_HEADER = "Retry-After"
RATE_LIMIT_RESET_HEADER = "X-RateLimit-Reset"
SECONDARY_RATE_LIMITED_STATUS = 403
SECONDARY_RATE_LIMIT_MARKERS = ("secondary rate limit",)
OBSERVED_AT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

AnsweredHeaders = Tuple[Tuple[str, str], ...]

TOKEN_ACTIVATION_ROUTES = (X_GUEST_ACTIVATE_ROUTE,)
TOKEN_ACTIVATION_METHODS = ("POST",)
QUERY_BODY_ROUTES = (YOUTUBE_INNERTUBE_ROUTE,)
QUERY_BODY_METHODS = ("POST",)

ORIGIN_CONTENT = "origin_content"
ORIGIN_FAILURE = "origin_failure"
NETWORK_INTERCEPTED = "network_intercepted"
CHANNEL_VERDICTS = (ORIGIN_CONTENT, ORIGIN_FAILURE, NETWORK_INTERCEPTED)
CAPTIVE_PORTAL_MARKERS = ('<base href="/login/">',)


class TransportError(RuntimeError):
    """An outbound request was refused or could not be completed."""


UNREACHABLE = "unreachable"


@dataclass(frozen=True)
class TransportRequest:
    """One read, spelled completely, before any credential is attached."""

    route_id: str
    method: str
    url: str
    headers: Tuple[Tuple[str, str], ...] = ()
    body: str = ""


@dataclass(frozen=True)
class TransportResponse:
    """One answer and the protocol facts every caller may retain."""

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


def channel_verdict(status: int, body: str) -> str:
    """Name the party that answered: the origin, or a local network appliance."""

    if 200 <= status < 300:
        return ORIGIN_CONTENT
    lowered = body.lower()
    for marker in CAPTIVE_PORTAL_MARKERS:
        if marker in lowered:
            return NETWORK_INTERCEPTED
    return ORIGIN_FAILURE


def rate_refused(status: int, body: str) -> bool:
    """Whether this answer is the origin asking for fewer requests."""

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
    """One header off an answer, matched without regard to case."""

    wanted = name.lower()
    for held, value in headers:
        if held.lower() == wanted:
            return value
    return ""


def observed_moment(observed_at: str) -> Optional[datetime]:
    """The moment an answer says it was read, or None when unusable."""

    try:
        return datetime.strptime(observed_at, OBSERVED_AT_FORMAT).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def http_date_moment(stated: str) -> Optional[datetime]:
    """One RFC 7231 HTTP-date, or None for anything unreadable."""

    try:
        moment = email.utils.parsedate_to_datetime(stated)
    except (TypeError, ValueError, OverflowError):
        return None
    if moment is None:
        return None
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


RATE_LIMIT_RESET_COUNTDOWN_CEILING_SECONDS = 100000000


def epoch_moment(stated: str, read_at: Optional[datetime] = None) -> Optional[datetime]:
    """When an X-RateLimit-Reset says its window ends, in either spelling."""

    held = stated.strip()
    if not held:
        return None
    try:
        seconds = int(held)
    except ValueError:
        return None
    if seconds < RATE_LIMIT_RESET_COUNTDOWN_CEILING_SECONDS:
        if read_at is None or seconds < 0:
            return None
        return read_at + timedelta(seconds=seconds)
    try:
        return datetime.fromtimestamp(seconds, timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


def remaining_seconds(deadline: Optional[datetime], read_at: Optional[datetime]) -> float:
    """Seconds from the read moment until an absolute deadline."""

    if deadline is None or read_at is None:
        return 0.0
    return max(0.0, (deadline - read_at).total_seconds())


def retry_after_seconds(stated: str, read_at: Optional[datetime]) -> float:
    """Retry-After in either RFC 7231 spelling, as seconds remaining."""

    held = stated.strip()
    if not held:
        return 0.0
    if held.isascii() and held.isdigit():
        return float(held)
    return remaining_seconds(http_date_moment(held), read_at)


def stated_cooldown_seconds(response: TransportResponse) -> float:
    """The longest usable interval this origin asked to be left alone."""

    read_at = observed_moment(response.observed_at)
    return max(
        retry_after_seconds(header_value(response.headers, RETRY_AFTER_HEADER), read_at),
        remaining_seconds(
            epoch_moment(header_value(response.headers, RATE_LIMIT_RESET_HEADER), read_at),
            read_at,
        ),
    )


def route_constant(
    route_id: str, route_constants: Mapping[str, RouteConstant]
) -> RouteConstant:
    """Resolve a declared route from the facade's current table."""

    route = route_constants.get(route_id)
    if route is None:
        raise TransportError("unknown route " + route_id)
    return route


def route_admissions(route_constants: Mapping[str, RouteConstant]) -> Dict[str, bool]:
    """Per-route booleans: whether no user credential is needed."""

    return {
        route_id: route.access_class != "K5"
        for route_id, route in sorted(route_constants.items())
    }


def admitted_methods(route_id: str) -> Tuple[str, ...]:
    """Every method this route may use: reads plus two closed exceptions."""

    if route_id in TOKEN_ACTIVATION_ROUTES:
        return READ_METHODS + TOKEN_ACTIVATION_METHODS
    if route_id in QUERY_BODY_ROUTES:
        return READ_METHODS + QUERY_BODY_METHODS
    return READ_METHODS
