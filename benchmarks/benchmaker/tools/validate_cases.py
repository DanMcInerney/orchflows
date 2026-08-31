#!/usr/bin/env python3
"""Acceptance oracle and compatibility facade for the benchmaker case set.

Checks every ``cases/<id>/`` package against the frozen case schema: schema
completeness, the angle/case bijection with the sixteen-row matrix, referenced
paths, seed rules, negative-case rules, probe inversion, and post-qualification
field coverage.  Exit 0 is silent when the set is clean; exit 1 prints one
``ERROR <case-id>: <message>`` line per violation.

The implementation is partitioned by ownership: ``case_toml`` parses the
documented TOML subset, ``case_validation`` owns schema and runtime checks,
and ``case_coverage`` owns the manifest-field census.  Their established names
remain importable here so this file stays the normative CLI and import facade.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

from case_coverage import (
    COVERAGE_CLASSES,
    COVERAGE_MARK,
    DECLARATION,
    POST_QUALIFICATION_FIELDS,
    CoverageError,
    _dropper,
    _gap_records,
    _single_manifest,
    census_errors,
    coverage_census,
    coverage_probe_errors,
    declared_coverage,
    probe_a_mutated_target,
    probe_source,
    probed_fields,
    probed_fields_from_source,
    recorded_gaps,
)
from case_toml import (
    TomlError,
    _Incomplete,
    _array,
    _escape,
    _integer,
    _quoted,
    _skip,
    _table,
    _triple,
    _value,
    load_case_toml,
    parse_toml,
)
from case_validation import (
    BRACE_TOKENS,
    BUILDER_CONTEXT_RE,
    CONDITIONAL_KEYS,
    DEFAULT_PROBE_TIMEOUT,
    HOST_PARALLELISM_ENV_VAR,
    LIST_KEYS,
    MATRIX,
    NEAR_MISS_MARKS,
    QUALIFICATIONS,
    SCHEMA_KEYS,
    SIZE_TIMEOUTS,
    SKIP_DIR_PREFIXES,
    STRING_KEYS,
    _first_line,
    _nonempty_string,
    _relative,
    check_angle,
    check_negative,
    check_paths,
    check_probe,
    check_schema,
    check_seeds,
    collect_seeds,
    host_parallelism,
    render_probe,
    run_probe,
    run_probe_output,
)

DEFAULT_CASES_DIR = HERE.parent / "cases"


def check_case(case_dir, angle_owner, errors, declarations=None):
    """Validate one case and append stable error lines to ``errors``."""
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
    parser.add_argument(
        "--cases-dir",
        default=str(DEFAULT_CASES_DIR),
        help="directory holding the case packages",
    )
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
                    "ERROR cases: matrix row '{}' has no valid case (expected '{}')".format(
                        angle, case_id
                    )
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
