#!/usr/bin/env python3
"""``scripts/harvest.py``'s clustering seam: pure functions, no sink I/O.

Normalizing an entry's text, shingling it, the greedy-union clustering
pass over a friction slice, and the ``rules/improvement.md`` rule 4
arithmetic each cluster is scored by. Nothing here touches the sink, the
clock or argv, which is what makes ``harvest.py``'s determinism checkable
in isolation from window resolution and file I/O. Stdlib only.
"""

from __future__ import annotations

import re

# One fixed constant, tuned against tests/test_harvest.py's fixture corpus.
JACCARD_THRESHOLD = 0.3
SHINGLE_SIZE = 3
# Digest members are capped so a large cluster does not inflate the file a
# driver reads whole; a cluster's own counts are never capped.
MEMBER_CAP = 12

_PATH_RE = re.compile(r"\S*[/\\]\S+")
_HASH_RE = re.compile(r"\b[0-9a-f]{7,64}\b")
_NUM_RE = re.compile(r"\b\d+\b")
_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Placeholders for the normalized classes; each is plain lowercase word
# characters so the token regex treats it as one ordinary token.
_PLACEHOLDER_REGEX = {
    "pathtok": r"\S*[/\\]\S+",
    "hashtok": r"[0-9a-fA-F]{7,64}",
    "numtok": r"\d+",
}


def entry_text(entry: dict) -> str:
    """The one text an entry is normalized, shingled and matched from."""

    return "{0} {1}".format(entry.get("observed") or "", entry.get("expected") or "")


def normalize(text: str) -> str:
    """Case-fold, then blank out paths, hashes and numbers so two entries
    differing only in one of those still shingle alike. Order matters:
    paths first, since they may embed digits or hex runs."""

    lowered = (text or "").lower()
    lowered = _PATH_RE.sub(" pathtok ", lowered)
    lowered = _HASH_RE.sub(" hashtok ", lowered)
    lowered = _NUM_RE.sub(" numtok ", lowered)
    return lowered


def tokens(text: str):
    return _TOKEN_RE.findall(normalize(text))


def shingles(token_list) -> set:
    """3-word shingles, or the whole token list as one degenerate shingle --
    an entry under the shingle size still needs a comparable set."""

    if len(token_list) < SHINGLE_SIZE:
        return {" ".join(token_list)} if token_list else set()
    return {
        " ".join(token_list[i:i + SHINGLE_SIZE])
        for i in range(len(token_list) - SHINGLE_SIZE + 1)
    }


def jaccard(a: set, b: set) -> float:
    union = a | b
    return (len(a & b) / len(union)) if union else 0.0


def cluster_entries(entries):
    """Greedy union over ``entries`` in the order given: each joins the
    first existing cluster it clears ``JACCARD_THRESHOLD`` against, else
    opens a new one. Never revisited once placed -- the mine may merge
    clusters this call kept apart; it never has to split one it fused."""

    clusters = []
    for entry in entries:
        entry_shingles = shingles(tokens(entry_text(entry)))
        for cluster in clusters:
            if jaccard(entry_shingles, cluster["shingles"]) >= JACCARD_THRESHOLD:
                cluster["members"].append(entry)
                cluster["shingles"] |= entry_shingles
                cluster["shared"] &= entry_shingles
                break
        else:
            clusters.append({
                "members": [entry],
                "shingles": set(entry_shingles),
                "shared": set(entry_shingles),
            })
    return clusters


def shingle_to_regex(shingle: str) -> str:
    """One shared shingle as a regex a later covered-line can replay: a
    placeholder widens back to what it stood for, the rest is literal."""

    words = [w for w in shingle.split(" ") if w]
    if not words:
        return ""
    return r"\s+".join(_PLACEHOLDER_REGEX.get(w, re.escape(w)) for w in words)


def slug(shared: set, fallback_tokens) -> str:
    words = []
    for one in sorted(shared):
        words.extend(one.split(" "))
    if not words:
        words = fallback_tokens[:6]
    seen = []
    for word in words:
        if word and word not in seen:
            seen.append(word)
    text = "-".join(seen)[:60].strip("-")
    return text or "cluster"


def cluster_counts(members) -> dict:
    """Improvement law rule 4's arithmetic: member count, distinct sessions
    among members that carry one, distinct ``(run, host)`` pairs among those
    that do not -- a stand-in only where the entry carries no session."""

    with_session = {m.get("session") for m in members if m.get("session")}
    without_session = {
        (m.get("run"), m.get("host")) for m in members if not m.get("session")
    }
    return {
        "members": len(members),
        "distinct_sessions": len(with_session),
        "distinct_run_host_pairs": len(without_session),
    }


def recurrence_met(counts: dict) -> bool:
    return (
        counts["members"] >= 3
        or (counts["distinct_sessions"] + counts["distinct_run_host_pairs"]) >= 2
    )


def build_cluster_records(clusters):
    """``cluster_entries``'s output, scored and shaped into the digest's
    ``clusters`` array: ranked by member count, members capped at
    ``MEMBER_CAP`` with the overflow counted rather than dropped silent."""

    records = []
    for cluster in clusters:
        members = cluster["members"]
        counts = cluster_counts(members)
        shared = cluster["shared"]
        fallback = tokens(entry_text(members[0])) if members else []
        records.append({
            "cluster_key": slug(shared, fallback),
            "counts": counts,
            "recurrence_met": recurrence_met(counts),
            "matcher_draft": sorted(filter(None, (
                shingle_to_regex(s) for s in shared
            ))),
            "members": members[:MEMBER_CAP],
            "omitted": max(0, len(members) - MEMBER_CAP),
        })
    records.sort(key=lambda r: r["counts"]["members"], reverse=True)
    return records


__all__ = (
    "JACCARD_THRESHOLD", "SHINGLE_SIZE", "MEMBER_CAP",
    "entry_text", "normalize", "tokens", "shingles", "jaccard",
    "cluster_entries", "shingle_to_regex", "slug", "cluster_counts",
    "recurrence_met", "build_cluster_records",
)
