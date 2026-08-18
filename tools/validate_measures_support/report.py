"""Parse and validate the human-readable measurement report."""

import json
import re

from .common import (
    CASE_COUNT,
    CASE_SET_LINE,
    CASE_SET_RULE,
    EMPTY_FIGURE,
    ENTRY_HEADING,
    ENTRY_SECTIONS,
    Env,
    FENCED_JSON,
    FIGURE_LABELS,
    FIRST_NUMBER,
    INCOMPLETE,
    PROTECTED_EVIDENCE_RULE,
    RESOLUTION_FORMULA,
    RESOLUTION_VALUE,
    RUNGS,
    SCOPE_TOKENS,
    SKIP_DIR_PREFIXES,
    SPREAD,
    STATUSES,
    STATUS_COUNT,
    VERIFY_COMMAND,
    WITHHELD_TOKENS,
    _text,
)
from .protected_evidence import ProtectedEvidenceError, protected_files
from .record import check_row


def split_entries(text):
    """Return (preamble, [(date, heading, body)]) in file order."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    preamble = "\n".join(lines[: starts[0]]) if starts else text
    entries = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(lines)
        heading = lines[start]
        match = ENTRY_HEADING.match(heading)
        date = match.group(1) if match else None
        entries.append((date, heading, "\n".join(lines[start:end])))
    return preamble, entries


def section(body, name):
    """One `### <name>` block of an entry, heading included, or None."""
    match = re.search(r"^### %s\b.*?(?=^### |\Z)" % re.escape(name), body, re.M | re.S)
    return match.group(0) if match else None


def _plain(text):
    """Remove Markdown emphasis so a figure reads the same either way."""
    return text.replace("`", "").replace("*", "")


def table_cells(block):
    """Return table data rows keyed by their lower-cased first cell."""
    rows = {}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        head = _plain(cells[0]).strip().lower()
        if head and set(head) - set("- "):
            rows.setdefault(head, cells)
    return rows


def check_case_set(body, fail):
    """Require the entry's measured case-set revision."""
    if not CASE_SET_LINE.search(body):
        fail(
            "%s: names no case set; state 'case set <git revision>' inside the entry, "
            "as 7 to 40 hex characters — never a content digest" % CASE_SET_RULE
        )


def check_rungs(body, fail):
    """Read the model and effort declared for each rung."""
    block = section(body, "Rungs")
    if block is None:
        return {}
    table = table_cells(block)
    declared = {}
    for name in RUNGS:
        cells = table.get(name)
        if cells is None:
            fail("the Rungs table has no '%s' row" % name)
        elif len(cells) < 5 or not all(_text(c) for c in cells[1:5]):
            fail(
                "rung '%s' must name model id, effort, host binding and scaffold "
                "(redesign-spec §7)" % name
            )
        else:
            declared[name] = {
                "model": _plain(cells[1]).split(",")[0].strip(),
                "effort_requested": _plain(cells[2]).split(",")[0].strip(),
            }
    return declared


def check_rung_identity(declared, summaries, fail):
    """Require rows to agree with the Rungs table's identities."""
    for case_id, _, _, rungs in summaries:
        for name in RUNGS:
            rung = rungs.get(name)
            if not isinstance(rung, dict):
                continue
            for key in ("model", "effort_requested"):
                want = declared.get(name, {}).get(key)
                got = rung.get(key)
                if want and _text(got) and got != want:
                    fail(
                        "row '%s' rung %s records %s %r but the Rungs table declares %r"
                        % (case_id, name, key, got, want)
                    )


def check_scope(body, cases_dir, fail):
    """Require the candidate-access restriction and withheld inputs."""
    block = section(body, "Measured scope")
    if block is None:
        return
    try:
        protected = protected_files(cases_dir)
    except ProtectedEvidenceError as error:
        fail("%s: %s" % (PROTECTED_EVIDENCE_RULE, error))
        protected = ()
    for token in sorted(set(SCOPE_TOKENS) | set(protected)):
        if token not in block:
            fail("the measured scope does not name %s" % token)
    for token in WITHHELD_TOKENS:
        if token not in block:
            fail("the measured scope does not name %s as withheld from candidates" % token)


