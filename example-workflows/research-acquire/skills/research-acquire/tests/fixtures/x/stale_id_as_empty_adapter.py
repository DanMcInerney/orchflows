"""A wrong result kept beside the tree: a rotated query id answered with nothing.

This stands for the adapter this ticket exists to not write — one whose 404
branch was never thought about, so the status X answers a stale query id with
comes back as a result set that happens to be empty. A caller then reads "this
account has no posts" off a page the origin never served, and nothing in the
artifact says otherwise.

Every other status is delegated to the shipped adapter on purpose: being wrong
in exactly one branch is what makes the oracle's rejection attributable to that
branch and to nothing else.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import x_guest

DESCRIPTOR = x_guest.DESCRIPTOR


def fetch_native_page(carrier, request):
    page = x_guest.fetch_native_page(carrier, request)
    if x_guest.STALE_IDENTIFIER in page.loss:
        return replace(page, outcome="empty", loss=(), warnings=())
    return page
