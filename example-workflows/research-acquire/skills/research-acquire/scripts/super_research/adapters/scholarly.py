"""K0 scholarly works over three origins: OpenAlex, Crossref, arXiv.

Measured, all three keyless and 200. ``api.openalex.org/works``
``?search=<q>&filter=from_publication_date:...,to_publication_date:...``
``&per-page=25`` answers ``{"meta": {...}, "results": [...]}``, empty the
same way — an empty list, never a missing key. A work: ``id`` (an
``https://openalex.org/W...`` locator, doubled as this module's
``canonical_locator``), ``display_name``, ``publication_date`` (a day, never
a time), ``cited_by_count``, ``type`` (the origin's own classification,
carried verbatim as ``canonical_content_kind``), ``authorships[].author.``
``display_name``, ``ids.doi``, ``primary_location.landing_page_url``.

``api.crossref.org/works?query=<q>&filter=from-pub-date:...,until-pub-date:``
``...&rows=20`` answers ``{"message": {"items": [...], ...}}``, empty the
same way. An item: ``DOI``, ``title`` (an array — ``title[0]`` is read),
``author[].given``/``.family`` (Crossref's own docs say ``family`` "may be
absent on some types", and measured rows confirm it), ``published.``
``date-parts`` — ``[[Y, M, D]]`` with the day sometimes omitted and the
month sometimes omitted too (``[[Y]]``) — ``is-referenced-by-``
``count``, ``URL``, ``container-title``, ``publisher``.

``export.arxiv.org/api/query?search_query=all:"<q>"[+AND+submittedDate:[``
``YYYYMMDDHHMM+TO+YYYYMMDDHHMM]]&start=0&max_results=10`` answers Atom XML,
a ``<feed>`` with zero or more ``<entry>``. An entry: ``id`` (a versioned
``http://arxiv.org/abs/`` address — measured as ``http``, never used as
``canonical_locator`` for that reason), ``title``, ``published`` (a full
``...Z`` instant, authoritative), repeated ``<author><name>``, ``summary``,
and two ``<link>``: ``rel="alternate" type="text/html"`` is the item's own
address, ``rel="related" type="application/pdf"`` its PDF. An unquoted
multi-word query reads as an OR of its words — measured live — so this
module always quotes the caller's argument as one phrase.

**Every origin bounds publication time at the origin, in its own grammar,
so ``WINDOW_REACH["scholarly"]`` declares ``True`` once.** A caller naming
one edge still narrows OpenAlex's and Crossref's filter to that one clause;
arXiv's range grammar takes two, so a missing edge is filled with a
measured sentinel — ``ARXIV_FAR_FUTURE``/``ARXIV_FAR_PAST`` — rather than
left unsent. The naive floor, year 1, answered 500 live; year 1900 and year
2100 both answered 200, so those are the measured sentinels, not the
calendar's own.

**The documented ``mailto`` etiquette is deliberately not sent**, on either
JSON origin: this package attaches no identity a route constant does not
spell, and a caller's email is not one.

**One adapter, three origins, one call each.** A caller names the operation
with a prefix; a bare query defaults to OpenAlex.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple, Sequence

from .. import schema, transport
from . import (
    AdapterDescriptor,
    AdapterRequest,
    NativePage,
    NativeRecord,
    build_native_page,
    fetch_one_page,
)
from html.parser import HTMLParser


# The kinds this module emits. OpenAlex's and Crossref's are the origin's own
# `type` string, verbatim — never a closed enum this module invents. arXiv
# publishes one thing and states no type field for it, so this module names
# what it is: a preprint.
ARXIV_KIND = "preprint"

# --- OpenAlex ---------------------------------------------------------

OA_ID_KEY = "id"
OA_DISPLAY_NAME_KEY = "display_name"
OA_TYPE_KEY = "type"
OA_PUBLICATION_DATE_KEY = "publication_date"
OA_CITED_BY_COUNT_KEY = "cited_by_count"
OA_AUTHORSHIPS_KEY = "authorships"
OA_AUTHOR_KEY = "author"
OA_IDS_KEY = "ids"
OA_DOI_KEY = "doi"
OA_PRIMARY_LOCATION_KEY = "primary_location"
OA_LANDING_PAGE_URL_KEY = "landing_page_url"

OA_DOI_ATTRIBUTE = "doi"
OA_LANDING_PAGE_URL_ATTRIBUTE = "landing_page_url"
OA_AUTHOR_ATTRIBUTE = "author"

OA_DATE_FORMAT = "%Y-%m-%d"

# What a work must state for its row to be complete, beyond the id every row
# is already required to carry to be identified at all.
OA_ROSTER_FIELDS = (OA_DISPLAY_NAME_KEY, OA_TYPE_KEY, OA_PUBLICATION_DATE_KEY)


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count an origin published as an exact number, or nothing at all.

    A bool is not a count, and a float — Crossref's own ``score`` among them —
    is never one either: only a json integer is.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _engagement(pairs: Sequence[Tuple[str, Any]]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def openalex_date_to_instant(date_str: Any) -> str:
    """OpenAlex's ``publication_date`` (a day) as the artifact's instant.

    OpenAlex never states a time of day, only a date, so the instant this
    returns is always midnight UTC of that date — this module's spelling of
    a day, the same convention `linkedin_jobs.route_day_to_utc_iso` uses. The
    caller attaches `date_precision_only` beside it; nothing here decides
    that on its own.
    """

    if not isinstance(date_str, str) or not date_str.strip():
        return ""
    try:
        moment = datetime.strptime(date_str.strip(), OA_DATE_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def _openalex_authors(work: Mapping[str, Any]) -> List[str]:
    """Every author's display name, in the order OpenAlex listed them."""

    names: List[str] = []
    authorships = work.get(OA_AUTHORSHIPS_KEY)
    for authorship in authorships if isinstance(authorships, list) else ():
        if not isinstance(authorship, Mapping):
            continue
        author = authorship.get(OA_AUTHOR_KEY)
        name = _text(author.get(OA_DISPLAY_NAME_KEY)) if isinstance(author, Mapping) else ""
        if name:
            names.append(name)
    return names


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    return tuple(key for key in keys if row.get(key) in (None, ""))


