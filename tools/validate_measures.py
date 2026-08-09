#!/usr/bin/env python3
"""Acceptance oracle for the BenchMaker measurement record.

Checks ``benchmarks/measures/benchmaker.md`` — the consumer-side record
that redesign-spec §3.2 places outside the sealed package — against the
entry idiom and the row schema. Stdlib only, no network. Exit 0 and
silent when the record is clean; exit 1 with one line per violation:

    ERROR <scope>: <message>

The flagless run is the acceptance oracle. ``--row <path>`` validates a
single row file in isolation, for a lane that has produced its row
before the rollup appends it; it checks the row schema only and never
stands in for the flagless run.

## The record's shape

The file opens with a preamble, then one ``## <YYYY-MM-DD> — <title>``
entry per measurement event, newest first. Each entry states, inside
itself, the ``benchmark_identity`` and ``set digest`` it covers, carries
an inline verify command, and holds one fenced ``json`` block per case
row. That block *is* the row: prose beside it explains and never
restates a field. A row file under the run's evidence store carries the
same block, so the rollup is a copy rather than a transcription.

An entry carries four ``###`` sections — ``Rungs``, ``Incomparability``,
``Measured scope``, ``Figures`` — and its rows. Three of them are read,
not merely counted:

* **Rungs** is a table keyed by rung name whose four remaining cells are
  model id, effort, host binding and scaffold. The model and effort a
  cell declares (its text up to the first comma, emphasis stripped) must
  be the model and effort every row records for that rung.
* **Measured scope** must name every protected path the covered
  ``manifest.json`` lists, and ``expected.md``, ``seeds/`` and ``probe/``
  as withheld from candidate contexts.
* **Figures** is a table keyed by figure name. Four of its figures are
  recomputed from the rows of the same entry and must agree with them:
  the status distribution (``<status> <count>`` pairs), the
  discriminating set and the inversions (each naming its case ids, or
  saying ``none``), and the margin in cases (its first number, equal to
  the strong rung's PASS count minus the weak rung's). ``resolution``
  states the literal ``max(measured rerun spread, 1 case)`` and then
  ``= <n> case(s)``; the spread it maxes against is stated elsewhere in
  the section as ``unmeasured`` or as a number of cases, and ``<n>`` must
  equal that maximum. The deterministic/judged fraction is required
  present and is not recomputable from the rows, which carry no
  oracle_class.

A figure the parser cannot read as a value is reported; a figure it can
read and that contradicts the rows is reported. Nothing is inferred.

## Completeness, conditional by design

An entry whose heading declares ``INCOMPLETE: N of 16 rows`` must carry
exactly N rows and must name every absent case in its body. An entry
without that declaration must carry one row per directory in
``cases/`` — sixteen — and a record whose case directory does not hold
sixteen cases is itself reported. That conditional is what lets an
incomplete record be honest instead of silent; deleting the declaration
is how a finished entry claims completeness, and the same code then
demands all sixteen rows.

## Row schema (frozen at T01-tracer-cs-cli-fresh)

Top level: ``case``, ``angle``, ``size``, ``trials_declared``,
``rungs``, ``status``, ``discriminating``, ``readings``,
``failed_checks``, ``scope``, ``observations``.

``rungs`` carries exactly ``strong`` and ``weak``, each with ``model``,
``effort_requested``, ``verdict``, ``artifact_identity``,
``artifact_path``, ``artifact_files``, ``manifest_benchmark_identity``,
``probe_exit_code``, ``trial_exit_codes``, ``probe_log``, ``canary``,
``bound`` and ``cost_actual``.

## Two decisions this checker encodes, both named in the record's gaps

**A fifth status.** The spec enumerates ``both-pass``, ``split``,
``both-fail`` and ``inversion``. None of the four is consistent with an
UNVERIFIED verdict, and forcing one would turn an UNVERIFIED into a PASS
or a FAIL, which ``scoring.md`` forbids. So ``undetermined`` is recorded
exactly when a verdict is UNVERIFIED, and never otherwise.

**Artifact identities resolve or they are violations.** A row's
``artifact_identity`` is recomputed over the bytes at ``artifact_path``
by the ``seal_set.py`` recipe applied to that subtree. ``.orch/`` is
gitignored runtime state, so once a run's evidence store is pruned these
identities stop resolving and this checker reports them. That is
deliberate: the alternative is an oracle that silently weakens the day
the store is deleted. Durable custody of the artifacts, or a law that
accepts an unresolvable identity, belongs to redesign-spec §10 step 2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import namedtuple
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RECORD = REPO_ROOT / "benchmarks" / "measures" / "benchmaker.md"
DEFAULT_CASES_DIR = REPO_ROOT / "benchmarks" / "benchmaker" / "cases"

# The seal this record covers. A measurement of a different seal is a
# different benchmark identity and updates these two constants with it.
BENCHMARK_IDENTITY = "sha256:0509fe444edad0f29e3ad5bdd5cf4aacf35dae6228c17d73fb6064014a660787"
SET_DIGEST = "sha256:75eb992563ba6f3258695ae7e06e8cff086daf74bfd4d01c8ad50b695aff4fcc"
CASE_COUNT = 16

SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
ENTRY_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2}) [—-] (.+)$")
INCOMPLETE = re.compile(r"INCOMPLETE: (\d+) of (\d+) rows")
FENCED_JSON = re.compile(r"^```json\n(.*?)^```", re.M | re.S)
IDENTITY_LINE = re.compile(r"benchmark_identity\s+(sha256:[0-9a-f]{64})")
SET_DIGEST_LINE = re.compile(r"set digest\s+(sha256:[0-9a-f]{64})")
VERIFY_COMMAND = re.compile(r"^ {4,}.*tools/validate_measures\.py", re.M)
TOML_SCALAR = re.compile(r'^(angle|size|exec_bound)\s*=\s*"(.*)"\s*$')
# 2026-08-09: `bound` became `exec_bound` and shed its construction half.
# A row recorded before that quotes the conflated string verbatim, and a
# record is a fact — it is not rewritten to match a later schema. Strip
# the construction clause before comparing, so the comparison still has
# teeth on the half that was ever a bound.
CONSTRUCTION_CLAUSE = re.compile(r"^\s*one BC\d+ share;\s*")
STATUS_COUNT = re.compile(r"(both-pass|both-fail|inversion|undetermined|split)\D{0,3}(\d+)")
RESOLUTION_VALUE = re.compile(r"=\s*(\d+(?:\.\d+)?)\s*cases?\b")
SPREAD = re.compile(r"spread[^.\n]{0,80}?\b(unmeasured|(\d+(?:\.\d+)?)\s*cases?)\b")
EMPTY_FIGURE = re.compile(r"\bnone\b|\bempty\b|\bno case", re.I)
FIRST_NUMBER = re.compile(r"-?\d+")

RUNGS = ("strong", "weak")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")
STATUSES = ("both-pass", "split", "both-fail", "inversion", "undetermined")
AMBIGUOUS = ("both-pass", "both-fail")
BOUND_STATUSES = ("within", "overrun", "unmeasured")

ROW_KEYS = (
    "case", "angle", "size", "trials_declared", "rungs", "status",
    "discriminating", "readings", "failed_checks", "scope", "observations",
)
RUNG_KEYS = (
    "model", "effort_requested", "verdict", "artifact_identity",
    "artifact_path", "artifact_files", "manifest_benchmark_identity",
    "probe_exit_code", "trial_exit_codes", "probe_log", "canary", "bound",
    "cost_actual",
)
BOUND_KEYS = ("declared", "probe_tier_ceiling_s", "probe_wall_clock_s", "status")
COST_KEYS = ("subagent_tokens", "tool_uses", "wall_ms", "attempts")
ENTRY_SECTIONS = ("Rungs", "Incomparability", "Measured scope", "Figures")
FIGURE_LABELS = (
    "status distribution", "discriminating set", "inversions",
    "margin in cases", "resolution", "deterministic",
)
RESOLUTION_FORMULA = "max(measured rerun spread, 1 case)"
# A10: the candidate-accessible restriction, and what candidates never see.
SCOPE_TOKENS = ("cs-antigoodhart-2/workload.json", "cs-nondet-fresh")
WITHHELD_TOKENS = ("expected.md", "seeds/", "probe/")
IDENTITY_STATEMENTS = (
    ("benchmark_identity", IDENTITY_LINE, BENCHMARK_IDENTITY),
    ("set digest", SET_DIGEST_LINE, SET_DIGEST),
)
SKIP_DIR_PREFIXES = (".", "_", "__")

Env = namedtuple("Env", "cases_dir cases resolve_root preamble_verify")


# --------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------


def _text(value):
    return isinstance(value, str) and value.strip() != ""


def _int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def tree_digest(root):
    """seal_set.py's recipe over one subtree: sorted per-file lock, hashed."""
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part.startswith(SKIP_DIR_PREFIXES) for part in relative.parts[:-1]):
            continue
        if relative.parts[-1].endswith(".pyc"):
            continue
        files.append(relative.as_posix())
    files.sort()
    lines = ["%s  %s" % (hashlib.sha256((root / f).read_bytes()).hexdigest(), f) for f in files]
    payload = ("".join(line + "\n" for line in lines)).encode("ascii")
    return "sha256:" + hashlib.sha256(payload).hexdigest(), len(lines)


