#!/usr/bin/env python3
"""Acceptance oracle for the benchmaker case set.

Checks every ``cases/<id>/`` package against the frozen case schema:
schema completeness, the angle/case bijection with the sixteen-row
matrix, existence of every referenced path, the seed rules, the
negative-case rules, and probe inversion — each case's probe must pass
the reference target and every good seed and fail every bad seed.

Stdlib only, no network. Exit 0 and silent when the set is clean; exit 1
with one line per violation:

    ERROR <case-id>: <message>

The case.toml subset this reads is: bare keys, one ``key = value`` per
logical line, plus plain table headers. Values are strings (single-line
or triple quoted, literal or basic), booleans, decimal integers, and
arrays of those. Types: ``id``, ``angle``, ``outcome``, ``target``,
``probe``, ``port``, ``tests`` and ``provenance`` are non-empty
strings; ``tests`` is the case's one-line statement of what it tests
and must be a single line; ``provenance`` names the artifact that
licenses the case; ``size`` is ``small``, ``medium`` or
``large`` and sets the per-probe-run timeout (60, 300, 900 s);
``parallel_safe`` is a boolean, and when it is false the case must
carry ``parallel_risk``, a non-empty string naming the mechanism by
which concurrent runs corrupt each other (forbidden when true);
``exec_bound`` is a non-empty string or a positive integer and carries
the **candidate-facing execution bound only** — the probe tier it names
must agree with ``size``, and it may not name a builder context
(``BC1``-``BC6``), because the construction allocation is
evaluation-design.md section 8's and telling a candidate how a case was
authored is a leak, not a bound; ``evidence`` and
``expected_qualification`` are lists of strings; ``negative`` is a
boolean. Every bad seed's ``defect.md`` carries exactly one
``deviation:`` line naming the deviation that produced it. Declared
paths are relative to
the case directory and use forward slashes. Where ``tomllib`` is
available the file is parsed twice and the two results must agree, so a
case.toml that drifts out of the subset is reported rather than
silently misread.

A probe runs once per implementation directory — ``target/`` first, then
each ``seeds/good*/`` and each ``seeds/bad-*/`` — with the case
directory as its working directory and ``CASE_IMPL`` and ``CASE_DIR``
exported. Exit 0 is a pass, any other status a fail. The command names
the implementation under test in whichever of three ways it prefers:

1. the tokens ``{impl}`` (the implementation directory), ``{target}``
   (the declared ``target`` path with its leading segment swapped for
   that directory) and ``{case_dir}``, substituted before tokenizing;
2. otherwise, the literal declared ``target`` value appearing as one
   argument, which is swapped for the implementation's equivalent;
3. otherwise, the implementation directory appended as a final argument
   — with nothing naming a file, the directory is the only unambiguous
   thing to hand over.

Substituted paths are case-relative and use forward slashes; the two
environment variables carry absolute paths.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # tomllib is 3.11+; this file supports 3.9.
    tomllib = None

HERE = Path(__file__).resolve().parent
DEFAULT_CASES_DIR = HERE.parent / "cases"
SIZE_TIMEOUTS = {"small": 60, "medium": 300, "large": 900}
DEFAULT_PROBE_TIMEOUT = 300

# Frozen by the run spec's angle matrix: angle -> case id.
MATRIX = {
    "deterministic-cli": "cs-cli-fresh",
    "time-semantics": "cs-ratelimit-fresh",
    "judged-outcome": "cs-judged-fresh",
    "anti-goodhart": "cs-antigoodhart-2",
    "refusal": "cs-refusal-2",
    "sparse-evidence": "cs-sparse-fresh",
    "contradiction": "cs-contradiction-fresh",
    "multi-domain": "cs-multidomain-fresh",
    "stateful": "cs-stateful-fresh",
    "nondeterminism": "cs-nondet-fresh",
    "cost-pressure": "cs-cost-fresh",
    "workflow-target": "cs-workflow-fresh",
    "ranking": "cs-ranking-fresh",
    "intake-refusal": "cs-intake-refusal",
    "run-conduct": "cs-run-conduct",
    "package-audit": "cs-package-audit",
}

STRING_KEYS = ("id", "angle", "outcome", "target", "probe", "port", "tests", "provenance")
LIST_KEYS = ("evidence", "expected_qualification")
SCHEMA_KEYS = frozenset(
    STRING_KEYS + LIST_KEYS + ("exec_bound", "negative", "size", "parallel_safe")
)
# The construction allocation belongs to evaluation-design.md section 8's
# capacity plan, never to a candidate-facing key. A builder-context token
# in exec_bound tells the candidate how the case was authored.
BUILDER_CONTEXT_RE = re.compile(r"\bBC\d+\b")
CONDITIONAL_KEYS = frozenset(("parallel_risk",))
QUALIFICATIONS = frozenset(
    (
        "discrimination",
        "reproducibility",
        "cost-within-bound",
        "schema-valid",
        "gaps-declared",
        "blocked-return",
    )
)
NEAR_MISS_MARKS = ("near-miss", "near miss")
SKIP_DIR_PREFIXES = (".", "_")
BRACE_TOKENS = ("{impl}", "{target}", "{case_dir}")


# --------------------------------------------------------------------
# the case.toml subset
# --------------------------------------------------------------------


class TomlError(Exception):
    """The file is outside the subset, or malformed."""


class _Incomplete(Exception):
    """The value continues on the next line."""


_ESCAPES = {"b": "\b", "t": "\t", "n": "\n", "f": "\f", "r": "\r", '"': '"', "\\": "\\"}
_HEX = "0123456789abcdefABCDEF"
_BARE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def _skip(text, i, newlines):
    while i < len(text):
        char = text[i]
        if char in " \t":
            i += 1
        elif char in "\r\n":
            if not newlines:
                return i
            i += 1
        elif char == "#":
            while i < len(text) and text[i] not in "\r\n":
                i += 1
        else:
            return i
    return i


def _escape(text, i):
    if i + 1 >= len(text):
        raise _Incomplete()
    char = text[i + 1]
    if char in _ESCAPES:
        return _ESCAPES[char], i + 2
    if char in "uU":
        width = 4 if char == "u" else 8
        digits = text[i + 2 : i + 2 + width]
        if len(digits) < width:
            raise _Incomplete()
        if any(d not in _HEX for d in digits):
            raise TomlError("bad unicode escape \\{}{}".format(char, digits))
        return chr(int(digits, 16)), i + 2 + width
    raise TomlError("unsupported escape \\{}".format(char))


def _quoted(text, i, quote, escapes):
    out = []
    j = i + 1
    while True:
        if j >= len(text):
            raise _Incomplete()
        char = text[j]
        if char in "\r\n":
            raise TomlError("newline inside a single-line string")
        if char == quote:
            return "".join(out), j + 1
        if escapes and char == "\\":
            decoded, j = _escape(text, j)
            out.append(decoded)
            continue
        out.append(char)
        j += 1


def _triple(text, i, delim, escapes):
    j = i + 3
    if text.startswith("\n", j):
        j += 1
    out = []
    while True:
        if j >= len(text):
            raise _Incomplete()
        if text.startswith(delim, j):
            return "".join(out), j + 3
        char = text[j]
        if escapes and char == "\\":
            k = j + 1
            while k < len(text) and text[k] in " \t":
                k += 1
            if k >= len(text):
                raise _Incomplete()
            if text[k] in "\r\n":
                while k < len(text) and text[k] in " \t\r\n":
                    k += 1
                j = k
                continue
            decoded, j = _escape(text, j)
            out.append(decoded)
            continue
        out.append(char)
        j += 1


def _integer(text, i):
    j = i
    if j < len(text) and text[j] in "+-":
        j += 1
    start = j
    while j < len(text) and (text[j].isdigit() or text[j] == "_"):
        j += 1
    digits = text[start:j].replace("_", "")
    if not digits:
        return None
    return int(text[i:start] + digits), j


def _array(text, i):
    items = []
    j = i + 1
    while True:
        j = _skip(text, j, newlines=True)
        if j >= len(text):
            raise _Incomplete()
        if text[j] == "]":
            return items, j + 1
        item, j = _value(text, j, newlines=True)
        items.append(item)
        j = _skip(text, j, newlines=True)
        if j >= len(text):
            raise _Incomplete()
        if text[j] == ",":
            j += 1
            continue
        if text[j] == "]":
            return items, j + 1
        raise TomlError("expected ',' or ']' inside an array")


def _value(text, i, newlines):
    i = _skip(text, i, newlines)
    if i >= len(text):
        raise _Incomplete()
    if text.startswith('"""', i):
        return _triple(text, i, '"""', True)
    if text.startswith("'''", i):
        return _triple(text, i, "'''", False)
    char = text[i]
    if char == '"':
        return _quoted(text, i, '"', True)
    if char == "'":
        return _quoted(text, i, "'", False)
    if char == "[":
        return _array(text, i)
    if text.startswith("true", i):
        return True, i + 4
    if text.startswith("false", i):
        return False, i + 5
    parsed = _integer(text, i)
    if parsed is not None:
        return parsed
    raise TomlError("unsupported value syntax at {!r}".format(text[i : i + 24]))