def openalex_record(position: int, work: Mapping[str, Any], standing_loss: Tuple[str, ...]) -> NativeRecord:
    """One OpenAlex work as the origin described it."""

    row = {
        OA_ID_KEY: _text(work.get(OA_ID_KEY)),
        OA_DISPLAY_NAME_KEY: _text(work.get(OA_DISPLAY_NAME_KEY)),
        OA_TYPE_KEY: _text(work.get(OA_TYPE_KEY)),
        OA_PUBLICATION_DATE_KEY: openalex_date_to_instant(work.get(OA_PUBLICATION_DATE_KEY)),
    }
    authors = _openalex_authors(work)
    named: List[Tuple[str, str]] = [(OA_AUTHOR_ATTRIBUTE, name) for name in authors]
    ids = work.get(OA_IDS_KEY)
    doi = _text(ids.get(OA_DOI_KEY)) if isinstance(ids, Mapping) else ""
    if doi:
        named.append((OA_DOI_ATTRIBUTE, doi))
    primary_location = work.get(OA_PRIMARY_LOCATION_KEY)
    landing_page_url = (
        _text(primary_location.get(OA_LANDING_PAGE_URL_KEY))
        if isinstance(primary_location, Mapping)
        else ""
    )
    if landing_page_url:
        named.append((OA_LANDING_PAGE_URL_ATTRIBUTE, landing_page_url))
    return NativeRecord(
        canonical_content_kind=row[OA_TYPE_KEY],
        canonical_locator=row[OA_ID_KEY],
        native_item_id=row[OA_ID_KEY],
        title=row[OA_DISPLAY_NAME_KEY],
        author=authors[0] if authors else "",
        published_at=row[OA_PUBLICATION_DATE_KEY],
        engagement=_engagement(((OA_CITED_BY_COUNT_KEY, work.get(OA_CITED_BY_COUNT_KEY)),)),
        attributes=tuple(named),
        native_position=position,
        # Standing, not conditional: every work this route will ever answer
        # states a date and never a time, the same reasoning
        # `linkedin_jobs.DESCRIPTOR.standing_loss` already carries.
        loss=standing_loss + (("field_omitted",) if _missing(row, OA_ROSTER_FIELDS) else ()),
    )


