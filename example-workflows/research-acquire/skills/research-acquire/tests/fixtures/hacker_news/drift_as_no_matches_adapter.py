"""A wrong result kept beside the tree: an index that moved read as no matches.

The other direction of the same confusion. This adapter runs the shipped one,
sees a search answer whose declared container is not there, and reports it as a
query that matched nothing. HN then looks quiet — a caller gets `empty` with no
loss code, no warning worth acting on, and no reason to suspect that this
package is reading keys Algolia stopped publishing. Without this one the oracle
could be satisfied by an adapter that never distinguished the two answers at
all, in the direction that fails silently.

One wrong conclusion drawn from what the shipped adapter returned, and nothing
else.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import hacker_news

DESCRIPTOR = hacker_news.DESCRIPTOR
SEARCH_DESCRIPTOR = hacker_news.SEARCH_DESCRIPTOR
SURFACE_DESCRIPTORS = hacker_news.SURFACE_DESCRIPTORS


def fetch_native_page(carrier, request):
    page = hacker_news.fetch_native_page(carrier, request)
    if hacker_news.SCHEMA_DRIFT not in page.loss:
        return page
    return replace(
        page,
        outcome="empty",
        warnings=("this query matched nothing",),
        loss=(),
    )
