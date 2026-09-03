"""Read the rendered host adapters consumed by installation."""

from __future__ import annotations

import json
import re
from pathlib import Path

# Only reached through installer/foundation.py, itself only reached
# through install.py's own bootstrap -- sys.path already carries the
# repository root by the time this module loads, so the fact is read
# from the leaf rather than re-walked here.
from scripts import _bootstrap

REPO_ROOT = _bootstrap.ROOT
HOSTS_DIR = REPO_ROOT / "hosts"
HOST_ADAPTERS_DIR = Path(__file__).resolve().parent / "host_adapters"
HOST_IDS = ("claude", "codex", "grok")
PROFILE_ROLES = ("planner", "worker")
_CODEX_AGENT_TYPE_RE = re.compile(r"^[a-z0-9_]+$")
GROK_MODEL_CENSUS = ("grok-4.6",)
GROK_EFFORTS = ("low", "medium", "high", "xhigh", "max")


def load_host_adapters(adapter_dir: Path = HOST_ADAPTERS_DIR) -> dict[str, dict]:
    hosts = {}
    for name in HOST_IDS:
        path = adapter_dir / f"{name}.json"
        try:
            rendered = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"{path}: unreadable rendered host adapter: {error}") from error
        if not isinstance(rendered, dict) or rendered.get("adapter_version") != 1:
            raise ValueError(f"{path}: unsupported rendered host adapter")
        host = rendered.get("host")
        if not isinstance(host, dict) or host.get("id") != name:
            raise ValueError(f"{path}: rendered host id must be {name}")
        hosts[name] = host
    extras = sorted(path.stem for path in adapter_dir.glob("*.json") if path.stem not in hosts)
    if extras:
        raise ValueError(
            f"{adapter_dir}: unexpected rendered host adapter(s): {', '.join(extras)}"
        )
    return hosts


def host_item_path(
    host: str,
    item: str,
    root: Path,
    adapters: dict[str, dict] | None = None,
    **values: str,
) -> Path:
    records = adapters if adapters is not None else load_host_adapters()
    try:
        template = records[host]["installed_items"][item]
    except KeyError as error:
        raise ValueError(f"{host}: no installed-item binding for {item}") from error
    try:
        relative = template.format(**values)
    except KeyError as error:
        raise ValueError(f"{host}: installed-item {item} needs {error.args[0]}") from error
    return root / Path(relative)


def marker(host: str, block: str, adapters: dict[str, dict] | None = None) -> dict:
    records = adapters if adapters is not None else load_host_adapters()
    try:
        return records[host]["managed_markers"][block]
    except KeyError as error:
        raise ValueError(f"{host}: no managed-marker binding for {block}") from error


def preflight_instruction_target(
    host: str,
    path: Path,
    block_content: str,
    import_target: Path | None = None,
    adapters: dict[str, dict] | None = None,
) -> None:
    """Refuse marker collisions while planning, before installation writes."""

    from .managed_text import upsert_import_line, upsert_marked_block

    spec = marker(host, "host_instructions", adapters)
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if spec["mode"] == "import":
        if import_target is None:
            raise ValueError(f"{host}: host instruction import needs a target")
        upsert_import_line(text, f"@{import_target}")
    elif spec["mode"] == "inline":
        upsert_marked_block(text, block_content, spec["start"], spec["end"])
    elif spec["mode"] != "owned-file":
        raise ValueError(f"{host}: unknown host instruction mode {spec['mode']}")


def load_role_profiles(adapter_dir: Path = HOST_ADAPTERS_DIR) -> dict[str, dict]:
    hosts = load_host_adapters(adapter_dir)
    for host, record in hosts.items():
        profiles = record.get("role_profiles")
        if not isinstance(profiles, dict):
            raise ValueError(f"{adapter_dir}: {host} has no role_profiles mapping")
        missing = [role for role in PROFILE_ROLES if role not in profiles]
        if missing:
            names = ", ".join(f"orch-{role}" for role in missing)
            raise ValueError(f"{adapter_dir}: missing role profile for {names}")
    profiles = {
        f"orch-{role}": {
            "role": role,
            **{
                host: hosts[host]["role_profiles"][role]["binding"]
                for host in HOST_IDS
            },
        }
        for role in PROFILE_ROLES
    }

    for host, record in hosts.items():
        for role in PROFILE_ROLES:
            name = f"orch-{role}"
            declared = record["role_profiles"].get(role, {}).get("name")
            if declared != name:
                raise ValueError(
                    f"{adapter_dir}: role profile {name} must declare name {name} "
                    f"for {host}, got {declared}"
                )

    codex_agent_types = set()
    grok_subagent_types = set()
    for name, profile in profiles.items():
        codex = profile["codex"]
        if not {"agent_type", "fork_turns", "model", "model_reasoning_effort"} <= set(codex):
            raise ValueError(f"{adapter_dir}: incomplete Codex binding for {name}")
        agent_type = codex["agent_type"]
        if _CODEX_AGENT_TYPE_RE.fullmatch(agent_type) is None:
            raise ValueError(f"{adapter_dir}: invalid Codex agent_type for {name}: {agent_type}")
        if agent_type in codex_agent_types:
            raise ValueError(f"{adapter_dir}: duplicate Codex agent_type: {agent_type}")
        codex_agent_types.add(agent_type)
        fork_turns = codex["fork_turns"]
        if fork_turns != "none" and not (
            fork_turns.isascii() and fork_turns.isdecimal() and not fork_turns.startswith("0")
        ):
            raise ValueError(f"{adapter_dir}: invalid Codex fork_turns for {name}: {fork_turns}")

        if "model" not in profile["claude"]:
            raise ValueError(f"{adapter_dir}: incomplete Claude binding for {name}")

        grok = profile["grok"]
        if not {"model", "effort", "subagent_type"} <= set(grok):
            raise ValueError(f"{adapter_dir}: incomplete Grok binding for {name}")
        if grok["model"] not in GROK_MODEL_CENSUS:
            raise ValueError(
                f"{adapter_dir}: Grok model outside the recorded census for {name}: "
                f"{grok['model']}"
            )
        if grok["effort"] not in GROK_EFFORTS:
            raise ValueError(
                f"{adapter_dir}: invalid Grok effort for {name}: {grok['effort']}"
            )
        subagent_type = grok["subagent_type"]
        if subagent_type in grok_subagent_types:
            raise ValueError(f"{adapter_dir}: duplicate Grok subagent_type: {subagent_type}")
        grok_subagent_types.add(subagent_type)
    return profiles
