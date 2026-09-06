"""Workflow-package containment and conservative literal-call checks.

The workflow remains prose.  This module only grades evidence the author
made unambiguous: package-local manifests and paths, plus literal Orchflows
commands.  It never turns sentences into steps or claims that a dynamic
branch will execute.
"""

from __future__ import annotations

import re
from pathlib import Path

try:
    from scripts import doclint, rings
except ImportError:  # pragma: no cover - installed flat script path
    import doclint
    import rings

from . import names, packages, standards, structure
from .common import MD_LINK_RE


COMMAND_RE = re.compile(
    r"(?:^|\s)(?:python(?:\.exe)?\s+)?"
    r"(?:[^\s`]*[\\/])?(tickets\.py|orchflows(?:\.py)?)\s+(\S+)(.*)$",
    re.IGNORECASE,
)
BACKTICK_RE = re.compile(r"`([^`\r\n]+)`")
NAME_FLAG_RE = re.compile(r"(?:^|\s)--(workflow|standard|skill)\s+([^\s\]]+)")
RETIRED_FLAGS = ("--pack", "--sheet", "--standard-file", "--workflow-file")
PRIVATE_DIRS = ("skills", "standards", "workflows")


def _items(package: Path, kind: str):
    root = package / rings.RING_DIRS[kind]
    if not root.is_dir():
        return []
    found = []
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest = directory / rings.MANIFESTS[kind]
        if manifest.is_file():
            found.append((directory, manifest))
    return found


def _commands(text: str):
    """Yield recognizable literal commands, joining flag continuations.

    Ordinary prose is outside the checker.  The accepted evidence is a
    command at the start of a line, an equally explicit ``python .../tickets.py``
    form, or a complete command inside one Markdown code span.
    """

    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        match = COMMAND_RE.search(line)
        inline = [
            found.group(0).strip()
            for span in BACKTICK_RE.findall(line)
            for found in [COMMAND_RE.search(span)]
            if found is not None
        ]
        for command in inline:
            yield command
        if match is None:
            index += 1
            continue
        # A command occurring after ordinary prose is only literal when the
        # Markdown code span above bounded it.
        if line[:match.start()].strip():
            index += 1
            continue
        parts = [" ".join(match.groups())]
        index += 1
        while index < len(lines):
            continuation = lines[index].strip()
            if not continuation or not continuation.lstrip("[").startswith("--"):
                break
            parts.append(continuation)
            index += 1
        yield " ".join(parts)


def _inside(path: Path, package: Path) -> bool:
    try:
        path.resolve().relative_to(package.resolve())
        return True
    except (OSError, ValueError):
        return False


def _validate_paths(package: Path, manifests, diag) -> None:
    for path in sorted(package.rglob("*")):
        if not _inside(path, package):
            diag.error(
                packages.rel(path),
                f"workflow package path escapes its public owner at {package}",
            )
    for manifest in manifests:
        text = packages._read_source(manifest)
        for match in MD_LINK_RE.finditer(text):
            target = match.group(1)
            resolved = doclint.resolve_link(manifest, target)
            if (
                resolved is not None
                and not _inside(resolved, package)
                and not _library_law_reference(resolved)
            ):
                diag.error(
                    packages.rel(manifest),
                    f"workflow package link escapes its public owner and the "
                    f"canonical library law roots: {target}",
                )


def _library_law_reference(path: Path) -> bool:
    """Whether an external link names canonical library prose authors may cite."""

    try:
        relative = path.resolve().relative_to(rings.lib_root().resolve())
    except (OSError, ValueError):
        return False
    return bool(relative.parts) and relative.parts[0] in {"contracts", "docs", "rules"}


def _validate_private_skills(package: Path, diag) -> None:
    for directory, manifest in _items(package, "skill"):
        pkg = {
            "path": directory, "skill_md": manifest, "kind": "skill",
            "is_standard": False,
        }
        fm, _body = packages.parse_frontmatter(
            packages._read_source(manifest), packages.rel(manifest), diag,
        )
        if fm is None:
            continue
        packages.validate_frontmatter(fm, pkg, diag)
        packages.validate_role(
            fm, pkg, diag, allowed=packages.APPLIED_ROLE_VALUES,
        )


