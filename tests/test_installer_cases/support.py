"""Installer receipts and conservative uninstall behavior."""

# install.py runs on every interpreter from 3.9 up -- it carries this same
# future import and guards its own optional tomllib. These tests are held to
# the same floor, so the suite runs wherever the installer it covers does.
from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path, PurePosixPath
from unittest.mock import patch

import install
from installer import foundation
from tools import validate

_ENV_GUARD = patch.dict(os.environ)


def setUpModule():
    """Every test here fakes a home dir; a real ``CLAUDE_CONFIG_DIR``,
    ``CODEX_HOME`` or ``GROK_HOME`` in the developer's environment would send
    user-scope writes outside that fake."""

    _ENV_GUARD.start()
    os.environ.pop("CLAUDE_CONFIG_DIR", None)
    os.environ.pop("CODEX_HOME", None)
    os.environ.pop("GROK_HOME", None)


_SHARED: dict = {}


def tearDownModule():
    _ENV_GUARD.stop()
    # Each root is dropped with the value cached out of it. Dropping the root
    # alone would leave the cache answering a later caller with a path this
    # just deleted -- the builders below all treat a present key as a hit.
    for key, cached in (
        ("root", "value"),
        ("uninstall_root", "uninstalled"),
        ("runtime_template_root", "runtime_template"),
    ):
        _SHARED.pop(cached, None)
        root = _SHARED.pop(key, None)
        if root is not None:
            # Strict, like every other removal in this suite: a root that
            # cannot be removed is a failure worth hearing, and no shared
            # root can hold a repository, so `tree_removal.remove_repo_tree`
            # is not the owner here (see its docstring's scope clause).
            shutil.rmtree(root)


def built_runtime_template() -> Path:
    """One really-built private runtime, kept for this process to copy from.

    A build is ``ensurepip`` plus a hash-locked dependency install -- 14s on
    the author's host, 8s per test on the Windows leg -- and the lifecycle
    cases asked for ten of them. What those cases grade is policy: reuse,
    repair, refuse, uninstall retention, receipt state. None of it is about
    how the runtime was made, and a copy of a real one satisfies the same
    health probe at any path, which is asserted here before any copy is made.

    The builder's own output stays covered by the two cases that grade it:
    the symlinked base interpreter, and the end-to-end install run out of an
    active project venv. Both keep calling the real builder.
    """

    if "runtime_template" not in _SHARED:
        root = Path(tempfile.mkdtemp(prefix="orchflows-runtime-template-"))
        _SHARED["runtime_template_root"] = root
        template = root / "runtime"
        install._build_private_runtime(template)
        if not install.private_runtime_is_healthy(template):
            raise RuntimeError("runtime template is unhealthy; refusing to seed copies")
        _SHARED["runtime_template"] = template
    return _SHARED["runtime_template"]


def copied_runtime_builds():
    """Patch the runtime builder to copy `built_runtime_template` into place.

    ``_create_private_runtime`` reads the builder off ``install`` at call
    time, so patching the module attribute reaches the staging build inside
    it. ``dirs_exist_ok``: that staging directory is an existing mkdtemp.

    The template is resolved here, before the patch exists. Resolving it
    inside ``build`` would route the template's own build back through the
    patch that build is meant to satisfy, and recur until the stack ends.
    """

    template = built_runtime_template()

    def build(runtime_home):
        home = Path(runtime_home)
        shutil.copytree(template, home, symlinks=True, dirs_exist_ok=True)
        return install.private_runtime_python(home)

    return patch.object(install, "_build_private_runtime", new=build)


