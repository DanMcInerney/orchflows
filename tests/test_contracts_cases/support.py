"""Shared readers for the contract regression case modules."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACTS = ROOT / "contracts"
SKILLS = ROOT / "skills"


def read(name):
    return (CONTRACTS / name).read_text(encoding="utf-8")


def read_flat(name):
    """Contract text with whitespace collapsed, so wrapped clauses match."""
    return re.sub(r"\s+", " ", read(name))


def read_at(relative):
    """Any repository file, by repository-relative path."""
    return (ROOT / relative).read_text(encoding="utf-8")


def read_at_flat(relative):
    """Any repository file, whitespace collapsed, so wrapped clauses match."""
    return re.sub(r"\s+", " ", read_at(relative))


def read_clause_flat(relative, number):
    """Return one numbered rules clause with whitespace collapsed."""
    match = re.search(
        rf"(?m)^{number}\. (.*?)(?=^\d+\. |\Z)", read_at(relative), re.S
    )
    if match is None:
        raise AssertionError(f"{relative} has no clause {number}")
    return re.sub(r"\s+", " ", match.group(1))


def read_bullet_flat(name, marker):
    """Return one top-level contract bullet with whitespace collapsed."""
    flat = read_flat(name)
    if marker not in flat:
        raise AssertionError(f"contracts/{name} has no bullet {marker}")
    return flat.split(marker, 1)[1].split(" - `", 1)[0]
