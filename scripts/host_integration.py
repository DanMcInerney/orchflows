"""Discover native hosts and register complete packages using their public CLIs."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import agy_integration
import package_files


HOSTS = ("codex", "claude", "grok", "kimi", "zcode", "agy")
MARKETPLACE = "orchflows-home"
NATIVE_HOMES = {"codex": ("CODEX_HOME", ".codex"), "claude": ("CLAUDE_CONFIG_DIR", ".claude"),
                "grok": ("GROK_HOME", ".grok"), "kimi": ("KIMI_CODE_HOME", ".kimi-code"),
                "zcode": ("ZCODE_HOME", ".zcode")}
# Claude Code writes these usage markers into its installed plugin copies.
HOST_MARKERS = (".in_use", ".orphaned_at")


def select_hosts(hosts: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    choices = tuple(hosts) if hosts is not None else ("auto",)
    if not choices:
        return ()
    if any(host not in (*HOSTS, "auto", "none") for host in choices):
        raise ValueError("Unknown host")
    if "none" in choices or "auto" in choices:
        if len(choices) != 1:
            raise ValueError("--host auto and --host none cannot be combined with other hosts")
        return HOSTS if choices[0] == "auto" else ()
    return tuple(host for host in HOSTS if host in choices)


def _run(executable: str, *arguments: str, cwd: Path | None = None) -> str:
    command: list[str] | str = [executable, *map(str, arguments)]
    if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
        # Windows runs batch launchers through cmd even with shell=False.
        # Quote every argument, including paths without spaces. Expansion and
        # embedded quotes cannot be transported safely through arbitrary wrappers.
        if any(any(char in value for char in '%!"\r\n') for value in command):
            raise ValueError("Windows batch launcher cannot safely pass quotes, %, ! or newlines; use a native host executable or a path without those characters")
        command = " ".join('"' + value + "\\" * (len(value) - len(value.rstrip("\\"))) + '"' for value in command)
    result = subprocess.run(command, cwd=cwd,
                            stdin=subprocess.DEVNULL, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=45,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-1200:]
        raise ValueError(f"{Path(executable).name} {' '.join(arguments[:3])} exited {result.returncode}: {detail}")
    return result.stdout


def _json(executable: str, *arguments: str, cwd: Path) -> object:
    try:
        return json.loads(_run(executable, *arguments, cwd=cwd))
    except json.JSONDecodeError as exc:
        raise ValueError("Host did not return supported JSON inventory; update the host or install manually") from exc


def _rows(value: object) -> list[dict]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError("Unsupported host inventory format; no registration changed")
    return value


def _candidates(host: str):
    found = shutil.which(host)
    if found:
        yield Path(found)
    if host == "agy":
        if os.name == "nt" and os.environ.get("LOCALAPPDATA"):
            yield Path(os.environ["LOCALAPPDATA"]) / "agy/bin/agy.exe"
        yield Path.home() / ".local/bin" / ("agy.exe" if os.name == "nt" else "agy")
        return
    variable, default = NATIVE_HOMES[host]
    native = Path(os.environ.get(variable) or Path.home() / default).expanduser()
    filename = host + (".exe" if os.name == "nt" else "")
    yield native / "bin" / filename
    yield Path.home() / ".local/bin" / filename
    if os.name == "nt":
        for variable in ("LOCALAPPDATA", "ProgramFiles"):
            directory = os.environ.get(variable)
            if directory:
                for name in (host, {"zcode": "ZCode", "codex": "Codex", "kimi": "Kimi Code"}.get(host, host)):
                    yield Path(directory) / "Programs" / name / filename
                    yield Path(directory) / name / filename
    elif sys.platform == "darwin":
        for root in (Path("/Applications"), Path.home() / "Applications"):
            name = {"zcode": "ZCode", "codex": "Codex", "kimi": "Kimi Code"}.get(host, host)
            yield root / f"{name}.app/Contents/Resources" / host
            if host == "zcode":
                yield root / "ZCode.app/Contents/MacOS/ZCode"
    else:
        yield Path("/opt") / host / host


def detect(hosts: list[str] | tuple[str, ...] | None = None) -> dict[str, dict]:
    explicit = hosts is not None and "auto" not in hosts
    result = {}
    for host in select_hosts(hosts):
        executable = next((str(path.resolve()) for path in _candidates(host) if path.is_file()), None)
        report = {"executable": executable, "status": "not_detected", "version": None}
        if executable:
            try:
                # A desktop executable is evidence of installation, not a CLI to launch.
                report["version"] = None if host == "zcode" else _run(executable, "--version").strip()
                report["status"] = "available"
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                report.update(status="failed", message=str(exc))
        elif explicit:
            report.update(status="needs_action", message=f"{host} was requested but its executable was not found; install it or add it to PATH")
        result[host] = report
    return result


def _same_path(left: str | None, right: Path) -> bool:
    if not left:
        return False
    # Native Windows inventories sometimes use the extended path prefix.
    value = left[4:] if left.startswith("\\\\?\\") else left
    return Path(value).expanduser().resolve() == right.resolve()


def _matches(source: Path, installed: str | None) -> bool:
    if not installed or not Path(installed).is_dir():
        return False
    return package_files.same(source, Path(installed), skip=HOST_MARKERS)


def _markets(host: str, executable: str, cwd: Path) -> list[dict]:
    data = _json(executable, "plugin", "marketplace", "list", "--json", cwd=cwd)
    if host == "codex":
        if not isinstance(data, dict):
            raise ValueError("Unsupported Codex marketplace inventory")
        data = data.get("marketplaces")
    rows = _rows(data)
    if any(not isinstance(row.get("name"), str) or not row["name"] for row in rows):
        raise ValueError("Unsupported marketplace identity; no registration changed")
    return rows


def _inventory(host: str, executable: str, cwd: Path) -> list[dict]:
    if host == "agy":
        return agy_integration.inventory(executable, cwd, _run)
    data = _json(executable, "plugin", "list", "--json", cwd=cwd)
    if host == "codex":
        if not isinstance(data, dict):
            raise ValueError("Unsupported Codex plugin inventory")
        result = []
        for row in _rows(data.get("installed")):
            result.append({"name": row["name"], "enabled": row["enabled"], "version": row.get("version"),
                           "marketplace": row["marketplaceName"], "source": (row.get("source") or {}).get("path"),
                           "path": row.get("installedPath"), "scope": "user"})
        return result
    if host == "claude":
        return [{"name": row["id"].split("@")[0], "marketplace": row["id"].partition("@")[2],
                 "enabled": row["enabled"], "version": row.get("version"), "path": row.get("installPath"),
                 "scope": row["scope"]} for row in _rows(data)]
    own = _rows(data)
    effective = _json(executable, "inspect", "--json", cwd=cwd)
    if not isinstance(effective, dict):
        raise ValueError("Unsupported Grok discovery inventory")
    skills = _rows(effective.get("skills"))
    discovered = _rows(effective.get("plugins"))
    # Effective discovery can hide disabled or duplicate native registrations.
    # Retain every registered entry so conflict checks see the complete state.
    rows = []
    for item in own:
        visible = next((row for row in discovered if row["name"] == item["name"]
                        and _same_path(row["path"], Path(item["path"]))), None)
        rows.append(({**item, "enabled": False, "scope": "user", **(visible or {})}, False, item.get("source")))
    rows.extend((row, True, None) for row in discovered
                if not any(item["name"] == row["name"] and _same_path(item["path"], Path(row["path"])) for item in own))
    result = []
    for row, inherited, source in rows:
        matching_skills = [s for s in skills if (s.get("source") or {}).get("plugin_name") == row["name"]
                           and Path(s["source"].get("path") or "").resolve().is_relative_to(Path(row["path"]).resolve())]
        result.append({"name": row["name"], "enabled": row["enabled"] and any(not s.get("disabled", False) for s in matching_skills),
                       "path": row["path"], "scope": row["scope"], "inherited": inherited, "source": source})
    return result


def _manual(host: str, home: Path, packages: list[dict]) -> dict:
    if host == "kimi":
        steps = [f'In Kimi: /plugins install "{Path(package["package_root"]).as_posix()}"' for package in packages]
        steps.append("Run /reload or /new. If /plugins is unavailable, update Kimi Code first.")
    else:
        steps = [f"In ZCode: Settings > Plugins > Create > Add marketplace > choose {home}; install "
                 + ", ".join(package["name"] for package in packages) + ".",
                 "After editing an installed library, uninstall and reinstall it in ZCode; same-version edits do not appear as updates. "
                 "ZCode cannot enforce manual-only skill invocation."]
    return {"status": "needs_action", "message": "Native in-app installation/verification required", "next_steps": steps}


def _package(host: str, executable: str, home: Path, package: dict, inventory: list[dict], *, install: bool) -> dict:
    name, source = package["name"], Path(package["package_root"])
    matches = [item for item in inventory if item["name"] == name]
    if len(matches) > 1:
        return {"status": "needs_action", "message": "Multiple installations found; remove duplicate registrations in the host, retaining the intended one"}
    existing = matches[0] if matches else None
    if existing and existing["enabled"] is not True:
        return {"status": "needs_action", "message": "Existing plugin is disabled; preserved. Enable it in the host to use it"}
    if existing and existing.get("scope") != "user":
        return {"status": "needs_action", "message": "Existing project/managed registration preserved; choose the intended user installation in the host"}
    if host == "agy":
        return agy_integration.package(executable, home, package, existing, install=install, run=_run)
    if host == "grok" and existing and existing.get("inherited"):
        if _matches(source, existing["path"]):
            return {"status": "ready", "message": "Available through compatible plugin discovery", "path": existing["path"]}
        return {"status": "needs_action", "message": "Compatible installation differs from this home; update it through its owning host"}
    if existing and ((host != "grok" and existing.get("marketplace") != MARKETPLACE)
                     or (host in {"codex", "grok"} and not _same_path(existing.get("source"), source))):
        return {"status": "needs_action", "message": "Plugin belongs to another source; preserved. Resolve the conflicting registration in the host"}

    if host in {"codex", "claude"}:
        markets = [row for row in _markets(host, executable, home) if row.get("name") == MARKETPLACE]
        if len(markets) > 1 or (markets and not _same_path(markets[0].get("root" if host == "codex" else "path"), home)):
            return {"status": "needs_action", "message": "orchflows-home marketplace points elsewhere; preserved. Remove or rename that registration before retrying"}
        if not markets:
            if not install:
                return {"status": "needs_action", "message": "Marketplace is not registered; rerun setup"}
            arguments = ("--scope", "user") if host == "claude" else ()
            _run(executable, "plugin", "marketplace", "add", str(home), *arguments, cwd=home)

    if existing:
        if host == "codex":
            native = json.loads((source / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
            current = existing.get("version") == native.get("version")
        else:
            current = _matches(source, existing.get("path"))
        if current and (host != "codex" or not install):
            return {"status": "ready", "message": "Already installed", "path": existing.get("path")}
    if not install:
        return {"status": "needs_action", "message": "Plugin is absent or stale; rerun setup"}

    installed_path = None
    if host == "codex":
        result = _json(executable, "plugin", "add", f"{name}@{MARKETPLACE}", "--json", cwd=home)
        if not isinstance(result, dict):
            raise ValueError("Unsupported Codex installation result")
        installed_path = result.get("installedPath")
    elif host == "claude":
        plugin = f"{name}@{MARKETPLACE}"
        if existing:
            # Claude's same-version update keeps its stale cached copy. Reinstall
            # only this verified home-owned package, keeping its data.
            _run(executable, "plugin", "marketplace", "update", MARKETPLACE, cwd=home)
            _run(executable, "plugin", "uninstall", plugin, "--scope", "user", "--keep-data", cwd=home)
        _run(executable, "plugin", "install", plugin, "--scope", "user", cwd=home)
    else:
        if existing:
            # Local installs can be copies on Windows, but Grok's update assumes
            # they are live links. Refresh only this verified home-owned package.
            _run(executable, "plugin", "uninstall", name, "--keep-data", cwd=home)
        _run(executable, "plugin", "install", str(source), "--trust", cwd=home)

    verified = [row for row in _inventory(host, executable, home) if row["name"] == name]
    if len(verified) != 1 or verified[0]["enabled"] is not True:
        raise ValueError("Native install completed but a single enabled plugin could not be verified")
    entry = verified[0]
    if (entry.get("scope") != "user"
            or (host in {"codex", "claude"} and entry.get("marketplace") != MARKETPLACE)
            or (host in {"codex", "grok"} and not _same_path(entry.get("source"), source))):
        raise ValueError("Native install completed but the expected user registration/source could not be verified")
    installed_path = installed_path or verified[0].get("path")
    if not _matches(source, installed_path):
        return {"status": "needs_action", "message": "Installed files still differ from source after the native reinstall; setup does not edit host caches. Inspect the installed copy in the host, then rerun setup"}
    return {"status": "updated" if existing else "ready", "message": "Installation verified; start a new session", "path": installed_path}


def integrate(home: Path, packages: list[dict], detected: dict[str, dict], *,
              requested: tuple[str, ...] = ("orchflows",), install: bool = False) -> dict[str, dict]:
    """Failures are isolated by host and package; callers report incomplete registrations."""
    result = {}
    for host, detection in detected.items():
        report = dict(detection)
        result[host] = report
        if report["status"] != "available":
            continue
        if host == "agy":
            report["warnings"] = [agy_integration.POLICY_WARNING]
        wanted = [p for p in packages if p["name"] in requested]
        if not wanted:
            report.update(status="needs_action", message="Prepare the Orchflows home with setup first")
            continue
        if host in {"kimi", "zcode"}:
            report.update(_manual(host, home, wanted))
            continue
        try:
            # Codex requires an explicitly selected profile to exist before even
            # its read-only inventory commands work. Default profiles bootstrap natively.
            if install and host == "codex" and os.environ.get("CODEX_HOME"):
                Path(os.environ["CODEX_HOME"]).expanduser().mkdir(parents=True, exist_ok=True)
            inventory = _inventory(host, report["executable"], home)
            installed_names = {row["name"] for row in inventory}
            wanted = [p for p in packages if p["name"] in requested or p["name"] in installed_names]
            reports = {}
            for package in wanted:
                try:
                    reports[package["name"]] = _package(host, report["executable"], home, package, inventory, install=install)
                except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
                    reports[package["name"]] = {"status": "failed", "message": str(exc)}
            states = {item["status"] for item in reports.values()}
            report.update(status=next(state for state in ("failed", "needs_action", "updated", "ready") if state in states), packages=reports)
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            report.update(status="failed", message=str(exc))
        if report["status"] in {"failed", "needs_action"}:
            report.setdefault("next_steps", []).append(f"Resolve the reported {host} issue, then rerun setup --host {host} --home \"{home}\"")
    return result


def issues(reports: dict[str, dict]) -> list[str]:
    return [f"{host}: {report['status'].replace('_', ' ')}; see hosts.{host} for details"
            for host, report in reports.items() if report["status"] in {"failed", "needs_action"}]
