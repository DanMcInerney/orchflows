#!/usr/bin/env python3
"""Regenerate the committed serial-compatibility manifest from live facts.

`tools/run_serial_compat.py` owns the contract this file writes; it is at the
510-line source ceiling, so the generator lives here and the runner keeps only
the flag that reaches it.

Two facts in the manifest are derived and one is not. The discovery block
(count, identities, sha256) and the mutation-owner inventory are what the
tree says today, so a hand-edited count is a number nobody recomputed.
A mutation owner's `restoration` is a *classification* a reviewer made about
how the seam is returned; no scan can recover it, so regeneration carries it
across by (module, owner) and leaves a newly-appeared owner unclassified for
a reviewer to rule on. The sentinel roster is chosen, never derived, and this
file proves it survived byte-for-byte rather than merely round-tripped.

Stdlib only, Python 3.9+, POSIX and Windows.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SENTINELS_KEY = '\n "sentinels": ['
BLOCK_END = "\n ]"


def render(manifest: dict) -> str:
    """The one committed spelling: sorted keys, one-space indent, LF, final newline."""
    return json.dumps(manifest, sort_keys=True, indent=1) + "\n"


def sentinels_block(text: str) -> str:
    """The sentinel roster exactly as it sits in the rendered bytes.

    `sentinels` sorts last, and no nested array closes at this indent, so the
    first `\\n ]` after the key is the roster's own close.
    """
    start = text.index(SENTINELS_KEY)
    return text[start:text.index(BLOCK_END, start) + len(BLOCK_END)]


def discovery(cases) -> dict:
    """The exact discovered identity multiset, as the runner hashes it."""
    identities = sorted(case.id() for case in cases)
    return {
        "count": len(identities),
        "identities": identities,
        "sha256": hashlib.sha256("\n".join(identities).encode("utf-8")).hexdigest(),
    }


def merge_owners(previous, scanned) -> list:
    """Scanned owners, each keeping the restoration its prior record carried."""
    prior = {(row.get("module"), row.get("owner")): row for row in previous or []}
    merged = []
    for row in scanned:
        record = dict(row)
        carried = prior.get((record.get("module"), record.get("owner")), {}).get("restoration")
        if carried is not None:
            record["restoration"] = carried
        merged.append(record)
    return sorted(merged, key=lambda record: (record["module"], record["owner"]))


def _identity(block) -> dict:
    block = block if isinstance(block, dict) else {}
    return {"count": block.get("count"), "sha256": block.get("sha256")}


def regenerate(manifest_path, tests_dir, discover, scan) -> dict:
    """Rewrite the manifest's derived facts and report what moved."""
    path = Path(manifest_path)
    before_text = path.read_text(encoding="utf-8")
    before = json.loads(before_text)
    after = dict(before)
    after["discovery"] = discovery(discover(tests_dir))
    after["mutation_owners"] = merge_owners(before.get("mutation_owners"), scan(tests_dir))
    after_text = render(after)
    if sentinels_block(after_text) != sentinels_block(before_text):
        raise ValueError("regeneration would rewrite the sentinel roster")
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(after_text)
    return {
        "manifest": str(path),
        "before": _identity(before.get("discovery")),
        "after": _identity(after["discovery"]),
        "owners": {
            "before": len(before.get("mutation_owners") or []),
            "after": len(after["mutation_owners"]),
        },
    }


def write_manifest(manifest_path, tests_dir, discover, scan, out=None) -> int:
    """The runner's `--write-manifest`: regenerate, report, exit 0."""
    report = regenerate(manifest_path, tests_dir, discover, scan)
    lines = [
        "serial manifest: %s" % report["manifest"],
        "discovery before: %s %s" % (report["before"]["count"], report["before"]["sha256"]),
        "discovery after: %s %s" % (report["after"]["count"], report["after"]["sha256"]),
        "mutation owners before: %d after: %d"
        % (report["owners"]["before"], report["owners"]["after"]),
    ]
    print("\n".join(lines), file=out if out is not None else sys.stdout)
    return 0
