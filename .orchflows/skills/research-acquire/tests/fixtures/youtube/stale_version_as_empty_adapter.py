"""A wrong result kept beside the tree: a refused request read as no results.

The InnerTube client version rotates with each YouTube web release. The day it
goes stale, this adapter reports that the search matched nothing and the video
had no metadata — a scheduled outage arriving as silence nobody can attribute,
on a route that is working perfectly for anyone sending a current version.

One wrong conclusion drawn from what the shipped adapter returned, and nothing
else.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import youtube_innertube

DESCRIPTOR = youtube_innertube.DESCRIPTOR


def fetch_native_page(carrier, request):
    page = youtube_innertube.fetch_native_page(carrier, request)
    if youtube_innertube.STALE_IDENTIFIER not in page.loss:
        return page
    return replace(page, outcome="empty", warnings=("no results",), loss=())
