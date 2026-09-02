#!/usr/bin/env python3
"""An item's non-Python tooling: declared beside the manifest, never installed.

The second of the three dependency classes. An item's own Python tooling is
``requirements.txt`` and ``orchflows_envs.py`` builds it; its Node tooling is
``package.json`` and ``orchflows_node.py`` installs it. This class -- ffmpeg,
node, a browser, an API key -- is the one orchflows cannot install and does
not try to: a system package manager is the machine owner's, and a key is
theirs alone. So the item declares what it needs in one ``tools.txt`` beside
its manifest and ``sync`` and ``check`` report what is missing, by name and
by the line that asked for it.

One declaration per line, comments and blanks dropped, in one of two forms::

    <name> [<version spec>] [:: <probe command>]
    env <NAME>

A probe decides by its exit code alone, under a short timeout: it is what a
tool with no name on ``PATH``, or one whose presence means more than a file
existing, declares. Without a probe the name is resolved on ``PATH``, and a
version spec is compared against the first version-shaped token of
``<tool> --version`` -- only when that token parses, because a tool free to
print anything for ``--version`` must not become a false missing report.

An environment variable is reported by name and never by value: a value
printed into a sync log is a secret in a terminal buffer.

Reading a declaration is inert; running a probe is running the item's
content. That is what trust grants, so an untrusted project ring item is
skipped whole and named with its remedy, exactly as its Python and Node
tooling is.

Stdlib only, cross-platform, Python 3.9 and up.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

try:
    from scripts import orchflows_envs
except ImportError:  # pragma: no cover - direct/installed flat script path
    import orchflows_envs


TOOLS_NAME = "tools.txt"
PROBE_SEPARATOR = "::"
PROBE_TIMEOUT = 10.0
ENV_KEYWORD = "env"
VERSION_FLAG = "--version"
TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# PEP 440's comparison operators, longest first so `==` cannot eat `===`.
SPEC_RE = re.compile(r"^(===|==|!=|<=|>=|~=|<|>)\s*([0-9][0-9A-Za-z.*+!-]*)$")
VERSION_TOKEN_RE = re.compile(r"\d+(?:\.\d+)*")
GRAMMAR = (
    "one declaration per line: '<name> [<version spec>] "
    "[:: <probe command>]', or 'env <NAME>'"
)


def tools_of(item_dir) -> Optional[Path]:
    """The item's tooling declaration beside its manifest, or ``None``."""

    candidate = Path(item_dir) / TOOLS_NAME
    return candidate if candidate.is_file() else None


def _specs(text: str):
    """``[(operator, version)]`` for one version spec, or ``None`` if it is not one."""

    parsed = []
    for clause in text.split(","):
        clause = clause.strip()
        if not clause:
            return None
        match = SPEC_RE.match(clause)
        if match is None:
            return None
        parsed.append((match.group(1), match.group(2)))
    return parsed


def parse_line(raw: str, number: int) -> Optional[Dict[str, object]]:
    """One line as a declaration, a problem, or ``None`` for nothing at all.

    A problem carries the same ``line``/``text`` a declaration does, so a
    caller reports a malformed line exactly where it reports a missing tool.
    """

    text = raw.split("#", 1)[0].strip()
    if not text:
        return None
    entry = {"line": number, "text": text}
    declaration, separator, probe = text.partition(PROBE_SEPARATOR)
    declaration, probe = declaration.strip(), probe.strip()
    if separator and not probe:
        return {**entry, "problem": f"'{PROBE_SEPARATOR}' with no probe command"}
    tokens = declaration.split()
    if not tokens:
        return {**entry, "problem": f"no tool name before '{PROBE_SEPARATOR}'"}
    if tokens[0] == ENV_KEYWORD:
        if separator:
            return {**entry, "problem": f"an '{ENV_KEYWORD}' line takes no probe"}
        if len(tokens) != 2 or not ENV_NAME_RE.fullmatch(tokens[1]):
            return {**entry, "problem": f"'{ENV_KEYWORD}' takes exactly one variable name"}
        return {**entry, "variable": tokens[1]}
    if not TOOL_NAME_RE.fullmatch(tokens[0]):
        return {**entry, "problem": f"'{tokens[0]}' is not a tool name; {GRAMMAR}"}
    specs = _specs(" ".join(tokens[1:])) if len(tokens) > 1 else []
    if specs is None:
        return {
            **entry,
            "problem": f"'{' '.join(tokens[1:])}' is not a version spec; {GRAMMAR}",
        }
    return {**entry, "name": tokens[0], "specs": specs, "probe": probe or None}


def declarations(tools: Path) -> Tuple[List[dict], List[dict]]:
    """``(declarations, problems)`` for one file: the grammar, and nothing else."""

    parsed, problems = [], []
    text = Path(tools).read_text(encoding="utf-8-sig")
    for number, raw in enumerate(text.splitlines(), start=1):
        entry = parse_line(raw, number)
        if entry is None:
            continue
        (problems if "problem" in entry else parsed).append(entry)
    return parsed, problems


# --- resolving one declaration ----------------------------------------


def _argv(command: str) -> List[str]:
    """A probe command as an argument vector.

    POSIX splitting eats the backslashes in a Windows path, so the native
    rules are used there and the quotes a caller wrote are stripped back off
    the tokens they surround.
    """

    if os.name != "nt":
        return shlex.split(command)
    tokens = shlex.split(command, posix=False)
    return [
        token[1:-1] if len(token) > 1 and token[0] == token[-1] == '"' else token
        for token in tokens
    ]