def openalex_records(
    rows: Sequence[Any], standing_loss: Tuple[str, ...]
) -> Tuple[List[NativeRecord], int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for work in rows:
        if not isinstance(work, Mapping) or not _text(work.get(OA_ID_KEY)):
            unidentified += 1
            continue
        records.append(openalex_record(len(records), work, standing_loss))
    return (records, unidentified)


# --- Crossref -----------------------------------------------------------

CR_DOI_KEY = "DOI"
CR_TYPE_KEY = "type"
CR_TITLE_KEY = "title"
CR_AUTHOR_KEY = "author"
CR_GIVEN_KEY = "given"
CR_FAMILY_KEY = "family"
CR_PUBLISHED_KEY = "published"
CR_DATE_PARTS_KEY = "date-parts"
CR_IS_REFERENCED_BY_COUNT_KEY = "is-referenced-by-count"
CR_URL_KEY = "URL"
CR_CONTAINER_TITLE_KEY = "container-title"
CR_PUBLISHER_KEY = "publisher"

# This module's own name for the one fact Crossref publishes that a
# `NativeRecord` field cannot hold without inventing a day: the exact
# date-parts array, joined by the character Crossref itself never uses in a
# component, for the record that carries no `published_at` because the
# origin gave no day. Carried rather than silently omitted.
CR_DATE_PARTS_ATTRIBUTE = "published_date_parts"
CR_CONTAINER_TITLE_ATTRIBUTE = "container-title"
CR_PUBLISHER_ATTRIBUTE = "publisher"

# A day present makes an instant; the day's own presence is what earns
# `date_precision_only` on that record; nothing here declares it standing,
# because the same route also answers month- and year-only dates a caller
# must not read as midnight of some invented day.
CR_ROSTER_FIELDS = (CR_TITLE_KEY, CR_TYPE_KEY)


def _crossref_author(authors: Any) -> str:
    """The first author's name, given and family together where both exist.

    Composition: ``"{given} {family}"`` when both are stated, the family
    alone when given is absent, the given alone when family is — Crossref's
    own docs note family "may be absent on some types" — and nothing at all
    when neither is. Never a fabricated surname.
    """

    if not isinstance(authors, list) or not authors:
        return ""
    first = authors[0]
    if not isinstance(first, Mapping):
        return ""
    given = _text(first.get(CR_GIVEN_KEY)).strip()
    family = _text(first.get(CR_FAMILY_KEY)).strip()
    if given and family:
        return given + " " + family
    return family or given


def crossref_date_parts_text(parts: Any) -> str:
    """The exact date-parts Crossref reported, joined verbatim, or nothing.

    ``-`` joins the components exactly as reported — never padded, never a
    day added: ``[2015, 4]`` becomes ``"2015-4"``, not ``"2015-04"`` and
    never ``"2015-04-01"``.
    """

    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list):
        return ""
    components = parts[0]
    if not components or not all(isinstance(part, int) and not isinstance(part, bool) for part in components):
        return ""
    return "-".join(str(part) for part in components)


