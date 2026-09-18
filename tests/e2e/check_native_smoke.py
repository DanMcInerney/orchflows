"""Check these three fixtures' outputs and native records, not arbitrary workflows.

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
    expected_names = {"orchflows:" + s for s in ("orch-work", "orch-review", "orch-build-workflow", "orch-review-revise-once")}
    require({s for s in init["slash_commands"] if s.startswith("orchflows:")} == expected_names,
            "Native core inventory differs from the current four entrypoints")
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
    elif case.name == "routing":
        require((workspace / "answer.txt").read_text().strip() == "42", "Wrong ordinary-task result")
        require(not delegations and not children, "Unselected Orchflows lifecycle added an agent")
        require(not any(c["name"] == "Skill" for _, c in calls), "Unmatched request invoked a skill")
    else:
        raise ValueError(f"Unknown fixture: {case.name}")
    if case.name != "routing":
        for filename in ("review.md", "handoff.md"):
            require((workspace / filename).read_text(encoding="utf-8").strip(), f"Missing {filename}")
    return {"case": case.name, "mechanical_checks": "passed", "seconds": result["seconds"],
            "session_id": init["session_id"], "manual_audit": "Required: assignments, review/gap semantics and tool effects"}


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