def relocated_user_install():
    """One user-scope install -- both hosts enabled, both config directories
    relocated -- applied once and shared by every test that only reads it.

    The apply is the whole cost of this module: it copies the library, every
    adapter, every agent and every script, and four tests were each paying
    for their own to read a different corner of one identical result.

    Read-only, and it has to stay that way: a test that writes into what this
    returns changes what the tests after it see. Anything that mutates its
    own install -- a reapply, an uninstall, a dry run proving nothing was
    written, a pre-seeded legacy file -- builds its own below, and the ones
    that grade *where* a surface lands unrelocated do too. Built on first use
    rather than in ``setUpModule`` so running one test costs one test.

    Returns the plan, the fake home, and the two relocated config directories.
    """

    if "value" not in _SHARED:
        root = Path(tempfile.mkdtemp(prefix="orchflows-shared-install-"))
        _SHARED["root"] = root
        home = root / "home"
        home.mkdir()
        claude_dir = root / "elsewhere" / "claude"
        claude_dir.mkdir(parents=True)
        codex_dir = root / "elsewhere" / "codex"
        codex_dir.mkdir(parents=True)
        with patch.object(install.Path, "home", return_value=home), patch.dict(
            os.environ,
            {"CLAUDE_CONFIG_DIR": str(claude_dir), "CODEX_HOME": str(codex_dir)},
        ), mock_host_clis("claude", "codex"):
            plan = install.build_plan("user", None)
            install.apply_plan(plan)
        _SHARED["value"] = (plan, home, claude_dir, codex_dir)
    return _SHARED["value"]


def relocated_user_uninstall():
    """The same install, its own copy, uninstalled once.

    Uninstall is destructive, so it cannot run over the shared read-only
    install -- but its *result* is read-only, and two tests read different
    halves of it: that Claude's adapters followed `CLAUDE_CONFIG_DIR` out of
    the removal and Codex's prompts and skills followed `CODEX_HOME`. One
    apply and one uninstall answer both.

    Returns the plan, the uninstall report, and the two config directories.
    """

    if "uninstalled" not in _SHARED:
        root = Path(tempfile.mkdtemp(prefix="orchflows-shared-uninstall-"))
        _SHARED["uninstall_root"] = root
        home = root / "home"
        home.mkdir()
        claude_dir = root / "elsewhere" / "claude"
        claude_dir.mkdir(parents=True)
        codex_dir = root / "elsewhere" / "codex"
        codex_dir.mkdir(parents=True)
        with patch.object(install.Path, "home", return_value=home), patch.dict(
            os.environ,
            {"CLAUDE_CONFIG_DIR": str(claude_dir), "CODEX_HOME": str(codex_dir)},
        ), mock_host_clis("claude", "codex"):
            plan = install.build_plan("user", None)
            install.apply_plan(plan)
            report = install.run_uninstall("user", None, dry_run=False)
        _SHARED["uninstalled"] = (plan, report, claude_dir, codex_dir)
    return _SHARED["uninstalled"]


def removed_unchanged(report: dict) -> set:
    return {
        action["path"]
        for action in report["skill_actions"]
        if action["action"] == "removed unchanged skill"
    }


def dangling_path_warnings(plan) -> list:
    """The hooks preflight's own warnings, selected by kind.

    A plan carries every true warning the run found, and which ones exist
    depends on the interpreter -- below 3.11 a codex plan also warns that
    the config merge went unparsed. Counting ``plan.warnings`` therefore
    pinned the interpreter, not the preflight; these tests mean "the hooks
    warning is here, once", so they select it and count that."""
    return [
        warning
        for warning in plan.warnings
        if "references a missing orchflows path" in warning
    ]


requires_tomllib = unittest.skipIf(
    install.tomllib is None,
    "reading back generated TOML requires tomllib (Python 3.11+); "
    "install.py guards its own use and still runs here",
)


# Spelled out rather than read off ``install``: a can-fail run against a
# revision that has no such constant must fail on behavior, not on an
# AttributeError raised in setUp. One case pins the constant to this literal.
SINK_ENV_VAR = "ORCHFLOWS_STATE_HOME"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_user_frontend(home: Path) -> Path:
    """Give a fake home the frontend precondition a project apply borrows."""

    destination = home / ".orchflows" / "ui"
    shutil.copytree(install.REPO_ROOT / "web" / "dist", destination)
    return destination


