"""Relevance seam: an auditable topical match over acquired records.

The bakeoff of 2026-08-17 measured what a caller does without this module:
it hand-writes lexical rules, and a bare alternation like ``valuation|share``
matches ``e-valuation`` and the verb ``share`` in threads about USB cables and
LoRa radios, at a rate indistinguishable from signal. The competing tool's
answer is a relevance floor that silently dropped 376 posts across four
queries with no record of which or why. This module is the auditable
counterpart: one query compiled once, one score per record with the terms and
phrases that earned it and the field each was found in, and a partition that
lists every record it would drop beside every one it keeps. Nothing here
drops a record on its own — a caller reads the audit and decides.

**What a match is.** Text is normalized (NFKC, casefolded) and split at every
character that is not a letter or a digit, so a term matches whole tokens
only — ``share`` never matches inside ``shareholder``, and ``valuation`` never
inside ``e-valuation``'s neighbour ``evaluation``. Tokens are reduced by one
conservative stemmer that strips only plural and inflection endings, so
``shares`` and ``share`` meet and ``valuation`` and ``evaluation`` do not. A
quoted segment of the query is a phrase, matched as a whole-token sequence in
order. Stopwords are dropped from the query's terms and never from a phrase.

**What a score is.** Term coverage — the share of the query's terms found —
weighted three to one against phrase coverage, in ``[0, 1]``; the exact
formula is :func:`score_text` and it is deterministic. A score ranks; it never
weights by engagement, never reads a parent's counts onto a child, and never
crosses platforms, because none of those is a fact about whether a record is
on topic.

Reliability bar: pure. Nothing here reaches a clock, a socket, or a file, and
every result carries the evidence for itself.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from . import schema

# The fields a record is read on when the caller names none: what the origin
# called the thing and what it said. `author` and `community` are deliberately
# not defaulted — a subreddit named after the topic is not a post about it —
# and a caller who wants them names them.
DEFAULT_FIELDS = ("title", "body")

# The weight of term coverage against phrase coverage in a score. Three to
# one, and written once so the number in a report and the number in the code
# are the same number.
TERM_WEIGHT = 0.75
PHRASE_WEIGHT = 0.25

# English function words dropped from a query's terms. Small on purpose: a
# stopword list is a claim about what carries no topic, and every entry here
# is a word no sentiment question is about. A phrase keeps its stopwords,
# because "the top" and "top" are different phrases.
STOPWORDS = frozenset(
    (
        "a an and are as at be but by for from has have if in into is it its "
        "of on or that the their there these they this to was were will with "
        "what which who whom why how do does did not no so than then too very "
        "can could should would may might must shall about after before over "
        "under up down out off"
    ).split()
)

# The endings the stemmer strips, in two passes — plural first, then
# inflection — each with the least the stem may be left with. That order is
# what makes `earnings` and `earning` meet at `earn`: one pass would leave the
# first at `earning`. Plurals and inflections only, and `ss` is never a
# plural: enough that `shares` meets `share` and `falling` meets `fall`, and
# no more, because a stemmer that reached for derivations is how `valuation`
# and `evaluation` would meet.
_PLURAL_SUFFIXES = (
    ("sses", 2, "ss"),
    ("ies", 2, "y"),
    ("s", 3, ""),
)
_INFLECTION_SUFFIXES = (
    ("ing", 4, ""),
    ("ed", 3, ""),
)


@dataclass(frozen=True)
class RelevanceQuery:
    """One compiled query: the terms it asks for and the phrases it quotes.

    ``terms`` are stems, deduplicated in first-seen order; ``phrases`` are
    token sequences, each from one quoted segment of the query text. A query
    that compiles to neither matches nothing, and :func:`compile_query` says
    so by raising rather than by scoring everything zero.
    """

    text: str
    terms: Tuple[str, ...]
    phrases: Tuple[Tuple[str, ...], ...]


@dataclass(frozen=True)
class RelevanceMatch:
    """One record's score, and the evidence that produced it.

    ``matched_terms`` and ``matched_phrases`` are what was found;
    ``fields`` names, per matched term, the record field it was found in
    (the first field in the caller's order). ``score`` is in ``[0, 1]``.
    """

    record_id: str
    score: float
    matched_terms: Tuple[str, ...]
    matched_phrases: Tuple[Tuple[str, ...], ...]
    fields: Tuple[Tuple[str, str], ...]


class RelevanceError(ValueError):
    """A query this module cannot turn into a match."""


def _strip(token: str, rules: Sequence[Tuple[str, int, str]]) -> str:
    for suffix, least, replacement in rules:
        if token.endswith(suffix) and len(token) - len(suffix) >= least:
            if suffix == "s" and token.endswith("ss"):
                return token
            return token[: -len(suffix)] + replacement
    return token


def stem(token: str) -> str:
    """One token's stem under the conservative rule set above: plural, then inflection."""

    return _strip(_strip(token, _PLURAL_SUFFIXES), _INFLECTION_SUFFIXES)


def tokenize(text: str) -> Tuple[str, ...]:
    """Whole tokens of one text: NFKC, casefolded, split at every non-alphanumeric.

    Every token is a run of letters and digits and nothing else, which is
    what makes a term match a word rather than a substring.
    """

    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens: List[str] = []
    held: List[str] = []
    for character in normalized:
        if character.isalnum():
            held.append(character)
        elif held:
            tokens.append("".join(held))
            held = []
    if held:
        tokens.append("".join(held))
    return tuple(tokens)


def stems(text: str) -> Tuple[str, ...]:
    return tuple(stem(token) for token in tokenize(text))


def compile_query(text: str) -> RelevanceQuery:
    """Turn one query text into terms and phrases, once.

    A double-quoted segment is a phrase and contributes its tokens as a
    sequence; everything else contributes its stems as terms, stopwords
    dropped. A phrase's own tokens are also terms, so a record matching the
    words but not the order still earns term coverage. Raises when nothing
    survives, because a query of stopwords is a question about nothing.
    """

    phrases: List[Tuple[str, ...]] = []
    remainder: List[str] = []
    parts = text.split('"')
    # Odd-indexed parts are inside quotes when the quotes are balanced; an
    # unbalanced final quote leaves its tail as plain text.
    for index, part in enumerate(parts):
        inside = index % 2 == 1 and index != len(parts) - 1
        if inside:
            phrase = tokenize(part)
            if phrase:
                phrases.append(phrase)
            remainder.append(part)
        else:
            remainder.append(part)
    terms: List[str] = []
    for token in tokenize(" ".join(remainder)):
        if token in STOPWORDS or len(token) < 2 and not token.isdigit():
            continue
        stemmed = stem(token)
        if stemmed not in terms:
            terms.append(stemmed)
    if not terms and not phrases:
        raise RelevanceError(
            "query {0!r} compiles to no term and no phrase: nothing in it names a"
            " topic".format(text)
        )
    return RelevanceQuery(text=text, terms=tuple(terms), phrases=tuple(phrases))


def _phrase_in(phrase: Tuple[str, ...], tokens: Tuple[str, ...]) -> bool:
    width = len(phrase)
    if not width or width > len(tokens):
        return False
    for start in range(len(tokens) - width + 1):
        if tokens[start : start + width] == phrase:
            return True
    return False


def score_text(
    query: RelevanceQuery, texts: Sequence[Tuple[str, str]]
) -> Tuple[float, Tuple[str, ...], Tuple[Tuple[str, ...], ...], Tuple[Tuple[str, str], ...]]:
    """Score one record's named texts against one query.

    ``texts`` is ``((field_name, text), ...)`` in the caller's field order.
    Returns the score, the terms matched, the phrases matched, and the field
    each matched term was first found in.

    score = TERM_WEIGHT × (matched terms ÷ query terms)
          + PHRASE_WEIGHT × (matched phrases ÷ query phrases)

    A query with no phrases takes its term coverage for its phrase coverage,
    so a plain query still reaches 1.0; a query with no terms (all quoted)
    takes its phrase coverage for both.
    """

    matched_terms: List[str] = []
    fields: List[Tuple[str, str]] = []
    matched_phrases: List[Tuple[str, ...]] = []
    per_field_stems: List[Tuple[str, Tuple[str, ...], Tuple[str, ...]]] = []
    for name, text in texts:
        tokens = tokenize(text)
        per_field_stems.append((name, tokens, tuple(stem(token) for token in tokens)))
    for term in query.terms:
        for name, _, field_stems in per_field_stems:
            if term in field_stems:
                matched_terms.append(term)
                fields.append((term, name))
                break
    for phrase in query.phrases:
        for _, tokens, _ in per_field_stems:
            if _phrase_in(phrase, tokens):
                matched_phrases.append(phrase)
                break
    term_coverage = (
        len(matched_terms) / float(len(query.terms)) if query.terms else None
    )
    phrase_coverage = (
        len(matched_phrases) / float(len(query.phrases)) if query.phrases else None
    )
    if term_coverage is None:
        term_coverage = phrase_coverage or 0.0
    if phrase_coverage is None:
        phrase_coverage = term_coverage
    score = TERM_WEIGHT * term_coverage + PHRASE_WEIGHT * phrase_coverage
    return (
        round(score, 6),
        tuple(matched_terms),
        tuple(matched_phrases),
        tuple(fields),
    )


def _texts_of(
    record: schema.AcquisitionRecord, fields: Sequence[str]
) -> Tuple[Tuple[str, str], ...]:
    texts = []
    for name in fields:
        if name == "title":
            texts.append((name, record.title))
        elif name == "body":
            texts.append((name, record.body))
        elif name == "author":
            texts.append((name, record.author))
        elif name == "community":
            texts.append((name, record.community))
        elif name == "attributes":
            texts.append((name, " ".join(value for _, value in record.attributes)))
        else:
            raise RelevanceError(
                "field {0!r} is not one this module reads; the readable fields are"
                " title, body, author, community, attributes".format(name)
            )
    return tuple(texts)


def match(
    record: schema.AcquisitionRecord,
    query: RelevanceQuery,
    fields: Sequence[str] = DEFAULT_FIELDS,
) -> RelevanceMatch:
    """One record's score against one compiled query, with its evidence."""

    score, terms, phrases, found_in = score_text(query, _texts_of(record, fields))
    return RelevanceMatch(
        record_id=record.record_id,
        score=score,
        matched_terms=terms,
        matched_phrases=phrases,
        fields=found_in,
    )


def rank(
    records: Iterable[schema.AcquisitionRecord],
    query: RelevanceQuery,
    fields: Sequence[str] = DEFAULT_FIELDS,
) -> Tuple[RelevanceMatch, ...]:
    """Every record scored, best first; ties broken by record id, never by engagement."""

    matches = [match(record, query, fields) for record in records]
    return tuple(sorted(matches, key=lambda found: (-found.score, found.record_id)))


def partition(
    records: Iterable[schema.AcquisitionRecord],
    query: RelevanceQuery,
    floor: float,
    fields: Sequence[str] = DEFAULT_FIELDS,
) -> Tuple[Tuple[RelevanceMatch, ...], Tuple[RelevanceMatch, ...]]:
    """The records at or above ``floor`` and the records below it, both listed.

    The second tuple is the audit: every record a caller would drop, with the
    score and the matches that put it there. A floor applied without reading
    it is the competing tool's silent floor; a floor applied after reading it
    is a decision with a record.
    """

    if not 0.0 <= floor <= 1.0:
        raise RelevanceError("floor must be in [0, 1], got {0!r}".format(floor))
    ranked = rank(records, query, fields)
    kept = tuple(found for found in ranked if found.score >= floor)
    dropped = tuple(found for found in ranked if found.score < floor)
    return kept, dropped


def audit_lines(dropped: Iterable[RelevanceMatch]) -> Tuple[str, ...]:
    """One line per dropped record: id, score, and what it did match, for a report."""

    lines = []
    for found in dropped:
        lines.append(
            "{0} score={1:.3f} terms={2} phrases={3}".format(
                found.record_id,
                found.score,
                ",".join(found.matched_terms) or "-",
                ";".join(" ".join(phrase) for phrase in found.matched_phrases) or "-",
            )
        )
    return tuple(lines)


def matched_field_counts(matches: Iterable[RelevanceMatch]) -> Dict[str, int]:
    """How many matched terms were found in each field, over a set of matches.

    The bakeoff's `search_by_date:SPCX` matched the *authors* `SPCECDET` and
    `spixy` — a token match that was not a topic match. Reading this table
    beside a ranking says where a query's evidence actually lives.
    """

    counts: Dict[str, int] = {}
    for found in matches:
        for _, name in found.fields:
            counts[name] = counts.get(name, 0) + 1
    return counts