def crossref_published(published: Any) -> Tuple[str, str, bool]:
    """This item's published-at instant, its raw date-parts text, and whether a day was stated.

    A day makes an instant — midnight UTC of that day, the same
    day-to-instant convention `openalex_date_to_instant` uses. A month or a
    year alone makes no instant at all: inventing a day would state a date
    Crossref never reported. Either way the exact date-parts ride in the
    third element the caller carries into `published_date_parts`.
    """

    date_parts = published.get(CR_DATE_PARTS_KEY) if isinstance(published, Mapping) else None
    text = crossref_date_parts_text(date_parts)
    if not text:
        return ("", "", False)
    components = date_parts[0]
    if len(components) < 3:
        return ("", text, False)
    try:
        moment = datetime(components[0], components[1], components[2], tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return ("", text, False)
    return (moment.strftime(RECORD_INSTANT_FORMAT), text, True)


def crossref_record(position: int, item: Mapping[str, Any]) -> NativeRecord:
    """One Crossref work as the origin described it."""

    titles = item.get(CR_TITLE_KEY)
    title = _text(titles[0]) if isinstance(titles, list) and titles else ""
    row = {
        CR_DOI_KEY: _text(item.get(CR_DOI_KEY)),
        CR_TITLE_KEY: title,
        CR_TYPE_KEY: _text(item.get(CR_TYPE_KEY)),
    }
    published_at, date_parts_text, day_stated = crossref_published(item.get(CR_PUBLISHED_KEY))
    named: List[Tuple[str, str]] = []
    if date_parts_text and not day_stated:
        named.append((CR_DATE_PARTS_ATTRIBUTE, date_parts_text))
    container = item.get(CR_CONTAINER_TITLE_KEY)
    if isinstance(container, list) and container and isinstance(container[0], str) and container[0]:
        named.append((CR_CONTAINER_TITLE_ATTRIBUTE, container[0]))
    publisher = _text(item.get(CR_PUBLISHER_KEY))
    if publisher:
        named.append((CR_PUBLISHER_ATTRIBUTE, publisher))
    missing = _missing(row, CR_ROSTER_FIELDS)
    if not date_parts_text:
        missing = missing + (CR_PUBLISHED_KEY,)
    return NativeRecord(
        canonical_content_kind=row[CR_TYPE_KEY],
        canonical_locator=_text(item.get(CR_URL_KEY)),
        native_item_id=row[CR_DOI_KEY],
        title=row[CR_TITLE_KEY],
        author=_crossref_author(item.get(CR_AUTHOR_KEY)),
        published_at=published_at,
        engagement=_engagement(((CR_IS_REFERENCED_BY_COUNT_KEY, item.get(CR_IS_REFERENCED_BY_COUNT_KEY)),)),
        attributes=tuple(named),
        native_position=position,
        loss=(
            (("date_precision_only",) if day_stated else ())
            + (("field_omitted",) if missing else ())
        ),
    )


def crossref_records(rows: Sequence[Any]) -> Tuple[List[NativeRecord], int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for item in rows:
        if not isinstance(item, Mapping) or not _text(item.get(CR_DOI_KEY)):
            unidentified += 1
            continue
        records.append(crossref_record(len(records), item))
    return (records, unidentified)


# --- arXiv ----------------------------------------------------------------

ATOM_ROOT_TAG = "feed"
ENTRY_TAG = "entry"
ID_TAG = "id"
TITLE_TAG = "title"
PUBLISHED_TAG = "published"
UPDATED_TAG = "updated"
SUMMARY_TAG = "summary"
AUTHOR_TAG = "author"
NAME_TAG = "name"
LINK_TAG = "link"

HREF_ATTRIBUTE = "href"
REL_ATTRIBUTE = "rel"
TYPE_ATTRIBUTE = "type"
ALTERNATE_REL = "alternate"
RELATED_REL = "related"
PDF_TYPE = "application/pdf"

ARXIV_AUTHOR_ATTRIBUTE = "author"
ARXIV_PDF_URL_ATTRIBUTE = "pdf_url"

ITEM_TEXT_TAGS = (ID_TAG, TITLE_TAG, PUBLISHED_TAG, UPDATED_TAG, SUMMARY_TAG, NAME_TAG)
ITEM_KEYS = ITEM_TEXT_TAGS + ("locator", "pdf_url")

ARXIV_ROSTER_FIELDS = (ID_TAG, TITLE_TAG, PUBLISHED_TAG, "locator")


class ArxivFeedParser(HTMLParser):
    """Collect this Atom document's root and the entries inside it.

    `html.parser` rather than an XML reader, the reason every markup-reading
    adapter in this package uses it: acquired text is untrusted and this
    parser expands no document-defined entity.
    """

    def __init__(self) -> None:
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = ""
        self.entries: List[Dict[str, Any]] = []
        self._in_entry = False
        self._in_author = False
        self._field = ""

    def handle_starttag(self, tag, attrs):
        if not self.root and tag == ATOM_ROOT_TAG:
            self.root = tag
            return
        if tag == ENTRY_TAG:
            entry: Dict[str, Any] = dict.fromkeys(ITEM_KEYS, "")
            entry["authors"] = []
            self.entries.append(entry)
            self._in_entry = True
            self._in_author = False
            self._field = ""
            return
        if not self._in_entry:
            return

        attributes = dict(attrs)
        entry = self.entries[-1]
        if tag == LINK_TAG:
            relation = attributes.get(REL_ATTRIBUTE) or ""
            href = attributes.get(HREF_ATTRIBUTE) or ""
            media_type = attributes.get(TYPE_ATTRIBUTE) or ""
            if relation == ALTERNATE_REL and href:
                entry["locator"] = entry["locator"] or href
            elif relation == RELATED_REL and media_type == PDF_TYPE and href:
                entry["pdf_url"] = entry["pdf_url"] or href
            return
        if tag == AUTHOR_TAG:
            self._in_author = True
            self._field = ""
            return
        if tag == NAME_TAG and self._in_author:
            self._field = NAME_TAG
            return
        if tag in ITEM_TEXT_TAGS:
            self._field = tag

    def handle_endtag(self, tag):
        if tag == ENTRY_TAG:
            self._in_entry = False
            self._in_author = False
            self._field = ""
        elif tag == AUTHOR_TAG:
            if self._in_author and self.entries:
                name = self.entries[-1][NAME_TAG].strip()
                if name:
                    self.entries[-1]["authors"].append(name)
                self.entries[-1][NAME_TAG] = ""
            self._in_author = False
            self._field = ""
        elif tag == self._field:
            self._field = ""

    def handle_data(self, data):
        if self._field and self._in_entry:
            self.entries[-1][self._field] += data


def arxiv_instant_to_utc_iso(stamped: str) -> str:
    """arXiv's own ``published``/``updated`` stamp as the artifact's instant.

    Measured: always a full instant with a trailing ``Z`` — never a bare
    date. A stamp in any other shape is a missing time rather than an
    approximated one.
    """

    text = stamped.strip()
    if not text:
        return ""
    try:
        moment = datetime.strptime(text, RECORD_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(RECORD_INSTANT_FORMAT)


def _arxiv_roster_row(entry: Dict[str, Any]) -> Dict[str, str]:
    return {
        ID_TAG: entry[ID_TAG].strip(),
        TITLE_TAG: " ".join(entry[TITLE_TAG].split()),
        PUBLISHED_TAG: arxiv_instant_to_utc_iso(entry[PUBLISHED_TAG]),
        "locator": entry["locator"].strip(),
    }


def arxiv_record(position: int, entry: Dict[str, Any]) -> NativeRecord:
    """One arXiv entry as the feed described it."""

    roster = _arxiv_roster_row(entry)
    authors = [name for name in entry["authors"] if name]
    named: List[Tuple[str, str]] = [(ARXIV_AUTHOR_ATTRIBUTE, name) for name in authors]
    pdf_url = entry["pdf_url"].strip()
    if pdf_url:
        named.append((ARXIV_PDF_URL_ATTRIBUTE, pdf_url))
    missing = tuple(name for name in ARXIV_ROSTER_FIELDS if not roster[name])
    return NativeRecord(
        canonical_content_kind=ARXIV_KIND,
        canonical_locator=roster["locator"],
        native_item_id=roster[ID_TAG],
        title=roster[TITLE_TAG],
        body=" ".join(entry[SUMMARY_TAG].split()),
        author=authors[0] if authors else "",
        published_at=roster[PUBLISHED_TAG],
        attributes=tuple(named),
        native_position=position,
        loss=("field_omitted",) if missing else (),
    )


def arxiv_records(entries: Sequence[Dict[str, Any]]) -> Tuple[List[NativeRecord], int]:
    records: List[NativeRecord] = []
    unidentified = 0
    for entry in entries:
        if not entry[ID_TAG].strip():
            unidentified += 1
            continue
        records.append(arxiv_record(len(records), entry))
    return (records, unidentified)


DATE_PRECISION_ONLY = "date_precision_only"

DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.OPENALEX_WORKS_ROUTE,
    platform="openalex",
    native_identity_namespace="openalex",
    representation_kind="native",
    operator_identity="openalex",
    # OpenAlex states a publication day and never a time of day, on every
    # work this route will ever answer — standing, the same reasoning
    # `linkedin_jobs.DESCRIPTOR.standing_loss` carries for its own route.
    standing_loss=(DATE_PRECISION_ONLY,),
    min_interval_ms=1000,
    burst=1,
    page_size=25,
)

CROSSREF_DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.CROSSREF_WORKS_ROUTE,
    platform="crossref",
    native_identity_namespace="crossref",
    representation_kind="native",
    operator_identity="crossref",
    min_interval_ms=1000,
    burst=1,
    page_size=20,
)

ARXIV_DESCRIPTOR = AdapterDescriptor(
    adapter_id="scholarly",
    adapter_version="1",
    access_class="K0",
    route_id=transport.ARXIV_QUERY_ROUTE,
    platform="arxiv",
    native_identity_namespace="arxiv",
    representation_kind="native",
    operator_identity="arxiv",
    # arXiv's own API terms ask for one request every three seconds.
    min_interval_ms=3000,
    burst=1,
    page_size=10,
)

SURFACE_DESCRIPTORS = (DESCRIPTOR, CROSSREF_DESCRIPTOR, ARXIV_DESCRIPTOR)

OPENALEX_OPERATION = "openalex"
CROSSREF_OPERATION = "crossref"
ARXIV_OPERATION = "arxiv"
SCHOLARLY_OPERATIONS = (OPENALEX_OPERATION, CROSSREF_OPERATION, ARXIV_OPERATION)

OPERATION_SURFACES = {
    OPENALEX_OPERATION: DESCRIPTOR,
    CROSSREF_OPERATION: CROSSREF_DESCRIPTOR,
    ARXIV_OPERATION: ARXIV_DESCRIPTOR,
}

NATIVE_ORDERS = {
    OPENALEX_OPERATION: "openalex_relevance_order",
    CROSSREF_OPERATION: "crossref_relevance_order",
    ARXIV_OPERATION: "arxiv_relevance_order",
}

# --- Request grammar --------------------------------------------------

RECORD_INSTANT_FORMAT = schema.INSTANT_FORMAT

OPENALEX_SEARCH_PARAM = "search"
OPENALEX_PER_PAGE_PARAM = "per-page"
OPENALEX_PER_PAGE_VALUE = "25"
OPENALEX_FILTER_PARAM = "filter"
OPENALEX_FROM_PUBLICATION_DATE_KEY = "from_publication_date"
OPENALEX_TO_PUBLICATION_DATE_KEY = "to_publication_date"
OPENALEX_RESULTS_KEY = "results"

CROSSREF_QUERY_PARAM = "query"
CROSSREF_ROWS_PARAM = "rows"
CROSSREF_ROWS_VALUE = "20"
CROSSREF_FILTER_PARAM = "filter"
CROSSREF_FROM_PUB_DATE_KEY = "from-pub-date"
CROSSREF_UNTIL_PUB_DATE_KEY = "until-pub-date"
CROSSREF_MESSAGE_KEY = "message"
CROSSREF_ITEMS_KEY = "items"

ARXIV_SEARCH_QUERY_PARAM = "search_query"
ARXIV_START_PARAM = "start"
ARXIV_START_VALUE = "0"
ARXIV_MAX_RESULTS_PARAM = "max_results"
ARXIV_MAX_RESULTS_VALUE = "10"
# Measured live: a range query needs both ends, so a missing edge
# is filled with a spelled sentinel rather than left unsent. Year 2100 and
# year 1900 both answered 200; year 1 (`000101010000`) answered 500, so 1900
# — decades before arXiv existed — is the measured floor, not the calendar's.
ARXIV_FAR_PAST = "190001010000"
ARXIV_FAR_FUTURE = "210001010000"
ARXIV_STAMP_FORMAT = "%Y%m%d%H%M"

SCHEMA_DRIFT = "schema_drift"
MALFORMED_JSON = "malformed_json"
HTTP_STATUS = "http_status"


def _parsed_instant(instant: str) -> Optional[datetime]:
    """One manifest instant parsed, or nothing a bound this module can send.

    A bound this cannot read is a bound not sent — the core's own window
    filter still holds on every row that comes back — rather than a bound
    sent wrong.
    """

    if not instant:
        return None
    try:
        return datetime.strptime(instant, RECORD_INSTANT_FORMAT)
    except ValueError:
        return None


def instant_to_date(instant: str) -> str:
    """One manifest instant as the day OpenAlex's and Crossref's filters take."""

    moment = _parsed_instant(instant)
    return moment.strftime("%Y-%m-%d") if moment else ""


def instant_to_arxiv_stamp(instant: str) -> str:
    """One manifest instant as the ``YYYYMMDDHHMM`` arXiv's range takes."""

    moment = _parsed_instant(instant)
    return moment.strftime(ARXIV_STAMP_FORMAT) if moment else ""


def openalex_filter(window_start: str, window_end: str) -> str:
    """OpenAlex's own ``filter=`` clause for this window, or nothing.

    Only the edges present are sent — an origin that takes independent
    bounds is narrowed by whichever ones the caller named, never invented on
    the caller's behalf.
    """

    clauses = []
    start = instant_to_date(window_start)
    if start:
        clauses.append(OPENALEX_FROM_PUBLICATION_DATE_KEY + ":" + start)
    end = instant_to_date(window_end)
    if end:
        clauses.append(OPENALEX_TO_PUBLICATION_DATE_KEY + ":" + end)
    return ",".join(clauses)


def crossref_filter(window_start: str, window_end: str) -> str:
    """Crossref's own ``filter=`` clause for this window, or nothing."""

    clauses = []
    start = instant_to_date(window_start)
    if start:
        clauses.append(CROSSREF_FROM_PUB_DATE_KEY + ":" + start)
    end = instant_to_date(window_end)
    if end:
        clauses.append(CROSSREF_UNTIL_PUB_DATE_KEY + ":" + end)
    return ",".join(clauses)


def arxiv_window_clause(window_start: str, window_end: str) -> str:
    """arXiv's own ``AND submittedDate:[... TO ...]`` clause, or nothing.

    arXiv's range grammar takes two ends; a caller naming only one still
    gets a genuinely narrowed read rather than an unsent bound, because the
    missing edge is filled with the measured sentinel rather than left out
    of a grammar that has no open-ended form.
    """

    start = instant_to_arxiv_stamp(window_start)
    end = instant_to_arxiv_stamp(window_end)
    if not start and not end:
        return ""
    return " AND submittedDate:[{0} TO {1}]".format(
        start or ARXIV_FAR_PAST, end or ARXIV_FAR_FUTURE
    )


def openalex_params(argument: str, window_start: str, window_end: str) -> Dict[str, str]:
    params = {
        OPENALEX_SEARCH_PARAM: argument,
        OPENALEX_PER_PAGE_PARAM: OPENALEX_PER_PAGE_VALUE,
    }
    clause = openalex_filter(window_start, window_end)
    if clause:
        params[OPENALEX_FILTER_PARAM] = clause
    return params


def crossref_params(argument: str, window_start: str, window_end: str) -> Dict[str, str]:
    params = {
        CROSSREF_QUERY_PARAM: argument,
        CROSSREF_ROWS_PARAM: CROSSREF_ROWS_VALUE,
    }
    clause = crossref_filter(window_start, window_end)
    if clause:
        params[CROSSREF_FILTER_PARAM] = clause
    return params


def arxiv_params(argument: str, window_start: str, window_end: str) -> Dict[str, str]:
    search_query = 'all:"{0}"{1}'.format(argument, arxiv_window_clause(window_start, window_end))
    return {
        ARXIV_SEARCH_QUERY_PARAM: search_query,
        ARXIV_START_PARAM: ARXIV_START_VALUE,
        ARXIV_MAX_RESULTS_PARAM: ARXIV_MAX_RESULTS_VALUE,
    }


def operation_for(request: AdapterRequest) -> Tuple[str, str]:
    """The operation this call performs, and the argument it performs it on.

    A caller names the operation with a prefix; absent one — or on an
    unrecognized prefix — a bare query defaults to OpenAlex, unchanged: a
    query that happens to contain a colon stays a query, the same rule
    `prediction_markets.operation_for` states for its own three origins.
    """

    named = request.target_ids[0] if request.target_ids else request.query
    kind, separator, argument = named.partition(":")
    if separator and kind in SCHOLARLY_OPERATIONS:
        return (kind, argument)
    return (OPENALEX_OPERATION, named)


# --- Response reading ---------------------------------------------------


def _answered(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    records: Tuple[NativeRecord, ...] = (),
    outcome: str = "ok",
    warnings: Tuple[str, ...] = (),
    loss: Tuple[str, ...] = (),
) -> NativePage:
    return build_native_page(
        descriptor,
        records,
        observed_at=response.observed_at,
        native_order=native_order,
        warnings=warnings,
        outcome=outcome,
        loss=loss,
    )


def _failed(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    loss: str,
    warning: str,
) -> NativePage:
    return _answered(
        descriptor, response, native_order, outcome="failed", warnings=(warning,), loss=(loss,)
    )


def _json_payload_of(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    operation: str,
) -> Tuple[Any, Optional[NativePage]]:
    """One JSON origin's answer, or the typed page that says why there is none."""

    if response.status != 200:
        return (
            None,
            _failed(
                descriptor,
                response,
                native_order,
                HTTP_STATUS,
                "http status {0} from {1}".format(response.status, descriptor.route_id),
            ),
        )
    try:
        return (json.loads(response.body), None)
    except ValueError:
        return (
            None,
            _failed(
                descriptor,
                response,
                native_order,
                MALFORMED_JSON,
                "{0} answered 200 with no json body".format(operation),
            ),
        )


def _resolved(
    descriptor: AdapterDescriptor,
    response: transport.TransportResponse,
    native_order: str,
    records: List[NativeRecord],
    row_count: int,
    unidentified: int,
    unidentified_message: str,
    drift_message: str,
    empty_message: str,
) -> NativePage:
    """The shared tail every origin's page assembly ends on, once rows are read.

    Three origins, one shape past this point: rows that named an id become
    records and a page reporting them, in the origin's own count, unless not
    one of them named an id — the payload reshaping, not a search with
    nothing in it — and no rows at all is a query or scope that matched
    nothing. Each origin supplies its own wording because the noun
    (work/item/entry) and the identifying field (id/DOI/id) are its own.
    """

    if records:
        warnings = (unidentified_message,) if unidentified else ()
        return _answered(descriptor, response, native_order, records=tuple(records), warnings=warnings)
    if row_count:
        return _failed(descriptor, response, native_order, SCHEMA_DRIFT, drift_message)
    return _answered(descriptor, response, native_order, outcome="empty", warnings=(empty_message,))


def _openalex_page(response: transport.TransportResponse, argument: str) -> NativePage:
    native_order = NATIVE_ORDERS[OPENALEX_OPERATION]
    payload, refused = _json_payload_of(DESCRIPTOR, response, native_order, OPENALEX_OPERATION)
    if refused is not None:
        return refused
    rows = payload.get(OPENALEX_RESULTS_KEY) if isinstance(payload, Mapping) else None
    if not isinstance(rows, list):
        return _failed(
            DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1} list: the payload this adapter reads has"
            " changed shape".format(OPENALEX_OPERATION, OPENALEX_RESULTS_KEY),
        )
    records, unidentified = openalex_records(rows, DESCRIPTOR.standing_loss)
    return _resolved(
        DESCRIPTOR,
        response,
        native_order,
        records,
        len(rows),
        unidentified,
        "{0} answered 200 with {1} work(s) naming no id: they are not rows this"
        " adapter can identify".format(OPENALEX_OPERATION, unidentified),
        "{0} answered 200 with {1} work(s) and no id on any of them: the payload"
        " has changed shape".format(OPENALEX_OPERATION, len(rows)),
        "{0} answered 200 with an empty {1} list: nothing matched {2!r}".format(
            OPENALEX_OPERATION, OPENALEX_RESULTS_KEY, argument
        ),
    )


