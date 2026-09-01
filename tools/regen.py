#!/usr/bin/env python3
"""One regeneration owner for every derived artifact in this tree.

Each artifact below is produced from something else in the repository: it is
never hand-edited, and it must never drift from the source it was produced
from. ``ARTIFACTS`` is the one declaration of which artifact belongs to which
generator. ``regen`` runs every generator; ``regen --check`` regenerates into
memory or a temporary tree and refuses any artifact whose committed bytes
would change, naming that artifact's own regeneration command.

``tools/validate.py`` calls :func:`check` directly, so a stale derived
artifact fails the five required checks instead of waiting for a sixth.

Two artifacts cost more than a byte comparison, and each is handled where the
cost lives rather than by skipping the check:

- The serial-compatibility manifest is regenerated from the *live test tree*,
  so its generator imports every test module and rewrites ``sys.modules``.
  Doing that inside a process that is itself running tests would corrupt the
  run, so the comparison happens in a child interpreter (``--no-spawn`` does
  it in place, which is what the child itself uses).
- That same comparison is memoised against a fingerprint of the generator's
  complete declared input closure (``inputs``). A hit means every input byte,
  the generator's own source, and the committed artifact are unchanged since
  the last time the regeneration was actually run and agreed -- so the answer
  cannot have changed. Any edit anywhere in that closure is a miss. The memo
  lives under ``.orch/`` (run state, never committed) and its absence only
  costs time.

Stdlib only, Python 3.9+, POSIX and Windows. Deterministic, UTF-8, LF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE_SUBPATH = (".orch", "regen-freshness.json")


class Finding(NamedTuple):
    """One graded artifact, in the shape ``validate.Diagnostics`` consumes."""

    artifact: str
    label: str
    level: str  # "error" or "warn"
    message: str
    paths: tuple = ()  # the artifact paths whose bytes would change


class Artifact(NamedTuple):
    """A derived artifact, its generator, and how each is exercised."""

    name: str
    label: str  # the file label a finding is reported against
    command: str  # the exact command that regenerates it
    drift: str  # what drifted, said in this artifact's own terms
    owners: tuple  # paths that must exist for the check to mean anything
    absent: str  # the WARN when an owner is missing; "" skips silently
    stale: object  # (root[, spawn]) -> tuple of drifted repo-relative paths
    write: object  # () -> exit code; regenerates in this checkout
    inputs: tuple = ()  # the generator's complete input closure, for the memo
    costly: bool = False  # regeneration is too expensive to run in place


# --- generated T0 shapes ---------------------------------------------------


def _stale_shapes(root: Path) -> tuple:
    from tools import render_shapes

    source = root / "contracts" / "shapes.json"
    drifted = []
    if not render_shapes.validator_is_current(root / "scripts" / "tickets_shapes.py", source):
        drifted.append("scripts/tickets_shapes.py")
    for name in render_shapes.contracts(source):
        if not render_shapes.contract_is_current(root / "contracts" / name, source):
            drifted.append("contracts/" + name)
    return tuple(drifted)


def _write_shapes() -> int:
    from tools import render_shapes

    render_shapes.write()
    return 0


# --- generated lifecycle table ---------------------------------------------


def _stale_lifecycle(root: Path) -> tuple:
    from tools import render_lifecycle

    target = root / "docs" / "lifecycle.md"
    return () if render_lifecycle.is_current(target) else ("docs/lifecycle.md",)


def _write_lifecycle() -> int:
    from tools import render_lifecycle

    render_lifecycle.write()
    return 0


# --- generated CI topology --------------------------------------------------


def _stale_ci_topology(root: Path) -> tuple:
    from tools import render_ci_topology as topology

    try:
        breakdown = topology.leg_breakdown(root / ".github" / "workflows" / "checks.yml")
        targets = (
            ("tools/preflight.py", topology.leg_total_clause(breakdown)),
            ("tests/tree_removal.py", topology.windows_split_clause(breakdown)),
        )
        drifted = []
        for relative, generated in targets:
            path = root / relative
            current = path.read_text(encoding="utf-8")
            if current != topology._replace_section(current, generated, path):
                drifted.append(relative)
        return tuple(drifted)
    except topology.TopologyUnreadable as error:
        raise ValueError(str(error)) from error


def _write_ci_topology() -> int:
    from tools import render_ci_topology

    render_ci_topology.write()
    return 0


# --- rendered host adapters and the host-block template --------------------


def _stale_hosts(root: Path) -> tuple:
    """Render into a temporary tree, then compare the committed bytes."""

    from tools import render_hosts

    committed = root / "installer" / "host_adapters"
    template = root / "templates" / "host-block.md"
    drifted = []
    with tempfile.TemporaryDirectory(prefix="orchflows-regen-") as directory:
        staging = Path(directory)
        rendered = staging / "host_adapters"
        template_copy = staging / "host-block.md"
        shutil.copyfile(str(template), str(template_copy))
        render_hosts.render_all(root / "hosts", rendered, template_copy)
        produced = sorted(rendered.glob("*.json"))
        for path in produced:
            target = committed / path.name
            if not target.is_file() or target.read_bytes() != path.read_bytes():
                drifted.append("installer/host_adapters/" + path.name)
        expected = {path.name for path in produced}
        for extra in sorted(committed.glob("*.json")):
            if extra.name not in expected:
                drifted.append("installer/host_adapters/" + extra.name + " (unexpected)")
        if template.read_bytes() != template_copy.read_bytes():
            drifted.append("templates/host-block.md")
    return tuple(drifted)


def _write_hosts() -> int:
    from tools import render_hosts

    render_hosts.render_all(host_template=render_hosts.HOST_BLOCK_TEMPLATE)
    return 0


# --- the serial-compatibility manifest -------------------------------------

MANIFEST_RELATIVE = "tests/serial_compat_manifest.json"


def _stale_manifest(root: Path, spawn: bool = True, discover=None, scan=None) -> tuple:
    if spawn:
        return _spawned_stale(root, "serial-compat-manifest")
    from tools import run_serial_compat, serial_manifest

    before, after, _report = serial_manifest.plan_regeneration(
        root / MANIFEST_RELATIVE,
        root / "tests",
        run_serial_compat.discover_cases if discover is None else discover,
        run_serial_compat.scan_mutation_owners if scan is None else scan,
    )
    return () if before == after else (MANIFEST_RELATIVE,)


def _write_manifest() -> int:
    from tools import run_serial_compat, serial_manifest

    return serial_manifest.write_manifest(
        ROOT / MANIFEST_RELATIVE,
        ROOT / "tests",
        run_serial_compat.discover_cases,
        run_serial_compat.scan_mutation_owners,
    )


ARTIFACTS = (
    Artifact(
        name="t0-shapes",
        label="contracts/shapes.json",
        command="python tools/render_shapes.py --write",
        drift="generated T0 shape consumers drifted from contracts/shapes.json",
        owners=("contracts/shapes.json", "scripts/tickets_shapes.py"),
        absent="T0 shape render check skipped: declaration or validator is absent",
        stale=_stale_shapes,
        write=_write_shapes,
    ),
    Artifact(
        name="lifecycle",
        label="docs/lifecycle.md",
        command="python tools/render_lifecycle.py",
        drift="generated lifecycle table drifted from transition code",
        owners=(
            "scripts/tickets_transitions.py",
            "scripts/tickets_lifecycle.py",
            "docs/lifecycle.md",
        ),
        absent="lifecycle render check skipped: transition owners are absent",
        stale=_stale_lifecycle,
        write=_write_lifecycle,
    ),
    Artifact(
        name="ci-topology",
        label=".github/workflows/checks.yml",
        command="python tools/render_ci_topology.py",
        drift="generated CI leg breakdown drifted from checks.yml's own matrix",
        owners=(
            ".github/workflows/checks.yml",
            "tools/preflight.py",
            "tests/tree_removal.py",
        ),
        absent="CI topology render check skipped: workflow or a rendered target is absent",
        stale=_stale_ci_topology,
        write=_write_ci_topology,
    ),
    Artifact(
        name="host-adapters",
        label="hosts",
        command="python tools/render_hosts.py --write",
        drift="rendered host adapters drifted from hosts/*.json",
        owners=("hosts", "installer/host_adapters", "templates/host-block.md"),
        absent="",
        stale=_stale_hosts,
        write=_write_hosts,
    ),
    Artifact(
        name="serial-compat-manifest",
        label=MANIFEST_RELATIVE,
        command="python tools/run_serial_compat.py --write-manifest",
        drift="committed serial-compatibility manifest drifted from the live test tree",
        owners=(MANIFEST_RELATIVE, "tests"),
        absent="serial-compat manifest check skipped: the manifest or tests/ is absent",
        stale=_stale_manifest,
        write=_write_manifest,
        inputs=(
            "tests/**/*.py",
            MANIFEST_RELATIVE,
            "tools/run_serial_compat.py",
            "tools/serial_manifest.py",
        ),
        costly=True,
    ),
)

NAMES = tuple(artifact.name for artifact in ARTIFACTS)


def artifact(name: str) -> Artifact:
    for record in ARTIFACTS:
        if record.name == name:
            return record
    raise KeyError(name)


def _selected(names) -> tuple:
    if names is None:
        return ARTIFACTS
    return tuple(artifact(name) for name in names)


# --- the input-closure memo ------------------------------------------------


def _fingerprint(root: Path, patterns) -> str:
    digest = hashlib.sha256()
    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
            digest.update(b"\0")
    return digest.hexdigest()


def _cache_path(root: Path) -> Path:
    return root.joinpath(*CACHE_SUBPATH)


def _cache_read(root: Path) -> dict:
    try:
        value = json.loads(_cache_path(root).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _cache_write(root: Path, value: dict) -> None:
    path = _cache_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, sort_keys=True, indent=1) + "\n")
    except OSError:  # a read-only or absent checkout only costs time
        pass


# --- the child interpreter -------------------------------------------------


def _spawned_stale(root: Path, name: str) -> tuple:
    """Ask a fresh interpreter, so no test tree is imported into this one."""

    done = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--check",
            "--only",
            name,
            "--root",
            str(root),
            "--no-cache",
            "--no-spawn",
            "--json",
        ],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        errors="replace",
    )
    report = None
    for line in (done.stdout or "").splitlines():
        if line.startswith("{"):
            try:
                report = json.loads(line)
            except ValueError:
                report = None
    if report is None:
        raise RuntimeError(
            "regeneration check could not run in a child interpreter (exit "
            "%s): %s" % (done.returncode, ((done.stderr or done.stdout or "").strip()[-400:]))
        )
    if report.get("failed", {}).get(name):
        raise RuntimeError(report["failed"][name])
    return tuple(report.get("stale", {}).get(name, ()))


# --- grading ---------------------------------------------------------------


def check(root: Path = ROOT, names=None, spawn: bool = True, cache: bool = True) -> list:
    """Grade every selected artifact against what its generator would write."""

    root = Path(root)
    memo = _cache_read(root) if cache else {}
    updated = dict(memo)
    findings = []
    for record in _selected(names):
        missing = [name for name in record.owners if not (root / name).exists()]
        if missing:
            if record.absent:
                findings.append(Finding(record.name, record.label, "warn", record.absent))
            continue
        mark = _fingerprint(root, record.inputs) if (cache and record.inputs) else None
        if mark is not None and memo.get(record.name) == mark:
            continue
        try:
            drifted = record.stale(root, spawn) if record.costly else record.stale(root)
        except Exception as error:  # a generator that cannot run is not a pass
            findings.append(
                Finding(
                    record.name,
                    record.label,
                    "error",
                    "%s could not be regenerated: %s; regenerate with: %s"
                    % (record.label, error, record.command),
                )
            )
            updated.pop(record.name, None)
            continue
        if drifted:
            findings.append(
                Finding(
                    record.name,
                    record.label,
                    "error",
                    "%s: %s; regenerate with: %s"
                    % (record.drift, ", ".join(drifted), record.command),
                    tuple(drifted),
                )
            )
            updated.pop(record.name, None)
        elif mark is not None:
            updated[record.name] = mark
    if cache and updated != memo:
        _cache_write(root, updated)
    return findings


def write(names=None) -> int:
    """Run every selected generator in this checkout; return the worst exit."""

    worst = 0
    for record in _selected(names):
        code = record.write() or 0
        worst = max(worst, code)
        print("%s: %s (%s)" % (record.name, "regenerated" if not code else "needs a ruling", record.command))
    return worst


def _report(findings) -> dict:
    stale = {}
    skipped = {}
    failed = {}
    for finding in findings:
        if finding.level == "warn":
            skipped[finding.artifact] = finding.message
        elif finding.paths:
            stale[finding.artifact] = list(finding.paths)
        else:
            failed[finding.artifact] = finding.message
    return {"stale": stale, "skipped": skipped, "failed": failed}


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - not a TextIOWrapper
        pass
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="refuse drift; write nothing")
    parser.add_argument("--only", action="append", choices=NAMES, help="one artifact; repeatable")
    parser.add_argument("--root", default=str(ROOT), help="tree to grade (--check only)")
    parser.add_argument("--no-cache", action="store_true", help="ignore the input-closure memo")
    parser.add_argument("--no-spawn", action="store_true", help="check costly artifacts in place")
    parser.add_argument("--json", action="store_true", help="emit one machine-readable line")
    args = parser.parse_args(argv)

    if not args.check:
        if args.root != str(ROOT):
            parser.exit(2, "error: --root grades another tree; it never writes to one\n")
        return write(args.only)

    findings = check(
        Path(args.root), args.only, spawn=not args.no_spawn, cache=not args.no_cache
    )
    if args.json:
        print(json.dumps(_report(findings), sort_keys=True))
    else:
        for finding in findings:
            print("%s %s: %s" % (finding.level.upper(), finding.label, finding.message))
        if not any(finding.level == "error" for finding in findings):
            print("derived artifacts are current: %s" % ", ".join(NAMES))
    return 1 if any(finding.level == "error" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
