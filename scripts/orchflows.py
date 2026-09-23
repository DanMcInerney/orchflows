#!/usr/bin/env python3
"""Set up and resolve a portable orchflows home (Python 3.11+, no dependencies)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import subprocess
import sys
import uuid
import venv

if __name__ == "__main__":
    sys.dont_write_bytecode = True

import host_config
import host_integration
import native_logs
import package_files


CORE_NAME = "orchflows"
CORE_ENTRIES = ("plugin.json", ".claude-plugin", ".codex-plugin", ".kimi-plugin", "skills", "guidance", "docs", "scripts",
                "README.md", "DESIGN.md", "AGENTS.md", "CLAUDE.md", "LICENSE")
NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
HOME_README = """# orchflows home

Docs: `.local/packages/orchflows/AGENTS.md`. Edit `libraries/<name>/`; `.local/` and `artifacts/` are ignored.
"""
HOME_GITIGNORE = """/.local/
**/__pycache__/
**/*.py[cod]
/artifacts/
"""


def home_path(value: str | Path | None = None) -> Path:
    """An explicit home must name a path; an empty ORCHFLOWS_HOME counts as unset."""
    if value is not None and not str(value).strip():
        raise ValueError("Home path is empty")
    selected = value if value is not None else os.environ.get("ORCHFLOWS_HOME")
    return Path(selected).expanduser().resolve() if selected else (Path.home() / ".orchflows").resolve()


def _contained(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes {root}: {path}")
    return resolved


def _name(value: str, kind: str = "library") -> str:
    if not NAME.fullmatch(value):
        raise ValueError(f"Invalid {kind} name: {value!r}")
    return value


def _manifest(root: Path) -> dict:
    path = root / "plugin.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"No package manifest found in {root}") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Malformed package manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("name"), str):
        raise ValueError(f"Package manifest needs a name: {path}")
    if not isinstance(manifest.get("version"), str) or not manifest["version"]:
        raise ValueError(f"Package manifest needs a version: {path}")
    return {"name": _name(manifest["name"]), "version": manifest["version"]}


def _files(root: Path, *, core: bool) -> list[Path]:
    """Enumerate deployable bytes without following links, caches, tests or evaluator-only trials."""
    if core:
        return package_files.files(root, entries=CORE_ENTRIES, skip={"tests", "example-workflows"})
    return package_files.files(root, skip={"trials"})


def _validate_core(root: Path) -> dict:
    manifest = _manifest(root)
    if manifest["name"] != CORE_NAME:
        raise ValueError(f"Core source must identify as {CORE_NAME}: {root}")
    for relative in ("skills", "guidance", "docs", "scripts/orchflows.py"):
        path = root / relative
        if not (path.is_file() if relative.endswith(".py") else path.is_dir()):
            raise ValueError(f"Incomplete core package; missing {relative}: {root}")
    return manifest


def _install(source: Path, destination: Path, *, core: bool) -> bool:
    """Stage and swap a package, retaining the previous copy if restoration fails."""
    stage = destination.with_name(f".{destination.name}-{uuid.uuid4().hex}")
    previous = None
    try:
        for path in _files(source, core=core):
            target = stage / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        if destination.exists():
            previous = destination.with_name(f".{destination.name}-previous-{uuid.uuid4().hex}")
            os.replace(destination, previous)
        try:
            os.replace(stage, destination)
        except OSError:
            if previous:
                try:
                    os.replace(previous, destination)
                except OSError as exc:
                    raise OSError(f"Package swap and restoration failed; previous copy retained at {previous}") from exc
            raise
        if previous:
            shutil.rmtree(previous, ignore_errors=True)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return previous is not None


def _seed_text(path: Path, contents: str) -> str:
    if package_files.is_link(path) or path.exists():
        return "preserved"
    path.write_text(contents, encoding="utf-8", newline="\n")
    return "created"


def _replace_text(path: Path, contents: str) -> str:
    temporary = path.with_name(f".{path.name}-{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="") as stream:
            stream.write(contents)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return "written"


def runtime_python(home: Path) -> Path:
    return home / ".local/runtime" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _registrable(libraries: list[dict]) -> list[dict]:
    """Home libraries that catalogs and hosts may register: unique names other than core."""
    names = [entry["name"] for entry in libraries]
    return [entry for entry in libraries if entry["name"] != CORE_NAME and names.count(entry["name"]) == 1]


def _catalog_texts(home: Path, libraries: list[dict], core_version: str | None = None) -> dict[str, str]:
    sources = {CORE_NAME: f"./.local/packages/{CORE_NAME}"}
    versions = {CORE_NAME: core_version}
    for entry in _registrable(libraries):
        sources[entry["name"]] = "./" + Path(entry["package_root"]).relative_to(home).as_posix()
        versions[entry["name"]] = entry["version"]
    catalogs = {
        ".agents/plugins/marketplace.json": {
            "name": "orchflows-home",
            "interface": {"displayName": "Orchflows Home"},
            "plugins": [{"name": name, "source": {"source": "local", "path": source},
                         "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                         "category": "Productivity"} for name, source in sources.items()],
        },
        ".claude-plugin/marketplace.json": {
            "name": "orchflows-home", "owner": {"name": "orchflows-home"},
            "plugins": [{"name": name, "source": source} for name, source in sources.items()],
        },
        "marketplace.json": {
            "name": "orchflows-home",
            "plugins": [{"name": name, "source": source,
                         **({"version": versions[name]} if versions[name] is not None else {})}
                        for name, source in sources.items()],
        },
    }
    return {relative: json.dumps(catalog, indent=2) + "\n" for relative, catalog in catalogs.items()}


def _install_runtime(home: Path) -> tuple[str, list[str]]:
    runtime = home / ".local/runtime"
    if not runtime.exists():
        venv.EnvBuilder(with_pip=False).create(runtime)
        return "created", []
    if (runtime / "pyvenv.cfg").is_file() and runtime_python(home).is_file():
        return "preserved", []
    return "unavailable", [f"Runtime is missing or incomplete; existing contents preserved: {runtime}"]


def _example_plan(home: Path, source: Path, example: str) -> str:
    _name(example, "example")
    destination, example_source = home / "libraries" / example, source / "example-workflows" / example
    if package_files.is_link(destination):
        raise ValueError(f"Setup does not write through links: {destination}")
    if destination.exists():
        return "preserved"
    if not example_source.is_dir():
        return "unavailable"
    if _manifest(example_source)["name"] != example:
        raise ValueError(f"Example identity differs from its requested name: {example_source}")
    return "installed"


def _init_git(home: Path) -> tuple[str, list[str]]:
    if (home / ".git").exists():
        return "preserved", []
    git = shutil.which("git")
    if not git:
        return "unavailable", []
    result = subprocess.run([git, "-C", str(home), "init", "--quiet"], capture_output=True, text=True, check=False)
    if result.returncode:
        return "unavailable", [f"Git initialization failed: {result.stderr.strip()}"]
    return "initialized", []


def setup(home: Path, source: Path, example: str | None = None, *,
          concurrency: int | None = None,
          hosts: list[str] | tuple[str, ...] | None = None) -> dict:
    home, source = home.resolve(), source.resolve()
    _validate_core(source)
    selected = host_integration.select_hosts(hosts)
    if concurrency is not None and (type(concurrency) is not int or concurrency < 1):
        raise ValueError("Concurrency must be a positive integer")
    if concurrency is not None and not selected:
        raise ValueError("--concurrency requires selected hosts")
    for relative in ("libraries", ".local", ".local/packages", f".local/packages/{CORE_NAME}", ".local/runtime",
                     ".agents", ".agents/plugins", ".claude-plugin", ".git"):
        if package_files.is_link(home / relative):
            raise ValueError(f"Setup does not write through links: {home / relative}")
    if example is not None:
        _example_plan(home, source, example)
    detected = host_integration.detect(hosts)
    host_plans, config_issues, config_failures = [], [], {}
    if concurrency is not None:
        for host, detection in detected.items():
            if detection["status"] == "available":
                if host not in host_config.SUPPORTED_HOSTS:
                    message = f"No verified concurrency setting for {host}; no settings changed for this host"
                    config_failures[host] = {"status": "unsupported", "message": message}
                    config_issues.append(message)
                    continue
                try:
                    host_plans.extend(host_config.prepare_host_configs(concurrency, (host,)))
                except (OSError, ValueError) as exc:
                    config_failures[host] = {"status": "unavailable", "message": str(exc)}
                    config_issues.append(str(exc))
        if not host_plans and not config_failures:
            config_issues.append("Concurrency tuning requires a detected host with a supported setting; no settings changed")
    core_path = home / ".local/packages" / CORE_NAME
    core_path.parent.mkdir(parents=True, exist_ok=True)
    lock = core_path.parent / ".setup.lock"
    try:
        lock.open("x").close()
    except FileExistsError as exc:
        raise ValueError(f"Setup lock exists: {lock}; check for an active installer before removing it") from exc
    try:
        manifest = _validate_core(source)
        plan = _example_plan(home, source, example) if example is not None else None
        for relative in ("libraries", ".agents/plugins", ".claude-plugin"):
            (home / relative).mkdir(parents=True, exist_ok=True)
        status = "reused"
        if source != core_path:
            status = "updated" if _install(source, core_path, core=True) else "installed"
        core = {"package_root": str(core_path), **manifest, "status": status}
        files = {"README.md": _seed_text(home / "README.md", HOME_README),
                 ".gitignore": _seed_text(home / ".gitignore", HOME_GITIGNORE)}
        runtime, issues = _install_runtime(home)
        example_info = None
        if example is not None:
            if plan == "installed":
                _install(source / "example-workflows" / example, home / "libraries" / example, core=False)
            elif plan == "unavailable":
                issues.append(f"Example {example} is absent from this core source; supply a checkout containing it")
            example_info = {"name": example, "status": plan, "package_root": str(home / "libraries" / example)}
        libraries, library_issues = _libraries(home)
        issues.extend(library_issues)
        for relative, text in _catalog_texts(home, libraries, manifest["version"]).items():
            files[relative] = _replace_text(home / relative, text)
        git, git_issues = _init_git(home)
        issues.extend(git_issues)
        host_configs, host_issues = host_config.apply_host_configs(host_plans)
        host_configs.update(config_failures)
        issues.extend(config_issues + host_issues)
        packages = [{**manifest, "package_root": str(core_path)}, *_registrable(libraries)]
        registrations = host_integration.integrate(home, packages, detected, install=True,
                                                  requested=(CORE_NAME, example) if example else (CORE_NAME,))
        issues.extend(host_integration.issues(registrations))
        return {"status": "partial" if issues else "ready", "home": str(home), "files": files,
                "runtime_python": str(runtime_python(home)), "core": core, "runtime": runtime, "example": example_info,
                "git": git, "host_configs": host_configs,
                "host_config_status": "skipped" if concurrency is None else "partial" if host_issues or config_issues else "configured",
                "hosts": registrations,
                "issues": issues}
    finally:
        lock.unlink()


def _libraries(home: Path) -> tuple[list[dict], list[str]]:
    entries, issues = [], []
    directory = home / "libraries"
    if not directory.is_dir():
        return entries, [f"Missing libraries directory: {directory}"]
    for path in sorted(directory.iterdir()):
        if path.name.startswith(".") or not path.is_dir():
            continue
        try:
            root = _contained(home, path)
            manifest = _manifest(root)
            if not (root / "skills").is_dir():
                raise ValueError(f"Library lacks a skills directory: {root}")
            entries.append({**manifest, "package_root": str(root)})
        except (OSError, ValueError) as exc:
            issues.append(str(exc))
    names = [entry["name"] for entry in entries]
    issues.extend(f"Ambiguous library name: {name}" for name in sorted(set(names)) if names.count(name) > 1 or name == CORE_NAME)
    return entries, issues


def resolve(home: Path, library: str, skill: str | None = None, resource: str | None = None) -> dict:
    home = home.resolve()
    _name(library)
    entries, issues = _libraries(home)
    matches = [entry for entry in entries if entry["name"] == library]
    if library == CORE_NAME:
        root = home / ".local/packages" / CORE_NAME
        matches.append({**_validate_core(root), "package_root": str(root)})
    if len(matches) > 1:
        raise ValueError(f"Ambiguous library name: {library}")
    if not matches:
        detail = "; ".join(issues)
        raise ValueError(f"Library {library} is not installed" + (f": {detail}" if detail else ""))
    result = dict(matches[0])
    root = Path(result["package_root"])
    if skill is not None:
        _name(skill, "skill")
        path = _contained(root, root / "skills" / skill / "SKILL.md")
        if not path.is_file():
            raise ValueError(f"Skill {library}:{skill} is not installed")
        result["skill_path"] = str(path)
    if resource is not None:
        windows = PureWindowsPath(resource)
        parts = PurePosixPath(resource.replace("\\", "/")).parts
        if not resource or windows.drive or windows.root or not parts or ".." in parts or any(":" in part for part in parts):
            raise ValueError(f"Resource must be a safe relative package path: {resource!r}")
        path = _contained(root, root.joinpath(*parts))
        # Devices such as NUL or CON "exist" inside any directory on Windows; only files and directories resolve.
        if not (path.is_file() or path.is_dir()):
            raise ValueError(f"Resource is not a file or directory in the package: {path}")
        result["resource_path"] = str(path)
    result["runtime_python"] = str(runtime_python(home))
    return result


def doctor(home: Path, hosts: list[str] | tuple[str, ...] | None = None) -> dict:
    home = home.resolve()
    host_integration.select_hosts(hosts)
    issues, checks = [], {}
    core = home / ".local/packages" / CORE_NAME
    core_version = None
    try:
        manifest = _validate_core(core)
        core_version = manifest["version"]
        checks["core"] = {"package_root": str(core), **manifest}
    except (OSError, ValueError) as exc:
        checks["core"] = "unavailable"
        issues.append(str(exc))
    runtime, python = home / ".local/runtime", runtime_python(home)
    checks["runtime"] = "ok" if (runtime / "pyvenv.cfg").is_file() and python.is_file() else "unavailable"
    if checks["runtime"] == "unavailable":
        issues.append(f"Runtime is missing or incomplete: {runtime}")
    entries, library_issues = _libraries(home)
    checks["libraries"] = entries
    issues.extend(library_issues)
    issues.extend(f"Missing home entry: {relative}" for relative in ("README.md", ".gitignore") if not (home / relative).exists())
    checks["catalogs"] = {}
    for relative, text in _catalog_texts(home, entries, core_version).items():
        path = home / relative
        stale = not path.is_file() or path.read_text(encoding="utf-8") != text
        checks["catalogs"][relative] = "stale" if stale else "ok"
        if stale:
            issues.append(f"Catalog {relative} does not match the installed libraries; rerun setup")
    packages = [checks["core"]] if isinstance(checks["core"], dict) else []
    packages.extend(_registrable(entries))
    registrations = host_integration.integrate(home, packages, host_integration.detect(hosts)) if home.is_dir() else {}
    issues.extend(host_integration.issues(registrations))
    return {"status": "incomplete" if issues else "ready", "home": str(home), "checks": checks, "hosts": registrations,
            "runtime_python": str(python) if checks["runtime"] == "ok" else None, "issues": issues}


def _display(result: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, separators=(",", ":")))
        return
    print(f"Orchflows home: {result['home']}")
    reports = result.get("hosts", {})
    if not reports:
        print("Home only; host registration was not requested.")
    for host, report in reports.items():
        print(f"{host:<10} {report['status'].replace('_', ' ').capitalize()}")
        if report.get("message"):
            print(f"  {report['message']}")
        for warning in report.get("warnings", []):
            print(f"  Note: {warning}")
        for name, package in report.get("packages", {}).items():
            print(f"  {name}: {package['message']}")
        for step in report.get("next_steps", []):
            print(f"  {step}")
    if reports and all(report["status"] == "not_detected" for report in reports.values()):
        print("Home prepared. Install a supported host, then rerun setup.")
    for issue in result.get("issues", []):
        print(f"Issue: {issue}")
    if result.get("host_config_status") == "configured":
        print("Requested concurrency settings applied.")
    if any(report["status"] in {"ready", "updated"} for report in reports.values()):
        print("Start new host sessions to load Orchflows.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    home_help = "Home directory; must not be empty (default: ORCHFLOWS_HOME when set and non-empty, else ~/.orchflows)"
    setup_parser = commands.add_parser("setup", help="Install or update the managed core and initialize a portable home")
    setup_parser.add_argument("--home", help=home_help)
    setup_parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    setup_parser.add_argument("--example", metavar="NAME", help="Copy a named library from the source's example-workflows directory")
    setup_parser.add_argument("--concurrency", type=int, metavar="N",
                              help="Tune supported concurrency limits in detected, selected hosts (default: preserve settings)")
    doctor_parser = commands.add_parser("doctor", help="Check a home without changing it")
    doctor_parser.add_argument("--home", help=home_help)
    for command in (setup_parser, doctor_parser):
        command.add_argument("--host", action="append", choices=(*host_integration.HOSTS, "auto", "none"),
                             help="Target host; repeat to select several. Default: auto. 'none' checks/prepares the home only")
        command.add_argument("--json", action="store_true", help="Print JSON even in a terminal (always JSON when piped)")
    resolve_parser = commands.add_parser("resolve", help="Resolve a package, skill or resource")
    resolve_parser.add_argument("--home", help=home_help)
    resolve_parser.add_argument("library")
    request = resolve_parser.add_mutually_exclusive_group()
    request.add_argument("--skill")
    request.add_argument("--resource")
    native_logs.add_parser(commands)
    args = parser.parse_args(argv)
    try:
        if args.command == "setup":
            result = setup(home_path(args.home), args.source.expanduser(), args.example,
                           concurrency=args.concurrency, hosts=args.host)
        elif args.command == "doctor":
            result = doctor(home_path(args.home), hosts=args.host)
        elif args.command == "resolve":
            result = resolve(home_path(args.home), args.library, args.skill, args.resource)
        else:
            result = native_logs.run(args)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2
    _display(result, as_json=args.command not in {"setup", "doctor"} or args.json or not sys.stdout.isatty())
    return 1 if args.command in {"setup", "doctor"} and result.get("issues") else 0


if __name__ == "__main__":
    raise SystemExit(main())
