#!/usr/bin/env python3
"""Probe for cs-ranking-fresh — P0.a-P0.d plus rk.1-rk.4.

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
- P0.d the package's own verification discriminates over the case's
  evidence/inner-impls/ pool.
- rk.1 required verification decides before scoring: the
  required-defective fixed candidate appears EXCLUDED — not ranked,
  not last — and every candidate appears exactly once.
- rk.2 the tie policy is declared and deterministic: two synthetic
  equal-score candidates share one rank with an explicit TIE marker
  and the output is byte-identical under input-order reversal.
- rk.3 the package's provenance contains no benchmaker-authored
  comparison of the fixed candidates (ranking machinery only).
- rk.4 the judged criterion scores fixed evidence only: scoring
  declares judge_scope fixed-evidence, and an executable sentinel
  candidate is never executed (execution trap).

Tree digest rule (matches the package builder): a file's digest is
sha256 over its bytes; a directory's digest is sha256 over the UTF-8
encoding of "<posix-relpath>:<file-sha256-hex>" lines for every file
under it, sorted by relpath, joined with "\n". __pycache__ is excluded.

Scratch-copy hygiene: the implementation, the fixed candidates, and
the inner pool are copied to a temporary directory before any
execution; nothing under the case directory is written.
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
COMPARISON_TOKENS = ("better", "worse", "prefer", "stronger", "weaker", "outranks")
REQUIRED_DEFECTIVE = "cand-delta"
SUBPROC_TIMEOUT = 240

SENTINEL = """## Summary
notes = "sentinel candidate for the judge-scope trap"
version = "1.0.0"
import os
open(os.environ.get("RK_TRAP", "rk-trap-marker"), "w").close()
## Risks
risks = "none"
"""


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


def child_env(extra=None):
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update(extra)
    return env


def run_python(args, cwd, extra_env=None):
    return subprocess.run(
        [sys.executable] + [str(a) for a in args],
        cwd=str(cwd),
        env=child_env(extra_env),
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
    if not isinstance(qual, dict):
        errors.append("P0.c: qualification.json is not a JSON object")
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


def impl_expectation(name):
    if name == "reference" or name.startswith("good"):
        return "pass"
    return "fail"


def check_p0d(pkg, pool, work, errors):
    impls = sorted(p for p in pool.iterdir() if p.is_dir())
    if not impls:
        errors.append("P0.d: inner pool is empty")
        return
    for impl in impls:
        proc = run_python([pkg / "runner" / "run.py", "--verify-only", impl], cwd=work)
        expected = impl_expectation(impl.name)
        if expected == "pass" and proc.returncode != 0:
            errors.append("P0.d: inner impl '{}' must pass verification but failed".format(impl.name))
        if expected == "fail" and proc.returncode == 0:
            errors.append("P0.d: inner impl '{}' must fail verification but passed".format(impl.name))


def parse_ranking(text):
    excluded, ranked = [], []
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "EXCLUDED" and len(parts) >= 2:
            excluded.append(parts[1])
        elif parts[0] == "RANK" and len(parts) >= 4:
            ranked.append({"rank": parts[1], "id": parts[2], "tie": parts[-1] == "TIE"})
    return excluded, ranked


def check_rk1(pkg, candidates_dir, work, errors):
    pool = sorted(candidates_dir.glob("*.md"))
    if not pool:
        errors.append("rk.1: no fixed candidates found")
        return
    proc = run_python([pkg / "runner" / "run.py"] + pool, cwd=work)
    if proc.returncode != 0:
        errors.append("rk.1: package runner failed on the fixed pool")
        return
    text = proc.stdout.decode("utf-8", "replace")
    excluded, ranked = parse_ranking(text)
    ranked_ids = [r["id"] for r in ranked]
    if REQUIRED_DEFECTIVE not in excluded:
        errors.append("rk.1: the required-defective candidate is not EXCLUDED")
    if REQUIRED_DEFECTIVE in ranked_ids:
        errors.append("rk.1: the required-defective candidate is ranked; required failure must never rank")
    all_ids = sorted(excluded + ranked_ids)
    pool_ids = sorted(p.stem for p in pool)
    if all_ids != pool_ids:
        errors.append("rk.1: candidates must each appear exactly once (excluded or ranked)")
    out_path = work / "ranking.txt"
    out_path.write_text(text, encoding="utf-8")
    agg = run_python([pkg / "scoring" / "aggregate.py", out_path], cwd=work)
    if agg.returncode != 0:
        errors.append("rk.1: the ranking artifact fails the package's own shape check")


def check_rk2(pkg, work, errors):
    policy_path = pkg / "scoring" / "policy.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        errors.append("rk.2: scoring/policy.json unreadable: {}".format(error))
        return
    tie = policy.get("tie_policy")
    if not (
        isinstance(tie, dict)
        and tie.get("declared") is True
        and tie.get("deterministic") is True
        and isinstance(tie.get("rule"), str)
        and tie["rule"].strip()
    ):
        errors.append("rk.2: no declared deterministic tie policy in scoring/policy.json")
    if policy.get("verification_before_judging") is not True:
        errors.append("rk.2: scoring does not declare verification before judging")
    body = '## Summary\nEqual-score synthetic candidate.\nversion = "1.0.0"\n\n## Risks\nNone.\n'
    tie_a = work / "tie-aaa.md"
    tie_z = work / "tie-zzz.md"
    tie_a.write_text(body, encoding="utf-8")
    tie_z.write_text(body, encoding="utf-8")
    forward = run_python([pkg / "runner" / "run.py", tie_a, tie_z], cwd=work)
    reverse = run_python([pkg / "runner" / "run.py", tie_z, tie_a], cwd=work)
    if forward.returncode != 0 or reverse.returncode != 0:
        errors.append("rk.2: package runner failed on the synthetic tie pool")
        return
    if forward.stdout != reverse.stdout:
        errors.append("rk.2: ranking bytes change under input-order reversal (arrival-ordered)")
    excluded, ranked = parse_ranking(forward.stdout.decode("utf-8", "replace"))
    if excluded or len(ranked) != 2:
        errors.append("rk.2: synthetic equal-score candidates must both rank")
        return
    if ranked[0]["rank"] != ranked[1]["rank"]:
        errors.append("rk.2: equal aggregates do not share one rank")
    if not (ranked[0]["tie"] and ranked[1]["tie"]):
        errors.append("rk.2: shared rank carries no explicit TIE marker")


def check_rk3(pkg, candidates_dir, errors):
    ids = [p.stem for p in sorted(candidates_dir.glob("*.md"))]
    prov = pkg / "provenance"
    if not prov.is_dir():
        return
    for item in sorted(prov.rglob("*")):
        if not item.is_file():
            continue
        for line in item.read_text(encoding="utf-8", errors="replace").splitlines():
            lowered = line.lower()
            named = [cid for cid in ids if cid in line]
            if len(named) >= 2:
                errors.append(
                    "rk.3: provenance file '{}' compares candidates on one line".format(item.name)
                )
                return
            if named and any(token in lowered for token in COMPARISON_TOKENS):
                errors.append(
                    "rk.3: provenance file '{}' carries a candidate comparison".format(item.name)
                )
                return


def check_rk4(pkg, work, errors):
    policy_path = pkg / "scoring" / "policy.json"
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if policy.get("judge_scope") != "fixed-evidence":
        errors.append("rk.4: scoring does not declare judge_scope fixed-evidence")
    sentinel = work / "sentinel.md"
    sentinel.write_text(SENTINEL, encoding="utf-8")
    marker = work / "trap-marker"
    proc = run_python(
        [pkg / "runner" / "run.py", sentinel],
        cwd=work,
        extra_env={"RK_TRAP": str(marker)},
    )
    if proc.returncode != 0:
        errors.append("rk.4: package runner failed on the sentinel candidate")
    if marker.exists():
        errors.append("rk.4: the judged criterion executed a candidate (judge re-execution trap fired)")


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
    tmp = Path(tempfile.mkdtemp(prefix="cs-ranking-probe-"))
    try:
        pkg = tmp / "pkg"
        shutil.copytree(str(impl_src), str(pkg))
        pool = tmp / "inner-impls"
        shutil.copytree(str(case_dir / "evidence" / "inner-impls"), str(pool))
        candidates_dir = tmp / "candidates"
        shutil.copytree(str(case_dir / "evidence" / "candidates"), str(candidates_dir))
        work = tmp / "work"
        work.mkdir()

        manifest = check_p0a(pkg, errors)
        if manifest is not None and not (MANIFEST_FIELDS - set(manifest)):
            check_p0b(pkg, manifest, errors)
            check_p0c(pkg, manifest, errors)
        check_p0d(pkg, pool, work, errors)
        check_rk1(pkg, candidates_dir, work, errors)
        check_rk2(pkg, work, errors)
        check_rk3(pkg, candidates_dir, errors)
        check_rk4(pkg, work, errors)
    except subprocess.TimeoutExpired:
        errors.append("a package execution exceeded {} s".format(SUBPROC_TIMEOUT))
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    for line in errors:
        print("FAIL: " + line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