def _validate_private_standards(package: Path, standard_roots, diag) -> None:
    roots = [package / rings.RING_DIRS["standard"], *standard_roots]
    root_packages = []
    for directory, manifest in _items(package, "standard"):
        source = packages._read_source(manifest)
        standard = {
            "path": directory, "manifest": manifest,
            "narrows": packages.declares_narrows(source),
        }
        standards.validate_standard_contents(standard, diag)
        fm, body = packages.parse_frontmatter(source, packages.rel(manifest), diag)
        if fm is None or body is None:
            continue
        if standard["narrows"]:
            standards.validate_standard_frontmatter(fm, standard, diag)
            standards.validate_standard_sections(body, standard, diag)
            standards.validate_standard_lens(body, fm, standard, diag, roots)
            standards.validate_standard_adapter(fm, {"skill_md": manifest}, diag)
            structure.validate_standard_budget(manifest, diag)
            continue
        pkg = {
            "path": directory, "skill_md": manifest, "kind": "standard",
            "is_standard": True, "frontmatter": fm, "body": body,
        }
        root_packages.append(pkg)
        packages.validate_frontmatter(fm, pkg, diag)
        packages.validate_role(fm, pkg, diag)
        packages.validate_anatomy(body, pkg, diag)
        standards.validate_standard_adapter(fm, pkg, diag)
        structure.validate_standard_budget(manifest, diag)
    names.validate_standard_sections(root_packages, diag)


def _literal_name(value: str):
    value = value.strip().strip("[]")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value if rings.NAME_RE.fullmatch(value) else None


def _validate_commands(package_records, manifests, diag, overrides) -> None:
    node_by_path = {str(path.resolve()): path for path in manifests}
    graph = {str(path.resolve()): set() for path in manifests}
    labels = {str(path.resolve()): packages.rel(path) for path in manifests}

    for owner, manifest in package_records:
        node = str(manifest.resolve())
        for command in _commands(packages._read_source(manifest)):
            for retired in RETIRED_FLAGS:
                if re.search(rf"(?:^|\s){re.escape(retired)}(?:\s|$)", command):
                    diag.error(
                        packages.rel(manifest),
                        f"literal workflow command uses obsolete flag {retired}; "
                        "use the current command help",
                    )
            for flag, raw in NAME_FLAG_RE.findall(command):
                name = _literal_name(raw)
                if name is None:
                    continue
                kind = "workflow" if flag == "workflow" else flag
                scoped_owner = owner if kind in rings.KINDS else None
                try:
                    record = rings.resolve(
                        kind, name, owner=scoped_owner, trust=False, **overrides,
                    )
                except rings.RingError as error:
                    diag.error(
                        packages.rel(manifest),
                        f"literal --{flag} name does not resolve: {error.detail}",
                    )
                    continue
                if (
                    kind == "workflow"
                    and _command_verb(command) == "frame-open"
                    and "--parent" in command.split()
                ):
                    target = str(Path(str(record["path"])).resolve())
                    if target in node_by_path:
                        graph[node].add(target)
        diag.warn(
            packages.rel(manifest),
            "static workflow check covers literal Orchflows commands and "
            "contained paths; dynamic or implied prose calls are unchecked",
        )

    cycle = structure.find_cycle(graph)
    if cycle:
        diag.error(
            labels[cycle[0]],
            "literal workflow call cycle: "
            + " -> ".join(labels[path] for path in cycle),
        )


def _command_verb(command: str) -> str:
    match = COMMAND_RE.search(command)
    return match.group(2) if match is not None else ""


def validate_workflow_packages(
    ring: Path,
    public_items,
    diag,
    *,
    standard_roots,
    overrides=None,
) -> None:
    """Grade private package members and literal calls for public workflows."""

    overrides = dict(overrides or {})
    package_records = []
    manifests = []
    for package, public_manifest in public_items:
        package = Path(package)
        workflow_manifests = [public_manifest]
        private_workflows = _items(package, "workflow")
        private_skills = _items(package, "skill")
        private_standards = _items(package, "standard")
        if private_workflows:
            structure.validate_templates(
                diag, roots=[package / rings.RING_DIRS["workflow"]],
            )
            workflow_manifests.extend(
                manifest for _directory, manifest in private_workflows
            )
        package_manifests = [
            *workflow_manifests,
            *(manifest for _directory, manifest in private_skills),
            *(manifest for _directory, manifest in private_standards),
        ]
        _validate_private_skills(package, diag)
        _validate_private_standards(package, standard_roots, diag)
        _validate_paths(package, package_manifests, diag)
        manifests.extend(workflow_manifests)
        package_records.extend(
            (package.name, manifest) for manifest in workflow_manifests
        )
    _validate_commands(package_records, manifests, diag, overrides)


__all__ = (
    "COMMAND_RE", "NAME_FLAG_RE", "PRIVATE_DIRS", "RETIRED_FLAGS",
    "validate_workflow_packages",
)
