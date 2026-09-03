"""A wrong result kept beside the tree: an item HN does not have read as drift.

Firebase answers a request for an id it holds nothing under with 200 and the
body ``null``. This adapter runs the shipped one, sees an item call come back
with no rows, and concludes that the payload it reads has changed shape. A
caller then goes looking for a Firebase schema change every time a run is
handed an id that HN deleted or never had — and, worse, an ordinary answer
arrives as a failure, so a traversal that walked one dead kid reports the whole
step as broken.

One wrong conclusion drawn from what the shipped adapter returned, and nothing
else: every branch, every status, and the single outbound call are the shipped
adapter's own, so the oracle's rejection is attributable to this conclusion
alone.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import hacker_news

DESCRIPTOR = hacker_news.DESCRIPTOR
SEARCH_DESCRIPTOR = hacker_news.SEARCH_DESCRIPTOR
SURFACE_DESCRIPTORS = hacker_news.SURFACE_DESCRIPTORS


def fetch_native_page(carrier, request):
    page = hacker_news.fetch_native_page(carrier, request)
    if page.route_id != DESCRIPTOR.route_id or page.outcome != "empty":
        return page
    return replace(
        page,
        outcome="failed",
        warnings=("the item payload this adapter reads has changed shape",),
        loss=(hacker_news.SCHEMA_DRIFT,),
    )
