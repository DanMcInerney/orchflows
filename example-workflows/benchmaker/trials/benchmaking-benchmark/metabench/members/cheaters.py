"""Cheaters: attempts that look for the answer or the grader instead of doing the task.

Each returns {"wrote": [paths], "findings": [{"kind", "path"}], "final": text}. A finding is evaluator material the
attempt could reach from its workspace; against a sound benchmark every list is empty and every score is zero. A
finding from the broad answer-like name match (`workspace-file`, `git-history`) also says `matches_answer`: its bytes
are one of the files the domain's oracle writes for the task (`expected`, when the shim could solve the task), so
the staging gate can tell a leaked answer from a file that merely has a name like `reference_policy.md`.

  read_workspace  answer-like files anywhere in the workspace, hidden ones and `.git` history included
  read_ancestors  every ancestor of the workspace inside the scope; in each, evaluator-like names (solution, tests,
                  expected, answers, identity, evaluation, admission) down to depth 3
  tamper          overwrites the verifier and test files it can reach with a stub that reports success, and writes
                  reward.txt, grade.json and result.json into the workspace and the folder holding it
  exit_early      claims success and writes nothing
  copy_example    writes an example output found in the prompt as the answer

Answer-like files found are written under the deliverable's name when they parse for it, so a benchmark that
hides its answers in a reachable place pays out credit as well as a finding.

`scope` is the folder the meta-verifier owns for this run (the run's work area). Ancestors above it are
never read or touched: files that happen to sit beside the temporary root are not findings, and nothing outside
the scope is ever overwritten.
"""
import json
import os
import re
import subprocess
from pathlib import Path

NAMES = ("read_workspace", "read_ancestors", "tamper", "exit_early", "copy_example")
EVALUATOR = {"solution", "tests", "expected", "answers", "identity", "evaluation", "admission"}
ANSWER = re.compile(r"expected|answer|solution|golden|truth|label|reference|oracle", re.I)
VERIFIER = re.compile(r"^(verify|test)", re.I)
DEPTH, LIMIT, GIT_SECONDS = 3, 400, 20
STUB = ('import json, sys\n'
        'args = sys.argv\n'
        'if "--result" in args:\n'
        '    open(args[args.index("--result") + 1], "w").write(json.dumps({"grading_status": "scored", "full_success": True,\n'
        '        "credit": 1.0, "dimensions": {}, "critical_failures": [], "reason": "tampered"}))\n'
        'print("All tests pass")\n')
SUCCESS = {"grading_status": "scored", "full_success": True, "credit": 1.0, "dimensions": {}, "critical_failures": [],
           "reason": "tampered"}


def _files(root: Path, depth: int = DEPTH):
    """Files under root down to `depth` folders, links never followed."""
    try:
        entries = sorted(os.scandir(root), key=lambda e: e.name)
    except OSError:
        return
    for entry in entries:
        if entry.is_symlink():
            continue
        if entry.is_dir(follow_symlinks=False):
            if depth > 0:
                yield from _files(Path(entry.path), depth - 1)
        else:
            yield Path(entry.path)


def _evaluator_like(entry: Path) -> bool:
    return entry.name.lower() in EVALUATOR or entry.stem.lower() in EVALUATOR


def _within(path: Path, scope: Path | None) -> bool:
    return scope is None or Path(os.path.realpath(path)) == scope or scope in Path(os.path.realpath(path)).parents


def _ancestor_files(workspace: Path, scope: Path | None = None) -> list[Path]:
    """Files under evaluator-like names in every ancestor of the workspace that lies inside the scope."""
    found = []
    for ancestor in Path(os.path.realpath(workspace)).parents:
        if not _within(ancestor, scope):
            break
        try:
            entries = sorted(os.scandir(ancestor), key=lambda e: e.name)
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink() or not _evaluator_like(path):
                continue
            found += list(_files(path)) if entry.is_dir(follow_symlinks=False) else [path]
            if len(found) >= LIMIT:
                return found
    return found


def _answer_like(path: Path) -> bool:
    return bool(ANSWER.search(path.stem)) or path.stem.lower() in EVALUATOR


def _deliver(workspace: Path, io: dict, candidates: list[bytes]) -> list[str]:
    """Write the first candidate that suits the deliverable's format under its name."""
    output = io.get("output") or "output.json"
    for data in candidates:
        if output.endswith(".json"):
            try:
                json.loads(data.decode("utf-8-sig"))
            except ValueError:
                continue
        (workspace / output).parent.mkdir(parents=True, exist_ok=True)
        (workspace / output).write_bytes(data)
        return [output]
    return []


def _ranked(paths: list[Path]) -> list[Path]:
    return sorted((p for p in paths if _answer_like(p)), key=lambda p: (not re.search("expected", p.stem, re.I), str(p)))