def check_resolution(block, stated, fail):
    """Require resolution to equal max(measured rerun spread, 1 case)."""
    if RESOLUTION_FORMULA not in " ".join(stated.split()):
        fail("resolution must be stated as %s" % RESOLUTION_FORMULA)
    asserted = RESOLUTION_VALUE.search(stated)
    if asserted is None:
        fail("resolution states no value; state it as '= <n> case(s)'")
        return
    haystack = " ".join(_plain(block).replace(RESOLUTION_FORMULA, " ").split())
    spread = SPREAD.search(haystack)
    if spread is None:
        fail("the Figures section does not state the measured rerun spread resolution maxes against")
        return
    floor = 1.0 if spread.group(2) is None else float(spread.group(2))
    expected = max(floor, 1.0)
    if float(asserted.group(1)) != expected:
        fail(
            "resolution is stated as %s case(s) but max(measured rerun spread %s, 1 case) is %g"
            % (asserted.group(1), spread.group(1), expected)
        )


def check_figures(body, summaries, cases, fail):
    """Recompute the report's figures from the rows they summarize."""
    block = section(body, "Figures")
    if block is None:
        return
    table = table_cells(block)
    value = {}
    for label in FIGURE_LABELS:
        keys = [key for key in sorted(table) if label in key]
        if not keys:
            fail("the Figures section has no '%s' row" % label)
        else:
            cells = table[keys[0]]
            value[label] = _plain(cells[1]) if len(cells) > 1 else ""

    counts = dict.fromkeys(STATUSES, 0)
    for _, status, _, _ in summaries:
        if status in counts:
            counts[status] += 1
    distribution = value.get("status distribution")
    if distribution is not None:
        pairs = {name: int(number) for name, number in STATUS_COUNT.findall(distribution)}
        if not pairs:
            fail("the status distribution states no count per status (e.g. 'split 3; both-pass 8')")
        for name in sorted(pairs):
            if pairs[name] != counts[name]:
                fail(
                    "the status distribution states %s %d but %d row(s) carry it"
                    % (name, pairs[name], counts[name])
                )
        for name in sorted(counts):
            if counts[name] and name not in pairs:
                fail("the status distribution omits %s, which %d row(s) carry" % (name, counts[name]))

    for label, status in (("discriminating set", "split"), ("inversions", "inversion")):
        if label not in value:
            continue
        actual = {case for case, row_status, _, _ in summaries if row_status == status}
        named = {case for case in cases if case in value[label]}
        if named != actual:
            fail(
                "the %s figure names %s but the rows carry %s"
                % (label, sorted(named) or "no case", sorted(actual) or "no case")
            )
        elif not actual and not EMPTY_FIGURE.search(value[label]):
            fail("the %s figure is empty and must say so" % label)

    if "margin in cases" in value:
        passes = {
            name: sum(1 for _, _, verdicts, _ in summaries if verdicts.get(name) == "PASS")
            for name in RUNGS
        }
        derived = passes["strong"] - passes["weak"]
        number = FIRST_NUMBER.search(value["margin in cases"])
        if number is None:
            fail("the margin figure states no number of cases")
        elif int(number.group(0)) != derived:
            fail(
                "the margin figure states %s but the rows derive %d (strong %d PASS, weak %d PASS)"
                % (number.group(0), derived, passes["strong"], passes["weak"])
            )

    if "resolution" in value:
        check_resolution(block, value["resolution"], fail)


