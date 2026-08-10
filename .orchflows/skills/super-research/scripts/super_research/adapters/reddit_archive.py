"""K3 Reddit hydration through the Arctic Shift archive.

Measured 2026-08-10 (findings.md §1, "Reddit"): Reddit's own ``.json``
surfaces return 403 to every User-Agent tried, and its RSS ceiling is one
to two requests per thirty seconds. Arctic Shift answered six back-to-back
requests at ~0.25 s with no throttle, returning ``score``,
``num_comments`` and ``created_utc`` — the native engagement the platform
itself will not serve keylessly.

It is an independent volunteer-run archive, so every record it produces
carries ``third_party_archive`` loss and names its operator: this is not
the platform speaking.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping, Tuple

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
    adapter_id="reddit_archive",
    adapter_version="1",
    access_class="K3",
    route_id=transport.ARCTIC_SHIFT_POSTS_ROUTE,
    platform="reddit",
    native_identity_namespace="reddit",
    representation_kind="native",
    operator_identity="arctic-shift",
    standing_loss=("third_party_archive",),
)

NATIVE_ORDER = "archive_ids_order"
REDDIT_ORIGIN = transport.REDDIT_SITE_ORIGIN
# Reddit names a submission by its fullname, not its bare id; wrong_merge_law
# rule 6 makes that prefix part of platform identity.
POST_FULLNAME_PREFIX = "t3_"
ENGAGEMENT_FIELDS = ("score", "num_comments")


def epoch_to_utc_iso(created_utc: Any) -> str:
    if not isinstance(created_utc, (int, float)) or isinstance(created_utc, bool):
        return ""
    moment = datetime.fromtimestamp(float(created_utc), tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _engagement_of(post: Mapping[str, Any]) -> Tuple[Tuple[str, int], ...]:
    # Only exact integer native metrics are admitted; upvote_ratio is a float
    # and is therefore not an engagement snapshot.
    return tuple(
        (name, post[name])
        for name in ENGAGEMENT_FIELDS
        if isinstance(post.get(name), int) and not isinstance(post.get(name), bool)
    )


def _record_for(position: int, post: Mapping[str, Any]) -> NativeRecord:
    permalink = post.get("permalink") or ""
    return NativeRecord(
        canonical_content_kind="post",
        canonical_locator=REDDIT_ORIGIN + permalink if permalink else (post.get("url") or ""),
        native_item_id=POST_FULLNAME_PREFIX + (post.get("id") or ""),
        title=post.get("title") or "",
        body=post.get("selftext") or "",
        author=post.get("author") or "",
        community=post.get("subreddit") or "",
        published_at=epoch_to_utc_iso(post.get("created_utc")),
        engagement=_engagement_of(post),
        native_position=position,
        loss=DESCRIPTOR.standing_loss,
    )


def _page_from(response: transport.TransportResponse) -> NativePage:
    """Turn one response the archive itself sent into exactly one page."""

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

    try:
        payload = json.loads(response.body)
        posts = payload["data"]
    except (ValueError, KeyError, TypeError):
        return build_native_page(
            DESCRIPTOR,
            (),
            observed_at=response.observed_at,
            native_order=NATIVE_ORDER,
            warnings=("archive payload was not a data-bearing json object",),
            outcome="failed",
            loss=("malformed_json",),
        )

    records = tuple(
        _record_for(position, post)
        for position, post in enumerate(posts)
        if isinstance(post, Mapping)
    )
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        outcome="ok" if records else "empty",
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Hydrate the requested thread ids and return exactly one NativePage."""

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"ids": ",".join(request.target_ids)},
        parse=_page_from,
        native_order=NATIVE_ORDER,
    )
