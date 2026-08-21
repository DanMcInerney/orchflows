#!/usr/bin/env python3
"""Record and evaluate selected/exhaustive serial proving pairs."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


REQUIRED_CLEAN_PAIRS = 20


def make_pair(selected: dict, exhaustive: dict, pair_id: str) -> dict:
    reasons = []
    if selected.get("mode") != "selected" or exhaustive.get("mode") != "exhaustive":
        reasons.append("observation-mode-mismatch")
    if selected.get("revision") != exhaustive.get("revision"):
        reasons.append("revision-mismatch")
    selected_identity = selected.get("discovery")
    exhaustive_identity = exhaustive.get("discovery")
    if selected_identity != exhaustive_identity:
        reasons.append("discovery-identity-mismatch")
    if not selected.get("ok"):
        reasons.append("selected-red")
    if not exhaustive.get("ok"):
        reasons.append("exhaustive-red")
    discrepancy = bool(selected.get("ok") and not exhaustive.get("ok"))
    return {
        "schema": "orchflows.serial-compat-pair.v1",
        "pair_id": pair_id,
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "revision": selected.get("revision"),
        "discovery": selected_identity,
        "selected": selected,
        "exhaustive": exhaustive,
        "selected_green_exhaustive_red": discrepancy,
        "reasons": reasons,
        "clean": not reasons,
    }


def evaluate_pairs(pairs) -> dict:
    ordered = sorted(pairs, key=lambda pair: (pair.get("recorded_at_utc", ""), pair.get("pair_id", "")))
    streak = 0
    for pair in ordered:
        streak = streak + 1 if pair.get("clean") else 0
    return {
        "schema": "orchflows.serial-compat-gate.v1",
        "required_clean_pairs": REQUIRED_CLEAN_PAIRS,
        "clean_streak": streak,
        "promotion_ready": streak >= REQUIRED_CLEAN_PAIRS,
        "pairs": ordered,
    }


def _load(path: Path, mode: str) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"mode": mode, "ok": False, "load_error": str(exc)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected", required=True)
    parser.add_argument("--exhaustive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--pair-id", required=True)
    args = parser.parse_args(argv)
    pair = make_pair(
        _load(Path(args.selected), "selected"),
        _load(Path(args.exhaustive), "exhaustive"),
        args.pair_id,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(pair, sort_keys=True, indent=1), encoding="utf-8")
    print(json.dumps(pair, sort_keys=True))
    return 0 if pair["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
