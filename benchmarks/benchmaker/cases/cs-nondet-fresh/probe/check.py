#!/usr/bin/env python3
"""Probe for cs-nondet-fresh — P0.a-P0.d plus nd.1-nd.3.

Invoked per the case's probe key:

    uv run --no-project python probe/check.py {impl}

cwd is the case directory; {impl} is target/ or one seeds/* package.
Exit 0 = pass; exit 1 with one FAIL line per violated check.

Checks:
- P0.a manifest present with the ten schema fields; benchmark_identity
  recomputes from the canonical payload.
- P0.b every component reference's sha256 verifies over the shipped
  bytes at its locator (file digest, or the tree digest defined below).
- P0.c qualification entries are verdict-contract complete.
- P0.d the package's own runner+scoring discriminates over the case's
  evidence/inner-impls/ pool at the declared trial count.
- nd.1 scoring declares trial count k >= 3 with the all-trials law;
  a synthetic pass-2-of-3 record aggregates to FAIL.
- nd.2 one case is anchored to evidence/trace.md's exhibited run, or
  provenance records an impossibility reason that is not
  "implementation artifact".
- nd.3 when BENCH_PROTECTED_DIR is set: discrimination also holds on
  the held-back streams, and no exhibited file contains a held-back
  stream constant. Silently skipped when unset (validator context).

Structural trial law: the probe runs the inner sampler the declared
number of times — every case's result must carry exactly the declared
trial count.

Tree digest rule (matches the package builder): a file's digest is
sha256 over its bytes; a directory's digest is sha256 over the UTF-8
encoding of "<posix-relpath>:<file-sha256-hex>" lines for every file
under it, sorted by relpath, joined with "\n". __pycache__ is excluded.

Scratch-copy hygiene: the implementation and the inner pool are copied
to a temporary directory before any execution; nothing under the case
directory is written.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MANIFEST_FIELDS = frozenset(
    (
        "benchmark_identity",
        "evaluation_design",
        "runnable_cases",
        "runner",
        "scoring",
        "provenance",
        "qualification",
        "expected_cost",
        "gaps",
        "protected_evidence",
    )
)
COMPONENT_FIELDS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
ENTRY_FIELDS = ("criterion", "verdict", "oracle", "oracle_class", "evidence", "covers", "required")
VERDICTS = ("PASS", "FAIL", "UNVERIFIED")
ORACLE_CLASSES = ("deterministic", "judged", "evidence")
SUBPROC_TIMEOUT = 240


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def tree_digest(path):
    path = Path(path)
    if path.is_file():
        return "sha256:" + sha256_hex(path.read_bytes())
    entries = []
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        rel = item.relative_to(path).as_posix()
        if "__pycache__" in rel.split("/"):
            continue
        entries.append(rel + ":" + sha256_hex(item.read_bytes()))
    return "sha256:" + sha256_hex("\n".join(entries).encode("utf-8"))


def canonical_identity(manifest):
    payload = {key: value for key, value in manifest.items() if key != "benchmark_identity"}
    data = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + sha256_hex(data.encode("utf-8"))


def resolve_locator(pkg, locator):
    if not isinstance(locator, str) or not locator or "\\" in locator:
        return None
    if locator.startswith("/") or (len(locator) > 1 and locator[1] == ":"):
        return None
    resolved = os.path.normpath(os.path.join(str(pkg), locator))
    root = os.path.normpath(str(pkg))
    if not (resolved == root or resolved.startswith(root + os.sep)):
        return None
    return Path(resolved)


def child_env():
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_python(args, cwd, stdin_bytes=None):
    return subprocess.run(
        [sys.executable] + [str(a) for a in args],
        cwd=str(cwd),
        env=child_env(),
        input=stdin_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=SUBPROC_TIMEOUT,
    )


def check_p0a(pkg, errors):
    manifest_path = pkg / "manifest.json"
    if not manifest_path.is_file():
        errors.append("P0.a: no manifest.json at the package root")
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as error:
        errors.append("P0.a: manifest.json is not valid JSON: {}".format(error))
        return None
    fields = set(manifest)
    for missing in sorted(MANIFEST_FIELDS - fields):
        errors.append("P0.a: manifest is missing field '{}'".format(missing))
    for extra in sorted(fields - MANIFEST_FIELDS):
        errors.append("P0.a: manifest carries field '{}' outside the schema".format(extra))
    if MANIFEST_FIELDS - fields:
        return manifest
    recorded = manifest.get("benchmark_identity")
    if not isinstance(recorded, str) or not recorded.startswith("sha256:"):
        errors.append("P0.a: benchmark_identity is not a sha256: value")
        return manifest
    recomputed = canonical_identity(manifest)
    if recomputed != recorded:
        errors.append(
            "P0.a: benchmark_identity does not recompute (recorded {}, recomputed {})".format(
                recorded, recomputed
            )
        )
    return manifest


def check_p0b(pkg, manifest, errors):
    for name in COMPONENT_FIELDS:
        ref = manifest.get(name)
        if not isinstance(ref, dict) or "identity" not in ref or "locator" not in ref:
            errors.append("P0.b: component '{}' is not an identity+locator reference".format(name))
            continue
        resolved = resolve_locator(pkg, ref["locator"])
        if resolved is None or not resolved.exists():
            errors.append("P0.b: component '{}' locator '{}' does not resolve inside the package".format(name, ref["locator"]))
            continue
        actual = tree_digest(resolved)
        if actual != ref["identity"]:
            errors.append(
                "P0.b: component '{}' digest mismatch at '{}' (recorded {}, actual {})".format(
                    name, ref["locator"], ref["identity"], actual
                )
            )


def check_p0c(pkg, manifest, errors):
    ref = manifest.get("qualification")
    if not isinstance(ref, dict):
        return
    resolved = resolve_locator(pkg, ref.get("locator", ""))
    if resolved is None:
        return
    qual_path = resolved / "qualification.json" if resolved.is_dir() else resolved
    if not qual_path.is_file():
        errors.append("P0.c: no qualification.json under '{}'".format(ref.get("locator")))
        return
    try:
        qual = json.loads(qual_path.read_text(encoding="utf-8"))
    except ValueError as error:
        errors.append("P0.c: qualification.json is not valid JSON: {}".format(error))
        return
    if "gaps" not in qual or not isinstance(qual["gaps"], list):
        errors.append("P0.c: qualification 'gaps' field must be an explicit list ([] allowed)")
    overall = qual.get("overall")
    if overall not in VERDICTS:
        errors.append("P0.c: qualification 'overall' must be one of {}".format(list(VERDICTS)))
    entries = qual.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.append("P0.c: qualification carries no entries")
        return
    required_fail = False
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append("P0.c: entry {} is not an object".format(index))
            continue
        for field in ENTRY_FIELDS:
            if field not in entry:
                errors.append("P0.c: entry {} is missing '{}'".format(index, field))
        if entry.get("verdict") not in VERDICTS:
            errors.append("P0.c: entry {} verdict must be one of {}".format(index, list(VERDICTS)))
        if entry.get("oracle_class") not in ORACLE_CLASSES:
            errors.append("P0.c: entry {} oracle_class must be one of {}".format(index, list(ORACLE_CLASSES)))
        if not isinstance(entry.get("required"), bool):
            errors.append("P0.c: entry {} 'required' must be a boolean".format(index))
        evidence = entry.get("evidence")
        if entry.get("verdict") == "PASS" and not (isinstance(evidence, str) and evidence.strip()):
            errors.append("P0.c: entry {} is PASS with an empty evidence field".format(index))
        if entry.get("verdict") == "FAIL" and entry.get("required") is True:
            required_fail = True
    if overall == "PASS" and required_fail:
        errors.append("P0.c: overall PASS coexists with a required FAIL")


def load_scoring(pkg, errors):
    policy_path = pkg / "scoring" / "policy.json"
    cases_path = pkg / "cases" / "cases.json"
    policy, cases = None, None
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        errors.append("scoring/policy.json unreadable: {}".format(error))
    try:
        cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    except (OSError, ValueError, KeyError) as error:
        errors.append("cases/cases.json unreadable: {}".format(error))
    return policy, cases


def check_nd1(pkg, policy, work, errors):
    trial_count = policy.get("trial_count") if isinstance(policy, dict) else None
    if not isinstance(trial_count, int) or isinstance(trial_count, bool) or trial_count < 3:
        errors.append("nd.1: scoring must declare an integer trial count >= 3")
        return None
    if policy.get("aggregation") != "all-trials":
        errors.append("nd.1: scoring must declare the all-trials aggregation law, found {!r}".format(policy.get("aggregation")))
    synthetic = {"cases": [{"id": "synthetic", "trials": ["PASS"] * (trial_count - 1) + ["FAIL"]}]}
    synth_path = work / "synthetic-results.json"
    synth_path.write_text(json.dumps(synthetic), encoding="utf-8")
    proc = run_python(
        [pkg / "scoring" / "aggregate.py", synth_path, "--policy", pkg / "scoring" / "policy.json"],
        cwd=work,
    )
    if proc.returncode == 0:
        errors.append("nd.1: a pass-{}-of-{} record aggregates to PASS; all-trials law violated".format(trial_count - 1, trial_count))
    return trial_count


def score_impl(pkg, impl_dir, work, label, cases_override=None):
    """Run the package's runner+scoring; return (aggregate_rc, results, note)."""
    results_path = work / ("results-" + label + ".json")
    args = [pkg / "runner" / "run.py", impl_dir, "--out", results_path]
    if cases_override is not None:
        args += ["--cases", cases_override]
    proc = run_python(args, cwd=work)
    if proc.returncode != 0:
        return None, None, "runner exited {}: {}".format(
            proc.returncode, proc.stderr.decode("utf-8", "replace").strip()[:200]
        )
    try:
        results = json.loads(results_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return None, None, "runner produced no readable results: {}".format(error)
    agg = run_python(
        [pkg / "scoring" / "aggregate.py", results_path, "--policy", pkg / "scoring" / "policy.json"],
        cwd=work,
    )
    return agg.returncode, results, None


def impl_expectation(name):
    if name == "reference" or name.startswith("good"):
        return "pass"
    return "fail"


def check_p0d(pkg, pool, trial_count, work, errors, cases_override=None, tag="P0.d"):
    impls = sorted(p for p in pool.iterdir() if p.is_dir())
    if not impls:
        errors.append(tag + ": inner pool is empty")
        return
    for impl in impls:
        rc, results, note = score_impl(pkg, impl, work, tag.replace(".", "") + "-" + impl.name, cases_override)
        if note is not None:
            errors.append("{}: {}: {}".format(tag, impl.name, note))
            continue
        if isinstance(trial_count, int):
            for case in results.get("cases", []):
                if len(case.get("trials", [])) != trial_count:
                    errors.append(
                        "{}: {}: case '{}' ran {} trials, declared {}".format(
                            tag, impl.name, case.get("id"), len(case.get("trials", [])), trial_count
                        )
                    )
        expected = impl_expectation(impl.name)
        if expected == "pass" and rc != 0:
            errors.append("{}: inner impl '{}' must pass but aggregated FAIL".format(tag, impl.name))
        if expected == "fail" and rc == 0:
            errors.append("{}: inner impl '{}' must fail but aggregated PASS".format(tag, impl.name))


def parse_trace(trace_path, errors):
    trace = {}
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        for key in ("items", "sample"):
            if line.startswith(key + ":"):
                trace[key] = [part.strip() for part in line[len(key) + 1 :].split(",") if part.strip()]
        for key in ("seed", "k"):
            if line.startswith(key + ":"):
                try:
                    trace[key] = int(line[len(key) + 1 :].strip())
                except ValueError:
                    errors.append("nd.2: trace.md carries a non-integer {}".format(key))
    for key in ("items", "seed", "k", "sample"):
        if key not in trace:
            errors.append("nd.2: trace.md is missing '{}:'".format(key))
            return None
    return trace


def check_nd2(pkg, cases, trace, errors):
    if trace is None or cases is None:
        return
    for case in cases:
        if case.get("anchor") != "evidence/trace.md":
            continue
        if case.get("stream") != trace["items"] or case.get("seed") != trace["seed"] or case.get("k") != trace["k"]:
            errors.append("nd.2: anchored case does not match the exhibited run's stream/seed/k")
            return
        expected = case.get("expected")
        if not isinstance(expected, list) or not expected:
            errors.append("nd.2: anchored case must pin its expected trials explicitly")
            return
        if expected[0] != trace["sample"]:
            errors.append("nd.2: anchored case trial 0 does not pin the exhibited sample")
        return
    for name in ("notes.md", "evaluation-design.md"):
        path = pkg / "provenance" / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().lower().startswith("anchor-impossibility:"):
                reason = line.split(":", 1)[1].strip()
                if reason and reason.lower() != "implementation artifact":
                    return
                errors.append("nd.2: anchor-impossibility reason is empty or an implementation artifact")
                return
    errors.append("nd.2: no case is anchored to evidence/trace.md and no impossibility reason is recorded")


def scan_for_constants(roots, constants, errors):
    needles = [c for c in constants if isinstance(c, str) and len(c) >= 6]
    if not needles:
        return
    for root in roots:
        for item in sorted(Path(root).rglob("*")):
            if not item.is_file():
                continue
            try:
                text = item.read_bytes().decode("utf-8", "replace")
            except OSError:
                continue
            for needle in needles:
                if needle in text:
                    errors.append(
                        "nd.3: exhibited file '{}' contains a held-back stream constant".format(item)
                    )
                    return


def check_nd3(pkg, pool, trial_count, work, case_dir, errors):
    protected = os.environ.get("BENCH_PROTECTED_DIR")
    if not protected:
        return  # degrade to public-subset checks (validator context)
    store = Path(protected)
    if not store.is_dir():
        errors.append("nd.3: BENCH_PROTECTED_DIR is set but is not a directory")
        return
    streams = sorted(store.glob("stream-*.json"))
    if not streams:
        return
    cases, constants = [], []
    for path in streams:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            errors.append("nd.3: protected stream '{}' unreadable: {}".format(path.name, error))
            continue
        cases.append(
            {
                "id": "protected-" + str(data.get("id", path.stem)),
                "stream": data["items"],
                "seed": data["seed"],
                "k": data["k"],
                "expected": None,
            }
        )
        constants.extend(data["items"])
    if not cases:
        return
    override = work / "protected-cases.json"
    override.write_text(json.dumps({"cases": cases}), encoding="utf-8")
    check_p0d(pkg, pool, trial_count, work, errors, cases_override=override, tag="nd.3")
    scan_for_constants([pkg, case_dir / "evidence"], constants, errors)


def main(argv):
    if len(argv) != 2:
        print("FAIL: usage: check.py <impl-dir>")
        return 1
    case_dir = Path(os.environ.get("CASE_DIR") or os.getcwd()).resolve()
    impl_src = Path(argv[1])
    if not impl_src.is_absolute():
        impl_src = (case_dir / impl_src).resolve()
    errors = []
    if not impl_src.is_dir():
        print("FAIL: implementation directory '{}' does not exist".format(argv[1]))
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="cs-nondet-probe-"))
    try:
        pkg = tmp / "pkg"
        shutil.copytree(str(impl_src), str(pkg))
        pool = tmp / "inner-impls"
        shutil.copytree(str(case_dir / "evidence" / "inner-impls"), str(pool))
        work = tmp / "work"
        work.mkdir()

        manifest = check_p0a(pkg, errors)
        if manifest is not None and not (MANIFEST_FIELDS - set(manifest)):
            check_p0b(pkg, manifest, errors)
            check_p0c(pkg, manifest, errors)
        policy, cases = load_scoring(pkg, errors)
        trial_count = None
        if policy is not None:
            trial_count = check_nd1(pkg, policy, work, errors)
        if policy is not None and cases is not None:
            check_p0d(pkg, pool, trial_count, work, errors)
            trace = parse_trace(case_dir / "evidence" / "trace.md", errors)
            check_nd2(pkg, cases, trace, errors)
            check_nd3(pkg, pool, trial_count, work, case_dir, errors)
    except subprocess.TimeoutExpired:
        errors.append("a package execution exceeded {} s".format(SUBPROC_TIMEOUT))
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    for line in errors:
        print("FAIL: " + line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