def case_keys(cases_dir, case_id):
    """The angle/size/exec_bound a case declares, or {} when unreadable.

    A deliberately narrow read of the case.toml subset: these three keys
    are single-line basic strings in every case of the frozen set, and
    validate_cases.py already owns the general parser.
    """
    path = cases_dir / case_id / "case.toml"
    if not path.is_file():
        return {}
    found = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    for line in text.splitlines():
        match = TOML_SCALAR.match(line.strip())
        if match:
            found[match.group(1)] = match.group(2)
    return found


def derive_status(strong, weak):
    if "UNVERIFIED" in (strong, weak):
        return "undetermined"
    if strong == "PASS" and weak == "PASS":
        return "both-pass"
    if strong == "FAIL" and weak == "FAIL":
        return "both-fail"
    if strong == "PASS" and weak == "FAIL":
        return "split"
    return "inversion"


def derive_verdict(trials, declared, canary, bound_status):
    """scoring.md, applied to the recorded trials. Never guesses PASS."""
    unclean = (
        canary == "hit"
        or bound_status == "overrun"
        or not isinstance(trials, list)
        or len(trials) != declared
        or any(code not in (0, 1) for code in trials)
    )
    if unclean:
        return "UNVERIFIED"
    return "PASS" if all(code == 0 for code in trials) else "FAIL"