def executable(name: str, which: Optional[Callable[[str], Optional[str]]] = None) -> str:
    """The file ``PATH`` resolves a command name to, or the name unchanged.

    A spawn is not a shell. ``CreateProcess`` searches ``PATH`` but appends
    only ``.exe``, never the rest of ``PATHEXT``, so a bare ``npm`` cannot
    start on Windows, where node's package managers ship as ``npm.CMD``
    shims that ``PATH`` resolves perfectly well. Spawning what ``which``
    already found starts the same file on every platform. A name that
    resolves to nothing is returned unchanged, so a spawn that was going to
    fail still fails where it did.
    """

    resolved = (shutil.which if which is None else which)(name)
    return resolved or name


def run(
    argv: Sequence[str],
    timeout: float,
    *,
    which: Optional[Callable[[str], Optional[str]]] = None,
) -> Tuple[Optional[int], str]:
    """``(exit code, output)`` for one probe; ``None`` when it could not run.

    The head of ``argv`` is spawned as ``executable`` resolves it.
    """

    argv = list(argv)
    if argv:
        argv[0] = executable(str(argv[0]), which)
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def _version_tuple(text: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def _compare(found: str, operator: str, wanted: str) -> bool:
    """One PEP 440-shaped comparison, read over the release segment only."""

    if operator == "===":
        return found == wanted
    if not VERSION_TOKEN_RE.fullmatch(wanted):
        return True
    left, right = _version_tuple(found), _version_tuple(wanted)
    width = max(len(left), len(right))
    left += (0,) * (width - len(left))
    right += (0,) * (width - len(right))
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    # `~=`: at least this release, and the same series above the last digit.
    return left >= right and left[: len(right) - 1] == right[: len(right) - 1]


def resolve(
    entry: Dict[str, object],
    *,
    environ=None,
    which: Optional[Callable[[str], Optional[str]]] = None,
    runner: Optional[Callable[[Sequence[str], float], Tuple[Optional[int], str]]] = None,
) -> Optional[str]:
    """What is missing for one declaration, or ``None`` when it is satisfied."""

    environ = os.environ if environ is None else environ
    which = shutil.which if which is None else which
    runner = run if runner is None else runner
    variable = entry.get("variable")
    if variable is not None:
        if str(environ.get(str(variable), "")).strip():
            return None
        return f"environment variable {variable} is not set"
    name = str(entry["name"])
    probe = entry.get("probe")
    if probe:
        code, _output = runner(_argv(str(probe)), PROBE_TIMEOUT)
        if code == 0:
            return None
        if code is None:
            return f"probe '{probe}' could not run"
        return f"probe '{probe}' exited {code}"
    if which(name) is None:
        return f"'{name}' is not on PATH"
    specs = list(entry.get("specs") or [])
    if not specs:
        return None
    _code, output = runner([name, VERSION_FLAG], PROBE_TIMEOUT)
    found = VERSION_TOKEN_RE.search(output or "")
    if found is None:
        return None
    unmet = [
        f"{operator} {wanted}"
        for operator, wanted in specs
        if not _compare(found.group(0), operator, wanted)
    ]
    if not unmet:
        return None
    return f"'{name}' is {found.group(0)}, which does not satisfy {', '.join(unmet)}"


def check(item_dir, **overrides) -> List[Dict[str, object]]:
    """Every unmet declaration in one item's file, with the line that asked."""

    tools = tools_of(item_dir)
    if tools is None:
        return []
    parsed, problems = declarations(tools)
    reports = [
        {"line": entry["line"], "text": entry["text"], "detail": entry["problem"]}
        for entry in problems
    ]
    for entry in parsed:
        missing = resolve(entry, **overrides)
        if missing is not None:
            reports.append({"line": entry["line"], "text": entry["text"], "detail": missing})
    return sorted(reports, key=lambda report: report["line"])


def check_inventory(records: List[Dict[str, object]], **overrides) -> List[Dict[str, object]]:
    """Every declaring item in one inventory, reported and never installed.

    ``records`` is ``rings.inventory``'s output, the resolver dispatch reads,
    so what is checked here is what a launch of that item would need.
    """

    reports = []
    for record in records:
        if record.get("reserved"):
            continue
        item_dir = Path(str(record["dir"]))
        if tools_of(item_dir) is None:
            continue
        kind, name = str(record["kind"]), str(record["name"])
        if record.get("trust") == "untrusted":
            reports.append({
                "kind": kind, "name": name, "line": None, "text": None,
                "detail": orchflows_envs.UNTRUSTED_REMEDY.format(
                    kind=kind, name=name, bundle=item_dir.parent.parent,
                ),
            })
            continue
        for report in check(item_dir, **overrides):
            reports.append({"kind": kind, "name": name, **report})
    return reports


__all__ = (
    "ENV_KEYWORD", "ENV_NAME_RE", "GRAMMAR", "PROBE_SEPARATOR", "PROBE_TIMEOUT",
    "SPEC_RE", "TOOLS_NAME", "TOOL_NAME_RE", "VERSION_FLAG", "VERSION_TOKEN_RE",
    "check", "check_inventory", "declarations", "executable", "parse_line",
    "resolve", "run", "tools_of",
)
