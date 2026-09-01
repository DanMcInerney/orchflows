"""Render the CI leg breakdown from the workflow matrix it actually runs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKS_WORKFLOW = ROOT / ".github" / "workflows" / "checks.yml"
PREFLIGHT = ROOT / "tools" / "preflight.py"
TREE_REMOVAL = ROOT / "tests" / "tree_removal.py"
BEGIN = "<!-- BEGIN GENERATED CI TOPOLOGY -->"
END = "<!-- END GENERATED CI TOPOLOGY -->"

_NUMBER_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
    6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
}
_OS_LABELS = {"ubuntu": "Ubuntu", "macos": "macOS", "windows": "Windows"}
_FLOW_LIST_RE = "(?m)^\\s*{}:\\s*\\[([^\\]]*)\\]"


class TopologyUnreadable(RuntimeError):
    """The CI matrix could not be read the way this renderer expects."""


def _flow_axis(text: str, name: str, source: Path) -> tuple:
    """One bracketed `key: [a, b, c]` matrix axis, straight out of the
    workflow -- never a second, hand-typed copy of the same list."""

    match = re.search(_FLOW_LIST_RE.format(re.escape(name)), text)
    if not match:
        raise TopologyUnreadable(f"{source}: no {name}: [...] axis")
    values = tuple(v.strip().strip("'\"") for v in match.group(1).split(",") if v.strip())
    if not values:
        raise TopologyUnreadable(f"{source}: {name}: [...] axis names none")
    return values


def _exclude_entries(text: str, source: Path) -> tuple:
    """Every `exclude:` list entry as a `{key: value}` mapping, read by
    indentation the way YAML block sequences nest: entries at a `- key:
    value` line, continuation keys at the same or greater indent, the
    list ending at the first line back at or above `exclude:`'s own
    indent. Not a YAML parser -- this is the one shape checks.yml's
    matrix uses, and preflight.py already reads its flow axes the same
    narrow, regex way rather than carrying a dependency for it."""

    lines = text.splitlines()
    exclude_indent = None
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "exclude:":
            start = index
            exclude_indent = len(line) - len(line.lstrip(" "))
            break
    if start is None:
        return ()
    entries = []
    current = None
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= exclude_indent:
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            if current is not None:
                entries.append(current)
            current = {}
            stripped = stripped[2:]
        if current is None or ":" not in stripped:
            raise TopologyUnreadable(f"{source}: malformed exclude entry: {line!r}")
        key, _, value = stripped.partition(":")
        current[key.strip()] = value.strip().strip("'\"")
    if current is not None:
        entries.append(current)
    return tuple(entries)


def leg_breakdown(workflow: Path = CHECKS_WORKFLOW) -> dict:
    """Every surviving `checks` job leg, grouped by OS label, computed the
    way GitHub Actions itself expands a matrix: the full cartesian product
    of every declared axis, minus any combination an `exclude` entry fully
    matches (an entry names a subset of keys; every combination agreeing
    with the named keys on every one of them is excluded, regardless of
    its other axes)."""

    text = workflow.read_text(encoding="utf-8")
    os_cells = _flow_axis(text, "os", workflow)
    versions = _flow_axis(text, "python-version", workflow)
    shards = _flow_axis(text, "shard", workflow)
    excludes = _exclude_entries(text, workflow)
    counts: dict = {}
    order: list = []
    for os_name in os_cells:
        label = os_name.split("-")[0]
        if label not in counts:
            counts[label] = 0
            order.append(label)
        for version in versions:
            for shard in shards:
                combo = {"os": os_name, "python-version": version, "shard": shard}
                if any(
                    all(combo.get(key) == value for key, value in entry.items())
                    for entry in excludes
                ):
                    continue
                counts[label] += 1
    return {"counts": counts, "order": tuple(order), "total": sum(counts.values())}


def _word(n: int) -> str:
    return _NUMBER_WORDS.get(n, str(n))


def _os_label(name: str) -> str:
    return _OS_LABELS.get(name, name.title())


def leg_clause(breakdown: dict = None) -> str:
    """`"two Ubuntu, one macOS, and two Windows"` -- Oxford-comma joined,
    in the matrix's own OS declaration order."""

    breakdown = breakdown if breakdown is not None else leg_breakdown()
    parts = [
        f"{_word(breakdown['counts'][name])} {_os_label(name)}"
        for name in breakdown["order"]
    ]
    if len(parts) > 1:
        parts[-1] = "and " + parts[-1]
    return ", ".join(parts) if len(parts) > 2 else " ".join(parts)


def leg_total_clause(breakdown: dict = None) -> str:
    """`"five active CI legs: two Ubuntu, one macOS, and two Windows"`."""

    breakdown = breakdown if breakdown is not None else leg_breakdown()
    return f"{_word(breakdown['total'])} active CI legs: {leg_clause(breakdown)}"


def windows_split_clause(breakdown: dict = None) -> str:
    """`"on both Windows legs and on none of the other three"`."""

    breakdown = breakdown if breakdown is not None else leg_breakdown()
    windows = breakdown["counts"].get("windows", 0)
    other = breakdown["total"] - windows
    phrase = "both Windows legs" if windows == 2 else f"all {_word(windows)} Windows legs"
    return f"on {phrase} and on none of the other {_word(other)}"


def _replace_section(text: str, generated: str, source: Path) -> str:
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise TopologyUnreadable(f"{source}: no {BEGIN} ... {END} span to replace")
    return pattern.sub(lambda _match: BEGIN + generated + END, text, count=1)


def render_preflight(breakdown: dict = None) -> str:
    return _replace_section(
        PREFLIGHT.read_text(encoding="utf-8"), leg_total_clause(breakdown), PREFLIGHT
    )


def render_tree_removal(breakdown: dict = None) -> str:
    return _replace_section(
        TREE_REMOVAL.read_text(encoding="utf-8"), windows_split_clause(breakdown), TREE_REMOVAL
    )


def is_current() -> bool:
    try:
        breakdown = leg_breakdown()
        return (
            PREFLIGHT.read_text(encoding="utf-8") == render_preflight(breakdown)
            and TREE_REMOVAL.read_text(encoding="utf-8") == render_tree_removal(breakdown)
        )
    except (OSError, TopologyUnreadable):
        return False


def write() -> None:
    # Render before opening: both renderers read the target file they are
    # about to overwrite, so computing both strings before either `open(...,
    # "w")` call keeps a renderer from truncating the prose it still needs
    # to read (rules/verification.md's evidence for this exact hazard: an
    # earlier open-then-render ordering here silently ate the docstring it
    # was regenerating). newline="" rather than write_text(newline=...): the
    # keyword is 3.10+ and the floor is 3.9.
    breakdown = leg_breakdown()
    preflight_text = render_preflight(breakdown)
    tree_removal_text = render_tree_removal(breakdown)
    with open(PREFLIGHT, "w", encoding="utf-8", newline="") as stream:
        stream.write(preflight_text)
    with open(TREE_REMOVAL, "w", encoding="utf-8", newline="") as stream:
        stream.write(tree_removal_text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="refuse generated-byte drift")
    args = parser.parse_args(argv)
    try:
        if args.check:
            if is_current():
                print("CI topology is current")
                return 0
            print(f"CI topology drift: run {Path(__file__).name}")
            return 1
        write()
        print("CI topology rendered")
        return 0
    except TopologyUnreadable as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
