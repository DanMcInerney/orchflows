#!/usr/bin/env python3
"""Acceptance oracle for the BenchMaker measurement record.

Checks ``benchmarks/measures/benchmaker.md`` — the consumer-side record
of what a measurement pass read — against the entry idiom and the row
schema. Stdlib only, no network. Exit 0 and silent when the record is
clean; exit 1 with one line per violation::

    ERROR <scope>: <message>

The flagless run is the acceptance oracle. ``--row <path>`` validates a
single row file in isolation, for a lane that has produced its row
before the rollup appends it; it checks the row schema only and never
stands in for the flagless run.

The record opens with a preamble, then one newest-first
``## <YYYY-MM-DD> — <title>`` entry per event. Each entry names its case
set revision, carries an inline verify command, and holds one fenced
JSON block per case row. Its Rungs, Incomparability, Measured scope and
Figures sections are checked against those rows and the covered case
manifest.

An entry declaring ``INCOMPLETE: N of 16 rows`` must carry exactly N
rows and name every absent case. Without that declaration, all sixteen
case directories must have rows.

Rows carry the frozen BenchMaker schema. Their case declarations,
verdict derivation, artifact identities, protected evidence, report
figures and completeness are checked by the private support package;
this module remains the executable and import facade.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Direct script execution starts with ``tools/`` rather than the repository
# on sys.path. Bind the namespace package so the same relative imports serve
# both ``python tools/validate_measures.py`` and normal module imports.
# This walk cannot instead read ``scripts._bootstrap.ROOT``: it is what
# puts the repository (and therefore ``scripts/``) on sys.path in the
# first place.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "tools"

from .validate_measures_support.case_schema import CaseSchemaError, case_keys
from .validate_measures_support.common import (
    AMBIGUOUS,
    BOUND_KEYS,
    BOUND_STATUSES,
    CASE_COUNT,
    CASE_KEYS,
    CASE_SCHEMA_RULE,
    CASE_SET_LINE,
    CASE_SET_RULE,
    CONSTRUCTION_CLAUSE,
    COST_KEYS,
    DEFAULT_CASES_DIR,
    DEFAULT_RECORD,
    EMPTY_FIGURE,
    ENTRY_HEADING,
    ENTRY_SECTIONS,
    Env,
    FENCED_JSON,
    FIGURE_LABELS,
    FIRST_NUMBER,
    INCOMPLETE,
    PROTECTED_EVIDENCE_RULE,
    REPO_ROOT,
    RESOLUTION_FORMULA,
    RESOLUTION_VALUE,
    ROW_KEYS,
    RUNG_KEYS,
    RUNGS,
    SCOPE_TOKENS,
    SHA256,
    SKIP_DIR_PREFIXES,
    SPREAD,
    STATUSES,
    STATUS_COUNT,
    TOML_SCALAR,
    VERDICTS,
    VERIFY_COMMAND,
    WITHHELD_TOKENS,
    _int,
    _text,
    tree_digest,
)
from .validate_measures_support.protected_evidence import (
    ProtectedEvidenceError,
    protected_files,
)
from .validate_measures_support.record import (
    check_bound,
    check_cost,
    check_row,
    check_row_file,
    check_rung,
    derive_status,
    derive_verdict,
    governing_exit,
)
from .validate_measures_support.report import (
    _plain,
    check_case_set,
    check_completeness,
    check_entry,
    check_figures,
    check_record,
    check_resolution,
    check_rung_identity,
    check_rungs,
    check_scope,
    section,
    split_entries,
    table_cells,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the BenchMaker measurement record.")
    parser.add_argument("--record", default=str(DEFAULT_RECORD), help="the measurement record")
    parser.add_argument("--cases-dir", default=str(DEFAULT_CASES_DIR), help="the case directory")
    parser.add_argument(
        "--row",
        metavar="PATH",
        help="validate this row file alone, for a lane that has not yet been rolled up. "
        "Checks the row schema only; it never stands in for the flagless run.",
    )
    args = parser.parse_args(argv)

    cases_dir = Path(args.cases_dir).resolve()
    resolve_root = REPO_ROOT
    errors = []
    if args.row:
        check_row_file(Path(args.row).resolve(), cases_dir, resolve_root, errors)
    else:
        check_record(Path(args.record).resolve(), cases_dir, resolve_root, errors)

    for line in errors:
        print(line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