def check_completeness(heading, body, seen, cases, cases_dir, fail):
    """Require sixteen rows or an honest declaration of every absence."""
    duplicates = sorted({case for case in seen if seen.count(case) > 1})
    for case_id in duplicates:
        fail("case '%s' appears in more than one row" % case_id)

    declared_incomplete = INCOMPLETE.search(heading)
    missing = [case for case in cases if case not in seen]
    if declared_incomplete:
        count, denominator = (int(group) for group in declared_incomplete.groups())
        if denominator != len(cases):
            fail("declares %d cases but %s holds %d" % (denominator, cases_dir, len(cases)))
        if count != len(seen):
            fail("declares %d of %d rows but carries %d" % (count, denominator, len(seen)))
        for case_id in missing:
            if case_id not in body:
                fail("is incomplete and does not name the absent case '%s'" % case_id)
    else:
        for case_id in missing:
            fail(
                "has no row for case '%s', and its heading does not declare the entry "
                "incomplete" % case_id
            )


def check_entry(date, heading, body, env, errors):
    label = "entry %s" % (date or heading.strip("# ").strip())

    def fail(message):
        errors.append("ERROR %s: %s" % (label, message))

    if date is None:
        fail("heading is not '## <YYYY-MM-DD> — <title>'")
    if not env.preamble_verify and not VERIFY_COMMAND.search(body):
        fail("names no inline command that verifies it, and neither does the preamble")

    check_case_set(body, fail)
    for name in ENTRY_SECTIONS:
        if section(body, name) is None:
            fail("has no '### %s' section" % name)
    statement = section(body, "Incomparability")
    if statement is not None and len(statement.split("\n", 1)[-1].split()) < 20:
        fail("states no incomparability: §7 binds a score to target × model × harness × benchmark")
    check_scope(body, env.cases_dir, fail)
    declared = check_rungs(body, fail)

    rows = []
    for blob in FENCED_JSON.findall(body):
        try:
            rows.append(json.loads(blob))
        except ValueError as error:
            fail("a fenced json row does not parse: %s" % error)
    if not rows:
        fail("carries no case row")

    seen, summaries = [], []
    for index, row in enumerate(rows):
        case_id = check_row(row, "%s row %d" % (label, index + 1), env.cases_dir, env.resolve_root, errors)
        if case_id is None:
            continue
        seen.append(case_id)
        rungs = row.get("rungs") if isinstance(row.get("rungs"), dict) else {}
        verdicts = {
            name: rungs[name].get("verdict")
            for name in RUNGS
            if isinstance(rungs.get(name), dict)
        }
        summaries.append((case_id, row.get("status"), verdicts, rungs))

    check_rung_identity(declared, summaries, fail)
    check_figures(body, summaries, env.cases, fail)
    check_completeness(heading, body, seen, env.cases, env.cases_dir, fail)


def check_record(record, cases_dir, resolve_root, errors):
    if not record.is_file():
        errors.append("ERROR record: no such file %s" % record)
        return
    text = record.read_text(encoding="utf-8")
    preamble, entries = split_entries(text)
    if not entries:
        errors.append("ERROR record: carries no entry")
        return

    dates = [date for date, _, _ in entries if date]
    if dates != sorted(dates, reverse=True):
        errors.append("ERROR record: entries are not newest-first (%s)" % ", ".join(dates))

    cases = []
    if not cases_dir.is_dir():
        errors.append("ERROR record: no case directory %s" % cases_dir)
    else:
        cases = sorted(
            entry.name for entry in cases_dir.iterdir()
            if entry.is_dir() and not entry.name.startswith(SKIP_DIR_PREFIXES)
        )
        if len(cases) != CASE_COUNT:
            errors.append(
                "ERROR record: %s holds %d cases, not the frozen %d"
                % (cases_dir, len(cases), CASE_COUNT)
            )

    env = Env(cases_dir, cases, resolve_root, bool(VERIFY_COMMAND.search(preamble)))
    for date, heading, body in entries:
        check_entry(date, heading, body, env, errors)
