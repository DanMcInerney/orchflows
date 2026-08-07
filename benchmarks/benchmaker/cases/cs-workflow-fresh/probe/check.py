#!/usr/bin/env python3
"""Probe for cs-workflow-fresh — P0.a-P0.d plus wf.1-wf.6.

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
  evidence/inner-impls/ pool (interpreter supplied from case evidence).
- wf.1 the package oracle rejects a transcript whose stages run out of
  order.
- wf.2 the package oracle rejects a join whose consumed identity
  differs from the frozen upstream identity.
- wf.3 gate coverage is per-edge: the last-edge-ungated inner
  near-miss is failed.
- wf.4 seal ordering: the provenance event ledger records
  qualification before identity minting, and no qualification verdict
  covers the package's own benchmark identity (covers resolve to
  component identities only).
- wf.5 design-evidence flow direction: the design component's
  evidence-source lines never point at the package's own downstream
  components (cases/, runner/, scoring/, qualification/).
- wf.6 the package-level aggregate gate rejects an empty run.

Tree digest rule (matches the package builder): a file's digest is
sha256 over its bytes; a directory's digest is sha256 over the UTF-8
encoding of "<posix-relpath>:<file-sha256-hex>" lines for every file
under it, sorted by relpath, joined with "\n". __pycache__ is excluded.

Scratch-copy hygiene: the implementation, the interpreter, and the
inner pool are copied to a temporary directory before any execution;
nothing under the case directory is written.
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
DOWNSTREAM_PREFIXES = ("cases/", "runner/", "scoring/", "qualification/")
DOWNSTREAM_NAMES = ("cases", "runner", "scoring", "qualification")
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


def run_python(args, cwd):
    return subprocess.run(
        [sys.executable] + [str(a) for a in args],
        cwd=str(cwd),
        env=child_env(),
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


def load_qualification(pkg, manifest, errors):
    ref = manifest.get("qualification")
    if not isinstance(ref, dict):
        return None
    resolved = resolve_locator(pkg, ref.get("locator", ""))
    if resolved is None:
        return None
    qual_path = resolved / "qualification.json" if resolved.is_dir() else resolved
    if not qual_path.is_file():
        errors.append("P0.c: no qualification.json under '{}'".format(ref.get("locator")))
        return None
    try:
        return json.loads(qual_path.read_text(encoding="utf-8"))
    except ValueError as error:
        errors.append("P0.c: qualification.json is not valid JSON: {}".format(error))
        return None


def check_p0c(qual, errors):
    if qual is None:
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


def run_package(pkg, impl_dir, interpreter, work):
    return run_python(
        [pkg / "runner" / "run.py", impl_dir, "--interpreter", interpreter],
        cwd=work,
    )


def check_p0d(pkg, pool, interpreter, work, errors):
    impls = sorted(p for p in pool.iterdir() if p.is_dir())
    if not impls:
        errors.append("P0.d: inner pool is empty")
        return
    for impl in impls:
        proc = run_package(pkg, impl, interpreter, work)
        expected = impl_expectation(impl.name)
        if expected == "pass" and proc.returncode != 0:
            errors.append("P0.d: inner impl '{}' must pass but the package failed it".format(impl.name))
        if expected == "fail" and proc.returncode == 0:
            errors.append("P0.d: inner impl '{}' must fail but the package passed it".format(impl.name))


def reference_transcript(interpreter, pool, work, errors):
    pipeline = pool / "reference" / "pipeline.json"
    proc = run_python([interpreter, pipeline], cwd=work)
    if proc.returncode != 0:
        errors.append("wf.1: interpreter failed on the reference pipeline")
        return None
    return proc.stdout.decode("utf-8").splitlines()


def stage_blocks(lines):
    blocks, current, name = [], [], None
    for line in lines:
        parts = line.split()
        if parts and parts[0] == "STAGE-START":
            name, current = parts[1], [line]
        elif parts and parts[0] == "STAGE-END":
            current.append(line)
            blocks.append((name, current))
            current, name = [], None
        elif name is not None:
            current.append(line)
    return blocks


def check_oracle_rejects(pkg, work, label, lines, errors, message):
    transcript = work / (label + ".txt")
    transcript.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    proc = run_python([pkg / "runner" / "check_transcript.py", transcript], cwd=work)
    if proc.returncode == 0:
        errors.append(message)


def check_wf1_wf2_wf6(pkg, interpreter, pool, work, errors):
    lines = reference_transcript(interpreter, pool, work, errors)
    if lines is None:
        return
    blocks = dict((name, block) for name, block in stage_blocks(lines))
    if not all(stage in blocks for stage in ("spec", "build", "verify")):
        errors.append("wf.1: reference transcript is missing canonical stages")
        return
    out_of_order = blocks["spec"] + blocks["verify"] + blocks["build"]
    check_oracle_rejects(
        pkg, work, "wf1-out-of-order", out_of_order, errors,
        "wf.1: package oracle accepts a transcript whose stages run out of order",
    )
    tampered = []
    tampered_done = False
    for line in lines:
        parts = line.split()
        if not tampered_done and len(parts) == 5 and parts[0] == "JOIN" and parts[4] != "MISSING":
            parts[4] = "0" * 64
            tampered.append(" ".join(parts))
            tampered_done = True
        else:
            tampered.append(line)
    if not tampered_done:
        errors.append("wf.2: reference transcript carries no join to tamper")
    else:
        check_oracle_rejects(
            pkg, work, "wf2-join-mismatch", tampered, errors,
            "wf.2: package oracle accepts a join whose identity differs from the frozen record",
        )
    check_oracle_rejects(
        pkg, work, "wf6-empty", [], errors,
        "wf.6: package-level aggregate gate accepts an empty run",
    )


def check_wf3(pkg, pool, interpreter, work, errors):
    near_miss = pool / "near-miss-lastgate"
    if not near_miss.is_dir():
        errors.append("wf.3: inner pool has no near-miss-lastgate")
        return
    proc = run_package(pkg, near_miss, interpreter, work)
    if proc.returncode == 0:
        errors.append("wf.3: the last-edge-ungated inner near-miss passes; gate coverage is not per-edge")


def check_wf4(pkg, manifest, qual, errors):
    events_path = pkg / "provenance" / "events.md"
    if not events_path.is_file():
        errors.append("wf.4: no provenance/events.md seal ledger")
    else:
        order = {}
        for index, line in enumerate(events_path.read_text(encoding="utf-8").splitlines()):
            for token in ("components-frozen", "qualification-recorded", "identity-minted"):
                if token in line and token not in order:
                    order[token] = index
        missing = [t for t in ("components-frozen", "qualification-recorded", "identity-minted") if t not in order]
        if missing:
            errors.append("wf.4: seal ledger is missing events: {}".format(", ".join(missing)))
        elif not (order["components-frozen"] < order["qualification-recorded"] < order["identity-minted"]):
            errors.append("wf.4: seal ledger records qualification after identity minting (late operation)")
    if qual is None or manifest is None:
        return
    component_ids = set()
    for name in COMPONENT_FIELDS:
        ref = manifest.get(name)
        if isinstance(ref, dict) and isinstance(ref.get("identity"), str):
            component_ids.add(ref["identity"])
    benchmark_identity = manifest.get("benchmark_identity")
    for index, entry in enumerate(qual.get("entries", []) or []):
        covers = entry.get("covers")
        if not isinstance(covers, dict):
            continue
        for value in covers.values():
            if value == benchmark_identity:
                errors.append("wf.4: qualification entry {} covers the package's own benchmark identity".format(index))
            elif value not in component_ids:
                errors.append("wf.4: qualification entry {} covers an identity that is no component of this package".format(index))


def check_wf5(pkg, errors):
    design_path = pkg / "provenance" / "evaluation-design.md"
    if not design_path.is_file():
        errors.append("wf.5: no provenance/evaluation-design.md")
        return
    sources = []
    for line in design_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("evidence-source:"):
            sources.append(stripped.split(":", 1)[1].strip())
    if not sources:
        errors.append("wf.5: design component names no evidence-source")
        return
    for source in sources:
        normalized = source.lower()
        if normalized.startswith(DOWNSTREAM_PREFIXES) or normalized in DOWNSTREAM_NAMES:
            errors.append(
                "wf.5: design cites downstream component '{}' as its own evidence source (reverse flow)".format(source)
            )


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
    tmp = Path(tempfile.mkdtemp(prefix="cs-workflow-probe-"))
    try:
        pkg = tmp / "pkg"
        shutil.copytree(str(impl_src), str(pkg))
        pool = tmp / "inner-impls"
        shutil.copytree(str(case_dir / "evidence" / "inner-impls"), str(pool))
        interpreter = tmp / "interpreter.py"
        shutil.copyfile(str(case_dir / "evidence" / "interpreter.py"), str(interpreter))
        work = tmp / "work"
        work.mkdir()

        manifest = check_p0a(pkg, errors)
        qual = None
        if manifest is not None and not (MANIFEST_FIELDS - set(manifest)):
            check_p0b(pkg, manifest, errors)
            qual = load_qualification(pkg, manifest, errors)
            check_p0c(qual, errors)
        check_p0d(pkg, pool, interpreter, work, errors)
        check_wf1_wf2_wf6(pkg, interpreter, pool, work, errors)
        check_wf3(pkg, pool, interpreter, work, errors)
        check_wf4(pkg, manifest, qual, errors)
        check_wf5(pkg, errors)
    except subprocess.TimeoutExpired:
        errors.append("a package execution exceeded {} s".format(SUBPROC_TIMEOUT))
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    for line in errors:
        print("FAIL: " + line)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
