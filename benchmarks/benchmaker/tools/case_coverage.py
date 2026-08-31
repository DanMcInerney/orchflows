"""Post-qualification manifest-field coverage checks."""
from __future__ import annotations

import ast
import json
import shlex
import shutil
import tempfile
from pathlib import Path

from case_toml import load_case_toml
from case_validation import (
    DEFAULT_PROBE_TIMEOUT,
    SIZE_TIMEOUTS,
    SKIP_DIR_PREFIXES,
    _nonempty_string,
    _relative,
    run_probe_output,
)

# ``example-workflows/references/benchmaker-manifest.md`` owns these eight.
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
        raise CoverageError("the probe command names no readable .py file inside the case")
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
    """Run a case's probe against a copy of ``target/`` with a mutated manifest."""
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
