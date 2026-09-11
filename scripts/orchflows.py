#!/usr/bin/env python3
"""Set up and resolve a portable orchflows home (Python 3.11+, no dependencies)."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import subprocess
import sys
import tomllib
import uuid
import venv


CORE_NAME = "orchflows-light"
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json")
CORE_ENTRIES = (
    "plugin.json", ".claude-plugin", ".codex-plugin", ".agents", "skills",
    "standards", "docs", "scripts", "README.md", "LICENSE", "LICENSE.md",
)
EXCLUDED = {
    ".git", ".local", ".venv", "venv", "__pycache__", ".pytest_cache",
    "node_modules", "test-results", "test-output",
    "worktrees", ".worktrees", "logs", "outputs",
}
NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")
HOME_README = """# My orchflows library

Keep custom native workflow packages in `libraries/<name>/`, with a portable
`plugin.json` and sibling `skills/<skill>/SKILL.md` files. Commit the libraries,
`config.toml`, `.gitattributes`, and useful run summaries with ordinary Git.
Setup initializes Git when available but never commits or publishes anything.

`.local/` contains this machine's Python runtime and managed core package. It is
ignored, as are raw logs and bulk run artifacts. Run metadata and `summary.md`
remain trackable. The seeded `.gitattributes` keeps their exact bytes across Git
checkouts, preserving summary hashes even when computers use different line
endings. Setup preserves existing attributes; setup and doctor report missing
byte-preservation rules when Git is available. Each library declares its own
optional dependencies; setup installs no third-party Python packages.

After cloning this home, restore `.local/` using Python 3.11+ and a supplied core
package: `python /path/to/orchflows-light/scripts/orchflows.py setup --home
/path/to/this-home --source /path/to/orchflows-light`. Setup preserves existing
files and libraries. Rerunning setup initializes missing pieces; it is not an
upgrade command. If a supplied source differs from the installed core, inspect
and explicitly move the old managed core aside before restoring from that source.
An unknown remote source cannot be restored automatically.

