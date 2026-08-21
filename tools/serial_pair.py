#!/usr/bin/env python3
"""Record and evaluate selected/exhaustive serial proving pairs."""

from __future__ import annotations

import argparse
import datetime
import json
import time
from pathlib import Path

try:
    from tools.serial_records import observation_defects
except ModuleNotFoundError:  # direct ``python tools/serial_pair.py`` execution
    from serial_records import observation_defects


REQUIRED_CLEAN_PAIRS = 20


def make_pair(selected: dict, exhaustive: dict, pair_id: str, recorded_at=None) -> dict:
    reasons = [
        "selected-" + defect for defect in observation_defects(selected, "selected")
    ]
    reasons.extend(
        "exhaustive-" + defect
        for defect in observation_defects(exhaustive, "exhaustive")
    )
    if selected.get("ok") is not True:
        reasons.append("selected-red")
    if exhaustive.get("ok") is not True:
        reasons.append("exhaustive-red")
    if selected.get("revision") != exhaustive.get("revision"):
        reasons.append("revision-mismatch")
    selected_identity = selected.get("discovery")
    exhaustive_identity = exhaustive.get("discovery")
    if selected_identity != exhaustive_identity:
        reasons.append("discovery-identity-mismatch")
    selected_manifest = selected.get("manifest")
    if selected_manifest != exhaustive.get("manifest"):
        reasons.append("manifest-identity-mismatch")
    discrepancy = selected.get("ok") is True and exhaustive.get("ok") is False
    reasons = list(dict.fromkeys(reasons))
    return {
        "schema": "orchflows.serial-compat-pair.v1",
        "pair_id": pair_id,
        "recorded_at_utc": recorded_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "revision": selected.get("revision"),
        "discovery": selected_identity,
        "manifest": selected_manifest,
        "selected": selected,
        "exhaustive": exhaustive,
        "selected_green_exhaustive_red": discrepancy,
        "reasons": reasons,
        "clean": not reasons,
    }


def _pair_defects(pair) -> list[str]:
    if not isinstance(pair, dict):
        return ["not-an-object"]
    defects = []
    if pair.get("schema") != "orchflows.serial-compat-pair.v1":
        defects.append("schema")
    if not isinstance(pair.get("pair_id"), str) or not pair.get("pair_id", "").strip():
        defects.append("pair-id")
    timestamp = pair.get("recorded_at_utc")
    try:
        datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        defects.append("recorded-at")
    expected = make_pair(
        pair.get("selected", {}), pair.get("exhaustive", {}),
        pair.get("pair_id"), timestamp,
    )
    for key in (
        "revision", "discovery", "manifest", "selected_green_exhaustive_red",
        "reasons", "clean",
    ):
        if pair.get(key) != expected.get(key):
            defects.append("inconsistent-" + key.replace("_", "-"))
    return sorted(set(defects))


def evaluate_pairs(pairs) -> dict:
    ordered = sorted(
        pairs,
        key=lambda pair: (
            pair.get("recorded_at_utc", "") if isinstance(pair, dict) else "",
            pair.get("pair_id", "") if isinstance(pair, dict) else "",
        ),
    )
    streak = 0
    streak_identity = None
    ever_ready = False
    seen_ids = set()
    defects = []
    resets = []
    for pair in ordered:
        pair_id = pair.get("pair_id") if isinstance(pair, dict) else None
        pair_defects = _pair_defects(pair)
        if pair_id in seen_ids:
            pair_defects.append("duplicate-pair-id")
        seen_ids.add(pair_id)
        if pair_defects:
            defects.append({"pair_id": pair_id, "reasons": sorted(set(pair_defects))})
            streak = 0
            streak_identity = None
            resets.append({"pair_id": pair_id, "reason": "invalid-pair"})
            continue
        identity = (json.dumps(pair.get("discovery"), sort_keys=True),
                    json.dumps(pair.get("manifest"), sort_keys=True))
        if not pair.get("clean"):
            streak = 0
            streak_identity = None
            resets.append({"pair_id": pair_id, "reason": "unclean-pair"})
            continue
        if streak_identity is not None and identity != streak_identity:
            streak = 0
            resets.append({"pair_id": pair_id, "reason": "contract-identity-change"})
        streak_identity = identity
        streak += 1
        ever_ready = ever_ready or streak >= REQUIRED_CLEAN_PAIRS
    promotion_ready = streak >= REQUIRED_CLEAN_PAIRS and not defects
    return {
        "schema": "orchflows.serial-compat-gate.v1",
        "required_clean_pairs": REQUIRED_CLEAN_PAIRS,
        "clean_streak": streak,
        "promotion_ready": promotion_ready,
        "rollback_required": ever_ready and not promotion_ready,
        "defects": defects,
        "resets": resets,
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
