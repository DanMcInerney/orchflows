"""K0 one *selected* public document, read as a document.

Measured 2026-08-10 (findings.md §0, control probes): ``example.com`` and
``wikipedia.org`` answered 200 with genuine origin content from this host, while
the network appliance answered other domains with a 503 login portal. Those are
the two static documents the evidence records, and they are what this adapter
may select between.

**This is the one adapter in the roster that could have been a generic HTTP
primitive, and the spec's non-goals forbid one.** Every other adapter here is
pinned to a vendor's endpoint shape: a caller cannot point ``github_rest`` at
Wikipedia, because ``/repos/<owner>/<repo>`` is GitHub's shape and the host is
``transport.py``'s. This one takes an argument, and an argument is one bad
branch away from being an address. If that branch existed, every other
constraint in this package would be decorative — any route at all could be
reached through it, under any verb the opener admits, with none of the pacing,
typing or ownership the route table exists to impose.

So the reachable target set is a **closed table**, :data:`PAGE_SELECTIONS`, and
it is enumerable in the literal sense: two names, each resolving to a route
``transport.py`` owns. A caller names a selection and fills the one segment
that selection declares. A caller string that names an *address* rather than a
document — anything carrying a scheme, an authority, or a path separator — is
refused as ``unselected_target``, and refused **before any call is made**, so
an attempt to point this adapter somewhere costs the network nothing and shows
up in the artifact as a refusal rather than as a read.

That last part is what makes the set closed rather than merely small: it holds
for every string a caller can write, not only for the ones somebody thought to
test. Row 5's fixture beside the tree is the same adapter with that one branch
put back, and the oracle rejects it.

**What a document read yields.** The body is the bytes the origin served, not
text extracted from them: the hash has to be of something exact, and an
extraction would fingerprint this package's reading of a page instead of the
page. ``normalize`` derives the hash from that body, so hashing happens once, in
the module that owns it. Links travel exactly as the document published them,
relative where the document was relative — resolving one here would mean
guessing at a base the document may state elsewhere, and the record carries the
address the origin answered from for a caller that wants to resolve them itself.

**Nothing here runs anything.** No shell, no interpreter, no process, no
dynamic import: this module imports :mod:`html.parser` and this package, and
that is the whole of it.
"""

from __future__ import annotations

import urllib.parse
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

# The primary selection: a public reference document, addressed by its title.
# Primary because an unprefixed target names one, which is what a step that
# hydrates a selected document means.
DESCRIPTOR = AdapterDescriptor(
    adapter_id="public_page",
    adapter_version="1",
    access_class="K0",
    route_id=transport.PUBLIC_PAGE_ARTICLE_ROUTE,
    # A selected document belongs to no platform in the sense every other
    # adapter here means one — there are no identities, no engagement and no
    # native id space. Left unstated, so a record's group scope falls to the
    # route that served it, which is the thing that actually distinguishes one
    # selection from another.
    platform="",
    native_identity_namespace="",
    representation_kind="page",
    operator_identity="wikimedia",
    # Nothing was measured about this route's ceiling beyond that it answered,
    # so all three numbers stay the protocol's conservative defaults. A limit
    # nobody has measured is not one to spend.
)

# The channel control: one document, no argument, and an answer known before it
# is asked. findings.md §0's whole caveat rests on a read like this one — only
# a document whose content is fixed can tell "this network is answering for the
# origin" from "the origin has nothing to say".
CONTROL_DESCRIPTOR = AdapterDescriptor(
    adapter_id="public_page",
    adapter_version="1",
    access_class="K0",
    route_id=transport.PUBLIC_PAGE_CONTROL_ROUTE,
    platform="",
    native_identity_namespace="",
    representation_kind="page",
    operator_identity="iana",
)

# Every route this adapter can reach, one descriptor each. The core collects
# route budgets from here, because a route nothing declares a budget for is a
# route the scheduler refuses to pace.
SURFACE_DESCRIPTORS = (DESCRIPTOR, CONTROL_DESCRIPTOR)

ARTICLE_SELECTION = "article"
CONTROL_SELECTION = "control"

# **The reachable target set.** Each selection names the route it reads and the
# one path segment a caller fills on it, or an empty string where the selection
# takes no argument. Nothing else in this file reaches the carrier, and no value
# here is composed from anything a caller supplied — a caller chooses which row
# of this table to use and what to put in its one slot, and can express nothing
# outside it.
PAGE_SELECTIONS: Dict[str, Tuple[AdapterDescriptor, str]] = {
    ARTICLE_SELECTION: (DESCRIPTOR, "title"),
    CONTROL_SELECTION: (CONTROL_DESCRIPTOR, ""),
}
PRIMARY_SELECTION = ARTICLE_SELECTION

NATIVE_ORDER = "selected_document_order"
CONTENT_KIND = "web_page"

# Where a document's links live, and what a link is. `<a href>` and nothing
# else: a stylesheet reference and a preconnect hint are not links a reader
# follows, and carrying them would bury the ones that are.
ANCHOR_TAG = "a"
HREF_ATTRIBUTE = "href"

# The named facts a document read reports that no record field means.
LINK_ATTRIBUTE = "link"
CONTENT_TYPE_ATTRIBUTE = "content_type"
REQUESTED_URL_ATTRIBUTE = "requested_url"
FINAL_URL_ATTRIBUTE = "final_url"

