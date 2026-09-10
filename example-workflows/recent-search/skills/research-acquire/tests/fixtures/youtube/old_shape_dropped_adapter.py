"""A wrong result kept beside the tree: the older thread shape read as gone.

The error a change that teaches this adapter a second shape is one step from:
concluding that a comment's fields live in the entity store *only*, so a thread
the store does not describe is not a comment. Page two of the measured answer
does carry every field there — which is what makes the belief comfortable — and
the header-then-threads capture beside it carries `comment.commentRenderer` with
`voteCount` and an integer `replyCount` and no store at all. Under this belief
that answer holds no comment, and a video the package used to read correctly
goes quiet without anything being typed.

So it keeps a `next` record whose named facts came from the entity store and
drops one whose facts are the older shape's. One wrong conclusion drawn from
what the shipped adapter returned, and nothing else: every branch, every status
and the single outbound call are the shipped adapter's own, so the oracle's
rejection is attributable to this conclusion alone.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import youtube_innertube

DESCRIPTOR = youtube_innertube.DESCRIPTOR


def _from_the_entity_store(record):
    named = dict(record.attributes)
    return any(name in named for name in youtube_innertube.COMMENT_ENTITY_TEXT_FACTS)


def fetch_native_page(carrier, request):
    page = youtube_innertube.fetch_native_page(carrier, request)
    operation, _ = youtube_innertube.operation_for(request)
    if operation != youtube_innertube.NEXT_OPERATION:
        return page
    kept = tuple(record for record in page.records if _from_the_entity_store(record))
    if len(kept) == len(page.records):
        return page
    return replace(page, records=kept, outcome="ok" if kept else "empty")
