"""K2 LinkedIn public profiles from the structured data the page embeds.

Measured 2026-08-10 (findings.md §1, "LinkedIn"): ``linkedin.com/in/<slug>``
answered 200 in 1.3 s with 577 KB carrying a **complete** ``ld+json`` Person
block — ``name``, ``jobTitle[]``, ``addressLocality``, ``description``,
``worksFor[]`` and ``alumniOf[]``. That is the largest single divergence from
the superseded spec, which placed this whole platform outside the roster on an
assumed 999 authwall.

So the one thing this module must not do is read an authwall. The measured
page carries "Sign in to" and "Join now" above the block and below it: they
are navigation chrome, the block is fully populated beside them, and an
adapter that branched on those strings would re-create the exact false
negative the measurement overturned. The only thing here that may make this
route a refusal is the origin's own status line.

The counterweight is that a ``K2`` route reads a shape the vendor may rewrite
without notice. A page that embeds no block, or a block that no longer holds a
Person, is ``schema_drift`` — naming what was looked for — and never an empty
profile, which is what a parser that went hunting for a familiar-looking name
would eventually report.

This module reads ``linkedin.com/in/<slug>`` and only that.
``linkedin.com/company/<slug>`` is a different path and would be a different
route; findings.md records a marker name for it and no field set, so a company
parser would be inferred rather than read.
"""

from __future__ import annotations

import json
from html.parser import HTMLParser
from typing import Any, List, Mapping, Sequence, Tuple

from .. import transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)

DESCRIPTOR = AdapterDescriptor(
    adapter_id="linkedin_public",
    adapter_version="1",
    access_class="K2",
    route_id=transport.LINKEDIN_PUBLIC_PROFILE_ROUTE,
    platform="linkedin",
    native_identity_namespace="linkedin",
    representation_kind="native",
    operator_identity="linkedin",
    # findings.md §1: 1.3 s per request. Nothing on this route was measured
    # refusing, so `burst` and `cooldown_ms` keep the protocol's conservative
    # defaults rather than a ceiling nobody observed.
    min_interval_ms=1300,
    # A public profile block reports no count of any kind, so neither metric is
    # declared. A name is never inferred: with `comment_count_metric` unset, a
    # snapshot named `comment_count` would be a missing comment count.
)

NATIVE_ORDER = "linkedin_profile_block_order"
CONTENT_KIND = "profile"

# The two strings the superseded spec's authwall assumption rested on. They are
# named here, once, so this module states that it has seen them and does not
# read them, and they appear nowhere else in this file — no branch, no filter,
# no warning. Declaring them is what makes that absence checkable from outside
# and what lets the suite prove the measured fixture really carries the chrome,
# so the claim is about a page that has it rather than one that quietly does
# not.
NAVIGATION_CHROME = ("sign in to", "join now")

# Where this page keeps its structured data, and which node of it is this
# route's answer. Declared, never searched for: the Person is found by
# schema.org's own @type, so a page whose graph moved says so instead of
# handing back whichever node happened to carry a `name`.
LD_JSON_SCRIPT_TYPE = "application/ld+json"
GRAPH_KEY = "@graph"
NODE_TYPE_KEY = "@type"
PERSON_TYPE = "Person"

# Every field findings.md §1 records this block carrying, under the block's own
# keys. A record missing one says so.
NAME_KEY = "name"
JOB_TITLE_KEY = "jobTitle"
ADDRESS_KEY = "address"
ADDRESS_LOCALITY_KEY = "addressLocality"
DESCRIPTION_KEY = "description"
WORKS_FOR_KEY = "worksFor"
ALUMNI_OF_KEY = "alumniOf"
URL_KEY = "url"
ROSTER_FIELDS = (
    NAME_KEY,
    JOB_TITLE_KEY,
    ADDRESS_LOCALITY_KEY,
    DESCRIPTION_KEY,
    WORKS_FOR_KEY,
    ALUMNI_OF_KEY,
)

# The four roster fields no other record field means. They travel under these
# exact names; `name` is the record's title and `description` is its body.
NAMED_LIST_FIELDS = (JOB_TITLE_KEY, WORKS_FOR_KEY, ALUMNI_OF_KEY)

# The statuses that separate the origin refusing from the page changing.
AUTHORIZATION_STATUSES = (401, 403)
AUTH_REQUIRED = "auth_required"


class _LdJsonParser(HTMLParser):
    """Collect every ld+json script this page embeds, in document order."""

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.blocks: List[str] = []
        self._capturing = False

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == LD_JSON_SCRIPT_TYPE:
            self.blocks.append("")
            self._capturing = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._capturing = False

    def handle_data(self, data):
        if self._capturing and self.blocks:
            self.blocks[-1] += data


def embedded_blocks(body: str) -> Tuple[str, ...]:
    """Every ``application/ld+json`` payload the page embeds, in document order."""

    parser = _LdJsonParser()
    parser.feed(body)
    parser.close()
    return tuple(block for block in parser.blocks if block.strip())


def graph_nodes(payload: Any) -> Tuple[Any, ...]:
    """One block's top-level nodes: its ``@graph``, or the block itself.

    Only the top level. A ``Person`` nested inside another node is that node's
    property — a page's ``reviewedBy``, say — and is not this route's answer.
    """

    if isinstance(payload, Mapping):
        graph = payload.get(GRAPH_KEY)
        return tuple(graph) if isinstance(graph, list) else (payload,)
    return tuple(payload) if isinstance(payload, list) else ()


def person_in(nodes: Sequence[Any]) -> Any:
    """The first node declaring itself a Person, or None when there is none."""

    for node in nodes:
        if isinstance(node, Mapping) and node.get(NODE_TYPE_KEY) == PERSON_TYPE:
            return node
    return None


