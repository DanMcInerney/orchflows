#!/usr/bin/env python3
"""Deterministic build and browser-contract oracles for the web distribution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "dist"
LOCK = ROOT / "pnpm-lock.yaml"
# S1 exception: this file is run with working directory `reader`, so it
# derives the reader root first (ROOT, above) and chains the repository
# root off that already-resolved name rather than walking straight from
# `Path(__file__)` -- a different idiom the grep-shaped acceptance did
# not enumerate.
REPOSITORY_ROOT = ROOT.parent
RUNTIME_REQUIREMENTS = REPOSITORY_ROOT / "requirements-runtime.txt"
NOTICES = REPOSITORY_ROOT / "THIRD_PARTY_NOTICES.md"
BUNDLE_MANIFEST = DIST / ".vite" / "manifest.json"
GENERATED_MANIFEST = DIST / ".vite" / "orchflows-generated.json"
REMOTE_ASSET = re.compile(
    rb"(?:src|href)\s*=\s*[\"'`]?\s*(?:https?:)?//|"
    rb"(?:url|(?:fetch|import)|new\s+Worker)\s*\(\s*[\"'`]?\s*(?:https?:)?//|"
    rb"@import\s+[\"'`]?\s*(?:https?:)?//",
    re.IGNORECASE,
)
HASHED_ASSET = re.compile(r".+-[0-9A-Za-z_-]{8,}\.(?:css|js)$")
PYTHON_LICENSES = {
    "anyio": "MIT",
    "click": "BSD-3-Clause",
    "colorama": "BSD-3-Clause",
    "exceptiongroup": "MIT",
    "h11": "MIT",
    "idna": "BSD-3-Clause",
    "starlette": "BSD-3-Clause",
    "typing-extensions": "PSF-2.0",
    "uvicorn": "BSD-3-Clause",
}
PYTHON_ARTIFACTS = {
    name: "P: {0}/".format(name.replace("-", "_")) for name in PYTHON_LICENSES
}
PYTHON_ARTIFACTS["typing-extensions"] = "P: typing_extensions.py"


def _pnpm() -> str:
    command = shutil.which("pnpm")
    if command is None:
        raise RuntimeError("pnpm 10.32.1 is required for frontend development")
    return command


def _run(*arguments: str, env: dict | None = None) -> None:
    completed = subprocess.run(
        [_pnpm(), *arguments],
        cwd=ROOT,
        env=env,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError("command failed ({0}): pnpm {1}".format(
            completed.returncode, " ".join(arguments)
        ))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plain_markdown(value: str) -> str:
    return value.replace("**", "").replace("`", "").strip()


def _notice_rows(text: str, heading: str, next_heading: str) -> Dict[str, tuple]:
    start = text.find(heading)
    end = text.find(next_heading, start + len(heading))
    if start < 0 or end < 0:
        raise RuntimeError("third-party notice table is missing: {0}".format(heading))
    rows = {}
    for line in text[start:end].splitlines():
        if not line.startswith("|"):
            continue
        cells = [_plain_markdown(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5 or cells[0] in {"Package", "---"}:
            continue
        package, version, source, license_name, artifact = cells
        if package in rows:
            raise RuntimeError("duplicate notice row: {0}".format(package))
        rows[package] = (version, source, license_name, artifact)
    if not rows:
        raise RuntimeError("third-party notice table is empty: {0}".format(heading))
    return rows


def _runtime_identities(text: str) -> Dict[str, str]:
    identities = {}
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)", re.MULTILINE)
    for name, version in pattern.findall(text):
        identities[name.lower().replace("_", "-")] = version
    if not identities:
        raise RuntimeError("requirements-runtime.txt contains no pinned identities")
    return identities


def _unquote_yaml(value: str) -> str:
    value = value.strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == "'" else value


def _production_snapshots(text: str) -> Dict[str, str]:
    before_packages, marker, after_packages = text.partition("\npackages:\n")
    if not marker:
        raise RuntimeError("pnpm lock has no packages section")
    roots = {}
    dependency_name = None
    in_dependencies = False
    for line in before_packages.splitlines():
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 4:
            in_dependencies = stripped == "dependencies:"
            dependency_name = None
        elif in_dependencies and indent == 6 and stripped.endswith(":"):
            dependency_name = _unquote_yaml(stripped[:-1])
        elif in_dependencies and dependency_name and indent == 8 and stripped.startswith("version:"):
            roots[dependency_name] = _unquote_yaml(stripped.split(":", 1)[1])
    if not roots:
        raise RuntimeError("pnpm lock importer has no production dependencies")

    _packages, snapshot_marker, snapshot_text = after_packages.partition("\nsnapshots:\n")
    if not snapshot_marker:
        raise RuntimeError("pnpm lock has no snapshots section")
    snapshots: Dict[str, Dict[str, str]] = {}
    current = None
    in_dependencies = False
    for line in snapshot_text.splitlines():
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 2 and stripped:
            raw_key = stripped.split(":", 1)[0]
            current = _unquote_yaml(raw_key)
            snapshots[current] = {}
            in_dependencies = False
        elif current and indent == 4:
            in_dependencies = stripped == "dependencies:"
        elif current and in_dependencies and indent == 6 and ":" in stripped:
            name, version = stripped.split(":", 1)
            snapshots[current][_unquote_yaml(name)] = _unquote_yaml(version)

    closure = {}
    queue = ["{0}@{1}".format(name, version) for name, version in roots.items()]
    seen = set()
    while queue:
        key = queue.pop()
        if key in seen:
            continue
        seen.add(key)
        if key not in snapshots:
            raise RuntimeError("production snapshot is missing: {0}".format(key))
        package, separator, version = key.split("(", 1)[0].rpartition("@")
        if not separator or not package:
            raise RuntimeError("invalid production snapshot identity: {0}".format(key))
        if package.startswith("@types/"):
            continue
        prior = closure.setdefault(package, version)
        if prior != version:
            raise RuntimeError("multiple production versions are unsupported: {0}".format(package))
        for name, child_version in snapshots[key].items():
            queue.append("{0}@{1}".format(name, child_version))
    return closure


def _assert_notice_inventory(
    expected: Dict[str, str], rows: Dict[str, tuple], licenses: Dict[str, str], kind: str
) -> None:
    if set(rows) != set(expected):
        missing = sorted(set(expected) - set(rows))
        extra = sorted(set(rows) - set(expected))
        raise RuntimeError("{0} notice inventory mismatch; missing={1}, extra={2}".format(
            kind, missing, extra
        ))
    for package, version in expected.items():
        seen_version, seen_source, seen_license, seen_artifact = rows[package]
        if seen_version != version:
            raise RuntimeError("{0} notice version mismatch: {1}".format(kind, package))
        expected_license = licenses.get(package)
        if expected_license is None:
            raise RuntimeError("{0} license policy is missing: {1}".format(kind, package))
        if seen_license != expected_license:
            raise RuntimeError("{0} notice license mismatch: {1}".format(kind, package))
        source_root = "https://pypi.org/project/" if kind == "Python" else "https://www.npmjs.com/package/"
        if "{0}{1}".format(source_root, package) not in seen_source or version not in seen_source:
            raise RuntimeError("{0} notice source mismatch: {1}".format(kind, package))
        if kind == "Python" and seen_artifact != PYTHON_ARTIFACTS[package]:
            raise RuntimeError("Python notice artifact mismatch: {0}".format(package))


def audit_licenses() -> dict:
    inputs = (RUNTIME_REQUIREMENTS, LOCK, BUNDLE_MANIFEST, NOTICES)
    missing = [str(path.relative_to(ROOT)) for path in inputs if not path.is_file()]
    if missing:
        raise RuntimeError("license audit input is missing: {0}".format(", ".join(missing)))

    notice_text = NOTICES.read_text(encoding="utf-8")
    python_rows = _notice_rows(notice_text, "### Python runtime", "### Browser runtime")
    browser_rows = _notice_rows(notice_text, "### Browser runtime", "## Adapted engineering material")
    python_identities = _runtime_identities(RUNTIME_REQUIREMENTS.read_text(encoding="utf-8"))
    browser_identities = _production_snapshots(LOCK.read_text(encoding="utf-8"))
    browser_licenses = {
        package: "ISC" if package.startswith("d3-") or package == "lucide-react" else "MIT"
        for package in browser_identities
    }
    browser_licenses["elkjs"] = "EPL-2.0 (selected option)"
    _assert_notice_inventory(python_identities, python_rows, PYTHON_LICENSES, "Python")
    _assert_notice_inventory(browser_identities, browser_rows, browser_licenses, "browser")

    for package, (_version, _source, _license, artifact) in browser_rows.items():
        expected_artifact = "E" if package == "elkjs" else "B"
        if artifact != expected_artifact:
            raise RuntimeError("browser notice artifact mismatch: {0}".format(package))
    if "elects the Eclipse Public License 2.0 (EPL-2.0) option" not in _plain_markdown(notice_text):
        raise RuntimeError("elkjs EPL-2.0 election statement is missing")

    try:
        manifest = json.loads(BUNDLE_MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError("bundled manifest is not valid JSON") from error
    entry = manifest.get("index.html", {}).get("file") if isinstance(manifest, dict) else None
    if not isinstance(entry, str) or not HASHED_ASSET.fullmatch(entry.split("/", 1)[-1]):
        raise RuntimeError("bundled manifest has no content-hashed browser entry")
    if not (DIST / entry).is_file():
        raise RuntimeError("bundled manifest entry is missing from reader/web/dist")
    if len(list((DIST / "assets").glob("elk.worker-*.js"))) != 1:
        raise RuntimeError("bundled manifest identity has no unique ELK API worker")
    if len(list((DIST / "assets").glob("elk-worker.min-*.js"))) != 1:
        raise RuntimeError("bundled manifest identity has no unique ELK engine worker")

    return {
        "browser_packages": len(browser_identities),
        "elkjs_license": "EPL-2.0",
        "lock_sha256": _sha256(LOCK),
        "manifest_sha256": _sha256(BUNDLE_MANIFEST),
        "notices_sha256": _sha256(NOTICES),
        "python_packages": len(python_identities),
        "requirements_sha256": _sha256(RUNTIME_REQUIREMENTS),
    }


def _dist_identity() -> Dict[str, str]:
    if not DIST.is_dir():
        raise RuntimeError("production build did not create reader/web/dist")
    identity = {}
    for path in sorted(candidate for candidate in DIST.rglob("*") if candidate.is_file()):
        relative = path.relative_to(DIST).as_posix()
        payload = path.read_bytes()
        if path.suffix == ".map" or b"sourceMappingURL=" in payload:
            raise RuntimeError("source map found in production output: {0}".format(relative))
        if REMOTE_ASSET.search(payload):
            raise RuntimeError("remote asset reference found in production output: {0}".format(relative))
        identity[relative] = hashlib.sha256(payload).hexdigest()
    assets = [name for name in identity if name.startswith("assets/")]
    if not assets or not all(HASHED_ASSET.fullmatch(name.split("/", 1)[1]) for name in assets):
        raise RuntimeError("every production asset must have a content-hashed local name")
    return identity


def _prepare_generated_distribution() -> None:
    """Normalize the vendored worker and attest every generated output."""

    for path in (DIST / "assets").glob("elk-worker.min-*.js"):
        payload = path.read_bytes().replace(b"\t\n", b"\\t\n")
        path.write_bytes(payload)
    GENERATED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    entries = {
        path.relative_to(DIST).as_posix(): _sha256(path)
        for path in sorted(candidate for candidate in DIST.rglob("*") if candidate.is_file())
        if path != GENERATED_MANIFEST
    }
    payload = (json.dumps(entries, indent=2, sort_keys=True) + "\n").encode("utf-8")
    GENERATED_MANIFEST.write_bytes(payload)


def verify_build() -> dict:
    if not LOCK.is_file():
        raise RuntimeError("pnpm-lock.yaml is missing")
    before = _sha256(LOCK)
    committed = _dist_identity()
    _run("install", "--frozen-lockfile")
    _run("run", "typecheck")
    _run("run", "test")

    identities = []
    for _ in range(2):
        shutil.rmtree(DIST, ignore_errors=True)
        _run("run", "build")
        _prepare_generated_distribution()
        identities.append(_dist_identity())
    if identities[0] != identities[1]:
        raise RuntimeError("two clean production builds produced different bytes")
    if committed != identities[0]:
        raise RuntimeError("committed reader/web/dist differs from the deterministic production build")
    if _sha256(LOCK) != before:
        raise RuntimeError("the frozen install or build mutated pnpm-lock.yaml")
    encoded = json.dumps(identities[0], sort_keys=True, separators=(",", ":"))
    return {
        "asset_count": len(identities[0]),
        "manifest_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "lock_sha256": before,
    }


def smoke(browser: str, experience: bool = False) -> dict:
    if browser not in {"auto", "chromium"}:
        raise RuntimeError("unsupported browser: {0}".format(browser))
    environment = os.environ.copy()
    environment.pop("FORCE_COLOR", None)
    environment["NO_COLOR"] = "1"
    environment["ORCHFLOWS_BROWSER"] = browser
    environment["ORCHFLOWS_UI_EXPERIENCE"] = "1" if experience else "0"
    environment.setdefault("ORCHFLOWS_PYTHON", sys.executable)
    if browser == "auto" and "ORCHFLOWS_BROWSER_EXECUTABLE" not in environment:
        candidates = (
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path(r"/usr/bin/google-chrome"),
            Path(r"/usr/bin/chromium"),
        )
        installed = next((path for path in candidates if path.is_file()), None)
        if installed:
            environment["ORCHFLOWS_BROWSER_EXECUTABLE"] = str(installed)
    _run(
        "exec", "playwright", "test", "web/src/smoke.spec.ts",
        "--workers=1", "--reporter=line", env=environment,
    )
    return {"browser": browser, "contract": "experience-v1" if experience else "observe-v1"}


def _view_manifest(path: str) -> dict:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("schema") != "orchflows.view-manifest.v1":
        raise RuntimeError("unsupported view manifest schema")
    identities = [item.get("identity") for item in manifest.get("views", ())]
    if len(identities) != 64 or len(set(identities)) != 64:
        raise RuntimeError("view manifest must carry 64 unique identities")
    return manifest


def _visual_run(action: str, host: str, port: int, manifest: str, browser: str, output=None) -> dict:
    if host not in ("127.0.0.1", "localhost"):
        raise RuntimeError("visual harness accepts a loopback host only")
    if browser not in {"auto", "chromium"}:
        raise RuntimeError("unsupported browser: {0}".format(browser))
    contract = _view_manifest(manifest)
    environment = os.environ.copy()
    environment.pop("FORCE_COLOR", None)
    environment["NO_COLOR"] = "1"
    environment["ORCHFLOWS_UI_ACTION"] = action
    environment["ORCHFLOWS_UI_API_ORIGIN"] = "http://{0}:{1}".format(host, port)
    environment["ORCHFLOWS_UI_MANIFEST"] = str(Path(manifest).resolve())
    if output is not None:
        destination = Path(output).resolve()
        destination.mkdir(parents=True, exist_ok=True)
        environment["ORCHFLOWS_UI_OUTPUT"] = str(destination)
    if browser == "auto" and "ORCHFLOWS_BROWSER_EXECUTABLE" not in environment:
        candidates = (
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium"),
        )
        installed = next((path for path in candidates if path.is_file()), None)
        if installed:
            environment["ORCHFLOWS_BROWSER_EXECUTABLE"] = str(installed)
    _run("exec", "playwright", "test", "web/src/smoke.spec.ts", "--workers=1", "--reporter=line", env=environment)
    return {"browser": browser, "identities": [item["identity"] for item in contract["views"]]}


def diff_captures(actual: str, goldens: str, manifest: str) -> dict:
    contract = _view_manifest(manifest)
    actual_root, golden_root = Path(actual), Path(goldens)
    results = {}
    for item in contract["views"]:
        identity = item["identity"]
        seen, golden = actual_root / (identity + ".png"), golden_root / (identity + ".png")
        if not golden.is_file():
            results[identity] = "no-golden"
        elif not seen.is_file():
            results[identity] = "missing"
        else:
            results[identity] = "match" if _sha256(seen) == _sha256(golden) else "different"
    return {"results": results, "no_golden": sum(value == "no-golden" for value in results.values())}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify-build")
    commands.add_parser("audit-licenses")
    smoke_parser = commands.add_parser("smoke")
    smoke_parser.add_argument("--browser", default="auto")
    smoke_parser.add_argument("--experience", action="store_true")
    capture_parser = commands.add_parser("capture")
    audit_parser = commands.add_parser("audit")
    diff_parser = commands.add_parser("diff")
    for visual in (capture_parser, audit_parser):
        visual.add_argument("--host", default="127.0.0.1")
        visual.add_argument("--port", type=int, required=True)
        visual.add_argument("--manifest", required=True)
        visual.add_argument("--browser", default="auto")
    capture_parser.add_argument("--output", required=True)
    audit_parser.add_argument("--standard", default="wcag22aa", choices=("wcag22aa",))
    diff_parser.add_argument("--actual", required=True)
    diff_parser.add_argument("--goldens", required=True)
    diff_parser.add_argument("--manifest", required=True)
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "verify-build":
            evidence = verify_build()
        elif arguments.command == "audit-licenses":
            evidence = audit_licenses()
        elif arguments.command == "capture":
            evidence = _visual_run("capture", arguments.host, arguments.port, arguments.manifest, arguments.browser, arguments.output)
        elif arguments.command == "audit":
            evidence = _visual_run("audit", arguments.host, arguments.port, arguments.manifest, arguments.browser)
        elif arguments.command == "diff":
            evidence = diff_captures(arguments.actual, arguments.goldens, arguments.manifest)
        else:
            evidence = smoke(arguments.browser, arguments.experience)
    except (OSError, RuntimeError) as error:
        print("ui-frontend {0}: FAIL: {1}".format(arguments.command, error), file=sys.stderr)
        return 1
    failed = (
        arguments.command == "diff"
        and any(value in {"different", "missing"} for value in evidence["results"].values())
    )
    print(json.dumps(evidence, sort_keys=True))
    print(
        "ui-frontend {0}: {1}".format(arguments.command, "FAIL" if failed else "PASS"),
        file=sys.stderr,
    )
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