def mock_host_clis(*hosts: str):
    """Return a deterministic PATH lookup patch for selected host CLIs."""

    installed = set(hosts)

    def lookup(candidate: str) -> str | None:
        host = candidate.split(".", 1)[0]
        return str(Path("mock-bin") / candidate) if host in installed else None

    return patch.object(install.shutil, "which", side_effect=lookup)


@contextmanager
def isolated_grok_home(root: Path):
    """Select a fresh Grok home under ``root`` for the body of the ``with``.

    ``GROK_HOME`` is the only relocation the grok CLI reads, so it is the only
    lever a test has: faking ``Path.home`` alone still leaves a real
    ``GROK_HOME`` in the developer's environment pointing every Grok write at
    the home they actually use. Yields the directory, already created, so a
    caller can seed it before the code under test reads it.
    """

    grok_home = Path(root) / "grok-home"
    grok_home.mkdir(parents=True, exist_ok=True)
    with patch.dict(os.environ, {"GROK_HOME": str(grok_home)}):
        yield grok_home


# A bare filename the way a stub writes one: `search_plan.py`, never
# `scripts/search_plan.py`. A stub that spelled the path would be stale the
# day the script moved, so the bare form is the contract and this is what
# reads it.
BARE_SCRIPT_RE = re.compile(r"\b([a-z_]+\.py)\b")


def normalised_doc(docstring: str | None) -> str:
    """``docstring`` as one line: every run of whitespace becomes one space.

    Where a line break falls in a docstring is a fact about the source
    column limit, not about the code it describes. An assertion over the raw
    text reads that break as content and fails on a reflow that changed no
    word, so every assertion over ``install.__doc__`` reads through here
    instead. Words are all that survives, and words are all that is pinned.
    """

    return " ".join((docstring or "").split())


def doc_sentence(docstring: str | None) -> str:
    """The opening sentence of ``docstring`` or of a rendered description.

    ``splitlines()[0]`` is the first *line*, which is the first sentence
    only for as long as the wrap agrees -- reflow the summary onto two
    lines and the reader silently loses its tail. For ``install.__doc__``
    at 60 columns that tail is the clause closing its host list, which is
    enough to hand a list extractor ``Grok Build from``; narrower, it is a
    host outright. Normalising first makes the sentence the unit the caller
    meant. Takes ``argparse``'s rendered description as readily as a
    docstring, so the two surfaces that must agree on a host list can be
    read by one caller.
    """

    normalised = normalised_doc(docstring)
    head, stop, _ = normalised.partition(". ")
    return head + "." if stop else normalised


def doc_claim(docstring: str | None) -> str:
    """``docstring`` normalised further, for asserting a claim is absent.

    A negative assertion has the opposite failure mode to a positive one: a
    wrap does not break it, it *hides* a restatement behind the break, and
    the assertion passes while the claim is back. So the text is lowered and
    a hyphen is read as the space it stands in for, which collapses
    ``Stdlib-only``, ``stdlib only`` and a ``Stdlib-``/``only`` line break
    to one string. Widening further -- looking for ``stdlib`` alone --
    would also refuse the true sentence that ``install.py`` itself imports
    nothing outside the stdlib, which is a different claim.
    """

    return " ".join(normalised_doc(docstring).lower().replace("-", " ").split())


def doc_bullet(docstring: str | None, marker: str) -> str:
    """The one bullet opening with ``marker``, normalised.

    The bullet -- not the blank-line paragraph -- is the unit, because the
    host list in ``install.__doc__`` runs unbroken from ``~/.orchflows/`` to
    Grok Build: splitting on a blank line hands back every bullet after the
    marker, so an assertion meant for one host reads its neighbours too. A
    bullet ends at the first line that is not its indented continuation.

    Returns ``""`` when no bullet opens with ``marker``, which fails the
    caller's assertion about what that bullet says -- a marker that stopped
    matching is the same defect as a claim that stopped being made.
    """

    collected: list[str] = []
    for line in (docstring or "").splitlines():
        if not collected:
            if line.startswith(marker):
                collected.append(line)
            continue
        if not line.strip() or not line.startswith((" ", "\t")):
            break
        collected.append(line)
    return normalised_doc(" ".join(collected))


