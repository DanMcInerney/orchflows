"""Validate measurement row records and derive their verdicts."""

import json

from .case_schema import CaseSchemaError, case_keys
from .common import (
    AMBIGUOUS,
    BOUND_KEYS,
    BOUND_STATUSES,
    CASE_SCHEMA_RULE,
    CONSTRUCTION_CLAUSE,
    COST_KEYS,
    FENCED_JSON,
    ROW_KEYS,
    RUNG_KEYS,
    RUNGS,
    SHA256,
    STATUSES,
    VERDICTS,
    _int,
    _text,
    tree_digest,
)


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
    """Apply scoring.md to recorded trials without guessing PASS."""
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

    value = rung.get("artifact_identity")
    if "artifact_identity" in rung and not (isinstance(value, str) and SHA256.match(value)):
        fail("%s 'artifact_identity' is not a sha256:<64 hex> identity" % label)

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

    declared = {}
    if not (cases_dir / case_id).is_dir():
        fail("no case directory '%s' under %s" % (case_id, cases_dir))
    else:
        try:
            declared = case_keys(cases_dir, case_id)
        except CaseSchemaError as error:
            fail("%s: %s" % (CASE_SCHEMA_RULE, error))
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
