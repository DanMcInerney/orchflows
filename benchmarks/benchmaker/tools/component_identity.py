#!/usr/bin/env python3
"""Bind the benchmaker manifest's component identities to the tree.

``benchmark_identity`` recomputes from the canonical manifest payload,
which proves the JSON is internally consistent. ``benchmark.lock``
proves the tree matches its own recipe. Nothing bound the two: the
manifest's directory-component identities reproduced under no recipe,
so a ``cases/`` change moved no manifest field and nothing detected it.

This tool is the missing recipe, and it is the one ``seal_set.py``
already uses one level up. A **file** component's identity is the
sha256 of its exact bytes. A **directory** component's identity is the
sha256 of its component lock: one ``<sha256>  <posix-path>`` line per
contained file, path relative to the component root, sorted by path,
LF-terminated. Nesting the same recipe means a component identity and
the set digest are computed the same way over the same bytes, so a
reader who can verify one can verify the other.

``protected_evidence`` is exempt and named as such: its bytes live
off-tree by policy, its identity is a per-file map rather than one
digest, and a tool that could recompute it would have to read the
material the policy withholds.

    uv run --no-project python benchmarks/benchmaker/tools/component_identity.py --verify
    uv run --no-project python benchmarks/benchmaker/tools/component_identity.py --write

``--verify`` recomputes every component identity and
``benchmark_identity`` from the tree: exit 0 and one line per component
when they agree, exit 1 with one line per divergence. ``--write``
rewrites the manifest with the recomputed identities and prints the new
``benchmark_identity``. Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SET_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_NAME = "manifest.json"
IDENTITY_KEY = "benchmark_identity"
# Off-tree by policy, per-file identity map — see the module docstring.
EXEMPT_COMPONENTS = ("protected_evidence",)
SKIP_DIR_PREFIXES = (".", "_", "__")


def component_files(root):
    """Every file under a directory component, as sorted posix paths."""
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
    # Byte order of the posix paths, so the payload is identical on
    # every platform regardless of the filesystem's listing rules.
    files.sort()
    return files


def component_lock_bytes(root):
    lines = []
    for relative in component_files(root):
        digest = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        lines.append("%s  %s" % (digest, relative))
    return ("".join(line + "\n" for line in lines)).encode("ascii")


def component_identity(root, locator):
    """The identity of one component, or an error string.

    Returns ``(identity, detail)`` on success and ``(None, error)`` when
    the locator resolves to nothing.
    """
    path = root / locator
    if path.is_file():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return "sha256:" + digest, "file"
    if path.is_dir():
        payload = component_lock_bytes(path)
        digest = hashlib.sha256(payload).hexdigest()
        count = len(component_files(path))
        return "sha256:" + digest, "directory over %d files" % count
    return None, "locator resolves to neither a file nor a directory"


def canonical_payload(manifest):
    """The bytes ``benchmark_identity`` is the sha256 of."""
    payload = {key: value for key, value in manifest.items() if key != IDENTITY_KEY}
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def manifest_bytes(manifest):
    """The manifest's own on-disk form: canonical, plus its identity."""
    return json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def recompute(root, manifest):
    """Recomputed identities and per-component report lines.

    Returns ``(identities, exempt, errors)`` where ``identities`` maps a
    component key to its recomputed identity.
    """
    identities = {}
    exempt = []
    errors = []
    for key in sorted(manifest):
        value = manifest[key]
        if not isinstance(value, dict) or "locator" not in value:
            continue
        if key in EXEMPT_COMPONENTS:
            exempt.append(key)
            continue
        locator = value["locator"]
        if not isinstance(locator, str) or not locator.strip():
            errors.append("ERROR component: %s has no usable locator" % key)
            continue
        identity, detail = component_identity(root, locator)
        if identity is None:
            errors.append("ERROR component: %s %s (%s)" % (key, detail, locator))
            continue
        identities[key] = (identity, detail)
    return identities, exempt, errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Recompute or verify the manifest's component identities against the tree."
    )
    parser.add_argument("--set-root", default=str(SET_ROOT), help="benchmarks/benchmaker directory")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rewrite the manifest's identities")
    mode.add_argument("--verify", action="store_true", help="compare the manifest to the tree")
    args = parser.parse_args(argv)

    root = Path(args.set_root).resolve()
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        print("ERROR component: no %s under %s" % (MANIFEST_NAME, root))
        return 1
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print("ERROR component: %s is not valid JSON (%s)" % (MANIFEST_NAME, exc))
        return 1
    if not isinstance(manifest, dict):
        print("ERROR component: %s is not a JSON object" % MANIFEST_NAME)
        return 1

    identities, exempt, errors = recompute(root, manifest)
    if errors:
        for line in errors:
            print(line)
        return 1

    if args.write:
        for key, (identity, _detail) in identities.items():
            manifest[key]["identity"] = identity
        manifest[IDENTITY_KEY] = "sha256:" + hashlib.sha256(
            canonical_payload(manifest)
        ).hexdigest()
        manifest_path.write_bytes(manifest_bytes(manifest))
        print("%s %s over %d components" % (IDENTITY_KEY, manifest[IDENTITY_KEY], len(identities)))
        for key in exempt:
            print("exempt %s (off-tree by policy)" % key)
        return 0

    drift = []
    for key, (identity, detail) in sorted(identities.items()):
        recorded = manifest[key].get("identity")
        if recorded == identity:
            print("ok %s %s (%s)" % (key, identity, detail))
        else:
            drift.append(
                "ERROR component: %s records %s but the tree computes %s (%s)"
                % (key, recorded, identity, detail)
            )
    expected = "sha256:" + hashlib.sha256(canonical_payload(manifest)).hexdigest()
    if manifest.get(IDENTITY_KEY) != expected:
        drift.append(
            "ERROR component: %s records %s but its payload computes %s"
            % (IDENTITY_KEY, manifest.get(IDENTITY_KEY), expected)
        )
    for key in exempt:
        print("exempt %s (off-tree by policy)" % key)
    for line in drift:
        print(line)
    if drift:
        return 1
    print("ok %s %s (manifest bound to tree)" % (IDENTITY_KEY, expected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
