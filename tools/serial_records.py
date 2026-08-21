#!/usr/bin/env python3
"""Validation shared by serial-compatibility timing and proving records."""

from __future__ import annotations

import datetime
import math
from collections.abc import Mapping


OBSERVATION_SCHEMA = "orchflows.serial-compat-observation.v1"
EXPECTED_SENTINELS = 14


def _natural(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _digest(value) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def observation_defects(observation, expected_mode=None) -> list[str]:
    """Return fail-closed structural and internal-consistency defects."""

    if not isinstance(observation, Mapping):
        return ["not-an-object"]
    defects = []
    if observation.get("schema") != OBSERVATION_SCHEMA:
        defects.append("schema")
    mode = observation.get("mode")
    if mode not in {"selected", "exhaustive"}:
        defects.append("mode")
    if expected_mode is not None and mode != expected_mode:
        defects.append("mode-mismatch")
    revision = observation.get("revision")
    if not isinstance(revision, str) or not revision.strip():
        defects.append("revision")
    if observation.get("worktree_clean") is not True:
        defects.append("worktree-dirty")
    try:
        datetime.datetime.strptime(observation.get("recorded_at_utc"), "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        defects.append("recorded-at")
    interpreter = observation.get("interpreter")
    if not isinstance(interpreter, Mapping):
        defects.append("interpreter")
    elif (
        not isinstance(interpreter.get("pid"), int)
        or isinstance(interpreter.get("pid"), bool)
        or interpreter.get("pid", 0) < 1
        or not isinstance(interpreter.get("version"), str)
        or not isinstance(interpreter.get("executable"), str)
    ):
        defects.append("interpreter-fields")
    discovery = observation.get("discovery")
    if not isinstance(discovery, Mapping):
        defects.append("discovery")
        discovery = {}
    if not _natural(discovery.get("count")) or discovery.get("count", 0) < 1:
        defects.append("discovery-count")
    if not _digest(discovery.get("sha256")):
        defects.append("discovery-sha256")
    manifest = observation.get("manifest")
    if not isinstance(manifest, Mapping) or not _digest(manifest.get("sha256")):
        defects.append("manifest-sha256")
    ok = observation.get("ok")
    if not isinstance(ok, bool):
        defects.append("ok")
    try:
        duration = float(observation.get("wall_time_seconds"))
    except (TypeError, ValueError):
        duration = float("nan")
    if not math.isfinite(duration) or duration < 0:
        defects.append("duration")
    outcomes = observation.get("outcomes")
    if not isinstance(outcomes, Mapping):
        defects.append("outcomes")
        outcomes = {}
    outcome_keys = (
        "tests", "failures", "errors", "skipped",
        "expected_failures", "unexpected_successes",
    )
    if any(not _natural(outcomes.get(key)) for key in outcome_keys):
        defects.append("outcome-counts")
    if mode == "selected":
        sentinels = observation.get("sentinels")
        count = sentinels.get("count") if isinstance(sentinels, Mapping) else None
        if count != EXPECTED_SENTINELS:
            defects.append("sentinel-count")
        if not isinstance(observation.get("boundaries"), list):
            defects.append("boundaries")
        if _natural(outcomes.get("tests")) and outcomes.get("tests") != count:
            defects.append("selected-test-count")
    if mode == "exhaustive" and _natural(outcomes.get("tests")):
        if outcomes.get("tests") != discovery.get("count"):
            defects.append("exhaustive-test-count")
    if ok is True and any(outcomes.get(key) for key in ("failures", "errors", "unexpected_successes")):
        defects.append("green-outcomes")
    if ok is True and mode == "selected":
        boundaries = observation.get("boundaries", [])
        if any(
            not isinstance(boundary, Mapping)
            or boundary.get("unexpected")
            or boundary.get("remaining")
            for boundary in boundaries
        ):
            defects.append("green-boundaries")
    return sorted(set(defects))
