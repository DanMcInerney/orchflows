#!/usr/bin/env python3
"""Case-author sanity oracle for cs-ratelimit-fresh. NOT the benchmark.

Usage (from the case directory):

    uv run --no-project python probe/check.py [IMPLEMENTATION]

IMPLEMENTATION is a directory holding a benchmark package (manifest.json
at its root); it may also arrive in ``CASE_IMPL``, and defaults to
``target``. Paths resolve against the caller's directory and then
against this case's own directory, so the probe runs from the case
directory or from the repository root.

Checks (exit 0 all pass, exit 1 with one line per failure):

  P0.a  manifest present, exactly the ten fields, benchmark_identity
        recomputes from the canonical payload.
  P0.b  every component reference's sha256 verifies over the shipped
        bytes at its locator, resolved relative to the package root.
  P0.c  qualification entries verdict-contract-complete; no overall
        PASS with a required FAIL; no PASS entry with empty evidence;
        manifest gaps field explicit.
  P0.d  inner discrimination: the package's own runner+scoring, run
        against evidence/inner-impls/, passes reference and good
        variants and fails every bad variant including the near miss.
  rl.1  the scoring path drives a scripted clock: the full inner sweep
        completes within a 30 s wall-clock envelope, impossible with
        real sleeps at the traced timelines (154 virtual seconds per
        implementation).
  rl.2  every identifier the package's cases invoke on the inner target
        appears in evidence/interface.md (anti-invention).

Hygiene: the package and the inner-implementation pool are copied to a
scratch directory before any execution; nothing under the case
directory is ever written.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True  # the probe never writes inside the case directory

CASE_DIR = Path(__file__).resolve().parent.parent
POOL_DIR = CASE_DIR / "evidence" / "inner-impls"
INTERFACE = CASE_DIR / "evidence" / "interface.md"
SWEEP_BUDGET_S = 30.0
COMPONENT_KEYS = (
    "evaluation_design",
    "runnable_cases",
    "runner",
    "scoring",
    "provenance",
    "qualification",
)
MANIFEST_KEYS = frozenset(
    COMPONENT_KEYS + ("benchmark_identity", "expected_cost", "gaps", "protected_evidence")
)
ENTRY_KEYS = ("verdict", "oracle", "oracle_class", "evidence", "covers", "required")
CLOCK_OPS = frozenset(("advance",))


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL")
    if not raw:
        raw = "target"
    for candidate in (Path(raw), CASE_DIR / raw):
        if candidate.is_dir():
            return candidate.resolve()
    return None


def sha256_file(path):
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_identity(manifest):
    payload = {k: v for k, v in manifest.items() if k != "benchmark_identity"}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def locate(root, locator):
    """Resolve a component locator inside the package root, or None."""
    if not isinstance(locator, str) or not locator or "\\" in locator:
        return None
    if locator.startswith("/") or (len(locator) > 1 and locator[1] == ":"):
        return None
    resolved = os.path.normpath(os.path.join(str(root), locator))
    base = os.path.normpath(str(root))
    if not (resolved == base or resolved.startswith(base + os.sep)):
        return None
    return Path(resolved)


def check_manifest(impl, failures):
    """P0.a + P0.b + P0.c. Returns the parsed manifest or None."""
    manifest_path = impl / "manifest.json"
    if not manifest_path.is_file():
        failures.append("P0.a: no manifest.json at the package root")
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as error:
        failures.append("P0.a: manifest.json is not valid JSON: %s" % error)
        return None
    if not isinstance(manifest, dict):
        failures.append("P0.a: manifest.json is not a JSON object")
        return None
    keys = set(manifest)
    for missing in sorted(MANIFEST_KEYS - keys):
        failures.append("P0.a: manifest field '%s' missing" % missing)
    for extra in sorted(keys - MANIFEST_KEYS):
        failures.append("P0.a: manifest carries unknown field '%s'" % extra)
    if keys != MANIFEST_KEYS:
        return None
    recorded = manifest.get("benchmark_identity")
    recomputed = canonical_identity(manifest)
    if recorded != recomputed:
        failures.append(
            "P0.a: benchmark_identity does not recompute (recorded %s, canonical %s)"
            % (recorded, recomputed)
        )

    for key in COMPONENT_KEYS:
        ref = manifest.get(key)
        if not (isinstance(ref, dict) and "identity" in ref and "locator" in ref):
            failures.append("P0.b: component '%s' lacks identity/locator" % key)
            continue
        path = locate(impl, ref["locator"])
        if path is None or not path.is_file():
            failures.append(
                "P0.b: component '%s' locator '%s' does not resolve to a file inside the package"
                % (key, ref["locator"])
            )
            continue
        actual = sha256_file(path)
        if actual != ref["identity"]:
            failures.append(
                "P0.b: component '%s' digest mismatch at '%s'" % (key, ref["locator"])
            )

    if not isinstance(manifest.get("gaps"), list):
        failures.append("P0.c: manifest 'gaps' must be an explicit list ([] allowed)")
    qual_ref = manifest.get("qualification")
    if isinstance(qual_ref, dict):
        qual_path = locate(impl, qual_ref.get("locator", ""))
        if qual_path is not None and qual_path.is_file():
            try:
                qual = json.loads(qual_path.read_text(encoding="utf-8"))
            except ValueError as error:
                failures.append("P0.c: qualification component is not valid JSON: %s" % error)
                qual = None
            if isinstance(qual, dict):
                entries = qual.get("entries")
                if not (isinstance(entries, list) and entries):
                    failures.append("P0.c: qualification carries no entries")
                else:
                    required_fail = False
                    for index, entry in enumerate(entries):
                        if not isinstance(entry, dict):
                            failures.append("P0.c: qualification entry %d is not an object" % index)
                            continue
                        for field in ENTRY_KEYS:
                            if field not in entry:
                                failures.append(
                                    "P0.c: qualification entry %d lacks '%s'" % (index, field)
                                )
                        if entry.get("verdict") == "FAIL" and entry.get("required") is True:
                            required_fail = True
                        if entry.get("verdict") == "PASS" and not str(entry.get("evidence", "")).strip():
                            failures.append(
                                "P0.c: qualification entry %d is PASS with empty evidence" % index
                            )
                    if qual.get("overall") == "PASS" and required_fail:
                        failures.append("P0.c: overall PASS coexists with a required FAIL")
    return manifest


def check_surface(impl, manifest, failures):
    """rl.2 — identifiers invoked on the inner target must be exhibited."""
    cases_ref = manifest.get("runnable_cases")
    if not isinstance(cases_ref, dict):
        return
    cases_path = locate(impl, cases_ref.get("locator", ""))
    if cases_path is None or not cases_path.is_file():
        return  # already failed in P0.b
    try:
        data = json.loads(cases_path.read_text(encoding="utf-8"))
    except ValueError as error:
        failures.append("rl.2: runnable cases are not valid JSON: %s" % error)
        return
    interface_text = INTERFACE.read_text(encoding="utf-8")
    invoked = set()
    for case in data.get("cases", []):
        for op in case.get("ops", []):
            name = op.get("op")
            if isinstance(name, str) and name not in CLOCK_OPS:
                invoked.add(name)
    for name in sorted(invoked):
        if not re.search(r"\b%s\b" % re.escape(name), interface_text):
            failures.append(
                "rl.2: cases invoke '%s' on the limiter but interface.md never exhibits it"
                % name
            )


def check_discrimination(impl, manifest, failures):
    """P0.d + rl.1 — scratch-copied sweep of the inner pool under a time envelope."""
    scoring_ref = manifest.get("scoring")
    if not isinstance(scoring_ref, dict) or locate(impl, scoring_ref.get("locator", "")) is None:
        return  # already failed in P0.b
    scoring_locator = scoring_ref["locator"]
    scratch = Path(tempfile.mkdtemp(prefix="cs-ratelimit-probe-"))
    try:
        package = scratch / "package"
        shutil.copytree(str(impl), str(package))
        pool = scratch / "pool"
        shutil.copytree(str(POOL_DIR), str(pool))
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        deadline = time.monotonic() + SWEEP_BUDGET_S
        for entry in sorted(pool.iterdir()):
            if not entry.is_dir():
                continue
            expect_pass = entry.name.startswith(("reference", "good"))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failures.append(
                    "rl.1: inner sweep exceeded the %.0f s scripted-clock envelope"
                    % SWEEP_BUDGET_S
                )
                return
            try:
                done = subprocess.run(
                    [sys.executable, str(package / scoring_locator), str(entry)],
                    cwd=str(package),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=remaining,
                )
            except subprocess.TimeoutExpired:
                failures.append(
                    "rl.1: scoring '%s' still running at the %.0f s scripted-clock "
                    "envelope — a real-sleep harness cannot replay 154 virtual seconds"
                    % (entry.name, SWEEP_BUDGET_S)
                )
                return
            if expect_pass and done.returncode != 0:
                failures.append(
                    "P0.d: package scoring fails inner '%s' (exit %d) but it must pass"
                    % (entry.name, done.returncode)
                )
            elif not expect_pass and done.returncode == 0:
                failures.append(
                    "P0.d: package scoring passes inner '%s' but it must fail" % entry.name
                )
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)


def main():
    impl = resolve_impl()
    if impl is None:
        sys.stderr.write("probe: no such implementation directory\n")
        return 2
    failures = []
    manifest = check_manifest(impl, failures)
    if manifest is not None:
        check_surface(impl, manifest, failures)
        if not any(f.startswith("P0.b") for f in failures):
            check_discrimination(impl, manifest, failures)
    if failures:
        sys.stderr.write("probe FAIL (%s): %d violation(s)\n" % (impl.name, len(failures)))
        for failure in failures:
            sys.stderr.write("  - %s\n" % failure)
        return 1
    sys.stdout.write("probe PASS (%s)\n" % impl.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
