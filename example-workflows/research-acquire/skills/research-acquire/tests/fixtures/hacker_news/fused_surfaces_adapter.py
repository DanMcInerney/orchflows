"""A wrong result kept beside the tree: one call that reads both surfaces.

The tempting version of this adapter. HN's index answers a query with hits that
carry only what Algolia keeps, and the item store has the counts and the tree —
so an adapter that searched and then hydrated its first hit would return a
richer page from one call, and every check about fields and typing would still
pass.

What it would cost is everything the core owns. Two reads leave on two routes
with two budgets, and the scheduler charges one; the page carries one
`observed_at` for two moments; the second read is invisible to the work ledger,
so a run's own accounting of what it consumed is wrong by exactly the reads
nobody declared. And the caller never chose to spend the second budget.

One wrong conclusion drawn from what the shipped adapter returned — that a page
may be assembled from more than one answer — and nothing else.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import hacker_news

DESCRIPTOR = hacker_news.DESCRIPTOR
SEARCH_DESCRIPTOR = hacker_news.SEARCH_DESCRIPTOR
SURFACE_DESCRIPTORS = hacker_news.SURFACE_DESCRIPTORS


def fetch_native_page(carrier, request):
    page = hacker_news.fetch_native_page(carrier, request)
    if page.route_id != SEARCH_DESCRIPTOR.route_id or not page.records:
        return page

    hydrated = hacker_news.fetch_native_page(
        carrier,
        hacker_news.AdapterRequest(
            step_id=request.step_id,
            target_ids=(page.records[0].native_item_id,),
        ),
    )
    return replace(page, records=page.records[:1] + hydrated.records + page.records[1:])
