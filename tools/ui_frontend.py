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
REMOTE_ASSET = re.compile(
    rb"(?:src|href)=[\"']https?://|url\(\s*[\"']?https?://|"
    rb"(?:fetch|import)\(\s*[\"']https?://|new\s+Worker\(\s*[\"']https?://",
    re.IGNORECASE,
)
HASHED_ASSET = re.compile(r".+-[0-9A-Za-z_-]{8,}\.(?:css|js)$")


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


def _dist_identity() -> Dict[str, str]:
    if not DIST.is_dir():
        raise RuntimeError("production build did not create web/dist")
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


def verify_build() -> dict:
    if not LOCK.is_file():
        raise RuntimeError("pnpm-lock.yaml is missing")
    before = _sha256(LOCK)
    _run("install", "--frozen-lockfile")
    _run("run", "typecheck")
    _run("run", "test")

    identities = []
    for _ in range(2):
        shutil.rmtree(DIST, ignore_errors=True)
        _run("run", "build")
        identities.append(_dist_identity())
    if identities[0] != identities[1]:
        raise RuntimeError("two clean production builds produced different bytes")
    if _sha256(LOCK) != before:
        raise RuntimeError("the frozen install or build mutated pnpm-lock.yaml")
    encoded = json.dumps(identities[0], sort_keys=True, separators=(",", ":"))
    return {
        "asset_count": len(identities[0]),
        "manifest_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "lock_sha256": before,
    }


def smoke(browser: str) -> dict:
    if browser not in {"auto", "chromium"}:
        raise RuntimeError("unsupported browser: {0}".format(browser))
    environment = os.environ.copy()
    environment["ORCHFLOWS_BROWSER"] = browser
    _run("exec", "playwright", "test", "--config", "web/playwright.config.ts", env=environment)
    return {"browser": browser, "contract": "observe-v1"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify-build")
    smoke_parser = commands.add_parser("smoke")
    smoke_parser.add_argument("--browser", default="auto")
    arguments = parser.parse_args(argv)
    try:
        evidence = verify_build() if arguments.command == "verify-build" else smoke(arguments.browser)
    except (OSError, RuntimeError) as error:
        print("ui-frontend {0}: FAIL: {1}".format(arguments.command, error), file=sys.stderr)
        return 1
    print(json.dumps(evidence, sort_keys=True))
    print("ui-frontend {0}: PASS".format(arguments.command), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