def _crossref_rows(payload: Any) -> Optional[List[Any]]:
    message = payload.get(CROSSREF_MESSAGE_KEY) if isinstance(payload, Mapping) else None
    items = message.get(CROSSREF_ITEMS_KEY) if isinstance(message, Mapping) else None
    return items if isinstance(items, list) else None


def _crossref_page(response: transport.TransportResponse, argument: str) -> NativePage:
    native_order = NATIVE_ORDERS[CROSSREF_OPERATION]
    payload, refused = _json_payload_of(
        CROSSREF_DESCRIPTOR, response, native_order, CROSSREF_OPERATION
    )
    if refused is not None:
        return refused
    rows = _crossref_rows(payload)
    if rows is None:
        return _failed(
            CROSSREF_DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "{0} answered 200 with no {1}.{2} list: the payload this adapter reads"
            " has changed shape".format(CROSSREF_OPERATION, CROSSREF_MESSAGE_KEY, CROSSREF_ITEMS_KEY),
        )
    records, unidentified = crossref_records(rows)
    return _resolved(
        CROSSREF_DESCRIPTOR,
        response,
        native_order,
        records,
        len(rows),
        unidentified,
        "{0} answered 200 with {1} item(s) naming no DOI: they are not rows this"
        " adapter can identify".format(CROSSREF_OPERATION, unidentified),
        "{0} answered 200 with {1} item(s) and no DOI on any of them: the payload"
        " has changed shape".format(CROSSREF_OPERATION, len(rows)),
        "{0} answered 200 with an empty {1} list: nothing matched {2!r}".format(
            CROSSREF_OPERATION, CROSSREF_ITEMS_KEY, argument
        ),
    )


