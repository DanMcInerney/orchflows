"""Canonical gate mutation-plan derivation."""

from __future__ import annotations

import hashlib
import json
import re


MALFORMED_GATE_MUTATIONS = "root mutation plan is malformed"
MUTATION_PATTERN = re.compile(r"(create|change|delete|write):(.+)")


def _valid_mutation_path(kind: str, path: str) -> bool:
    plan_path = path.removesuffix("/")
    parts = plan_path.split("/")
    return (
        bool(plan_path)
        and "\\" not in path
        and not path.startswith("/")
        and ((kind == "write") == path.endswith("/"))
        and all(part not in ("", ".", "..") for part in parts)
        and not any(character in path for character in "*?[]")
        and ":" not in parts[0]
    )


def _parse_mutations(mutations):
    if mutations is None:
        mutations = []
    if not isinstance(mutations, list):
        return None

    parsed = []
    for mutation in mutations:
        if not isinstance(mutation, str):
            return None
        match = MUTATION_PATTERN.fullmatch(mutation)
        if match is None or not _valid_mutation_path(*match.groups()):
            return None
        parsed.append(match.groups())
    return parsed


def _canonical_paths(parsed_mutations) -> list:
    return sorted({path for _kind, path in parsed_mutations})


def _canonical_utf8_json(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_identity(canonical: bytes) -> str:
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _canonical_gate_mutation_plan(mutations):
    parsed = _parse_mutations(mutations)
    if parsed is None:
        return None, MALFORMED_GATE_MUTATIONS

    paths = _canonical_paths(parsed)
    canonical = _canonical_utf8_json(paths)
    return {"identity": _sha256_identity(canonical), "paths": paths}, None
