"""Floor members: attempts that know nothing of the task and must earn nothing.

`noop` writes nothing, `empty` writes an empty deliverable, `echo_input` copies the task's input into the
deliverable's name. A domain's own `random_valid_format` heuristic (a well-formed answer with no work behind it)
is also a floor. Each returns the files to write, as {relative path: bytes}.
"""
from pathlib import Path

GENERIC = ("noop", "empty", "echo_input")


def _output(io: dict) -> str:
    return io.get("output") or "output.json"


def run(name: str, workspace: Path, prompt: str, io: dict, domain=None) -> dict[str, bytes]:
    workspace = Path(workspace)
    if name == "noop":
        return {}
    if name == "empty":
        return {_output(io): b""}
    if name == "echo_input":
        sources = [n for n in (io.get("inputs") or []) if (workspace / n).is_file()]
        if not sources:
            sources = sorted(p.relative_to(workspace).as_posix() for p in workspace.glob("*") if p.is_file())
        return {_output(io): (workspace / sources[0]).read_bytes()} if sources else {}
    heuristic = getattr(domain, "HEURISTICS", {}).get(name)
    if heuristic is None:
        raise ValueError(f"unknown floor {name!r}")
    return heuristic(workspace, prompt)
