"""One-shot authoring for the named ``compositions/errand`` delivery."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

if __package__:
    from .tickets_admission import ADMISSION_PENDING, ticket_cohort
    from .tickets_format import (
        MUTATION_OPERATIONS, _extract_all, _extract_flag, _split_commas,
        canonical_json,
    )
    from .tickets_input_producers import render_ticket_inputs
    from .tickets_issue import _render_ticket, issue_admitted_ticket
    from .tickets_store import _cwd, _segment_error
else:
    from tickets_admission import ADMISSION_PENDING, ticket_cohort
    from tickets_format import (
        MUTATION_OPERATIONS, _extract_all, _extract_flag, _split_commas,
        canonical_json,
    )
    from tickets_input_producers import render_ticket_inputs
    from tickets_issue import _render_ticket, issue_admitted_ticket
    from tickets_store import _cwd, _segment_error


ERRAND_USAGE = (
    "errand <run> <id> --task TEXT (--executor E | --sequence E[,E...]) "
    "--path PATH [--path PATH ...] --bound B "
    "(--pre-existing-oracle NAME=COMMAND | --born-red-oracle NAME=COMMAND | "
    "--authored-here-oracle NAME=COMMAND)"
)
ORACLE_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SKILL_NAME_RE = re.compile(r"^orch-[a-z][a-z-]*$")


def _mutation(value: str) -> str:
    raw = str(value).strip().replace("\\", "/")
    operation, separator, named = raw.partition(":")
    if separator and operation in MUTATION_OPERATIONS:
        path = named
    else:
        path = raw
        target = _cwd() / path
        operation = "write" if raw.endswith("/") or target.is_dir() else (
            "change" if target.exists() else "create"
        )
    path = path.strip()
    if operation == "write":
        path = path.rstrip("/") + "/"
    return f"{operation}:{path}"


def _caller_is_isolated() -> bool:
    process = subprocess.run(
        ["git", "rev-parse", "--git-dir", "--git-common-dir"],
        cwd=str(_cwd()), text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if process.returncode:
        return False
    lines = [line.strip() for line in process.stdout.splitlines() if line.strip()]
    if len(lines) != 2:
        return False
    resolved = [
        (Path(value) if Path(value).is_absolute() else _cwd() / value).resolve()
        for value in lines
    ]
    return resolved[0] != resolved[1]


def _oracle(value: str, provenance: str):
    name, separator, command = str(value).partition("=")
    name, command = name.strip(), command.strip()
    if not separator or not ORACLE_NAME_RE.fullmatch(name) or not command:
        raise ValueError(
            "an errand oracle is NAME=COMMAND, with a unique lower-kebab name"
        )
    if "`" in command or "\n" in command or "\r" in command:
        raise ValueError("an errand oracle command is one line and contains no backtick")
    return {"name": name, "command": command, "provenance": provenance}


def _values(args: list, *flags: str) -> list:
    values = []
    for flag in flags:
        values.extend(_extract_all(args, flag))
    return values


def _cmd_errand(rest):
    args = list(rest)
    task = _extract_flag(args, "--task")
    simple_task = _extract_flag(args, "--simple-task")
    executor = _extract_flag(args, "--executor")
    sequence_arg = _extract_flag(args, "--sequence")
    bound = _extract_flag(args, "--bound")
    path_values = _values(args, "--path")
    paths_arg = _extract_flag(args, "--paths")
    scope_arg = _extract_flag(args, "--write-scope")
    mutations = _values(args, "--mutation")
    pre_existing = _values(args, "--pre-existing-oracle", "--born-red-oracle", "--oracle-born-red")
    authored = _values(args, "--authored-here-oracle", "--oracle-authored-here")
    generic = _values(args, "--oracle")
    generic_provenance = _extract_flag(args, "--oracle-provenance")
    provenance_alias = _extract_flag(args, "--provenance")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"errand does not accept {stray}. usage: {ERRAND_USAGE}"}
    if len(args) != 2:
        return {"error": f"usage: {ERRAND_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    if task is not None and simple_task is not None:
        return {"error": "errand takes one of --task or --simple-task"}
    task = task if task is not None else simple_task
    if not str(task or "").strip():
        return {"error": f"errand requires --task TEXT. usage: {ERRAND_USAGE}"}
    sequence = _split_commas(sequence_arg)
    if sequence:
        if len(sequence) < 2 or any(not SKILL_NAME_RE.fullmatch(item) for item in sequence):
            return {"error": "--sequence takes at least two exact comma-separated orch-* skill names"}
        if len(set(sequence)) != len(sequence):
            return {"error": "--sequence repeats a skill; each chain entry runs once"}
        if executor is not None and executor != sequence[0]:
            return {"error": "--executor must equal --sequence's head when both are supplied"}
        executor = sequence[0]
    if not executor or not SKILL_NAME_RE.fullmatch(executor):
        return {"error": f"errand requires --executor E or --sequence E[,E...]. usage: {ERRAND_USAGE}"}
    if not str(bound or "").strip():
        return {"error": f"errand requires --bound B. usage: {ERRAND_USAGE}"}
    path_values.extend(_split_commas(paths_arg))
    path_values.extend(_split_commas(scope_arg))
    mutations.extend(_mutation(path) for path in path_values)
    if not mutations:
        return {"error": f"errand requires at least one --path PATH. usage: {ERRAND_USAGE}"}
    provenance = generic_provenance or provenance_alias or "pre-existing"
    if provenance == "born-red":
        provenance = "pre-existing"
    if provenance not in {"pre-existing", "authored-here"}:
        return {"error": "--oracle-provenance is pre-existing, born-red, or authored-here"}
    try:
        oracles = [
            *(_oracle(value, "pre-existing") for value in pre_existing),
            *(_oracle(value, "authored-here") for value in authored),
            *(_oracle(value, provenance) for value in generic),
        ]
    except ValueError as error:
        return {"error": str(error)}
    if not oracles:
        return {"error": f"errand requires one named oracle. usage: {ERRAND_USAGE}"}
    names = [item["name"] for item in oracles]
    if len(set(names)) != len(names):
        return {"error": "errand oracle names must be unique"}
    normalized_mutations = []
    for value in mutations:
        try:
            rendered = _mutation(value)
        except OSError as error:
            return {"error": str(error)}
        if rendered not in normalized_mutations:
            normalized_mutations.append(rendered)
    write_scope = []
    for mutation in normalized_mutations:
        path = mutation.split(":", 1)[1]
        if path not in write_scope:
            write_scope.append(path)
    fields = {
        "id": ticket_id,
        "run": run,
        "status": "pending",
        "admission": ADMISSION_PENDING,
        "cohort": ticket_cohort(ticket_id),
        "executor": executor,
        "sequence": sequence or None,
        "pack": "orch-code-pack",
        "independence": "checker" if any(item["provenance"] == "authored-here" for item in oracles) else None,
        "depends_on": [],
        "write_scope": write_scope,
        "mutations": normalized_mutations,
        "isolation": "required" if _caller_is_isolated() else "none",
        "bound": bound,
        "claimed_by": "",
        "claimed_at": "",
    }
    inputs = [
        "- input: " + canonical_json({"name": "simple-task", "type": "literal", "value": task}),
        *("- input: " + canonical_json({"name": item["name"], "type": "literal", "value": item["command"]}) for item in oracles),
    ]
    criteria = [
        f'- {item["name"]} passes for the delivered result | oracle: `{item["command"]}` | oracle_class: deterministic | provenance: {item["provenance"]}'
        for item in oracles
    ]
    sections = [
        ("Objective", str(task).strip()),
        ("Fixed inputs", "\n".join(inputs)),
        ("Completion test", "\n".join(criteria)),
        ("Return fields", "status; result; verification; changed_artifacts; feedback; risks; Carry"),
        ("Result", ""), ("Verification", ""),
        ("Feedback", "[]"), ("Risks", "[]"), ("Carry", ""),
    ]
    text, input_error = render_ticket_inputs(_render_ticket(fields, sections), run)
    if input_error is not None:
        return {"error": input_error}
    return issue_admitted_ticket(run, ticket_id, text)


__all__ = ("ERRAND_USAGE", "_cmd_errand")
