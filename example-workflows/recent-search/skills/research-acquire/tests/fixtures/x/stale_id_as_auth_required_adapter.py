"""A wrong result kept beside the tree: a rotated query id blamed on a credential.

The second way the 404 can be misread. This adapter types it `auth_required`,
which is the reading that says a keyless route needs a credential it never
needed — the exact claim the 2026-08-10 probes recorded to be false, since the three
operations whose ids were current answered 200 with the same guest token.

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
        return replace(page, loss=(x_guest.AUTH_REQUIRED,))
    return page
