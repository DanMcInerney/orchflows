"""Shared document-reading mechanics for static-tree invariant cases."""
import ast
import re
import sys
from pathlib import Path

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.validate as validate  # noqa: E402

COMPOSITIONS = ROOT / "example-workflows"
WORKFLOW_FILE = "SKILL.md"
CALL_EDGE_RE = re.compile(r"`(orch-[a-z0-9-]+)`")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FRONTMATTER_RE = re.compile(r"---\n(.*?)\n---\n(.*)", re.DOTALL)

_PACKAGES = None


def packages():
    """One ``discover_packages()`` walk for the whole collection."""
    global _PACKAGES
    if _PACKAGES is None:
        _PACKAGES = validate.discover_packages()
    return _PACKAGES


def frontmatter_name(skill_md: Path):
    """Read a declared name independently of validate.py's parser."""
    for line in skill_md.read_text(encoding="utf-8").split("\n"):
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


def read_flat(path: Path) -> str:
    """File text with whitespace collapsed, so wrapped clauses match."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


def split_document(path: Path):
    """Return ``(frontmatter fields, body)`` for a markdown document."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.fullmatch(text)
    if match is None:
        return {}, text
    fields = {}
    for line in match.group(1).splitlines():
        if not line[:1].strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, match.group(2)


def bodies(*paths: Path) -> str:
    return "".join(split_document(path)[1] for path in paths)


def workflow_files(directory: Path):
    """One workflow's whole surface: its single body. A workflow is a skill
    whose prose calls callables, so there are no stubs beside it to read."""
    return (directory / WORKFLOW_FILE,)


def workflow_directories():
    """Every `example-workflows/<name>/` that is a workflow, not shared data."""
    return sorted(
        directory for directory in COMPOSITIONS.iterdir()
        if directory.is_dir() and (directory / WORKFLOW_FILE).is_file()
    )


def called_name(node):
    """The bare name of a call target, independent of import style."""
    function = node.func
    if isinstance(function, ast.Attribute):
        return function.attr
    return function.id if isinstance(function, ast.Name) else None


def calls_named(node, name):
    return any(
        isinstance(child, ast.Call) and called_name(child) == name
        for child in ast.walk(node)
    )