def _text(value: Any) -> str:
    """One value the block reported, as a string, or nothing."""

    return value.strip() if isinstance(value, str) else ""


def _named_values(person: Mapping[str, Any], key: str) -> Tuple[str, ...]:
    """One repeated field's values, in the order the block listed them.

    The block writes a single value either as a bare string or as a list of
    one, and an entry is either a string or an object with a ``name``. Both
    shapes are the origin's; neither is flattened into the other, and nothing
    else is admitted.
    """

    reported = person.get(key)
    entries = reported if isinstance(reported, list) else (reported,)
    found = []
    for entry in entries:
        if isinstance(entry, Mapping):
            entry = entry.get(NAME_KEY)
        text = _text(entry)
        if text:
            found.append(text)
    return tuple(found)


def address_locality(person: Mapping[str, Any]) -> str:
    """The block's own locality, from the address node that declares it."""

    address = person.get(ADDRESS_KEY)
    if not isinstance(address, Mapping):
        return ""
    return _text(address.get(ADDRESS_LOCALITY_KEY))


def roster_row_of(person: Mapping[str, Any]) -> Mapping[str, Any]:
    """The whole roster row as the block reported it, under the block's names."""

    row = {
        NAME_KEY: _text(person.get(NAME_KEY)),
        ADDRESS_LOCALITY_KEY: address_locality(person),
        DESCRIPTION_KEY: _text(person.get(DESCRIPTION_KEY)),
    }
    for key in NAMED_LIST_FIELDS:
        row[key] = _named_values(person, key)
    return row


def _attributes_of(row: Mapping[str, Any]) -> Tuple[Tuple[str, str], ...]:
    """The four roster fields no other record field means, under their own names."""

    carried = []
    for key in NAMED_LIST_FIELDS:
        carried.extend((key, value) for value in row[key])
    if row[ADDRESS_LOCALITY_KEY]:
        carried.append((ADDRESS_LOCALITY_KEY, row[ADDRESS_LOCALITY_KEY]))
    return tuple(carried)


def _record_for(slug: str, person: Mapping[str, Any]) -> NativeRecord:
    row = roster_row_of(person)
    missing = tuple(key for key in ROSTER_FIELDS if not row[key])
    return NativeRecord(
        canonical_content_kind=CONTENT_KIND,
        # The address the block itself published. Taken from there and not
        # composed here, because a route's host belongs to `transport.py`.
        canonical_locator=_text(person.get(URL_KEY)),
        # The slug this run read: the route's own path segment, and LinkedIn's
        # own public name for a member.
        native_item_id=slug,
        title=row[NAME_KEY],
        body=row[DESCRIPTION_KEY],
        author=slug,
        # A public profile page states no publication time, so this record
        # states none rather than borrowing the moment it was read.
        attributes=_attributes_of(row),
        native_position=0,
        loss=("field_omitted",) if missing else (),
    )


def _failed(
    response: transport.TransportResponse, loss: str, warning: str
) -> NativePage:
    return build_native_page(
        DESCRIPTOR,
        (),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        warnings=(warning,),
        outcome="failed",
        loss=(loss,),
    )


def _page_from(response: transport.TransportResponse, slug: str) -> NativePage:
    """Turn one response the origin itself sent into exactly one page."""

    if response.status in AUTHORIZATION_STATUSES:
        # The one lawful way this adapter says `auth_required`: the origin said
        # so. It is never read off a string in the page, which is the whole
        # difference between this branch and the assumed authwall.
        return _failed(
            response,
            AUTH_REQUIRED,
            "route {0} answered {1}: the origin refused this read".format(
                DESCRIPTOR.route_id, response.status
            ),
        )
    if response.status != 200:
        return _failed(
            response,
            "http_status",
            "http status {0} from {1}".format(response.status, DESCRIPTOR.route_id),
        )

    blocks = embedded_blocks(response.body)
    if not blocks:
        return _failed(
            response,
            "schema_drift",
            "route {0} answered 200 and embedded no {1} block: the page this"
            " adapter reads has changed shape".format(
                DESCRIPTOR.route_id, LD_JSON_SCRIPT_TYPE
            ),
        )

    nodes = []
    for block in blocks:
        try:
            payload = json.loads(block)
        except ValueError:
            return _failed(
                response,
                "malformed_json",
                "route {0} answered 200 with a {1} block that is not json".format(
                    DESCRIPTOR.route_id, LD_JSON_SCRIPT_TYPE
                ),
            )
        nodes.extend(graph_nodes(payload))

    person = person_in(nodes)
    if person is None:
        return _failed(
            response,
            "schema_drift",
            "route {0} answered 200 with {1} block(s) holding no top-level node"
            ' of {2} "{3}": the page this adapter reads has changed shape'.format(
                DESCRIPTOR.route_id, len(blocks), NODE_TYPE_KEY, PERSON_TYPE
            ),
        )

    return build_native_page(
        DESCRIPTOR,
        (_record_for(slug, person),),
        observed_at=response.observed_at,
        native_order=NATIVE_ORDER,
        outcome="ok",
    )


def slug_of(request: AdapterRequest) -> str:
    """The profile this route reads, in the one form its path takes.

    A hydration step names it in ``target_ids``; a discovery step names it in
    ``query``. LinkedIn's vanity slug is the whole path segment, so nothing is
    stripped from it.
    """

    return request.target_ids[0] if request.target_ids else request.query


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one public profile page and return exactly one NativePage."""

    slug = slug_of(request)

    def parse(response: transport.TransportResponse) -> NativePage:
        return _page_from(response, slug)

    return fetch_one_page(
        DESCRIPTOR,
        carrier,
        params={"slug": slug},
        parse=parse,
        native_order=NATIVE_ORDER,
    )