# The calls that turn raw docstring text into something an assertion may
# read. `rewrapped_doc` is deliberately absent: it hands back source text at
# a different column limit, which is exactly what must not be asserted over.
DOC_NORMALISERS = frozenset({
    "normalised_doc", "doc_sentence", "doc_claim", "doc_bullet",
    "codex_bullet", "stdlib_claims",
})


def _reads_raw_doc(node, tainted: set) -> bool:
    """Does ``node`` evaluate to docstring text no normaliser has touched?

    ``install.__doc__`` is the source, a name assigned from raw text carries
    it, and any call that is not a normaliser passes it through -- a
    ``.partition`` or an ``or ""`` hands back the same line breaks it was
    given. A normaliser call ends the taint, whatever it was handed.
    """

    if isinstance(node, ast.Attribute) and node.attr == "__doc__":
        return isinstance(node.value, ast.Name) and node.value.id == "install"
    if isinstance(node, ast.Name):
        return node.id in tainted
    if isinstance(node, ast.Call):
        name = node.func.attr if isinstance(node.func, ast.Attribute) else \
            getattr(node.func, "id", "")
        if name in DOC_NORMALISERS:
            return False
    return any(_reads_raw_doc(child, tainted) for child in ast.iter_child_nodes(node))


def _bound_names(target):
    """Every name ``target`` binds, unpacking included.

    ``_, separator, body = raw.partition(marker)`` binds three names to
    three pieces of raw text, and reading the assignment target as one name
    misses all three -- which is how the assertion that actually broke went
    unnamed the first time this walker was pointed at it.
    """

    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _bound_names(element)
    elif isinstance(target, ast.Starred):
        yield from _bound_names(target.value)


def raw_doc_assertions(tree) -> list:
    """``(assertion, line)`` for every assertion reading raw docstring text.

    The two assertions this repository had both pinned prose by substring,
    and one reached the raw text through a local rather than inline -- so
    the names are followed to a fixed point before the assertions are read.
    A fix that repaired only the assertions standing on the day it was
    written would have a shelf life; this states the law instead.
    """

    tainted: set = set()
    while True:
        found = set()
        for node in ast.walk(tree):
            targets = ()
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                targets = getattr(node, "targets", None) or [node.target]
            elif isinstance(node, ast.NamedExpr):
                targets = [node.target]
            if targets and node.value is not None and _reads_raw_doc(node.value, tainted):
                for target in targets:
                    found.update(_bound_names(target))
        if found <= tainted:
            break
        tainted |= found

    offenders = []
    for node in ast.walk(tree):
        called = isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        if not called or not node.func.attr.startswith("assert"):
            continue
        if any(_reads_raw_doc(argument, tainted) for argument in node.args):
            offenders.append((node.func.attr, node.lineno))
    return offenders


def rewrapped_doc(docstring: str | None, width: int) -> str:
    """``docstring`` reflowed to ``width`` columns: the can-fail fixture.

    A lawful rewrap moves line breaks and nothing else -- paragraphs and
    bullets keep their order and their words, a bullet keeps its two-space
    continuation indent, and no word or hyphenated compound is split. It is
    built beside the tree out of the real docstring rather than by rewriting
    ``install.py`` (rules/verification.md Section 8), so a test can ask what
    an assertion would say against a reflow nobody has committed yet.
    """

    lines: list[str] = []
    buffer: list[str] = []
    indent = ""

    def flush() -> None:
        if buffer:
            lines.extend(
                textwrap.wrap(
                    " ".join(buffer),
                    width=width,
                    subsequent_indent=indent,
                    break_long_words=False,
                    break_on_hyphens=False,
                )
            )
            del buffer[:]

    for line in (docstring or "").splitlines():
        if not line.strip():
            flush()
            indent = ""
            lines.append("")
            continue
        if line.startswith("- "):
            flush()
            indent = "  "
        elif not line.startswith((" ", "\t")):
            flush()
            indent = ""
        buffer.append(line.strip())
    flush()
    return "\n".join(lines) + "\n"
