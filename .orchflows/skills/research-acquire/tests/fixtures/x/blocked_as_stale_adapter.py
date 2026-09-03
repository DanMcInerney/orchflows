"""A wrong result kept beside the tree: every refusal read as a rotated id.

The error in the opposite direction, and the reason the oracle needs a side
that fails for over-claiming. An adapter that types every failure
`stale_identifier` satisfies "a stale id is never silence" trivially, while
sending whoever reads the run off to walk a javascript bundle over an
operation the origin has simply decided not to serve a guest.

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
    if x_guest.AUTH_REQUIRED in page.loss:
        return replace(page, loss=(x_guest.STALE_IDENTIFIER,))
    return page