def governing_exit(trials):
    if not isinstance(trials, list) or not trials:
        return None
    for code in trials:
        if code != 0:
            return code
    return 0


# --------------------------------------------------------------------
# row schema
# --------------------------------------------------------------------


def check_bound(bound, declared_bound, label, fail):
    if not isinstance(bound, dict):
        fail("%s 'bound' is not an object" % label)
        return None
    for key in BOUND_KEYS:
        if key not in bound:
            fail("%s bound lacks '%s'" % (label, key))
    status = bound.get("status")
    if status not in BOUND_STATUSES:
        fail("%s bound status %r is not one of %s" % (label, status, list(BOUND_STATUSES)))
    recorded = bound.get("declared")
    if isinstance(recorded, str):
        recorded = CONSTRUCTION_CLAUSE.sub("", recorded)
    if declared_bound is not None and recorded != declared_bound:
        fail(
            "%s bound.declared %r does not match the case's declared execution bound %r"
            % (label, bound.get("declared"), declared_bound)
        )
    ceiling = bound.get("probe_tier_ceiling_s")
    wall = bound.get("probe_wall_clock_s")
    numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (ceiling, wall))
    if not numeric:
        fail("%s bound ceiling and wall clock must both be numbers" % label)
    elif wall > ceiling and status != "overrun":
        fail(
            "%s ran %.2f s against a %s s ceiling but bound status is %r, not 'overrun'"
            % (label, wall, ceiling, status)
        )
    return status


def check_cost(cost, label, fail):
    if not isinstance(cost, dict):
        fail("%s 'cost_actual' is not an object" % label)
        return
    for key in COST_KEYS:
        if key not in cost:
            fail("%s cost_actual lacks '%s'" % (label, key))
        elif not _int(cost[key]) or cost[key] < 0:
            fail("%s cost_actual '%s' must be a non-negative integer" % (label, key))
    if _int(cost.get("attempts")) and cost["attempts"] < 1:
        fail("%s cost_actual attempts must be at least 1" % label)