Use `.local/runtime/Scripts/python.exe` on Windows or `.local/runtime/bin/python`
elsewhere to call `.local/packages/orchflows-light/scripts/orchflows.py`. Pass
`--home /path/to/this-home`, or set `ORCHFLOWS_HOME`, from any project. `doctor`
checks the installation and `resolve NAME --skill SKILL` returns concrete paths.
The portable native catalogs live in `.agents/plugins/marketplace.json` (Codex)
and `.claude-plugin/marketplace.json` (Claude), named `orchflows-home`. Setup seeds
them when absent and preserves edits. Register this home through each host's
native marketplace controls. Setup sets both hosts' user concurrency settings
to 15; use --concurrency N to choose another value or --skip-host-config to
preserve host settings. See the installed core's docs/native-hosts.md for the
different limits, configuration paths, and backups.
"""
HOME_GITIGNORE = """# Machine-specific packages, runtime, caches and working files.
/.local/
**/__pycache__/
**/*.py[cod]
# Keep compact run metadata and summaries; ignore raw and bulk outputs.
/logs/*/*/*
!/logs/*/*/run.json
!/logs/*/*/summary.md
"""
HOME_GITATTRIBUTES = """# Preserve compact run bytes, including the summary's recorded SHA-256.
/logs/**/run.json -text
/logs/**/summary.md -text
"""


def home_path(value: str | Path | None = None) -> Path:
    selected = value if value is not None else os.environ.get("ORCHFLOWS_HOME")
    return Path(selected).expanduser().resolve() if selected else (Path.home() / ".orchflows").resolve()


def _contained(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes {root}: {path}")
    return resolved


def _name(value: str, kind: str = "library") -> str:
    if not NAME.fullmatch(value) or value in {".", ".."}:
        raise ValueError(f"Invalid {kind} name: {value!r}")
    return value


def _read_toml(path: Path, *, required: bool = False) -> dict:
    if not path.exists():
        if required:
            raise ValueError(f"Missing configuration: {path}")
        return {}
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Malformed configuration preserved at {path}: {exc}") from exc


def _manifest(root: Path) -> dict:
    found = []
    for relative in MANIFESTS:
        path = _contained(root, root / relative)
        if not path.is_file():
            continue
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Malformed package manifest {path}: {exc}") from exc
        if not isinstance(manifest, dict) or not isinstance(manifest.get("name"), str):
            raise ValueError(f"Package manifest needs a name: {path}")
        _name(manifest["name"])
        if not isinstance(manifest.get("version"), str) or not manifest["version"]:
            raise ValueError(f"Package manifest needs a version: {path}")
        found.append(manifest)
    if not found:
        raise ValueError(f"No package manifest found in {root}")
    if len({entry["name"] for entry in found}) != 1:
        raise ValueError(f"Ambiguous package names in {root}")
    return {"name": found[0]["name"], "version": found[0]["version"]}


def _is_link(path: Path) -> bool:
    # Windows junctions expose reparse attributes even on Python 3.11, which
    # lacks os.path.isjunction. Reject them before walking or copying content.
    return path.is_symlink() or bool(
        getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _files(root: Path, *, core: bool) -> list[Path]:
    """Enumerate deployable bytes without following links or copying host state."""
    paths = []

    def visit(path: Path) -> None:
        if path.name in EXCLUDED or (core and path.name in {"tests", "example-workflows"}) or path.suffix in {".pyc", ".pyo"}:
            return
        if _is_link(path):
            raise ValueError(f"Package copy does not follow links: {path}")
        if path.is_dir():
            for child in sorted(path.iterdir()):
                visit(child)
        elif path.is_file():
            paths.append(path)

    entries = [root / entry for entry in CORE_ENTRIES] if core else sorted(root.iterdir())
    for entry in entries:
        if entry.exists() or entry.is_symlink():
            visit(entry)
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _identity(root: Path) -> dict:
    manifest = _manifest(root)
    digest = hashlib.sha256()
    for path in _files(root, core=True):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        contents = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(contents).to_bytes(8, "big"))
        digest.update(contents)
    return {**manifest, "content_sha256": digest.hexdigest()}


def _validate_core(root: Path) -> dict:
    manifest = _manifest(root)
    if manifest["name"] != CORE_NAME:
        raise ValueError(f"Core source must identify as {CORE_NAME}: {root}")
    for relative in ("skills", "standards", "docs", "scripts/orchflows.py"):
        path = _contained(root, root / relative)
        valid = path.is_file() if relative.endswith(".py") else path.is_dir()
        if not valid:
            raise ValueError(f"Incomplete core package; missing {relative}: {root}")
    return _identity(root)


def _copy_package(source: Path, destination: Path, *, core: bool) -> None:
    files = _files(source, core=core)
    stage = destination.parent / f".{destination.name}-{uuid.uuid4().hex}"
    stage.mkdir()
    try:
        for path in files:
            target = stage / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        if destination.exists():
            raise ValueError(f"Package destination already exists: {destination}")
        stage.rename(destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def _create_text(path: Path, contents: str) -> str:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(contents)
        return "created"
    except FileExistsError:
        return "preserved"


def runtime_python(home: Path) -> Path:
    relative = "Scripts/python.exe" if os.name == "nt" else "bin/python"
    # A POSIX venv normally links its executable to the base interpreter.
    runtime = _contained(home, home / ".local/runtime")
    return runtime / relative


def _check_runtime(home: Path) -> dict:
    runtime = _contained(home, home / ".local/runtime")
    python = runtime_python(home)
    if not (runtime / "pyvenv.cfg").is_file() or not python.is_file():
        raise ValueError(f"Runtime is missing or incomplete; existing contents preserved: {runtime}")
    probe = subprocess.run(
        [str(python), "-I", "-B", "-c",
         "import json,sys; print(json.dumps({'version':list(sys.version_info[:3]),'prefix':sys.prefix,'base_prefix':sys.base_prefix}))"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if probe.returncode != 0:
        raise ValueError(f"Runtime interpreter failed; existing contents preserved: {python}")
    try:
        result = json.loads(probe.stdout)
        version = tuple(result["version"])
        prefix = Path(result["prefix"]).resolve()
        base_prefix = Path(result["base_prefix"]).resolve()
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid runtime interpreter response: {python}") from exc
    if prefix != runtime or base_prefix == runtime or version < (3, 11):
        raise ValueError(f"Expected a Python 3.11+ venv at {runtime}; existing contents preserved")
    return {"runtime_python": str(python), "version": ".".join(map(str, version))}


def _toml_string(value: str) -> str:
    # JSON basic strings are compatible with TOML for these text/path values.
    return json.dumps(value, ensure_ascii=False)


def _config_text(identity: dict) -> str:
    lines = ["# Portable home identity; machine paths belong in .local/config.toml.", "schema_version = 1", "", "[core]"]
    lines.extend(f"{key} = {_toml_string(value)}" for key, value in identity.items())
    return "\n".join(lines) + "\n"


def _check_config_identity(config: dict, identity: dict) -> list[str]:
    expected = config.get("core", {})
    if not isinstance(expected, dict):
        return ["config.toml [core] must be a table; file preserved"]
    return [f"Installed core {key} differs from config.toml; file preserved"
            for key in ("name", "version", "content_sha256")
            if key in expected and expected[key] != identity[key]]


def _catalogs(home: Path, libraries: list[dict], *, create: bool) -> tuple[dict, list[str]]:
    sources = {CORE_NAME: f"./.local/packages/{CORE_NAME}"}
    names = [entry["name"] for entry in libraries]
    for entry in libraries:
        if entry["name"] != CORE_NAME and names.count(entry["name"]) == 1:
            relative = Path(entry["package_root"]).relative_to(home).as_posix()
            sources[entry["name"]] = f"./{relative}"
    catalogs = {
        ".agents/plugins/marketplace.json": {
            "name": "orchflows-home",
            "interface": {"displayName": "Orchflows Home"},
            "plugins": [{"name": name, "source": {"source": "local", "path": source},
                         "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                         "category": "Productivity"}
                        for name, source in sources.items()],
        },
        ".claude-plugin/marketplace.json": {
            "name": "orchflows-home", "owner": {"name": "orchflows-home"},
            "plugins": [{"name": name, "source": source} for name, source in sources.items()],
        },
    }
    statuses, issues = {}, []
    for relative, catalog in catalogs.items():
        path = _contained(home, home / relative)
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
            statuses[relative] = _create_text(path, json.dumps(catalog, indent=2) + "\n")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            plugins = data.get("plugins") if isinstance(data, dict) else None
            if not isinstance(plugins, list) or not all(isinstance(item, dict) for item in plugins):
                raise ValueError("plugins must be an array of objects")
            for name, source in sources.items():
                matches = [item for item in plugins if item.get("name") == name]
                registered = matches[0].get("source") if len(matches) == 1 else None
                if isinstance(registered, dict):
                    registered = registered.get("path") if registered.get("source") == "local" else None
                if registered != source:
                    issues.append(f"Catalog {relative} needs registration for {name} at {source}; existing file preserved")
            if data.get("name") != "orchflows-home":
                issues.append(f"Catalog {relative} has a different marketplace name; existing file preserved")
            statuses.setdefault(relative, "ok")
        except (OSError, UnicodeError, ValueError) as exc:
            statuses.setdefault(relative, "unavailable")
            issues.append(f"Catalog {relative} is unreadable or malformed; existing file preserved: {exc}")
    return statuses, issues


def _gitignore_issues(home: Path) -> list[str]:
    git = shutil.which("git")
    if not git or not (home / ".git").exists():
        return []
    paths = (".local/config.toml", "logs/2000-01/doctor-check/raw/output.json",
             "logs/2000-01/doctor-check/artifacts/output.html")
    result = subprocess.run(
        [git, "-C", str(home), "check-ignore", "--no-index", "-z", "--stdin"],
        input="\0".join(paths) + "\0", text=True, capture_output=True, check=False,
    )
    if result.returncode not in (0, 1):
        return [f"Could not check the home's Git ignore rules: {result.stderr.strip()}"]
    ignored = set(result.stdout.split("\0"))
    return [f"Git does not ignore {path}; add an ignore rule after reviewing the preserved .gitignore"
            for path in paths if path not in ignored]


def _gitattributes_issues(home: Path) -> list[str]:
    try:
        attributes = _contained(home, home / ".gitattributes")
        if not attributes.is_file():
            return ["Missing home file: .gitattributes; rerun setup to seed run byte-preservation rules"]
    except (OSError, ValueError) as exc:
        return [str(exc)]
    git = shutil.which("git")
    if not git or not (home / ".git").exists():
        return []
    paths = ("logs/2000-01/doctor-check/run.json", "logs/2000-01/doctor-check/summary.md")
    result = subprocess.run(
        [git, "-C", str(home), "check-attr", "-z", "--stdin", "text"],
        input="\0".join(paths) + "\0", text=True, capture_output=True, check=False,
    )
    if result.returncode:
        return [f"Could not check the home's Git attributes: {result.stderr.strip()}"]
    fields = result.stdout.split("\0")
    values = dict(zip(fields[::3], fields[2::3]))
    return [f"Git does not preserve exact bytes for {path}; add /logs/**/{Path(path).name} -text "
            "after reviewing the preserved .gitattributes"
            for path in paths if values.get(path) != "unset"]


def setup(home: Path, source: Path, example: str | None = None, *,
          concurrency: int = 15, skip_host_config: bool = False) -> dict:
    # Load the sibling even when a caller uses runpy/importlib from another directory.
    spec = importlib.util.spec_from_file_location("orchflows_host_config", Path(__file__).with_name("host_config.py"))
    host_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(host_config)

    home, source = home.resolve(), source.resolve()
    # Validate input and existing configuration before any filesystem mutation.
    for relative in ("config.toml", "README.md", ".gitignore", ".gitattributes", ".git", "libraries", "logs", ".local",
                     ".local/config.toml", ".local/runtime", ".local/packages", f".local/packages/{CORE_NAME}",
                     ".agents/plugins/marketplace.json", ".claude-plugin/marketplace.json"):
        _contained(home, home / relative)
    config = _read_toml(home / "config.toml")
    _read_toml(home / ".local/config.toml")
    source_identity = _validate_core(source)
    if example is not None:
        _name(example, "example")
        destination = _contained(home, home / "libraries" / example)
        example_source = _contained(source, source / "example-workflows" / example)
        if not destination.exists() and example_source.is_dir():
            if _manifest(example_source)["name"] != example:
                raise ValueError(f"Example identity differs from its requested name: {example_source}")
    host_plans = [] if skip_host_config else host_config.prepare_host_configs(concurrency)
    home.mkdir(parents=True, exist_ok=True)
    for relative in ("libraries", "logs", ".local/packages"):
        (home / relative).mkdir(parents=True, exist_ok=True)

    issues = []
    core = home / ".local/packages" / CORE_NAME
    if core.exists():
        identity = _validate_core(core)
        core_status = "reused"
        if identity != source_identity:
            core_status = "preserved"
            issues.append(f"Existing core differs from supplied source; setup preserves it. Setup is not an upgrade command: inspect {core} and explicitly move it aside before restoring a different source")
    else:
        _copy_package(source, core, core=True)
        identity = source_identity
        core_status = "installed"

    files = {
        "config.toml": _create_text(home / "config.toml", _config_text(identity)),
        "README.md": _create_text(home / "README.md", HOME_README),
        ".gitignore": _create_text(home / ".gitignore", HOME_GITIGNORE),
        ".gitattributes": _create_text(home / ".gitattributes", HOME_GITATTRIBUTES),
    }
    if files["config.toml"] == "preserved":
        issues.extend(_check_config_identity(config, identity))
    python = runtime_python(home)
    local_text = ("# Machine-local paths; ignored by the home repository.\nschema_version = 1\n"
                  f"source = {_toml_string(str(source))}\n"
                  f"core = {_toml_string(str(core))}\n"
                  f"runtime_python = {_toml_string(str(python))}\n")
    files[".local/config.toml"] = _create_text(home / ".local/config.toml", local_text)

    runtime = home / ".local/runtime"
    runtime_status = "preserved" if runtime.exists() else "created"
    try:
        if not runtime.exists():
            venv.EnvBuilder(with_pip=False).create(runtime)
        runtime_info = _check_runtime(home)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        runtime_status = "unavailable"
        runtime_info = {"runtime_python": str(python)}
        issues.append(str(exc))

    example_info = None
    if example is not None:
        if destination.exists():
            example_status = "preserved"
        elif not example_source.is_dir():
            example_status = "unavailable"
            issues.append(f"Example {example} is absent from this core source; supply a checkout containing it")
        else:
            _copy_package(example_source, destination, core=False)
            example_status = "installed"
        example_info = {"name": example, "status": example_status, "package_root": str(destination)}

    libraries, library_issues = _libraries(home)
    catalogs, catalog_issues = _catalogs(home, libraries, create=True)
    files.update(catalogs)
    issues.extend(library_issues)
    issues.extend(catalog_issues)

    git_status = "preserved"
    if not (home / ".git").exists():
        git = shutil.which("git")
        if git:
            result = subprocess.run([git, "-C", str(home), "init", "--quiet"], capture_output=True, text=True, check=False)
            git_status = "initialized" if result.returncode == 0 else "unavailable"
            if result.returncode:
                issues.append(f"Git initialization failed: {result.stderr.strip()}")
        else:
            git_status = "unavailable"
    issues.extend(_gitignore_issues(home))
    issues.extend(_gitattributes_issues(home))
    host_configs, host_issues = host_config.apply_host_configs(host_plans)
    issues.extend(host_issues)
    return {"status": "partial" if issues else "ready", "home": str(home), "files": files,
            "runtime_python": str(python),
            "core": {"status": core_status, "package_root": str(core), **identity},
            "runtime": {"status": runtime_status, **runtime_info}, "example": example_info,
            "git": git_status, "host_configs": host_configs,
            "host_config_status": "skipped" if skip_host_config else "partial" if host_issues else "configured",
            "issues": issues}


def _libraries(home: Path) -> tuple[list[dict], list[str]]:
    entries, issues = [], []
    directory = _contained(home, home / "libraries")
    if not directory.is_dir():
        return entries, [f"Missing libraries directory: {directory}"]
    for path in sorted(directory.iterdir()):
        if path.name.startswith("."):
            continue
        try:
            root = _contained(home, path)
            if not root.is_dir():
                continue
            manifest = _manifest(root)
            skills = _contained(root, root / "skills")
            if not skills.is_dir():
                raise ValueError(f"Library lacks a skills directory: {root}")
            entries.append({**manifest, "package_root": str(root)})
        except (OSError, ValueError) as exc:
            issues.append(str(exc))
    names = [entry["name"] for entry in entries]
    for name in sorted(set(names)):
        if names.count(name) > 1 or name == CORE_NAME:
            issues.append(f"Ambiguous library name: {name}")
    return entries, issues


def resolve(home: Path, library: str, skill: str | None = None, resource: str | None = None) -> dict:
    home = home.resolve()
    _name(library)
    entries, issues = _libraries(home)
    matches = [entry for entry in entries if entry["name"] == library]
    if library == CORE_NAME:
        root = _contained(home, home / ".local/packages" / CORE_NAME)
        matches.append({**_validate_core(root), "package_root": str(root)})
    if len(matches) > 1:
        raise ValueError(f"Ambiguous library name: {library}")
    if not matches:
        detail = "; ".join(issues)
        raise ValueError(f"Library {library} is not installed" + (f": {detail}" if detail else ""))
    result = matches[0].copy()
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
        if not path.exists():
            raise ValueError(f"Resource does not exist: {path}")
        result["resource_path"] = str(path)
    result["runtime_python"] = _check_runtime(home)["runtime_python"]
    return result


def doctor(home: Path) -> dict:
    home = home.resolve()
    issues, checks = [], {}
    config = {}
    for relative in ("config.toml", ".local/config.toml"):
        try:
            parsed = _read_toml(_contained(home, home / relative), required=True)
            if relative == "config.toml":
                config = parsed
            checks[relative] = "ok"
        except (OSError, ValueError) as exc:
            checks[relative] = "unavailable"
            issues.append(str(exc))
    try:
        core = _contained(home, home / ".local/packages" / CORE_NAME)
        identity = _validate_core(core)
        checks["core"] = {"package_root": str(core), **identity}
        issues.extend(_check_config_identity(config, identity))
    except (OSError, ValueError) as exc:
        checks["core"] = "unavailable"
        issues.append(str(exc))
    try:
        checks["runtime"] = _check_runtime(home)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        checks["runtime"] = "unavailable"
        issues.append(str(exc))
    entries = []
    try:
        entries, library_issues = _libraries(home)
        checks["libraries"] = entries
        issues.extend(library_issues)
    except (OSError, ValueError) as exc:
        checks["libraries"] = "unavailable"
        issues.append(str(exc))
    for relative in ("README.md", ".gitignore", "logs"):
        try:
            if not _contained(home, home / relative).exists():
                issues.append(f"Missing home entry: {relative}")
        except ValueError as exc:
            issues.append(str(exc))
    try:
        checks["catalogs"], catalog_issues = _catalogs(home, entries, create=False)
        issues.extend(catalog_issues)
    except (OSError, ValueError) as exc:
        issues.append(str(exc))
    issues.extend(_gitignore_issues(home))
    issues.extend(_gitattributes_issues(home))
    runtime = checks.get("runtime")
    return {"status": "incomplete" if issues else "ready", "home": str(home), "checks": checks,
            "runtime_python": runtime.get("runtime_python") if isinstance(runtime, dict) else None,
            "issues": issues}


def _add_home(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--home", default=argparse.SUPPRESS, help="Home directory (default: ORCHFLOWS_HOME or ~/.orchflows)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    _add_home(parser)
    commands = parser.add_subparsers(dest="command", required=True)
    setup_parser = commands.add_parser("setup", help="Initialize or restore a portable home")
    _add_home(setup_parser)
    setup_parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    setup_parser.add_argument("--example", metavar="NAME", help="Copy a named library from the supplied source's example-workflows directory")
    host_options = setup_parser.add_mutually_exclusive_group()
    host_options.add_argument("--concurrency", type=int, default=15, metavar="N",
                              help="Set Codex's spawned-thread cap and Claude's shared tool/subagent cap (default: 15)")
    host_options.add_argument("--skip-host-config", action="store_true", help="Preserve all native host settings")
    doctor_parser = commands.add_parser("doctor", help="Check a home without changing it")
    _add_home(doctor_parser)
    resolve_parser = commands.add_parser("resolve", help="Resolve a package, skill or resource")
    _add_home(resolve_parser)
    resolve_parser.add_argument("library")
    request = resolve_parser.add_mutually_exclusive_group()
    request.add_argument("--skill")
    request.add_argument("--resource")
    run_parser = commands.add_parser("run", help="Record a workflow run")
    _add_home(run_parser)
    run_commands = run_parser.add_subparsers(dest="run_command", required=True)
    start_parser = run_commands.add_parser("start")
    _add_home(start_parser)
    start_parser.add_argument("--workflow", required=True)
    start_parser.add_argument("--project")
    finish_parser = run_commands.add_parser("finish")
    _add_home(finish_parser)
    finish_parser.add_argument("run_dir", type=Path)
    finish_parser.add_argument("--status", required=True, choices=["complete", "partial", "blocked"])
    finish_parser.add_argument("--summary", required=True, type=Path)
    from native_logs import add_parser, run as read_native_history
    add_parser(commands)
    args = parser.parse_args(argv)
    try:
        home = home_path(getattr(args, "home", None))
        if args.command == "setup":
            result = setup(home, args.source.expanduser().resolve(), args.example,
                           concurrency=args.concurrency, skip_host_config=args.skip_host_config)
        elif args.command == "doctor":
            result = doctor(home)
        elif args.command == "resolve":
            result = resolve(home, args.library, args.skill, args.resource)
        elif args.command == "history":
            result = read_native_history(args)
        else:
            from run_log import finish_run, start_run
            if args.run_command == "start":
                result = start_run(home, args.workflow, args.project)
            else:
                result = finish_run(home, args.run_dir, args.status, args.summary)
    except (OSError, ValueError, subprocess.SubprocessError, ImportError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        return 2
    # Native logs can exceed the character repertoire of Windows pipe encodings.
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=args.command == "history"))
    return 1 if args.command in {"setup", "doctor"} and result.get("issues") else 0


if __name__ == "__main__":
    raise SystemExit(main())
