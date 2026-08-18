"""Record extraction for GitHub REST repository-shaped responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from .. import NativeRecord


ID_KEY = "id"
FULL_NAME_KEY = "full_name"
HTML_URL_KEY = "html_url"
DESCRIPTION_KEY = "description"
OWNER_KEY = "owner"
USER_KEY = "user"
AUTHOR_KEY = "author"
LOGIN_KEY = "login"
CREATED_AT_KEY = "created_at"
PUBLISHED_AT_KEY = "published_at"
TITLE_KEY = "title"
BODY_KEY = "body"
NAME_KEY = "name"
NUMBER_KEY = "number"
STATE_KEY = "state"
TAG_NAME_KEY = "tag_name"
LANGUAGE_KEY = "language"
TOPICS_KEY = "topics"
REPOSITORY_URL_KEY = "repository_url"

STARS_METRIC = "stargazers_count"
FORKS_METRIC = "forks_count"
OPEN_ISSUES_METRIC = "open_issues_count"
COMMENTS_METRIC = "comments"

REPOSITORY_KIND = "repository"
ISSUE_KIND = "issue"
RELEASE_KIND = "release"

# What each kind of row promises, so a record short of it says so. The evidence
# records that these routes answer and what they cost, not a field list, so
# these are this adapter's own declaration.
REPOSITORY_ROW_KEYS = (ID_KEY, FULL_NAME_KEY, HTML_URL_KEY, OWNER_KEY, CREATED_AT_KEY)
ISSUE_ROW_KEYS = (ID_KEY, TITLE_KEY, USER_KEY, CREATED_AT_KEY, HTML_URL_KEY)
RELEASE_ROW_KEYS = (ID_KEY, TAG_NAME_KEY, AUTHOR_KEY, PUBLISHED_AT_KEY, HTML_URL_KEY)

ROUTE_INSTANT_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def exact_count(value: Any) -> Optional[int]:
    """One count GitHub published as an exact number, or nothing."""

    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def id_text(value: Any) -> str:
    """One GitHub id as its decimal spelling, which is the form a record holds."""

    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    return value if isinstance(value, str) else ""


def login_of(payload: Mapping[str, Any], key: str) -> str:
    """The account one nested party names itself by, or nothing."""

    party = payload.get(key)
    return _text(party.get(LOGIN_KEY)) if isinstance(party, Mapping) else ""


def route_instant_to_utc_iso(stamped: Any) -> str:
    """GitHub's stamp as the artifact's instant, or nothing.

    GitHub writes ISO-8601 UTC with a trailing ``Z`` and no fraction, which is
    the artifact's own form. Anything else is a missing time rather than an
    approximated one.
    """

    if not isinstance(stamped, str) or not stamped.strip():
        return ""
    try:
        moment = datetime.strptime(stamped.strip(), ROUTE_INSTANT_FORMAT)
    except ValueError:
        return ""
    return moment.replace(tzinfo=timezone.utc).strftime(ROUTE_INSTANT_FORMAT)


def _missing(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    """Which of this row's declared fields the payload did not report.

    Absence, never falsehood: a repository nobody has starred reports zero
    stars, and zero is a count.
    """

    return tuple(key for key in keys if row.get(key) is None or row.get(key) == "")


def _engagement(pairs: Sequence[Tuple[str, Any]]) -> Tuple[Tuple[str, int], ...]:
    counted = []
    for name, value in pairs:
        exact = exact_count(value)
        if exact is not None:
            counted.append((name, exact))
    return tuple(counted)


def repository_record(
    position: int, payload: Mapping[str, Any], missing_loss: str
) -> NativeRecord:
    """One repository as GitHub described it, read or found."""

    owner = login_of(payload, OWNER_KEY)
    row = {
        ID_KEY: id_text(payload.get(ID_KEY)),
        FULL_NAME_KEY: _text(payload.get(FULL_NAME_KEY)),
        HTML_URL_KEY: _text(payload.get(HTML_URL_KEY)),
        OWNER_KEY: owner,
        CREATED_AT_KEY: route_instant_to_utc_iso(payload.get(CREATED_AT_KEY)),
    }
    named: List[Tuple[str, str]] = []
    language = _text(payload.get(LANGUAGE_KEY))
    if language:
        named.append((LANGUAGE_KEY, language))
    topics = payload.get(TOPICS_KEY)
    for topic in topics if isinstance(topics, list) else ():
        # A repository's own labels for itself, in its own order, each carried
        # as the exact string GitHub published.
        if _text(topic):
            named.append((TOPICS_KEY, topic))
    return NativeRecord(
        canonical_content_kind=REPOSITORY_KIND,
        # The address GitHub published for it, absolute and carried as
        # published: this origin states an item's own address, so nothing here
        # is composed from a host.
        canonical_locator=row[HTML_URL_KEY],
        native_item_id=row[ID_KEY],
        # The repository's full name is what identifies it to a person, and its
        # numeric id is what identifies it to GitHub. The title is the first
        # and the identity is the second.
        title=row[FULL_NAME_KEY],
        body=_text(payload.get(DESCRIPTION_KEY)),
        author=owner,
        published_at=row[CREATED_AT_KEY],
        engagement=_engagement(
            (
                (STARS_METRIC, payload.get(STARS_METRIC)),
                (FORKS_METRIC, payload.get(FORKS_METRIC)),
                (OPEN_ISSUES_METRIC, payload.get(OPEN_ISSUES_METRIC)),
            )
        ),
        attributes=tuple(named),
        native_position=position,
        loss=(missing_loss,) if _missing(row, REPOSITORY_ROW_KEYS) else (),
    )


def issue_record(
    position: int, payload: Mapping[str, Any], missing_loss: str
) -> NativeRecord:
    """One issue as the repository listed it."""

    row = {
        ID_KEY: id_text(payload.get(ID_KEY)),
        TITLE_KEY: _text(payload.get(TITLE_KEY)),
        USER_KEY: login_of(payload, USER_KEY),
        CREATED_AT_KEY: route_instant_to_utc_iso(payload.get(CREATED_AT_KEY)),
        HTML_URL_KEY: _text(payload.get(HTML_URL_KEY)),
    }
    named: List[Tuple[str, str]] = []
    number = id_text(payload.get(NUMBER_KEY))
    if number:
        # The number a person cites an issue by, which is not the id GitHub
        # identifies it by: two repositories both have an issue 1.
        named.append((NUMBER_KEY, number))
    state = _text(payload.get(STATE_KEY))
    if state:
        named.append((STATE_KEY, state))
    repository_url = _text(payload.get(REPOSITORY_URL_KEY))
    if repository_url:
        # How this route names the repository an issue belongs to: an address,
        # never the numeric id a repository record is identified by. Carried
        # verbatim so a caller can tie the two, because recovering an id by
        # taking a url apart would be this adapter inventing an identity.
        named.append((REPOSITORY_URL_KEY, repository_url))
    return NativeRecord(
        canonical_content_kind=ISSUE_KIND,
        canonical_locator=row[HTML_URL_KEY],
        native_item_id=row[ID_KEY],
        # Left unstated for the reason above: this payload states no id for the
        # repository, and `native_parent_id` holds an id or nothing.
        native_parent_id="",
        title=row[TITLE_KEY],
        body=_text(payload.get(BODY_KEY)),
        author=row[USER_KEY],
        published_at=row[CREATED_AT_KEY],
        engagement=_engagement(((COMMENTS_METRIC, payload.get(COMMENTS_METRIC)),)),
        attributes=tuple(named),
        native_position=position,
        loss=(missing_loss,) if _missing(row, ISSUE_ROW_KEYS) else (),
    )


def release_record(
    position: int, payload: Mapping[str, Any], missing_loss: str
) -> NativeRecord:
    """One release as the repository listed it."""

    row = {
        ID_KEY: id_text(payload.get(ID_KEY)),
        TAG_NAME_KEY: _text(payload.get(TAG_NAME_KEY)),
        AUTHOR_KEY: login_of(payload, AUTHOR_KEY),
        PUBLISHED_AT_KEY: route_instant_to_utc_iso(payload.get(PUBLISHED_AT_KEY)),
        HTML_URL_KEY: _text(payload.get(HTML_URL_KEY)),
    }
    named = ((TAG_NAME_KEY, row[TAG_NAME_KEY]),) if row[TAG_NAME_KEY] else ()
    return NativeRecord(
        canonical_content_kind=RELEASE_KIND,
        canonical_locator=row[HTML_URL_KEY],
        native_item_id=row[ID_KEY],
        # A release payload states no id for its repository either, and unlike
        # an issue it states no address for one, so there is nothing to carry.
        native_parent_id="",
        # A release names itself and falls back to its tag, which is what
        # GitHub shows when a release was published without a name.
        title=_text(payload.get(NAME_KEY)) or row[TAG_NAME_KEY],
        body=_text(payload.get(BODY_KEY)),
        author=row[AUTHOR_KEY],
        # When it was published, not when its commit was made: a release exists
        # for a reader at the moment it is published.
        published_at=row[PUBLISHED_AT_KEY],
        attributes=named,
        native_position=position,
        loss=(missing_loss,) if _missing(row, RELEASE_ROW_KEYS) else (),
    )