def check_rung(rung, name, row, declared_bound, resolve_root, fail):
    label = "rung %s" % name
    if not isinstance(rung, dict):
        fail("%s is not an object" % label)
        return None
    for key in RUNG_KEYS:
        if key not in rung:
            fail("%s lacks '%s'" % (label, key))

    for key in ("model", "effort_requested", "artifact_path", "probe_log"):
        if key in rung and not _text(rung[key]):
            fail("%s '%s' must be a non-empty string" % (label, key))

    for key in ("artifact_identity", "manifest_benchmark_identity"):
        value = rung.get(key)
        if key in rung and not (isinstance(value, str) and SHA256.match(value)):
            fail("%s '%s' is not a sha256:<64 hex> identity" % (label, key))

    if "artifact_files" in rung and not (_int(rung["artifact_files"]) and rung["artifact_files"] > 0):
        fail("%s artifact_files must be a positive integer" % label)

    canary = rung.get("canary")
    if canary not in ("clean", "hit"):
        fail("%s canary %r is not 'clean' or 'hit'" % (label, canary))

    bound_status = check_bound(rung.get("bound"), declared_bound, label, fail)
    check_cost(rung.get("cost_actual"), label, fail)

    trials = rung.get("trial_exit_codes")
    declared_trials = row.get("trials_declared")
    if not isinstance(trials, list) or not trials:
        fail("%s trial_exit_codes must be a non-empty list" % label)
        trials = None
    elif _int(declared_trials) and len(trials) != declared_trials:
        fail(
            "%s records %d trial exit code(s) against %d declared trial(s)"
            % (label, len(trials), declared_trials)
        )
    if trials is not None:
        for code in trials:
            if not (_int(code) or _text(code)):
                fail("%s trial exit code %r is neither an integer nor a named marker" % (label, code))
        expected_exit = governing_exit(trials)
        if rung.get("probe_exit_code") != expected_exit:
            fail(
                "%s probe_exit_code %r does not govern its trials %r (expected %r)"
                % (label, rung.get("probe_exit_code"), trials, expected_exit)
            )

    verdict = rung.get("verdict")
    if verdict not in VERDICTS:
        fail("%s verdict %r is not one of %s" % (label, verdict, list(VERDICTS)))
    elif trials is not None and _int(declared_trials):
        derived = derive_verdict(trials, declared_trials, canary, bound_status)
        if derived != verdict:
            fail(
                "%s records %s but its trials %r, canary %r and bound %r derive %s "
                "(scoring.md: PASS iff the probe exits 0 at the declared trial count; "
                "a crash, timeout, canary hit or bound overrun is UNVERIFIED)"
                % (label, verdict, trials, canary, bound_status, derived)
            )

    failed = row.get("failed_checks")
    if isinstance(failed, dict):
        listed = failed.get(name)
        if not isinstance(listed, list):
            fail("%s has no failed_checks list" % label)
        elif verdict == "PASS" and listed:
            fail("%s is PASS but lists failed checks %r" % (label, listed))
        elif verdict == "FAIL" and not listed:
            fail("%s is FAIL but names no failed check" % label)

    identity = rung.get("artifact_identity")
    path = rung.get("artifact_path")
    if resolve_root is not None and isinstance(identity, str) and _text(path):
        resolved = (resolve_root / path).resolve()
        if not resolved.is_dir():
            fail("%s artifact_path %r does not resolve to a directory" % (label, path))
        else:
            actual, count = tree_digest(resolved)
            if actual != identity:
                fail(
                    "%s artifact_identity %s does not recompute over %s (shipped %s)"
                    % (label, identity, path, actual)
                )
            elif _int(rung.get("artifact_files")) and rung["artifact_files"] != count:
                fail(
                    "%s artifact_files %d but %d files at %s"
                    % (label, rung["artifact_files"], count, path)
                )

    return verdict


def check_row(row, scope, cases_dir, resolve_root, errors):
    case_id = row.get("case") if isinstance(row, dict) else None
    name = case_id if _text(case_id) else scope

    def fail(message):
        errors.append("ERROR %s: %s" % (name, message))

    if not isinstance(row, dict):
        errors.append("ERROR %s: row is not a JSON object" % scope)
        return None
    for key in ROW_KEYS:
        if key not in row:
            fail("row lacks '%s'" % key)
    if not _text(case_id):
        fail("'case' must be a non-empty string")
        return None

    declared = case_keys(cases_dir, case_id)
    if not (cases_dir / case_id).is_dir():
        fail("no case directory '%s' under %s" % (case_id, cases_dir))
    for key in ("angle", "size"):
        if key in declared and row.get(key) != declared[key]:
            fail("'%s' is %r but case.toml declares %r" % (key, row.get(key), declared[key]))

    if not (_int(row.get("trials_declared")) and row["trials_declared"] > 0):
        fail("'trials_declared' must be a positive integer")

    if not _text(row.get("scope")):
        fail("'scope' must be a non-empty string naming what was and was not measured")
    observations = row.get("observations")
    if not (isinstance(observations, list) and observations and all(_text(o) for o in observations)):
        fail("'observations' must be a non-empty list of non-empty strings")

    failed = row.get("failed_checks")
    if not isinstance(failed, dict) or set(failed) != set(RUNGS):
        fail("'failed_checks' must be an object carrying exactly %s" % list(RUNGS))

    rungs = row.get("rungs")
    verdicts = {}
    if not isinstance(rungs, dict) or set(rungs) != set(RUNGS):
        fail("'rungs' must be an object carrying exactly %s" % list(RUNGS))
    else:
        for rung_name in RUNGS:
            verdicts[rung_name] = check_rung(
                rungs[rung_name], rung_name, row, declared.get("exec_bound"), resolve_root, fail
            )

    status = row.get("status")
    if status not in STATUSES:
        fail("status %r is not one of %s" % (status, list(STATUSES)))
    elif all(verdicts.get(r) in VERDICTS for r in RUNGS):
        derived = derive_status(verdicts["strong"], verdicts["weak"])
        if derived != status:
            fail(
                "status %r is inconsistent with verdicts strong=%s weak=%s (derives %r)"
                % (status, verdicts["strong"], verdicts["weak"], derived)
            )

    if row.get("discriminating") is not (status == "split"):
        fail("'discriminating' must be true exactly when status is 'split'")

    readings = row.get("readings")
    if not isinstance(readings, list):
        fail("'readings' must be a list")
    elif status in AMBIGUOUS and not [r for r in readings if _text(r)]:
        fail(
            "status %r admits two readings (redesign-spec §5) and 'readings' names neither; "
            "this run records both and resolves neither" % status
        )
    elif status not in AMBIGUOUS and readings:
        fail("status %r admits one reading, so 'readings' must be empty" % status)

    return case_id


