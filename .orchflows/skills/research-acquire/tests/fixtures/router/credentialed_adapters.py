"""Adapters beside the tree: three ways a run could turn out to want a key.

Each is Reddit's own feed with one property of its answer spoiled, so a
rejection is attributable to that one difference and nothing under test was
mutated to produce it.

`environment_reading` is the one the keyless claim actually turns on. It reads
a token out of the environment and refuses without one — which is what eight
of the prior spec's eleven adapters were said to do. Run with the variable
exported it answers perfectly, and run with the environment emptied it
refuses; that difference is the whole reason the suite empties the environment
instead of sampling it. A keyless run that passed on a laptop with the key set
would have proven nothing, and this file is what makes that statement testable
rather than rhetorical.

Nothing in the package imports this file and no discovery pattern matches it.
"""

from __future__ import annotations

import os
from dataclasses import replace

from super_research.adapters import reddit_feed

TOKEN_VARIABLE = "SUPER_RESEARCH_TOKEN"
AUTH_REQUIRED = "auth_required"


def correct(carrier, request):
    """Reddit's own feed, unchanged. What makes the three below attributable."""

    return reddit_feed.fetch_native_page(carrier, request)


def environment_reading(carrier, request):
    """Answers when a token is exported, and refuses when one is not."""

    page = correct(carrier, request)
    if os.environ.get(TOKEN_VARIABLE):
        return page
    return replace(
        page,
        records=(),
        outcome="refused",
        loss=(AUTH_REQUIRED,),
        warnings=("export " + TOKEN_VARIABLE + " to read this route",),
    )


def always_auth_required(carrier, request):
    """Refuses whatever the environment holds — the honest version of the same."""

    return replace(correct(carrier, request), records=(), outcome="failed", loss=(AUTH_REQUIRED,))


def empty_success(carrier, request):
    """Comes back with nothing and calls it a success.

    A refusal nobody has to admit to: no loss code, no failed outcome, and a
    caller who asked what a subreddit is posting gets an artifact saying it is
    posting nothing. The keyless claim is that an adapter *reaches its declared
    capability*, and this is what checking only the first half would admit.
    """

    return replace(correct(carrier, request), records=(), outcome="ok")
