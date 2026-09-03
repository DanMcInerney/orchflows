"""A wrong result kept beside the tree: every player answer read as withheld.

The opposite error to `empty_captions_as_absence_adapter`, and the one that
matters for whether the oracle checks anything at all. This adapter types every
player answer `attestation_required`, including the one that did list caption
tracks. It would satisfy any claim of the form "a withheld list is named" while
naming a withholding that did not happen, and a caller would be told
attestation blocked a video this package could have read.

One wrong conclusion drawn from what the shipped adapter returned, and nothing
else.

Loaded by path, part of no package, never imported by the tree under test.
"""

from dataclasses import replace

from super_research.adapters import youtube_innertube

DESCRIPTOR = youtube_innertube.DESCRIPTOR


def fetch_native_page(carrier, request):
    operation, _ = youtube_innertube.operation_for(request)
    page = youtube_innertube.fetch_native_page(carrier, request)
    if operation != youtube_innertube.PLAYER_OPERATION:
        return page
    if youtube_innertube.ATTESTATION_REQUIRED in page.loss:
        return page
    return replace(
        page,
        warnings=page.warnings + ("captions were withheld from this client",),
        loss=page.loss + (youtube_innertube.ATTESTATION_REQUIRED,),
    )
