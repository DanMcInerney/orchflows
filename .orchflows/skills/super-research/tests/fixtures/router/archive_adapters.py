"""Archives beside the tree: five ways an archive could pass for the platform.

Each is the shipped `reddit_archive` with exactly one property of its output
spoiled — the label off the record, the label moved to where nothing reads it,
the operator unnamed, the operator named as Reddit itself — plus one keyless
route wearing the archive's label. A rejection is attributable to that one
difference, and nothing under test was mutated to produce it.

The one that matters most is `page_labelled_only`. `normalize_page` builds a
record's loss from the record's own and never from the page's, so an archive
that labels the page and not the rows produces an artifact where every row
looks like Reddit speaking, on an adapter whose descriptor declares the label
and whose page carries it. It is the mistake that would survive a check
written against the descriptor.

Nothing in the package imports this file and no discovery pattern matches it.
"""

from __future__ import annotations

from dataclasses import replace

from super_research.adapters import reddit_archive, reddit_feed

THIRD_PARTY_ARCHIVE = "third_party_archive"
THE_PLATFORM = "reddit"


def correct(carrier, request):
    """The shipped archive, unchanged. What makes the four below attributable."""

    return reddit_archive.fetch_native_page(carrier, request)


def _unlabelled_records(page):
    return tuple(
        replace(record, loss=tuple(code for code in record.loss if code != THIRD_PARTY_ARCHIVE))
        for record in page.records
    )


def unlabelled(carrier, request):
    """The archive with the label taken off the rows it belongs to."""

    page = correct(carrier, request)
    return replace(page, records=_unlabelled_records(page))


def page_labelled_only(carrier, request):
    """The label on the page, where the record a caller keeps never reads it."""

    page = correct(carrier, request)
    return replace(
        page, records=_unlabelled_records(page), loss=page.loss + (THIRD_PARTY_ARCHIVE,)
    )


def anonymous(carrier, request):
    """Labelled a third-party archive, and it will not say which one."""

    return replace(correct(carrier, request), operator_identity="")


def as_the_platform(carrier, request):
    """The archive answering under Reddit's own name — the whole error, in one field."""

    return replace(correct(carrier, request), operator_identity=THE_PLATFORM)


# The same three mistakes one level up, where the adapter declares itself
# rather than where it answers. A descriptor is what a later adapter copies, so
# an archive that declares nothing here would hand the omission on.
UNDECLARED_LOSS_ROSTER = (replace(reddit_archive.DESCRIPTOR, standing_loss=()),)
ANONYMOUS_OPERATOR_ROSTER = (replace(reddit_archive.DESCRIPTOR, operator_identity=""),)
OPERATOR_IS_THE_PLATFORM_ROSTER = (
    replace(reddit_archive.DESCRIPTOR, operator_identity=THE_PLATFORM),
)


def keyless_route(carrier, request):
    """Reddit's own feed, unchanged: rows that are the platform speaking."""

    return reddit_feed.fetch_native_page(carrier, request)


def keyless_route_wearing_the_label(carrier, request):
    """Reddit's own feed claiming to be an archive of itself.

    The other direction, and it costs a caller the same thing: a record the
    platform published, marked as something a volunteer mirror said.
    """

    page = reddit_feed.fetch_native_page(carrier, request)
    return replace(
        page,
        records=tuple(
            replace(record, loss=record.loss + (THIRD_PARTY_ARCHIVE,))
            for record in page.records
        ),
    )