# --------------------------------------------------------------------
# the record
# --------------------------------------------------------------------


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
    """One '### <name> …' block of an entry, heading included, or None."""
    match = re.search(r"^### %s\b.*?(?=^### |\Z)" % re.escape(name), body, re.M | re.S)
    return match.group(0) if match else None


def _plain(text):
    """Markdown emphasis removed, so a figure reads the same either way."""
    return text.replace("`", "").replace("*", "")


def table_cells(block):
    """{first cell, lowercased: cells} for a markdown table's data rows."""
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


def protected_files(cases_dir):
    """The protected paths the covered manifest names, or () when unreadable."""
    try:
        manifest = json.loads((cases_dir.parent / "manifest.json").read_text(encoding="utf-8"))
        files = manifest["protected_evidence"]["identity"]["files"]
    except (OSError, ValueError, KeyError, TypeError):
        return ()
    return tuple(sorted(files)) if isinstance(files, dict) else ()


def check_identity(body, fail):
    """A4: the entry names the seal it covers, and it is the covered seal."""
    for label, pattern, expected in IDENTITY_STATEMENTS:
        stated = pattern.findall(body)
        if not stated:
            fail("does not state the %s it covers" % label)
        elif expected not in stated:
            fail("states %s %s, which is not the covered %s" % (label, stated[0], expected))


def check_rungs(body, fail):
    """A9: model id, effort, host binding and scaffold per rung.

    Returns what the table declares per rung, for the rows to agree with.
    """
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
    """A9: no row may record a rung the Rungs table does not declare."""
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
    """A10: the candidate-accessible restriction, and every withheld input."""
    block = section(body, "Measured scope")
    if block is None:
        return
    for token in sorted(set(SCOPE_TOKENS) | set(protected_files(cases_dir))):
        if token not in block:
            fail("the measured scope does not name %s" % token)
    for token in WITHHELD_TOKENS:
        if token not in block:
            fail("the measured scope does not name %s as withheld from candidates" % token)


def check_resolution(block, stated, fail):
    """A11: resolution is max(measured rerun spread, 1 case), not a claim."""
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
    """A11: the §5 figures, each recomputed from the rows it summarizes."""
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
    """A5: sixteen rows, or a declaration that names every absent case."""
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

    check_identity(body, fail)
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


def check_row_file(path, cases_dir, resolve_root, errors):
    if not path.is_file():
        errors.append("ERROR row: no such file %s" % path)
        return
    blobs = FENCED_JSON.findall(path.read_text(encoding="utf-8"))
    if len(blobs) != 1:
        errors.append("ERROR row: %s carries %d fenced json blocks, expected exactly 1" % (path, len(blobs)))
        return
    try:
        row = json.loads(blobs[0])
    except ValueError as error:
        errors.append("ERROR row: %s does not parse: %s" % (path, error))
        return
    check_row(row, str(path), cases_dir, resolve_root, errors)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the BenchMaker measurement record.")
    parser.add_argument("--record", default=str(DEFAULT_RECORD), help="the measurement record")
    parser.add_argument("--cases-dir", default=str(DEFAULT_CASES_DIR), help="the sealed case directory")
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
