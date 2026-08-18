"""Schema, path, seed, and probe checks for benchmaker cases."""
from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

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

STRING_KEYS = (
    "id",
    "angle",
    "outcome",
    "target",
    "probe",
    "port",
    "tests",
    "provenance",
)
LIST_KEYS = ("evidence", "expected_qualification")
SCHEMA_KEYS = frozenset(
    STRING_KEYS + LIST_KEYS + ("exec_bound", "negative", "size", "parallel_safe")
)
# Construction allocation is not a candidate-facing execution bound.
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
    if declared_target and (
        declared_target == "target" or declared_target.startswith("target/")
    ):
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
    env["PYTHONDONTWRITEBYTECODE"] = "1"
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
            isinstance(data[key], list)
            and all(_nonempty_string(value) for value in data[key])
        ):
            fail("'{}' must be a list of non-empty strings".format(key))
    if "exec_bound" in data:
        bound = data["exec_bound"]
        ok = _nonempty_string(bound) or (
            isinstance(bound, int) and not isinstance(bound, bool) and bound > 0
        )
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
                fail("'exec_bound' names a probe tier other than size = '{}'".format(tier))
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
            fail(
                "parallel_safe = false requires 'parallel_risk' naming the "
                "corruption mechanism"
            )
    if _nonempty_string(data.get("id")) and data["id"] != name:
        fail("id '{}' does not match the directory name".format(data["id"]))
    for value in data.get("expected_qualification", []) or []:
        if isinstance(value, str) and value not in QUALIFICATIONS:
            fail(
                "expected_qualification '{}' is not one of {}".format(
                    value, sorted(QUALIFICATIONS)
                )
            )
    if (
        isinstance(data.get("expected_qualification"), list)
        and not data["expected_qualification"]
    ):
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
    if not bad:
        fail("no bad seed, so probe inversion is unproved")
        return
    for seed in bad:
        code, detail = run_probe(case_dir, command, declared, seed, timeout)
        if code is None:
            fail("probe against {}: {}".format(seed.name, detail))
        elif code == 0:
            fail("probe must fail seed {} but it passed".format(seed.name))