def _table(data, header):
    """Enter the table named by a ``[header]`` line."""
    if header.startswith("[["):
        raise TomlError("arrays of tables are outside the case schema")
    if not header.endswith("]"):
        raise TomlError("malformed table header: {!r}".format(header))
    name = header[1:-1].strip()
    if not name:
        raise TomlError("empty table header")
    table = data
    for part in name.split("."):
        part = part.strip()
        if not part or any(c not in _BARE for c in part):
            raise TomlError("table names must be bare: {!r}".format(name))
        table = table.setdefault(part, {})
        if not isinstance(table, dict):
            raise TomlError("key {!r} redefined as a table".format(part))
    return table


def parse_toml(text):
    """Parse the case.toml subset. Raises TomlError outside it."""
    data = {}
    table = data
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        index += 1
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            table = _table(data, stripped)
            continue
        key, sep, rest = stripped.partition("=")
        key = key.strip()
        if not sep:
            raise TomlError("not a 'key = value' line: {!r}".format(stripped))
        if not key or any(c not in _BARE for c in key):
            raise TomlError("keys must be bare: {!r}".format(key))
        if key in table:
            raise TomlError("duplicate key {!r}".format(key))
        buffer = rest
        while True:
            try:
                value, end = _value(buffer, 0, newlines=False)
            except _Incomplete:
                if index >= len(lines):
                    raise TomlError("unterminated value for key {!r}".format(key))
                buffer += "\n" + lines[index]
                index += 1
                continue
            if _skip(buffer, end, newlines=True) != len(buffer):
                raise TomlError("trailing text after the value for key {!r}".format(key))
            table[key] = value
            break
    return data