# What separates a document's name from an address. A value carrying any of
# these can express a scheme or an authority, and a selection value may express
# neither: it names a document *inside* a selection whose host and endpoint the
# route table already fixed.
ADDRESS_CHARACTERS = (":", "/", "\\")

UNSELECTED_TARGET = "unselected_target"
HTTP_STATUS = "http_status"

# Declared here and produced nowhere in this module. Both selections are public
# documents; no status either can answer with is a report that this package
# needed a credential, and a caller naming something outside the table is
# refused by this adapter rather than by an origin.
AUTH_REQUIRED = "auth_required"


class _AnchorParser(HTMLParser):
    """Collect the addresses this document links to, in the order it lists them."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.links: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != ANCHOR_TAG:
            return
        href = dict(attrs).get(HREF_ATTRIBUTE) or ""
        if href.strip():
            self.links.append(href.strip())


def names_an_address(value: str) -> bool:
    """Whether this value is trying to be an address rather than a document name.

    Two tests, and the cheap one is the one that actually closes the set: a
    value carrying a colon, a slash or a backslash can express a scheme or an
    authority, and a value carrying none of them cannot. ``urlsplit`` runs
    behind it as a second opinion rather than as the rule, because a rule with
    no exceptions is worth more here than one extra character of freedom.
    """

    if any(character in value for character in ADDRESS_CHARACTERS):
        return True
    parts = urllib.parse.urlsplit(value)
    return bool(parts.scheme or parts.netloc)


def selected_read(named: str) -> Tuple[str, str, str]:
    """Which selection this call reads and what fills it, or why it is refused.

    Returns ``(selection, value, refusal)`` with exactly one of the first and
    the last set. A caller names a selection outright, names one with a value
    after a colon, or names nothing and takes the primary — and in every case
    the value has to be a document's name rather than an address.
    """

    target = named.strip()
    if target in PAGE_SELECTIONS:
        selection, value = target, ""
    else:
        kind, separator, argument = target.partition(":")
        if separator and kind in PAGE_SELECTIONS:
            selection, value = kind, argument.strip()
        else:
            selection, value = PRIMARY_SELECTION, target

    _, parameter = PAGE_SELECTIONS[selection]
    if not parameter:
        if value:
            return ("", "", "selection {0} takes no argument, and {1!r} is one".format(
                selection, value
            ))
        return (selection, "", "")
    if not value:
        return ("", "", "selection {0} names no document".format(selection))
    if names_an_address(value):
        return ("", "", (
            "{0!r} names an address rather than a document inside a selection."
            " This adapter reads one of {1} and cannot be pointed anywhere: a"
            " host belongs to the route table.".format(value, sorted(PAGE_SELECTIONS))
        ))
    return (selection, value, "")


def _record_for(response: transport.TransportResponse) -> NativeRecord:
    """One document, as the origin served it."""

    parser = _AnchorParser()
    parser.feed(response.body)
    parser.close()

    named: List[Tuple[str, str]] = [
        (CONTENT_TYPE_ATTRIBUTE, response.content_type),
        # What was asked and what answered. Where they differ, that difference
        # is the redirect, stated as the two facts it is made of rather than as
        # a chain this channel cannot see.
        (REQUESTED_URL_ATTRIBUTE, response.url),
        (FINAL_URL_ATTRIBUTE, response.final_url),
    ]
    named.extend((LINK_ATTRIBUTE, link) for link in parser.links)
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        # Where the document actually came from, so two requests that land on
        # one document name one thing.
        canonical_locator=response.final_url or response.url,
        # The bytes the origin served. `normalize` hashes exactly this, which is
        # what makes the fingerprint a fingerprint of the document.
        body=response.body,
        attributes=tuple(named),
        native_position=0,
    )


def _page(
    descriptor: AdapterDescriptor,
    observed_at: str,
    records: Tuple[NativeRecord, ...] = (),
    warnings: Tuple[str, ...] = (),
    outcome: str = "ok",
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        descriptor,
        records,
        observed_at=observed_at,
        native_order=NATIVE_ORDER,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _page_from(
    descriptor: AdapterDescriptor, response: transport.TransportResponse
) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status != 200:
        return _page(
            descriptor,
            response.observed_at,
            warnings=(
                "http status {0} from {1}".format(response.status, descriptor.route_id),
            ),
            outcome="failed",
            loss=(HTTP_STATUS,),
        )
    # A 200 is a document, whatever is in it. There is no drift branch here and
    # that is deliberate: this adapter declares no shape the body must have, so
    # it has no shape to notice the loss of. An empty body is an empty document.
    return _page(descriptor, response.observed_at, records=(_record_for(response),))


def _refused(reason: str) -> NativePage:
    """A target this adapter will not read, refused without touching the network."""

    return _page(
        DESCRIPTOR,
        "",
        warnings=(reason,),
        outcome="refused",
        loss=(UNSELECTED_TARGET,),
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one selected document and return exactly one NativePage.

    The refusal happens here, ahead of the read, and that placement is the whole
    guarantee: a target naming no selection never becomes a request, so there is
    no url for anything downstream to be careless with and no call for an origin
    to answer.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    selection, value, refusal = selected_read(named)
    if refusal:
        return _refused(refusal)

    descriptor, parameter = PAGE_SELECTIONS[selection]

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(descriptor, response)

    return fetch_one_page(
        descriptor,
        carrier,
        params={parameter: value} if parameter else {},
        parse=parse,
        native_order=NATIVE_ORDER,
    )