def _arxiv_page(response: transport.TransportResponse, argument: str) -> NativePage:
    native_order = NATIVE_ORDERS[ARXIV_OPERATION]
    if response.status != 200:
        return _failed(
            ARXIV_DESCRIPTOR,
            response,
            native_order,
            HTTP_STATUS,
            "http status {0} from {1}".format(response.status, ARXIV_DESCRIPTOR.route_id),
        )

    parser = ArxivFeedParser()
    parser.feed(response.body)
    parser.close()

    if not parser.root:
        return _failed(
            ARXIV_DESCRIPTOR,
            response,
            native_order,
            SCHEMA_DRIFT,
            "route {0} answered 200 with a document not rooted in <feed>: it is not"
            " an Atom feed this adapter can read".format(ARXIV_DESCRIPTOR.route_id),
        )

    records, unidentified = arxiv_records(parser.entries)
    return _resolved(
        ARXIV_DESCRIPTOR,
        response,
        native_order,
        records,
        len(parser.entries),
        unidentified,
        "{0} answered 200 with {1} entry(ies) naming no id: they are not rows"
        " this adapter can identify".format(ARXIV_OPERATION, unidentified),
        "{0} answered 200 with {1} entry(ies) and no id on any of them: the"
        " payload has changed shape".format(ARXIV_OPERATION, len(parser.entries)),
        "{0} answered 200 with a <feed> holding no <entry>: nothing matched"
        " {1!r}".format(ARXIV_OPERATION, argument),
    )


def fetch_native_page(carrier: transport.Transport, request: AdapterRequest) -> NativePage:
    """Read one of the three declared operations and return exactly one NativePage.

    One call on one route: which route is the operation's own, declared in
    ``OPERATION_SURFACES``, and the three are paced apart because they are
    three origins.
    """

    operation, argument = operation_for(request)
    descriptor = OPERATION_SURFACES[operation]

    if operation == OPENALEX_OPERATION:
        params = openalex_params(argument, request.window_start, request.window_end)

        def parse(response: transport.TransportResponse) -> NativePage:
            return _openalex_page(response, argument)

    elif operation == CROSSREF_OPERATION:
        params = crossref_params(argument, request.window_start, request.window_end)

        def parse(response: transport.TransportResponse) -> NativePage:
            return _crossref_page(response, argument)

    else:
        params = arxiv_params(argument, request.window_start, request.window_end)

        def parse(response: transport.TransportResponse) -> NativePage:
            return _arxiv_page(response, argument)

    return fetch_one_page(
        descriptor,
        carrier,
        params=params,
        parse=parse,
        native_order=NATIVE_ORDERS[operation],
    )