def load_case_toml(path):
    text = path.read_text(encoding="utf-8")
    data = parse_toml(text)
    if tomllib is not None:
        try:
            reference = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise TomlError("invalid TOML: {}".format(error))
        if reference != data:
            raise TomlError(
                "this validator's parser and tomllib disagree; keep case.toml "
                "inside the subset documented in validate_cases.py"
            )
    return data


# --------------------------------------------------------------------
# checks
# --------------------------------------------------------------------


def _nonempty_string(value):
    return isinstance(value, str) and value.strip() != ""


def _relative(case_dir, declared):
    """Resolve a declared path, or return None when it is not usable."""
    if "\\" in declared:
        return None
    if declared.startswith("/") or (len(declared) > 1 and declared[1] == ":"):
        return None
    target = os.path.normpath(os.path.join(str(case_dir), declared))
    root = os.path.normpath(str(case_dir))
    if not (target == root or target.startswith(root + os.sep)):
        return None
    return Path(target)


def _first_line(raw):
    text = raw.decode("utf-8", "replace").strip() if isinstance(raw, bytes) else str(raw)
    return text.splitlines()[0].strip() if text.strip() else ""


def render_probe(command, declared_target, impl_rel):
    """Tokenize the probe command with the implementation substituted in."""
    swapped = impl_rel
    if declared_target and (declared_target == "target" or declared_target.startswith("target/")):
        swapped = impl_rel + declared_target[len("target") :]
    braced = any(token in command for token in BRACE_TOKENS)
    rendered = command
    if braced:
        rendered = (
            command.replace("{impl}", impl_rel)
            .replace("{target}", swapped)
            .replace("{case_dir}", ".")
        )
    argv = shlex.split(rendered)
    if not argv:
        raise ValueError("probe command is empty")
    if braced:
        return argv
    if declared_target and declared_target in argv:
        return [swapped if item == declared_target else item for item in argv]
    return argv + [impl_rel]


