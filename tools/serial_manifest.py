#!/usr/bin/env python3
"""Regenerate the committed serial-compatibility manifest from live facts.

`tools/run_serial_compat.py` owns the contract this file writes; it already
fills one-read size on its own, so the generator lives here and the runner
keeps only the flag that reaches it.

Two facts in the manifest are derived and one is not. The discovery block
(count, identities, sha256) and the mutation-owner inventory are what the
tree says today, so a hand-edited count is a number nobody recomputed.
A mutation owner's `restoration` is a *classification* a reviewer made about
how the seam is returned; no scan can recover it, so regeneration carries it
across by (module, owner) and marks a newly-appeared owner `unclassified` for
a reviewer to rule on. That marker is one the runner's loader refuses, so the
command that wrote it must not report success: it names every owner awaiting
a ruling and exits non-zero, leaving the regenerated file in place so the
ruling is made on the marked row rather than on hand-written derived facts.
The sentinel roster is chosen, never derived, and this file proves it survived
byte-for-byte rather than merely round-tripped.

Stdlib only, Python 3.9+, POSIX and Windows.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SENTINELS_KEY = '\n "sentinels": ['
BLOCK_END = "\n ]"
UNCLASSIFIED = "unclassified"
POLICY = "tools/serial-compat-policy.md"
NEEDS_RULING = 2


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
    """Scanned owners, each keeping the restoration its prior record carried.

    An owner no prior record classified is marked, not left silent: a missing
    key is a pending decision nobody can find in a several-hundred-row file.
    """
    prior = {(row.get("module"), row.get("owner")): row for row in previous or []}
    merged = []
    for row in scanned:
        record = dict(row)
        carried = prior.get((record.get("module"), record.get("owner")), {}).get("restoration")
        record["restoration"] = UNCLASSIFIED if carried is None else carried
        merged.append(record)
    return sorted(merged, key=lambda record: (record["module"], record["owner"]))


def unruled(owners) -> list:
    """Every marked owner, named the way a reviewer has to go find it."""
    return ["%s::%s [%s]" % (row.get("module"), row.get("owner"),
                             ", ".join(row.get("seams") or ()))
            for row in owners if row.get("restoration") == UNCLASSIFIED]


def _identity(block) -> dict:
    block = block if isinstance(block, dict) else {}
    return {"count": block.get("count"), "sha256": block.get("sha256")}


def plan_regeneration(manifest_path, tests_dir, discover, scan):
    """The bytes on disk, the bytes regeneration would write, and the report.

    Pure: nothing here touches the manifest. `regenerate` writes what this
    returns and `tools/regen.py --check` compares it without writing, so the
    freshness gate and the regeneration cannot answer differently.
    """
    path = Path(manifest_path)
    before_text = path.read_text(encoding="utf-8")
    before = json.loads(before_text)
    after = dict(before)
    after["discovery"] = discovery(discover(tests_dir))
    after["mutation_owners"] = merge_owners(before.get("mutation_owners"), scan(tests_dir))
    after_text = render(after)
    if sentinels_block(after_text) != sentinels_block(before_text):
        raise ValueError("regeneration would rewrite the sentinel roster")
    return before_text, after_text, {
        "manifest": str(path),
        "before": _identity(before.get("discovery")),
        "after": _identity(after["discovery"]),
        "owners": {
            "before": len(before.get("mutation_owners") or []),
            "after": len(after["mutation_owners"]),
        },
        "unruled": unruled(after["mutation_owners"]),
    }


def regenerate(manifest_path, tests_dir, discover, scan) -> dict:
    """Rewrite the manifest's derived facts and report what moved."""
    _before_text, after_text, report = plan_regeneration(
        manifest_path, tests_dir, discover, scan
    )
    with open(str(Path(manifest_path)), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(after_text)
    return report


def write_manifest(manifest_path, tests_dir, discover, scan, out=None) -> int:
    """The runner's `--write-manifest`: regenerate, report, rule or refuse."""
    report = regenerate(manifest_path, tests_dir, discover, scan)
    lines = [
        "serial manifest: %s" % report["manifest"],
        "discovery before: %s %s" % (report["before"]["count"], report["before"]["sha256"]),
        "discovery after: %s %s" % (report["after"]["count"], report["after"]["sha256"]),
        "mutation owners before: %d after: %d"
        % (report["owners"]["before"], report["owners"]["after"]),
    ]
    if report["unruled"]:
        lines.append("mutation owners needing a ruling (%d), per %s:"
                     % (len(report["unruled"]), POLICY))
        lines.extend("  " + name for name in report["unruled"])
        lines.append("set each marked restoration in the written manifest, then run this again")
    print("\n".join(lines), file=out if out is not None else sys.stdout)
    return NEEDS_RULING if report["unruled"] else 0
