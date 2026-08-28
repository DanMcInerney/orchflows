#!/usr/bin/env python3
"""Render deterministic installer adapters from the top-level host records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HOSTS_DIR = REPO_ROOT / "hosts"
ADAPTERS_DIR = REPO_ROOT / "installer" / "host_adapters"
HOST_IDS = ("claude", "codex", "grok")
REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "id",
        "display_name",
        "cli_candidates",
        "home",
        "managed_markers",
        "installed_items",
        "frontmatter",
        "launch",
        "role_profiles",
        "capabilities",
    }
)


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: unreadable host data: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path}: host data must be a JSON object")
    return value


def _require_nonempty_mapping(host: dict, field: str, path: Path) -> dict:
    value = host.get(field)
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{path}: {field} must be a non-empty object")
    return value


def _validate_host(path: Path, host: dict) -> None:
    missing = sorted(REQUIRED_FIELDS - set(host))
    if missing:
        raise ValueError(f"{path}: missing host field(s): {', '.join(missing)}")
    if host.get("schema_version") != 1:
        raise ValueError(f"{path}: unsupported schema_version")
    if host.get("id") != path.stem:
        raise ValueError(f"{path}: id must match filename {path.stem}")
    if not isinstance(host.get("cli_candidates"), list) or not host["cli_candidates"]:
        raise ValueError(f"{path}: cli_candidates must be a non-empty array")

    markers = _require_nonempty_mapping(host, "managed_markers", path)
    claimed: dict[tuple[str, str], str] = {}
    for name, marker in markers.items():
        if not isinstance(marker, dict):
            raise ValueError(f"{path}: managed marker {name} must be an object")
        if not {"target", "mode", "start", "end"} <= set(marker):
            raise ValueError(f"{path}: incomplete managed marker {name}")
        if marker["start"] == marker["end"]:
            raise ValueError(f"{path}: managed marker {name} has identical endpoints")
        for endpoint in (marker["start"], marker["end"]):
            key = (marker["target"], endpoint)
            previous = claimed.get(key)
            if previous is not None:
                raise ValueError(
                    f"{host['id']}: managed marker collision on {marker['target']}: "
                    f"{previous} and {name}"
                )
            claimed[key] = name

    _require_nonempty_mapping(host, "installed_items", path)
    frontmatter = _require_nonempty_mapping(host, "frontmatter", path)
    if not isinstance(frontmatter.get("legal_keys"), list) or not frontmatter["legal_keys"]:
        raise ValueError(f"{path}: frontmatter.legal_keys must be a non-empty array")
    launch = _require_nonempty_mapping(host, "launch", path)
    if not isinstance(launch.get("verb"), str) or not launch["verb"]:
        raise ValueError(f"{path}: launch.verb must be non-empty")
    profiles = _require_nonempty_mapping(host, "role_profiles", path)
    if set(profiles) != {"planner", "worker"}:
        raise ValueError(f"{path}: role_profiles must declare planner and worker")
    for role, profile in profiles.items():
        if profile.get("name") != f"orch-{role}" or not isinstance(profile.get("binding"), dict):
            raise ValueError(f"{path}: invalid {role} role profile")
    capabilities = _require_nonempty_mapping(host, "capabilities", path)
    if set(capabilities) != {"isolation", "effort"}:
        raise ValueError(f"{path}: capabilities must declare isolation and effort")
    if not set(capabilities.values()) <= {"native", "requested"}:
        raise ValueError(f"{path}: capabilities must be native or requested")


def load_sources(source_dir: Path = HOSTS_DIR) -> dict[str, dict]:
    paths = sorted(source_dir.glob("*.json"))
    hosts = {}
    for path in paths:
        host = _read_json(path)
        _validate_host(path, host)
        hosts[host["id"]] = host
    if tuple(sorted(hosts)) != HOST_IDS:
        raise ValueError(
            f"{source_dir}: expected host files {', '.join(HOST_IDS)}, got "
            f"{', '.join(sorted(hosts)) or '(none)'}"
        )
    return hosts


def _adapter_bytes(source_path: Path, host: dict) -> bytes:
    source_bytes = source_path.read_bytes()
    adapter = {
        "adapter_version": 1,
        "source": f"hosts/{source_path.name}",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "host": host,
    }
    return (json.dumps(adapter, indent=2, sort_keys=True) + "\n").encode("utf-8")


def render_all(source_dir: Path = HOSTS_DIR, output_dir: Path = ADAPTERS_DIR) -> tuple[str, ...]:
    hosts = load_sources(source_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = set()
    for name in sorted(hosts):
        output = output_dir / f"{name}.json"
        output.write_bytes(_adapter_bytes(source_dir / f"{name}.json", hosts[name]))
        expected.add(output.name)
    for stale in output_dir.glob("*.json"):
        if stale.name not in expected:
            stale.unlink()
    return tuple(sorted(hosts))


def check_all(source_dir: Path = HOSTS_DIR, output_dir: Path = ADAPTERS_DIR) -> tuple[str, ...]:
    hosts = load_sources(source_dir)
    for name in sorted(hosts):
        output = output_dir / f"{name}.json"
        expected = _adapter_bytes(source_dir / f"{name}.json", hosts[name])
        if not output.is_file() or output.read_bytes() != expected:
            raise ValueError(f"{output}: rendered host adapter is stale; run tools/render_hosts.py --write")
    extras = sorted(path.name for path in output_dir.glob("*.json") if path.stem not in hosts)
    if extras:
        raise ValueError(f"{output_dir}: unexpected rendered host adapter(s): {', '.join(extras)}")
    return tuple(sorted(hosts))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the rendered adapters")
    args = parser.parse_args(argv)
    try:
        names = render_all() if args.write else check_all()
    except ValueError as error:
        parser.exit(1, f"error: {error}\n")
    print(f"host adapters {'rendered' if args.write else 'current'}: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
