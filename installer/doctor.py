"""Read-only comparison of one desired installation plan with disk state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .managed_text import upsert_import_line, upsert_marked_block
from .models import Plan


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finding(identity: str, path: Path | None = None, **details) -> dict:
    finding = {"id": identity}
    if path is not None:
        finding["path"] = str(path)
    finding.update(details)
    return finding


def _planned_files(plan: Plan):
    """Every file the desired plan wants on disk, as the doctor reads it.

    A second reading of the same ``Plan`` that ``application.apply_plan``
    writes from, and nothing in either file holds the two equal. What holds
    them equal is ``tests/test_install_doctor_parity.py``: it runs the real
    write loop over a plan held maximal against ``Plan``'s fields and fails
    on any ``(path, kind)`` one enumerates and the other does not. Add a
    field here without adding it there and a healthy install reports itself
    as ``receipt.unexpected-entry`` junk -- which is what happened to the
    whole Grok column once already.
    """

    for source, destination in plan.lib_copies:
        yield "catalog", "lib", destination, source, None
    for source, destination in plan.scripts:
        yield "catalog", "script", destination, source, None
    for source, destination in plan.frontend_assets:
        yield "catalog", "frontend-asset", destination, source, None
    for destination, content in plan.by_name:
        yield "by-name", "by-name", destination, None, content
    for kind, entries in (
        ("adapter", plan.claude_adapters),
        ("prompt", plan.codex_prompts),
        ("codex-skill", plan.codex_skills),
        ("grok-skill", plan.grok_skills),
    ):
        for destination, content in entries:
            yield "redirect", kind, destination, None, content
    for kind, entries in (
        ("claude-agent", plan.claude_agents),
        ("codex-agent", plan.codex_agents),
        ("grok-agent", plan.grok_agents),
    ):
        for destination, content in entries:
            yield "role-profile", kind, destination, None, content
    for config in plan.configs:
        yield "configuration", config.kind, config.dest, None, config.content
    # The two whole managed files: Claude's ``~/.orchflows/host-block.md`` and
    # Grok's ``$GROK_HOME/rules/orchflows.md``. Neither is a ``configs`` entry,
    # so each is named here or is inspected by nothing -- and an installed file
    # the desired plan never names reads back as ``receipt.unexpected-entry``,
    # which is the report telling a whole host to delete itself.
    for managed in (plan.host_block, plan.grok_rules):
        if managed is not None:
            yield "configuration", managed.kind, managed.dest, None, managed.content


def _read_receipt(path: Path):
    if not path.is_file():
        return None, _finding("receipt.missing", path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, _finding("receipt.unreadable", path, actual=type(error).__name__)
    if not isinstance(value, dict):
        return None, _finding("receipt.invalid-shape", path, actual=type(value).__name__)
    return value, None


def _inspect_receipt(
    plan: Plan,
    receipt: dict,
    planned_files: list,
    current_source_commit: str | None,
) -> list[dict]:
    findings = []
    for field, expected in (
        ("version", 4),
        ("scope", plan.scope),
        ("project_root", str(plan.project_root) if plan.project_root is not None else None),
        ("lib_home", str(plan.lib_home)),
        ("bin_dir", str(plan.bin_dir)),
    ):
        if receipt.get(field) != expected:
            findings.append(
                _finding(
                    f"receipt.{field}",
                    plan.receipt_path,
                    expected=expected,
                    actual=receipt.get(field),
                )
            )
    if receipt.get("install_in_progress") is True:
        findings.append(_finding("receipt.install-in-progress", plan.receipt_path))
    if (
        current_source_commit is not None
        and receipt.get("source_commit") != current_source_commit
    ):
        findings.append(
            _finding(
                "receipt.source-commit",
                plan.receipt_path,
                expected=current_source_commit,
                actual=receipt.get("source_commit"),
            )
        )

    raw_entries = receipt.get("files")
    if not isinstance(raw_entries, list):
        findings.append(
            _finding("receipt.files-shape", plan.receipt_path, actual=type(raw_entries).__name__)
        )
        raw_entries = []
    entries = {}
    for entry in raw_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            findings.append(_finding("receipt.file-entry-shape", plan.receipt_path))
            continue
        key = (entry["path"], entry.get("kind"))
        if key in entries:
            findings.append(_finding("receipt.duplicate-entry", Path(entry["path"])))
        entries[key] = entry

    expected = {(str(destination), kind) for _, kind, destination, _, _ in planned_files}
    for path_text, kind in sorted(expected):
        entry = entries.get((path_text, kind))
        path = Path(path_text)
        if entry is None:
            findings.append(_finding("receipt.missing-entry", path, kind=kind))
            continue
        recorded = entry.get("sha256")
        if not isinstance(recorded, str):
            findings.append(_finding("receipt.missing-hash", path, kind=kind))
        elif path.is_file() and _digest(path) != recorded:
            findings.append(_finding("receipt.hash", path, kind=kind))
    for path_text, kind in sorted(set(entries) - expected):
        findings.append(_finding("receipt.unexpected-entry", Path(path_text), kind=kind))

    expected_blocks = {
        (str(block.dest), block.start_marker, block.end_marker) for block in plan.blocks
    }
    actual_blocks = {
        (entry.get("path"), entry.get("start_marker"), entry.get("end_marker"))
        for entry in receipt.get("blocks", [])
        if isinstance(entry, dict)
    }
    for path_text, _start, _end in sorted(expected_blocks - actual_blocks):
        findings.append(_finding("receipt.missing-block", Path(path_text)))

    expected_imports = set()
    if plan.claude_import is not None:
        expected_imports.add(
            (str(plan.claude_import.dest), f"@{plan.claude_import.import_target}")
        )
    actual_imports = {
        (entry.get("path"), entry.get("import_line"))
        for entry in receipt.get("imports", [])
        if isinstance(entry, dict)
    }
    for path_text, _line in sorted(expected_imports - actual_imports):
        findings.append(_finding("receipt.missing-import", Path(path_text)))
    return findings


def _inspect_planned_file(surface, kind, destination, source, content):
    if source is not None and not source.is_file():
        return _finding("desired-plan.missing-source", source, kind=kind)
    if not destination.is_file():
        return _finding(f"{surface}.missing", destination, kind=kind)
    try:
        matches = (
            destination.read_bytes() == source.read_bytes()
            if source is not None
            else destination.read_text(encoding="utf-8") == content
        )
    except (OSError, UnicodeError) as error:
        return _finding(
            f"{surface}.unreadable", destination, kind=kind, actual=type(error).__name__
        )
    if not matches:
        return _finding(f"{surface}.content", destination, kind=kind)
    return None


def inspect_installation(
    plan: Plan, *, current_source_commit: str | None = None
) -> dict:
    """Return a deterministic drift report without changing the filesystem."""

    findings = []
    planned_files = list(_planned_files(plan))
    destinations = {}
    for surface, kind, destination, source, content in planned_files:
        key = str(destination)
        if key in destinations:
            findings.append(
                _finding(
                    "desired-plan.duplicate-destination",
                    destination,
                    kinds=sorted((destinations[key], kind)),
                )
            )
        else:
            destinations[key] = kind
        finding = _inspect_planned_file(surface, kind, destination, source, content)
        if finding is not None:
            findings.append(finding)

    for block in plan.blocks:
        path = block.dest
        if not path.is_file():
            findings.append(_finding("configuration.block-missing", path))
            continue
        try:
            current = path.read_text(encoding="utf-8")
            desired = upsert_marked_block(
                current, block.content, block.start_marker, block.end_marker
            )
        except (OSError, UnicodeError, ValueError) as error:
            findings.append(
                _finding("configuration.block-unreadable", path, actual=type(error).__name__)
            )
        else:
            if desired != current:
                findings.append(_finding("configuration.block-content", path))

    if plan.claude_import is not None:
        imp = plan.claude_import
        if not imp.dest.is_file():
            findings.append(_finding("configuration.import-missing", imp.dest))
        else:
            try:
                current = imp.dest.read_text(encoding="utf-8")
                desired, _action = upsert_import_line(
                    current,
                    f"@{imp.import_target}",
                    imp.legacy_start_marker,
                    imp.legacy_end_marker,
                )
            except (OSError, UnicodeError, ValueError) as error:
                findings.append(
                    _finding("configuration.import-unreadable", imp.dest, actual=type(error).__name__)
                )
            else:
                if desired != current:
                    findings.append(_finding("configuration.import-content", imp.dest))

    receipt, receipt_finding = _read_receipt(plan.receipt_path)
    if receipt_finding is not None:
        findings.append(receipt_finding)
    elif receipt is not None:
        findings.extend(
            _inspect_receipt(plan, receipt, planned_files, current_source_commit)
        )

    findings.sort(
        key=lambda item: (
            item["id"],
            item.get("path", ""),
            json.dumps(item, sort_keys=True, default=str),
        )
    )
    return {
        "status": "coherent" if not findings else "drift",
        "findings": findings,
    }