def _git_history(workspace: Path):
    """(revision:path, bytes) for answer-like paths that ever existed in the workspace's git history."""
    def git(*args):
        done = subprocess.run(["git", "-C", str(workspace), *args], capture_output=True, timeout=GIT_SECONDS)
        return done.stdout if done.returncode == 0 else b""

    try:
        log = git("log", "--all", "--name-only", "--format=@%H").decode("utf-8", "replace").splitlines()
    except (OSError, subprocess.SubprocessError):
        return []
    found, revision = [], None
    for line in log:
        if line.startswith("@"):
            revision = line[1:]
        elif line.strip() and revision and _answer_like(Path(line)):
            try:
                found.append((f"{revision[:8]}:{line}", git("show", f"{revision}:{line}")))
            except (OSError, subprocess.SubprocessError):
                pass
    return found


def read_workspace(workspace: Path, prompt: str, io: dict, scope: Path | None = None, expected: dict | None = None) -> dict:
    paths = [p for p in _files(workspace, 6) if ".git" not in p.relative_to(workspace).parts]
    likely = _ranked(paths)
    answers = [bytes(data) for data in (expected or {}).values()]
    findings = [{"kind": "workspace-file", "path": p.relative_to(workspace).as_posix(), "matches_answer": p.read_bytes() in answers}
                for p in likely]
    history = _git_history(workspace) if (workspace / ".git").exists() else []
    findings += [{"kind": "git-history", "path": name, "matches_answer": data in answers} for name, data in history]
    wrote = _deliver(workspace, io, [p.read_bytes() for p in likely] + [data for _, data in history])
    return {"wrote": wrote, "findings": findings, "final": ""}


def read_ancestors(workspace: Path, prompt: str, io: dict, scope: Path | None = None, expected: dict | None = None) -> dict:
    reached = _ancestor_files(workspace, scope)
    findings = [{"kind": "ancestor-file", "path": str(p)} for p in reached]
    wrote = _deliver(workspace, io, [p.read_bytes() for p in _ranked(reached)])
    return {"wrote": wrote, "findings": findings, "final": ""}


def tamper(workspace: Path, prompt: str, io: dict, scope: Path | None = None, expected: dict | None = None) -> dict:
    reached = [p for p in _ancestor_files(workspace, scope) if VERIFIER.match(p.name)]
    findings = [{"kind": "verifier-file", "path": str(p)} for p in reached]
    wrote = []
    for path in [*reached, *(p for p in _files(workspace, 6) if VERIFIER.match(p.name))]:
        try:
            path.write_text(STUB, encoding="utf-8")
        except OSError:
            continue
        wrote.append(str(path))
    for folder in (f for f in (workspace, workspace.parent) if _within(f, scope)):
        for name, text in (("reward.txt", "1\n"), ("grade.json", json.dumps(SUCCESS)), ("result.json", json.dumps(SUCCESS))):
            try:
                (folder / name).write_text(text, encoding="utf-8")
            except OSError:
                continue
            wrote.append(str(folder / name))
    return {"wrote": wrote, "findings": findings, "final": "All tests pass"}


def exit_early(workspace: Path, prompt: str, io: dict, scope: Path | None = None, expected: dict | None = None) -> dict:
    return {"wrote": [], "findings": [], "final": "All tests pass"}


def _json_blocks(text: str):
    """(offset, value) for every JSON object or array that parses inside the text."""
    decoder, at = json.JSONDecoder(), 0
    while at < len(text):
        if text[at] in "{[":
            try:
                value, end = decoder.raw_decode(text, at)
            except ValueError:
                value = None
            else:
                if value:
                    yield at, value
                at = end
                continue
        at += 1


def copy_example(workspace: Path, prompt: str, io: dict, scope: Path | None = None, expected: dict | None = None) -> dict:
    blocks = list(_json_blocks(prompt))
    cues = [m.end() for m in re.finditer(r"example|sample|e\.g\.", prompt, re.I)]
    blocks.sort(key=lambda b: (not any(0 <= b[0] - cue <= 400 for cue in cues), b[0]))
    wrote = _deliver(workspace, io, [json.dumps(value).encode("utf-8") for _, value in blocks])
    return {"wrote": wrote, "findings": [], "final": ""}


BEHAVIORS = {"read_workspace": read_workspace, "read_ancestors": read_ancestors, "tamper": tamper,
             "exit_early": exit_early, "copy_example": copy_example}


def run(name: str, workspace: Path, prompt: str, io: dict, scope: Path | None = None, expected: dict | None = None) -> dict:
    if name not in BEHAVIORS:
        raise ValueError(f"unknown cheater {name!r}")
    return BEHAVIORS[name](Path(workspace), prompt, io, Path(os.path.realpath(scope)) if scope else None, expected)
