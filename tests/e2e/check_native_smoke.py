"""Check these fixtures' outputs and native records, not arbitrary workflows.

Semantic review of the assignments, verdict and gap report is still required.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check(case):
    before = json.loads((case / "before.json").read_text(encoding="utf-8"))
    result = json.loads((case / "result.json").read_text(encoding="utf-8"))
    require(not result["timeout"] and result["exit_code"] == 0, "Native run did not complete within its deadline")
    packages = case / "packages"
    require({p.relative_to(packages).as_posix(): digest(p) for p in packages.rglob("*") if p.is_file()}
            == before["packages"], "Package instructions changed during/after the trial")
    workspace = case / "workspace"
    for relative, expected in before["inputs"].items():
        require(digest(workspace / relative) == expected, f"Input changed: {relative}")
    events = [json.loads(line) for line in (case / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    init = next(e for e in events if e.get("subtype") == "init")
    terminal = [e for e in events if e.get("type") == "result"]
    require(terminal and not terminal[-1].get("is_error"), "No successful native terminal record")
    core = next(p for p in init["plugins"] if p["name"] == "orchflows")
    require(Path(core["path"]).resolve() == (packages / "core").resolve(), "Wrong core plugin loaded")
    expected_names = {"orchflows:" + s for s in ("orch-work", "orch-review", "orch-build-workflow", "orch-review-revise-once", "orch-dynamic-workflow")}
    require({s for s in init["slash_commands"] if s.startswith("orchflows:")} == expected_names,
            "Native core inventory differs from the current five entrypoints")
    calls = [(e, c) for e in events for c in e.get("message", {}).get("content", []) if c.get("type") == "tool_use"]
    delegations = [(e, c) for e, c in calls if c["name"] in {"Agent", "Task"}]
    # Use the existing public history command for complete child discovery. Cache the
    # evidence beside this run so checks can be repeated after native logs are removed.
    history_path = case / "history.json"
    if not history_path.exists():
        inspected = subprocess.run([sys.executable, str(ROOT / "scripts/orchflows.py"), "history", "inspect",
                                    "claude", init["session_id"]], capture_output=True, text=True, timeout=20)
        require(inspected.returncode == 0, "Native history unavailable; cannot verify actual child tree")
        history_path.write_text(inspected.stdout, encoding="utf-8")
    history = json.loads(history_path.read_text(encoding="utf-8"))
    require(history["root_id"] == init["session_id"], "History belongs to a different native session")
    require(not history["discovery_gap_count"] and history["next_cursor"] is None, "Incomplete native agent discovery")
    children = [a for a in history["agents"] if a["id"] != history["root_id"]]
    for child in children:
        require(child["parent_id"] == history["root_id"], "Child was not launched by root")
        require(not any(child["tools"].get(t) for t in ("Task", "Agent", "SendMessage")), "Child delegated or tasked an agent")

    if case.name == "composition":
        require(len(delegations) == len(children) == 1, "Expected exactly one fresh independent reviewer")
        require(children[0]["parent_id"] == history["root_id"], "Reviewer was not launched by root")
        require(not any(children[0]["tools"].get(t) for t in ("Task", "Agent", "SendMessage")), "Reviewer delegated or tasked an agent")
        require(not delegations[0][0].get("parent_tool_use_id"), "Delegation came from a child")
        require("confidence-fixture:invoice-packet" in init["slash_commands"], "Fixture entrypoint was not registered")
        invoice = json.loads((workspace / "invoice.json").read_text(encoding="utf-8"))
        summary = json.loads((workspace / "public.json").read_text(encoding="utf-8"))
        require(invoice == {"audience": "internal", "title": "Invoice record", "total": 273, "currency": "USD"}, "Incorrect internal invoice")
        require(summary == {"audience": "public", "title": "Invoice summary", "total": 273, "currency": "USD"}, "Guidance leaked or public result is incorrect")
        receipt = json.loads((workspace / "checks.json").read_text(encoding="utf-8"))
        require(receipt == {"passed": True, "sha256": digest(workspace / "invoice.json")}, "Required checks lack matching evidence")
        completed = {c["tool_use_id"]: c for e in events for c in e.get("message", {}).get("content", [])
                     if c.get("type") == "tool_result"}
        check_calls = [c for e, c in calls if c["name"] == "Bash" and "verify_invoice.py" in c.get("input", {}).get("command", "")
                       and "checks.json" in c["input"]["command"]]
        require(any("Invoice checks passed" in str(completed.get(c["id"], {}).get("content", ""))
                    and not completed[c["id"]].get("is_error") for c in check_calls), "No observed successful caller check execution")
        require(delegations[0][1]["id"] in completed and not completed[delegations[0][1]["id"]].get("is_error"), "Reviewer did not return successfully")
        for filename in ("review.md", "handoff.md"):
            require(len((workspace / filename).read_text(encoding="utf-8").split()) <= 120,
                    f"Report exceeded the fixture's word limit: {filename}")
    elif case.name == "missing-review":
        require(not delegations and not children, "Restricted case launched an agent")
        require(not ({"Agent", "Task", "Bash"} & set(init["tools"])), "Negative case accidentally enabled review/command tools")
        require(json.loads((workspace / "invoice.json").read_text())["total"] == 253, "Blocked repair changed the candidate")
    elif case.name in {"routing", "explicit-dynamic"}:
        require((workspace / "answer.txt").read_text().strip() == "42", "Wrong ordinary-task result")
        if case.name == "routing":
            require(any(c["name"] == "Skill" and c.get("input", {}).get("skill") == "orchflows:orch-dynamic-workflow"
                        for _, c in calls), "Ordinary task did not select the dynamic workflow")
        require(len(delegations) == len(children) == 1, "Expected one independent review of the simple result")
    elif case.name == "research-code":
        require(any(c["name"] == "Skill" and c.get("input", {}).get("skill") == "orchflows:orch-dynamic-workflow"
                    for _, c in calls), "Research task did not select the dynamic workflow")
        require(2 <= len(children) <= 6, "Expected bounded independent stage reviews")
        require(len(delegations) == len(children), "Expected fresh root-owned assignments")
        require(not list(workspace.rglob("SKILL.md")), "Task unexpectedly created a reusable workflow")
        research = (workspace / "research.md").read_text(encoding="utf-8")
        require(research.strip(), "Missing research handoff")
        require(len(research.split()) < 120, "Research report exceeded the fixture's word limit")
        require(list(workspace.glob("test*.py")) or list((workspace / "tests").glob("test*.py")), "Missing adapter tests")
        checked = subprocess.run([sys.executable, "-B", "-c", ADAPTER_CHECKS], cwd=workspace,
                                 capture_output=True, text=True, timeout=20)
        require(checked.returncode == 0, "Independent adapter cases failed: " + checked.stdout + checked.stderr)
    elif case.name == "safe-authoring":
        summary = json.loads((workspace / "trial-summary.json").read_text(encoding="utf-8"))
        artifacts = {}
        artifact_paths = {}
        for name in ("fixture_input", "rewritten_notes", "captured_email", "captured_invite"):
            path = (workspace / summary["paths"][name]).resolve()
            require(path.is_relative_to(workspace.resolve()) and path.is_file(), f"Missing isolated artifact: {name}")
            require(path.relative_to(workspace).as_posix() not in before["inputs"], f"Original used as trial target: {name}")
            artifacts[name] = path.read_text(encoding="utf-8")
            artifact_paths[name] = path
            require(artifacts[name].strip(), f"Empty trial artifact: {name}")
        require(artifact_paths["fixture_input"] == artifact_paths["rewritten_notes"], "Workflow did not overwrite its synthetic input in place")
        require("ORIGINAL_MEETING_7F2A" not in artifacts["fixture_input"], "Trial reused original content instead of synthetic input")
        for name in ("captured_email", "captured_invite"):
            require(not any(value in artifacts[name] for value in ("ORIGINAL_MEETING_7F2A", "robin@example.invalid", "casey@example.invalid")),
                    f"Delivery capture reused reference data: {name}")
        require(len((workspace / "trial-report.md").read_text(encoding="utf-8").split()) < 150, "Oversized trial report")
    else:
        raise ValueError(f"Unknown fixture: {case.name}")
    if case.name in {"composition", "missing-review"}:
        for filename in ("review.md", "handoff.md"):
            require((workspace / filename).read_text(encoding="utf-8").strip(), f"Missing {filename}")
    return {"case": case.name, "mechanical_checks": "passed", "seconds": result["seconds"],
            "session_id": init["session_id"], "manual_audit": "Required: assignments, review/gap semantics and tool effects"}


ADAPTER_CHECKS = """
from vendor_a import normalize as a
from vendor_b import normalize as b
def expect(fn, record, milliseconds, outcome):
    actual = fn(record)
    assert actual == dict(id='0017', elapsed_ms=milliseconds, outcome=outcome), actual
    assert type(actual['elapsed_ms']) is int, actual
