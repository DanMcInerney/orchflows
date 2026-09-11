"""A wrong result kept beside the tree: read-only by having no capability.

The cheapest way to pass a read-only check is to reach nothing at all, and an
oracle that only looked for a write verb would find none here and be perfectly
satisfied. This adapter declares an empty operation set: no repository, no
issue, no release, no search, and therefore no write either. It is the vacuity
direction, and without a clause that rejects it the whole of row 2 would be
satisfiable by an adapter that does not work.

Loaded by path, part of no package, never imported by the tree under test.
"""

from super_research.adapters import build_native_page, github_rest

DESCRIPTOR = github_rest.DESCRIPTOR
SEARCH_DESCRIPTOR = github_rest.SEARCH_DESCRIPTOR
SURFACE_DESCRIPTORS = github_rest.SURFACE_DESCRIPTORS

GITHUB_OPERATIONS = ()
OPERATION_SURFACES = {}


def fetch_native_page(carrier, request):
    return build_native_page(DESCRIPTOR, (), outcome="empty")
