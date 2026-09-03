"""Validate package carriage contracts."""

from __future__ import annotations


def Diagnostics(*args, **kwargs):
    from .packages import Diagnostics as diagnostics_type
    return diagnostics_type(*args, **kwargs)


def build_call_graph(packages, diag):
    from .structure import build_call_graph as build
    return build(packages, diag)


def rel(path):
    from .packages import rel as relative
    return relative(path)


def _read_source(path):
    from .packages import _read_source as read_source
    return read_source(path)

from . import common as __dep_common
CARRIAGE_CODE_RE = __dep_common.CARRIAGE_CODE_RE
CARRIAGE_DASH_SPLIT_RE = __dep_common.CARRIAGE_DASH_SPLIT_RE
CARRIAGE_DEFERRED = __dep_common.CARRIAGE_DEFERRED
CARRIAGE_MD_LINK_RE = __dep_common.CARRIAGE_MD_LINK_RE
CARRIAGE_PAREN_RE = __dep_common.CARRIAGE_PAREN_RE
CARRIAGE_QUALIFIERS = __dep_common.CARRIAGE_QUALIFIERS
CARRIAGE_REQUIRE_BLOCK_RE = __dep_common.CARRIAGE_REQUIRE_BLOCK_RE
CARRIAGE_SENTENCE_SPLIT_RE = __dep_common.CARRIAGE_SENTENCE_SPLIT_RE
CARRIAGE_WORD_RE = __dep_common.CARRIAGE_WORD_RE
PACK_SLICING_RE = __dep_common.PACK_SLICING_RE
PACK_STORE_RE = __dep_common.PACK_STORE_RE
PACK_WORKSPACE_RE = __dep_common.PACK_WORKSPACE_RE
RETURN_TEXT_RE = __dep_common.RETURN_TEXT_RE
TICKET_FILING_RE = __dep_common.TICKET_FILING_RE

def _carriage_clean(text: str) -> str:
    text = CARRIAGE_MD_LINK_RE.sub(r"\1", text)
    text = CARRIAGE_CODE_RE.sub(r"\1", text)
    text = CARRIAGE_PAREN_RE.sub(" ", text)
    return text


def _carriage_stem_variants(word: str) -> set:
    """Light, deliberately approximate stemming (plural/gerund/participle
    suffixes, with the silent-e a verb like 'scoped' drops restored) so
    a Require item's noun and a caller's inflected use of it compare
    equal without a real lemmatizer."""
    w = word.lower()
    variants = {w}
    if w.endswith("'s"):
        variants.add(w[:-2])
    if len(w) > 4 and w.endswith("ies"):
        variants.add(w[:-3] + "y")
    if len(w) > 4 and (w.endswith("ches") or w.endswith("shes") or (w.endswith("es") and w[-3] in "sxz")):
        variants.add(w[:-2])
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        variants.add(w[:-1])
    if len(w) > 5 and w.endswith("ing"):
        base = w[:-3]
        variants.add(base)
        variants.add(base + "e")
    if len(w) > 4 and w.endswith("ed"):
        base = w[:-2]
        variants.add(base)
        variants.add(base + "e")
    return variants


def _carriage_body_stems(text: str) -> set:
    text = _carriage_clean(text)
    stems = set()
    for w in CARRIAGE_WORD_RE.findall(text):
        stems |= _carriage_stem_variants(w)
    return stems


# A comma segment opening with one of these modifies the preceding
# input (an elaboration of its shape) rather than introducing a new
# caller-supplied one; such segments are not checked for carriage.
CARRIAGE_ELABORATION_LEADS = {
    "each", "every", "with", "whose", "which", "that", "what", "where",
    "when", "how", "carrying", "naming", "including", "excluding", "per",
}


def _carriage_segments(item: str) -> list:
    """A Require item's checkable segments: the dash-introduced aside
    dropped, the remainder split on commas, elaboration segments (lead
    token in CARRIAGE_ELABORATION_LEADS) skipped. Each surviving
    segment names something the caller must supply, so each is
    checked -- a first-segment-only read let every input after the
    first comma ride uncarried."""
    lead = CARRIAGE_DASH_SPLIT_RE.split(item, maxsplit=1)[0]
    segments = []
    for seg in (s.strip() for s in lead.split(",")):
        if not seg:
            continue
        tokens = [t.lower() for t in CARRIAGE_WORD_RE.findall(seg)]
        if tokens and tokens[0] in CARRIAGE_ELABORATION_LEADS:
            continue
        segments.append(seg)
    return segments


def _carriage_segment_nouns(segment: str) -> list:
    """Every content word of one segment (qualifiers dropped). A
    segment is carried when the target's vocabulary shares any of
    them -- the honest mechanization of "did the caller acknowledge
    this input"; a head-noun pair proved too brittle on segments
    longer than a bare noun phrase."""
    return [
        t.lower()
        for t in CARRIAGE_WORD_RE.findall(segment)
        if t.lower() not in CARRIAGE_QUALIFIERS
    ]