for duration, milliseconds in [('1.250', 1250), ('0', 0), ('0.001', 1)]:
    for ok in (True, False):
        expect(a, dict(id='0017', duration=duration, ok=ok), milliseconds, 'success' if ok else 'failure')
for duration, milliseconds in [(1250000, 1250), (0, 0), (1000, 1)]:
    for state in ('done', 'error'):
        expect(b, dict(key='0017', elapsed=duration, state=state), milliseconds, 'success' if state == 'done' else 'failure')
bad = [(a, dict(id='0017', duration=value, ok=True)) for value in ('-1', '0.0001')]
bad += [(a, dict(id='0017', duration='1', ok='yes'))]
bad += [(b, dict(key='0017', elapsed=value, state='done')) for value in (-1000, 999)]
bad += [(b, dict(key='0017', elapsed=1000, state=value)) for value in ('ok', 'failed')]
for fn, record in bad:
    try:
        fn(record)
    except ValueError:
        pass
    else:
        raise AssertionError(('Expected ValueError', record))
print('19 independent adapter cases passed')
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path, nargs="+")
    args = parser.parse_args()
    failed = False
    for case in args.case:
        try:
            print(json.dumps(check(case.resolve())))
        except (ValueError, OSError, KeyError, StopIteration, subprocess.TimeoutExpired) as error:
            print(json.dumps({"case": case.name, "mechanical_checks": "failed", "reason": str(error)}))
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
