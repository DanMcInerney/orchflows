"""Shared offline harness for the two social-adapter case modules."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from super_research import adapters, transport
from super_research.adapters import bluesky, x_fxtwitter
from tests import helpers

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"
BLUESKY_DIR = FIXTURE_DIR / "bluesky"
FXTWITTER_DIR = FIXTURE_DIR / "x_fxtwitter"

SEARCH_ROUTE = transport.BLUESKY_SEARCH_POSTS_ROUTE
AUTHOR_ROUTE = transport.BLUESKY_AUTHOR_FEED_ROUTE
FXTWITTER_ROUTE = transport.FXTWITTER_API_ROUTE

JSON_TYPE = "application/json"
HTML_TYPE = "text/html"

# The two posts the search fixture carries, and the handle both are under.
BSKY_HANDLE = "bsky.app"
BSKY_ROOT_URI = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3msqpuobiwk2t"
BSKY_REPLY_URI = "at://did:plc:z72i7hdynmk6r22z27h6tvur/app.bsky.feed.post/3msqpusnigc2t"
BSKY_DID = "did:plc:z72i7hdynmk6r22z27h6tvur"
# The third row of the author feed is a repost: a post by somebody else that
# this actor passed on, so its author is the account that wrote it.
BSKY_REPOSTED_HANDLE = "buttondown.com"

# The statuses the X fixtures carry.
X_ROOT_ID = "2088841930813690331"
X_SELF_REPLY_ID = "2088847137115144643"
X_SEARCH_REPLY_ID = "2089361198391214168"
X_SEARCH_ROOT_ID = "2089361176186491316"
X_SEARCH_PARENT_ID = "2089083612171739470"
X_PROFILE_ID = "34743251"
X_HANDLE = "SpaceX"


def read_fixture(directory, name):
    return directory.joinpath(name).read_text(encoding="utf-8")


def payload_of(directory, name):
    return json.loads(read_fixture(directory, name))


def discovery(query, **bounds):
    return adapters.AdapterRequest(step_id="s1-social", query=query, **bounds)


def hydration(target, **bounds):
    return adapters.AdapterRequest(step_id="s1-social", target_ids=(target,), **bounds)


def answered(module, route_id, body, request, status=200, content_type=JSON_TYPE):
    """Run one adapter over one canned answer; return its page and the opener."""

    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: (status, body, content_type)}
    )
    return (module.fetch_native_page(carrier, request), opener)


def bluesky_page(name, request, route_id=SEARCH_ROUTE, status=200, content_type=JSON_TYPE):
    return answered(
        bluesky, route_id, read_fixture(BLUESKY_DIR, name), request, status, content_type
    )


def fxtwitter_page(name, request, status=200, content_type=JSON_TYPE):
    return answered(
        x_fxtwitter, FXTWITTER_ROUTE, read_fixture(FXTWITTER_DIR, name), request, status,
        content_type,
    )


def built_url(route_id, params):
    """The address the transport builds for these params — the one oracle for a url."""

    return transport.build_transport_request(route_id, params).url


def named(record):
    """One record's attributes as a mapping, for asserting one name at a time."""

    return dict(record.attributes)
