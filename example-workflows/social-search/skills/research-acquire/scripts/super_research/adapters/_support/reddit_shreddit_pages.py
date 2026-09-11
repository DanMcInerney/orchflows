"""NativePage typing for parsed Reddit Shreddit partials."""

from __future__ import annotations

from typing import List, Optional

from ... import transport
from .. import AdapterDescriptor, NativePage, build_native_page
from .reddit_shreddit_contract import (
    COMMENTS_DESCRIPTOR,
    COMMENTS_OPERATION,
    COMMENT_TAG,
    COMMENT_TREE_TAG,
    DESCRIPTOR,
    HTTP_STATUS,
    LISTING_OPERATION,
    NATIVE_ORDERS,
    POST_TAG,
    SCHEMA_DRIFT,
    SEARCH_OPERATION,
    TELEMETRY_TAG,
    THING_ID_ATTRIBUTE,
    exact_count,
)
from .reddit_shreddit_extract import (
    _CommentParser,
    _ListingParser,
    _SearchParser,
    _comment_record,
    _listing_record,
    _search_record,
    collapsed,
)


def _failed(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    loss: str,
    warning: str,
) -> NativePage:
    return build_native_page(
        descriptor,
        (),
        observed_at=response.observed_at,
        native_order=native_order,
        warnings=(warning,),
        outcome="failed",
        loss=(loss,),
    )


def _drifted(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    detail: str,
) -> NativePage:
    """Type a successful response whose custom-element shape has changed."""

    return _failed(
        descriptor,
        response,
        native_order,
        SCHEMA_DRIFT,
        "route {0} answered {1} and {2}: the partial this adapter reads has"
        " changed shape".format(descriptor.route_id, response.status, detail),
    )


def _status_refused(
    descriptor: AdapterDescriptor, response: transport.TransportResponse, native_order: str
) -> Optional[NativePage]:
    if response.status == 200:
        return None
    return _failed(
        descriptor,
        response,
        native_order,
        HTTP_STATUS,
        "http status {0} from {1}".format(response.status, descriptor.route_id),
    )


def _listing_page(response: transport.TransportResponse) -> NativePage:
    native_order = NATIVE_ORDERS[LISTING_OPERATION]
    refused = _status_refused(DESCRIPTOR, response, native_order)
    if refused is not None:
        return refused
    parser = _ListingParser()
    parser.feed(response.body)
    parser.close()
    records = tuple(
        _listing_record(position, post) for position, post in enumerate(parser.posts)
    )
    if not records and not parser.partials:
        return _drifted(
            DESCRIPTOR, response, native_order, "carried no <" + POST_TAG + "> and no partial"
        )
    return build_native_page(
        DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        cursor_out=parser.next_cursor,
        native_order=native_order,
        outcome="ok" if records else "empty",
        warnings=()
        if records
        else (
            "route {0} answered 200 with no <{1}>: this listing holds no post".format(
                DESCRIPTOR.route_id, POST_TAG
            ),
        ),
    )


def _search_page(
    descriptor: AdapterDescriptor, response: transport.TransportResponse
) -> NativePage:
    native_order = NATIVE_ORDERS[SEARCH_OPERATION]
    refused = _status_refused(descriptor, response, native_order)
    if refused is not None:
        return refused
    parser = _SearchParser()
    parser.feed(response.body)
    parser.close()
    records = tuple(
        _search_record(position, row)
        for position, row in enumerate(parser.rows)
        if row.get("thing_id") or row.get("context")
    )
    if not records and parser.trackers:
        return _drifted(
            descriptor,
            response,
            native_order,
            "carried {0} <{1}> row(s) naming no identity".format(
                parser.trackers, TELEMETRY_TAG
            ),
        )
    return build_native_page(
        descriptor,
        records,
        observed_at=response.observed_at,
        cursor_out=parser.next_cursor,
        native_order=native_order,
        outcome="ok" if records else "empty",
        warnings=()
        if records
        else (
            "route {0} answered 200 with no <{1}> row: this query matched"
            " nothing".format(descriptor.route_id, TELEMETRY_TAG),
        ),
    )


def _comments_page(response: transport.TransportResponse, community: str) -> NativePage:
    native_order = NATIVE_ORDERS[COMMENTS_OPERATION]
    refused = _status_refused(COMMENTS_DESCRIPTOR, response, native_order)
    if refused is not None:
        return refused
    parser = _CommentParser()
    parser.feed(response.body)
    parser.close()
    records = tuple(
        _comment_record(
            position,
            comment,
            collapsed(parser.bodies.get(comment.get(THING_ID_ATTRIBUTE, ""), [])),
            community,
        )
        for position, comment in enumerate(parser.comments)
    )
    if not records and not parser.trees:
        return _drifted(
            COMMENTS_DESCRIPTOR,
            response,
            native_order,
            "carried no <" + COMMENT_TREE_TAG + "> and no <" + COMMENT_TAG + ">",
        )
    warnings: List[str] = []
    if not records:
        warnings.append(
            "route {0} answered 200 with a <{1}> holding no <{2}>: this post has"
            " no comment".format(
                COMMENTS_DESCRIPTOR.route_id, COMMENT_TREE_TAG, COMMENT_TAG
            )
        )
    else:
        stated = exact_count(parser.total_comments)
        if stated is not None and stated > len(records):
            warnings.append(
                "this post states {0} comments and this page carried {1}: the rest"
                " are behind the more-comments continuation, which declares a POST"
                " this package does not admit".format(stated, len(records))
            )
    return build_native_page(
        COMMENTS_DESCRIPTOR,
        records,
        observed_at=response.observed_at,
        native_order=native_order,
        outcome="ok" if records else "empty",
        warnings=tuple(warnings),
    )
