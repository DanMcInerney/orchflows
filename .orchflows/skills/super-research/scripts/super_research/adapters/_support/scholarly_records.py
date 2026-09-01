"""Field vocabulary, date grammar and record construction for `scholarly`.

Three origins, three payload vocabularies, one shared law: nothing here is
inferred, aliased across origins, or parsed further than the origin itself
stated it. A key spelled with a hyphen (``is-referenced-by-count``,
``container-title``) travels under that exact spelling, because it is
Crossref's own name and not this module's.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .. import NativeRecord

RECORD_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

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
# origin gave no day. Documented rather than silently omitted — see
# `references/route-notes/scholarly.md` "Crossref month precision".
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