def run_probe_output(case_dir, command, declared_target, impl_dir, timeout):
    """Return (returncode, output). returncode is None when it could not run."""
    impl_rel = impl_dir.relative_to(case_dir).as_posix()
    try:
        argv = render_probe(command, declared_target, impl_rel)
    except ValueError as error:
        return None, "probe command does not tokenize: {}".format(error)
    env = dict(os.environ)
    env["CASE_IMPL"] = str(impl_dir)
    env["CASE_DIR"] = str(case_dir)
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # validation never writes into a case
    try:
        done = subprocess.run(
            argv,
            cwd=str(case_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except FileNotFoundError:
        return None, "probe command not found: {}".format(argv[0])
    except OSError as error:
        return None, "probe command failed to start: {}".format(error)
    except subprocess.TimeoutExpired:
        return None, "probe exceeded {} s".format(timeout)
    return done.returncode, (done.stderr + done.stdout).decode("utf-8", "replace")


def run_probe(case_dir, command, declared_target, impl_dir, timeout):
    """Return (returncode, detail). returncode is None when it could not run."""
    code, output = run_probe_output(case_dir, command, declared_target, impl_dir, timeout)
    return (code, output) if code is None else (code, _first_line(output))


def check_schema(data, name, fail):
    for key in sorted(SCHEMA_KEYS - set(data)):
        fail("case.toml is missing required key '{}'".format(key))
    for key in sorted(set(data) - SCHEMA_KEYS - CONDITIONAL_KEYS):
        fail("case.toml carries key '{}', outside the frozen schema".format(key))
    for key in STRING_KEYS:
        if key in data and not _nonempty_string(data[key]):
            fail("'{}' must be a non-empty string".format(key))
    for key in LIST_KEYS:
        if key in data and not (
            isinstance(data[key], list) and all(_nonempty_string(v) for v in data[key])
        ):
            fail("'{}' must be a list of non-empty strings".format(key))
    if "exec_bound" in data:
        bound = data["exec_bound"]
        ok = _nonempty_string(bound) or (isinstance(bound, int) and not isinstance(bound, bool) and bound > 0)
        if not ok:
            fail("'exec_bound' must be a non-empty string or a positive integer")
        elif isinstance(bound, str):
            if BUILDER_CONTEXT_RE.search(bound):
                fail(
                    "'exec_bound' names a builder context; the construction "
                    "allocation belongs to evaluation-design.md, not to a "
                    "candidate-facing key"
                )
            tier = data.get("size")
            if tier in SIZE_TIMEOUTS and "tier" in bound and tier not in bound:
                fail(
                    "'exec_bound' names a probe tier other than size = '{}'".format(tier)
                )
    if "negative" in data and not isinstance(data["negative"], bool):
        fail("'negative' must be a boolean")
    if _nonempty_string(data.get("tests")) and "\n" in data["tests"].strip():
        fail("'tests' must be a single line")
    if "size" in data and data["size"] not in SIZE_TIMEOUTS:
        fail("'size' must be one of {}".format(sorted(SIZE_TIMEOUTS)))
    if "parallel_safe" in data:
        safe = data["parallel_safe"]
        if not isinstance(safe, bool):
            fail("'parallel_safe' must be a boolean")
        elif safe and "parallel_risk" in data:
            fail("'parallel_risk' is only allowed when parallel_safe is false")
        elif not safe and not _nonempty_string(data.get("parallel_risk")):
            fail("parallel_safe = false requires 'parallel_risk' naming the corruption mechanism")
    if _nonempty_string(data.get("id")) and data["id"] != name:
        fail("id '{}' does not match the directory name".format(data["id"]))
    for value in data.get("expected_qualification", []) or []:
        if isinstance(value, str) and value not in QUALIFICATIONS:
            fail("expected_qualification '{}' is not one of {}".format(value, sorted(QUALIFICATIONS)))
    if isinstance(data.get("expected_qualification"), list) and not data["expected_qualification"]:
        fail("expected_qualification must name at least one requirement")


def check_angle(data, name, angle_owner, fail):
    angle = data.get("angle")
    if not _nonempty_string(angle):
        return
    if angle not in MATRIX:
        fail("angle '{}' is not a row of the frozen matrix".format(angle))
        return
    if MATRIX[angle] != name:
        fail("angle '{}' belongs to case '{}' in the matrix".format(angle, MATRIX[angle]))
        return
    if angle in angle_owner:
        fail("angle '{}' is already claimed by case '{}'".format(angle, angle_owner[angle]))
        return
    angle_owner[angle] = name


def check_paths(case_dir, data, fail):
    for required in ("target", "evidence"):
        if not (case_dir / required).is_dir():
            fail("no {}/ directory".format(required))
    expected = case_dir / "expected.md"
    if not expected.is_file():
        fail("no expected.md")
    elif not expected.read_text(encoding="utf-8").strip():
        fail("expected.md is empty")
    declared = data.get("target")
    if _nonempty_string(declared):
        resolved = _relative(case_dir, declared)
        if resolved is None:
            fail("target '{}' must be a relative forward-slash path inside the case".format(declared))
        elif not resolved.exists():
            fail("target '{}' does not exist".format(declared))
    for item in data.get("evidence", []) or []:
        if not isinstance(item, str):
            continue
        resolved = _relative(case_dir, item)
        if resolved is None:
            fail("evidence '{}' must be a relative forward-slash path inside the case".format(item))
            continue
        if not resolved.exists():
            fail("evidence '{}' does not exist".format(item))
        if item.split("/")[0] == "seeds":
            fail("evidence '{}' points into seeds/; builders never see seeds".format(item))


def collect_seeds(case_dir, fail):
    seeds_dir = case_dir / "seeds"
    good, bad = [], []
    if not seeds_dir.is_dir():
        return good, bad
    for entry in sorted(seeds_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith(SKIP_DIR_PREFIXES):
            continue
        if entry.name.startswith("bad-"):
            bad.append(entry)
        elif entry.name.startswith("good"):
            good.append(entry)
        else:
            fail("seed '{}' is named neither good* nor bad-<slug>".format(entry.name))
    return good, bad


def check_seeds(bad, negative, fail):
    near_miss = 0
    for seed in bad:
        defect = seed / "defect.md"
        if not defect.is_file():
            fail("seed '{}' has no defect.md".format(seed.name))
            continue
        text = defect.read_text(encoding="utf-8")
        if not text.strip():
            fail("seed '{}' has an empty defect.md".format(seed.name))
            continue
        deviations = [
            line
            for line in text.splitlines()
            if line.startswith("deviation:") and line[len("deviation:") :].strip()
        ]
        if len(deviations) != 1:
            fail(
                "seed '{}' defect.md must carry exactly one 'deviation:' line, found {}".format(
                    seed.name, len(deviations)
                )
            )
        haystack = (text + " " + seed.name).lower()
        if any(mark in haystack for mark in NEAR_MISS_MARKS):
            near_miss += 1
    if negative:
        return
    if len(bad) < 3:
        fail("positive cases need at least 3 bad seeds, found {}".format(len(bad)))
    if near_miss < 1:
        fail("no bad seed is declared a near-miss in its defect.md or its name")


def check_negative(case_dir, data, fail):
    if "blocked-return" not in (data.get("expected_qualification") or []):
        fail("negative cases must expect 'blocked-return' qualification")
    expected = case_dir / "expected.md"
    if not expected.is_file():
        return
    text = expected.read_text(encoding="utf-8").lower()
    if "blocked" not in text:
        fail("expected.md must state the expected blocked return")
    if "gap" not in text:
        fail("expected.md must state the expected gap content")


def check_probe(case_dir, data, good, bad, fail):
    command = data.get("probe")
    if not _nonempty_string(command):
        return
    timeout = SIZE_TIMEOUTS.get(data.get("size"), DEFAULT_PROBE_TIMEOUT)
    declared = data.get("target") if _nonempty_string(data.get("target")) else ""
    passing = [("target", case_dir / "target")]
    passing.extend((seed.name, seed) for seed in good)
    for label, impl in passing:
        code, detail = run_probe(case_dir, command, declared, impl, timeout)
        if code is None:
            fail("probe against {}: {}".format(label, detail))
        elif code != 0:
            fail("probe must pass {} but exited {} ({})".format(label, code, detail or "no output"))
    # Negative cases are waived the three-bad-seed floor, never waived
    # inversion: with nothing to fail, a working probe and a permanently
    # broken one read the same, so the absence is reported, not skipped.
    if not bad:
        fail("no bad seed, so probe inversion is unproved")
        return
    for seed in bad:
        code, detail = run_probe(case_dir, command, declared, seed, timeout)
        if code is None:
            fail("probe against {}: {}".format(seed.name, detail))
        elif code == 0:
            fail("probe must fail seed {} but it passed".format(seed.name))


# --------------------------------------------------------------------
# post-qualification field coverage
# --------------------------------------------------------------------

# `compositions/references/benchmaker-manifest.md` owns these eight. None is
# re-derivable after the fact, so a candidate that omits one ships a package
# no consumer can repair. Each probe declares the fields it requires in a
# module-level `PROBED_MANIFEST_FIELDS` mapping, read here without importing
# the probe; a declaration is then proved by removing the field from a copy
# of the case's target and watching the probe fail. A field no angle reaches,
# and a case that reaches none, are legal only when the package manifest
# records the gap.
POST_QUALIFICATION_FIELDS = (
    "anchors",
    "builders",
    "reference_audit",
    "attack_audit",
    "measurement",
    "resolution",
    "retirement_trigger",
    "incomparability",
)
COVERAGE_CLASSES = ("constrained", "presence-only")
COVERAGE_MARK = "manifest field coverage:"
DECLARATION = "PROBED_MANIFEST_FIELDS"


class CoverageError(Exception):
    """A coverage declaration cannot be read, or is not a declaration."""


def probed_fields_from_source(source, label="probe"):
    """The probe's declared field -> coverage class, without importing it."""
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        raise CoverageError("{} does not parse: {}".format(label, error))
    found = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == DECLARATION
            for target in node.targets
        ):
            continue
        try:
            found = ast.literal_eval(node.value)
        except (ValueError, SyntaxError):
            raise CoverageError(
                "{} assigns {} something that is not a literal mapping".format(
                    label, DECLARATION
                )
            )
    if found is None:
        return {}
    if not isinstance(found, dict):
        raise CoverageError("{}'s {} is not a mapping".format(label, DECLARATION))
    return found


def probe_source(case_dir, command):
    """The probe file a case's command runs, resolved inside the case."""
    try:
        tokens = shlex.split(command or "")
    except ValueError:
        return None
    for token in tokens:
        if not token.endswith(".py"):
            continue
        resolved = _relative(case_dir, token)
        if resolved is not None and resolved.is_file():
            return resolved
    return None


def probed_fields(case_dir, command):
    path = probe_source(case_dir, command)
    if path is None:
        raise CoverageError(
            "the probe command names no readable .py file inside the case"
        )
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        raise CoverageError("cannot read {}: {}".format(path.name, error))
    return probed_fields_from_source(source, path.name)


def declared_coverage(cases_dir):
    """case id -> declared {field: class}, over every case directory."""
    declared = {}
    for entry in sorted(Path(cases_dir).iterdir()):
        if not entry.is_dir() or entry.name.startswith(SKIP_DIR_PREFIXES):
            continue
        data = load_case_toml(entry / "case.toml")
        declared[entry.name] = probed_fields(entry, data.get("probe"))
    return declared


def recorded_gaps(package_dir):
    """The package manifest's `gaps`. Unreadable is refused, never empty."""
    path = Path(package_dir) / "manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CoverageError("cannot read {}: {}".format(path, error))
    gaps = manifest.get("gaps")
    if not isinstance(gaps, list):
        raise CoverageError("{} states no 'gaps' list".format(path))
    return [gap for gap in gaps if isinstance(gap, str)]


def coverage_census(declared):
    """field -> the case ids that probe it, for all eight fields."""
    census = dict((field, []) for field in POST_QUALIFICATION_FIELDS)
    for case_id in sorted(declared):
        for field in sorted(declared[case_id] or {}):
            if field in census:
                census[field].append(case_id)
    return census


def _gap_records(gaps, sentence):
    return any("{} {}".format(COVERAGE_MARK, sentence) in gap for gap in gaps)


def census_errors(declared, gaps):
    """Every field probed by a case or recorded as a gap, and the reverse."""
    out = []
    for case_id in sorted(declared):
        fields = declared[case_id] or {}
        for field in sorted(fields):
            if field not in POST_QUALIFICATION_FIELDS:
                out.append(
                    "ERROR {}: '{}' is not a post-qualification field".format(
                        case_id, field
                    )
                )
            if fields[field] not in COVERAGE_CLASSES:
                out.append(
                    "ERROR {}: coverage class '{}' is not one of {}".format(
                        case_id, fields[field], list(COVERAGE_CLASSES)
                    )
                )
        sentence = "{} probes no field".format(case_id)
        if not fields and not _gap_records(gaps, sentence):
            out.append(
                "ERROR cases: {} probes no post-qualification field and the manifest "
                "records no gap '{} {}'".format(case_id, COVERAGE_MARK, sentence)
            )
    census = coverage_census(declared)
    for field in POST_QUALIFICATION_FIELDS:
        sentence = "no case probes '{}'".format(field)
        if not census[field] and not _gap_records(gaps, sentence):
            out.append(
                "ERROR cases: {} and the manifest records no gap '{} {}'".format(
                    sentence, COVERAGE_MARK, sentence
                )
            )
    return out


def _single_manifest(root):
    found = [path for path in sorted(root.rglob("manifest.json")) if path.is_file()]
    return found[0] if len(found) == 1 else None


def probe_a_mutated_target(case_dir, mutate):
    """Run a case's probe against a copy of `target/` with a mutated manifest."""
    case_dir = Path(case_dir)
    data = load_case_toml(case_dir / "case.toml")
    scratch = tempfile.mkdtemp(prefix="case-coverage-")
    try:
        copy = Path(scratch) / case_dir.name
        shutil.copytree(str(case_dir), str(copy))
        manifest_path = _single_manifest(copy / "target")
        if manifest_path is None:
            return None, "target carries no single manifest.json to mutate"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mutate(manifest)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        declared = data.get("target") if _nonempty_string(data.get("target")) else ""
        return run_probe_output(
            copy,
            data.get("probe") or "",
            declared,
            copy / "target",
            SIZE_TIMEOUTS.get(data.get("size"), DEFAULT_PROBE_TIMEOUT),
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _dropper(field):
    def mutate(manifest):
        manifest.pop(field, None)

    return mutate


def coverage_probe_errors(case_dir, declared):
    """A declared field the probe does not actually require is not coverage."""
    out = []
    case_dir = Path(case_dir)
    for field in sorted(declared or {}):
        if field not in POST_QUALIFICATION_FIELDS:
            continue
        code, detail = probe_a_mutated_target(case_dir, _dropper(field))
        if code is None:
            out.append(
                "ERROR {}: the coverage probe could not run: {}".format(
                    case_dir.name, detail
                )
            )
        elif code == 0:
            out.append(
                "ERROR {}: the probe still passes with '{}' removed from the target "
                "manifest, so declaring it probed states more than the probe "
                "enforces".format(case_dir.name, field)
            )
    return out


def check_case(case_dir, angle_owner, errors, declarations=None):
    name = case_dir.name

    def fail(message):
        errors.append("ERROR {}: {}".format(name, message))

    toml_path = case_dir / "case.toml"
    if not toml_path.is_file():
        fail("no case.toml")
        return
    try:
        data = load_case_toml(toml_path)
    except TomlError as error:
        fail("case.toml: {}".format(error))
        return
    except OSError as error:
        fail("case.toml unreadable: {}".format(error))
        return

    check_schema(data, name, fail)
    check_angle(data, name, angle_owner, fail)
    check_paths(case_dir, data, fail)
    negative = data.get("negative") is True
    good, bad = collect_seeds(case_dir, fail)
    check_seeds(bad, negative, fail)
    if negative:
        check_negative(case_dir, data, fail)
    check_probe(case_dir, data, good, bad, fail)
    try:
        declared = probed_fields(case_dir, data.get("probe"))
    except CoverageError as error:
        fail("coverage declaration: {}".format(error))
        return
    if declarations is not None:
        declarations[name] = declared
    errors.extend(coverage_probe_errors(case_dir, declared))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the benchmaker case set.")
    parser.add_argument("--cases-dir", default=str(DEFAULT_CASES_DIR), help="directory holding the case packages")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="CASE_ID",
        help="validate only this case; repeatable. Drops the requirement that all "
        "sixteen matrix rows be present, so it never stands in for the full run.",
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="print the post-qualification field census, one field per line, and stop.",
    )
    args = parser.parse_args(argv)

    cases_dir = Path(args.cases_dir).resolve()
    errors = []
    if not cases_dir.is_dir():
        print("ERROR cases: no such directory {}".format(cases_dir))
        return 1

    found = {
        entry.name: entry
        for entry in sorted(cases_dir.iterdir())
        if entry.is_dir() and not entry.name.startswith(SKIP_DIR_PREFIXES)
    }
    if args.only:
        for wanted in args.only:
            if wanted not in found:
                errors.append("ERROR cases: no case directory '{}'".format(wanted))
        selected = [found[name] for name in args.only if name in found]
    else:
        selected = list(found.values())

    if args.coverage:
        try:
            census = coverage_census(declared_coverage(cases_dir))
            declared = declared_coverage(cases_dir)
        except (CoverageError, TomlError, OSError) as error:
            print("ERROR cases: coverage census: {}".format(error))
            return 1
        for field in POST_QUALIFICATION_FIELDS:
            covering = census[field]
            classes = sorted({declared[case][field] for case in covering})
            print(
                "{}\t{}\t{}".format(
                    field,
                    ",".join(classes) or "uncovered",
                    " ".join(covering) or "-",
                )
            )
        return 0

    angle_owner = {}
    declarations = {}
    for case_dir in selected:
        check_case(case_dir, angle_owner, errors, declarations)

    if not args.only:
        for angle, case_id in sorted(MATRIX.items()):
            if angle not in angle_owner:
                errors.append(
                    "ERROR cases: matrix row '{}' has no valid case (expected '{}')".format(angle, case_id)
                )
        try:
            errors.extend(census_errors(declarations, recorded_gaps(cases_dir.parent)))
        except CoverageError as error:
            errors.append("ERROR cases: coverage census: {}".format(error))

    for line in errors:
        print(line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
