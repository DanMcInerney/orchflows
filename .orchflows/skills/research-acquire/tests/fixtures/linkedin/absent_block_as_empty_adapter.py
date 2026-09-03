"""A wrong result kept beside the tree: a page that moved answered with nothing.

The other way to lose a K2 route. This one gets the authwall question right
and the drift question wrong: a page that no longer embeds the block comes
back as a result set that happens to be empty, so a caller reads "this member
has no public profile" off a page that never said so, and the day LinkedIn
rewrites its markup passes without anyone noticing.

Every other branch is delegated to the shipped adapter on purpose: being wrong
in exactly one branch is what makes the oracle's rejection attributable to
that branch and to nothing else.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import linkedin_public

DESCRIPTOR = linkedin_public.DESCRIPTOR


def fetch_native_page(carrier, request):
    page = linkedin_public.fetch_native_page(carrier, request)
    if "schema_drift" in page.loss:
        return replace(page, outcome="empty", loss=(), warnings=())
    return page
