"""A wrong result kept beside the tree: every page called a page that moved.

The opposite error, and the reason the oracle needs a side that fails on a
success. An adapter that types drift onto everything satisfies "a missing
block is never silent" perfectly and is useless: it reports that LinkedIn
changed its markup every time a profile is read correctly, and the one real
drift, when it comes, arrives indistinguishable from the noise.

Without this module the oracle could be passed by refusing to answer at all.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import linkedin_public

DESCRIPTOR = linkedin_public.DESCRIPTOR


def fetch_native_page(carrier, request):
    page = linkedin_public.fetch_native_page(carrier, request)
    if page.outcome == "ok":
        return replace(
            page,
            records=(),
            outcome="failed",
            loss=("schema_drift",),
            warnings=("the page this adapter reads has changed shape",),
        )
    return page
