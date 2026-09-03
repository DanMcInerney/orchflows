"""A wrong result kept beside the tree: withheld captions read as an absence.

This is the adapter this ticket exists to not write. It runs the shipped
adapter, sees the player answer come back with no caption track listed, and
concludes that the video has no captions — off a 200 whose title, view count
and publish date all arrived perfectly. A caller then records something false
about the video rather than something true about the read, and it does so on
every video it will ever read, because the 2026-08-10 probes recorded that empty list
on five clients and three videos without exception.

It also reads the shipped adapter's own ``CAPTION_FETCH_FIELD``, which the
shipped adapter declares and never reads, so the scan that states that count as
zero is shown to be able to rise.

One wrong conclusion drawn from what the shipped adapter returned, and nothing
else: every branch, every status, and the single outbound call are the shipped
adapter's own, so the oracle's rejection is attributable to this conclusion
alone.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import youtube_innertube

DESCRIPTOR = youtube_innertube.DESCRIPTOR

# Read here, and read nowhere in the shipped module: an adapter that believed a
# video simply had no captions would be one step from reaching for this.
CAPTION_FETCH_FIELD = youtube_innertube.CAPTION_FETCH_FIELD


def _without_attestation(codes):
    return tuple(code for code in codes if code != youtube_innertube.ATTESTATION_REQUIRED)


def fetch_native_page(carrier, request):
    page = youtube_innertube.fetch_native_page(carrier, request)
    if not page.records or youtube_innertube.ATTESTATION_REQUIRED not in page.loss:
        return page
    return replace(
        page,
        records=tuple(
            replace(record, loss=_without_attestation(record.loss)) for record in page.records
        ),
        warnings=("this video has no captions",),
        loss=_without_attestation(page.loss),
    )