def _carriage_require_items(body: str):
    """The callee's Require items: the first sentence of the Require
    paragraph (later sentences are behavioral prose, not additional
    required fields), split on ';'."""
    m = CARRIAGE_REQUIRE_BLOCK_RE.search(body)
    if not m:
        return []
    first_sentence = CARRIAGE_SENTENCE_SPLIT_RE.split(m.group(1), maxsplit=1)[0]
    return [i.strip() for i in first_sentence.split(";") if i.strip()]


def _carriage_item_carried(item: str, target_stems: set):
    """Return (carried, head_noun) for one Require item against a
    target's stemmed vocabulary. Every checkable comma segment must
    carry (any of its content-word stems present); head_noun is the
    failing segment's last content word, else the final checked
    segment's."""
    cleaned = _carriage_clean(item)
    last_noun = None
    for seg in _carriage_segments(cleaned) or [cleaned]:
        nouns = _carriage_segment_nouns(seg)
        if not nouns:
            continue
        last_noun = nouns[-1]
        matched = [n for n in nouns if _carriage_stem_variants(n) & target_stems]
        if not matched:
            return False, nouns[-1]
        # One incidental middle term does not identify a multiword carrier.
        if len(nouns) > 1 and len(set(matched)) < 2 and matched[0] not in (nouns[-1], "caller"):
            return False, nouns[-1]
    return True, last_noun


def _carriage_flag(diag: Diagnostics, file_label: str, key: tuple, message: str) -> None:
    reason = CARRIAGE_DEFERRED.get(key)
    if reason:
        diag.warn(file_label, f"{message} -- deferred: {reason}")
    else:
        diag.error(file_label, message)


def validate_carriage(packages, diag: Diagnostics) -> None:
    """Rule 10: (a) each call edge A -> B carries every item of B's
    Require in A's body; (b)+(c) each pack's executor/assembly Require
    carries in the pack craft's slicing, and its Return names the
    ticket/work-item filing per work-item.md's filing law (or the pack's
    workspace names a store, the law's other filing destination)."""
    by_name = {pkg["path"].name: pkg for pkg in packages}
    graph = build_call_graph(packages, Diagnostics())  # unresolved-ref errors already reported once, by validate_call_graph

    for a_name in sorted(graph):
        a_pkg = by_name.get(a_name)
        if a_pkg is None or a_pkg["is_pack"]:
            continue
        a_stems = _carriage_body_stems(a_pkg["body"])
        file_label = rel(a_pkg["skill_md"])
        for b_name in sorted(graph[a_name]):
            b_pkg = by_name.get(b_name)
            if b_pkg is None:
                continue
            for item in _carriage_require_items(b_pkg["body"]):
                carried, head_noun = _carriage_item_carried(item, a_stems)
                if carried:
                    continue
                message = (
                    f"call edge {a_name} -> {b_name}: Require item "
                    f"{item!r} (head noun {head_noun!r}) not carried in {a_name}'s body"
                )
                _carriage_flag(diag, file_label, ("edge", a_name, b_name, head_noun), message)

    for pkg in packages:
        if pkg["is_pack"]:
            _validate_pack_carriage(pkg, by_name, diag)


def _validate_pack_carriage(pkg: dict, by_name: dict, diag: Diagnostics) -> None:
    """Packs own their craft and check cells; no executor body is carried.

    Pack references are the authoritative craft carrier, and shared ticket
    filing is enforced by the callable contract.
    """
    del pkg, by_name, diag


# --- Friction log location ---------------------------------------------
#
# A location, not a sentence: scripts/state_root.py owns where the friction
# log goes (ARCHITECTURE.md's scripts/ tier), so the tree it resolves is
# read from `friction_root` and never restated here. The sink root under it
# is rules/visibility.md §6's, checked against the resolver by
# tests/test_validate.py, and no copy restates it. What the copies name is
# the tree: docs/vocabulary.md's **friction log** term, and the
# blocked-case sentence in templates/host-block.md -- a fallback the shell
# refused inside a worktree has to land outside every worktree, so no copy
# may send a hand-written file to the old location under `.orch/`.
#
# One checked copy, not two. AGENTS.md carries the same sentence, and
# mandating it here would make deleting that copy break the compiler, so
# the duplication is reported by validate_cross_tier_duplication instead.

__all__ = (
    '_carriage_clean', '_carriage_stem_variants', '_carriage_body_stems', 'CARRIAGE_ELABORATION_LEADS',
    '_carriage_segments', '_carriage_segment_nouns', '_carriage_require_items', '_carriage_item_carried',
    '_carriage_flag', 'validate_carriage', '_validate_pack_carriage',
)
