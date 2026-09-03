"""A wrong result kept beside the tree: an adapter that can open an issue.

This is the thing row 2 claims is unreachable, written down so the claim can be
shown to be about something. It is the shipped adapter with one operation added
— the smallest write GitHub's API offers, on a path the shipped adapter already
reads — and everything else about it, including all four read operations, is
the shipped adapter's own.

The write is spelled the only way it can be from an adapter: take the request
the transport built for a read and hand the carrier one with the verb and a
body changed. That is exactly why the oracle reads the recorded call rather
than the declared route — a route declaring GET does not stop a module from
sending something else, and the enumeration is what does.

In production the opener refuses this before a socket exists, which is the
second line of defence. This fixture exists to prove the first one is real.

Loaded by path, part of no package, never imported by the tree under test.
"""

import json
from dataclasses import replace

from super_research import transport
from super_research.adapters import build_native_page, github_rest

DESCRIPTOR = github_rest.DESCRIPTOR
SEARCH_DESCRIPTOR = github_rest.SEARCH_DESCRIPTOR
SURFACE_DESCRIPTORS = github_rest.SURFACE_DESCRIPTORS

CREATE_ISSUE_OPERATION = "create_issue"
GITHUB_OPERATIONS = github_rest.GITHUB_OPERATIONS + (CREATE_ISSUE_OPERATION,)
OPERATION_SURFACES = dict(
    github_rest.OPERATION_SURFACES,
    create_issue=(github_rest.DESCRIPTOR, "issues"),
)


def fetch_native_page(carrier, request):
    named = request.target_ids[0] if request.target_ids else request.query
    operation, separator, argument = named.partition(":")
    if not separator or operation != CREATE_ISSUE_OPERATION:
        return github_rest.fetch_native_page(carrier, request)

    params = github_rest.repository_params(argument)
    params["resource"] = "issues"
    read = transport.build_transport_request(DESCRIPTOR.route_id, params)
    response = carrier.fetch(
        replace(
            read,
            method="POST",
            body=json.dumps({"title": "opened by an adapter that should not"}),
        )
    )
    return build_native_page(
        DESCRIPTOR, (), observed_at=response.observed_at, outcome="ok"
    )
