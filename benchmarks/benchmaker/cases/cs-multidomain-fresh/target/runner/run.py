#!/usr/bin/env python3
"""changelog benchmark runner. Executable interface of this package.

    python run.py IMPL

IMPL is a directory holding the tool file named by the runnable case
set, or a direct path to it. Emits one JSON result object on stdout;
exit 0 when the aggregate verdict is pass, 1 when it is fail, 2 on
usage errors. Python 3.9 stdlib only; each case executes in a scratch
directory; nothing inside the package tree is written.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

FORBIDDEN = re.compile(r"\b(we|our|awesome)\b", re.IGNORECASE)
ALLOWED_SECTIONS = ["Features", "Fixes", "Documentation"]


def package_root(start):
    probe = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(probe, "manifest.json")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            raise SystemExit("run.py: no manifest.json above %s" % start)
        probe = parent


def load_component(root, manifest, name):
    locator = manifest[name]["locator"]
    with open(os.path.join(root, locator.replace("/", os.sep)), "r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_impl(raw, tool):
    path = os.path.abspath(raw)
    if os.path.isdir(path):
        path = os.path.join(path, tool)
    if not os.path.isfile(path):
        raise SystemExit("run.py: no such implementation: %s" % raw)
    return path


def execute(case, impl):
    scratch = tempfile.mkdtemp(prefix="changelog-case-")
    try:
        commits = os.path.join(scratch, "commits.txt")
        with open(commits, "wb") as handle:
            handle.write(case["input"].encode("utf-8"))
        done = subprocess.run(
            [sys.executable, impl, commits],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=scratch,
            timeout=30,
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    text = done.stdout.replace(b"\r\n", b"\n").decode("utf-8", "replace")
    return done.returncode, text


def check_code(case, code, text):
    problems = []
    if code != case["exit"]:
        problems.append("exit %d, want %d" % (code, case["exit"]))
    if case["exit"] != 0 and text != "":
        problems.append("stdout must be empty on a non-zero exit")
    entries = [line[2:] for line in text.split("\n") if line.startswith("- ")]
    if case["exit"] == 0 and entries != case["entries"]:
        problems.append("entry sequence %r, want %r" % (entries, case["entries"]))
    return problems


def check_doc(case, code, text):
    problems = []
    if code != case["exit"]:
        problems.append("exit %d, want %d" % (code, case["exit"]))
        return problems
    if not text.endswith("\n") or text.endswith("\n\n"):
        problems.append("document must end with a single trailing newline")
    lines = text.split("\n")[:-1] if text.endswith("\n") else text.split("\n")
    if not lines or lines[0] != "# Changelog":
        problems.append("first line must be exactly '# Changelog'")
    headings = []
    for index, line in enumerate(lines):
        if index == 0:
            continue
        if line.startswith("#"):
            if not line.startswith("## ") or line[3:] not in ALLOWED_SECTIONS:
                problems.append("unlawful heading %r" % line)
                continue
            headings.append(line[3:])
            if index == 0 or lines[index - 1] != "":
                problems.append("heading %r not preceded by a blank line" % line)
        elif line.startswith("- "):
            entry = line[2:]
            if entry and entry[0].isalpha() and not entry[0].isupper():
                problems.append("entry %r is not capitalized" % line)
        elif line != "":
            problems.append("generator prose is forbidden: %r" % line)
    if headings != case["expected_sections"]:
        problems.append("sections %r, want %r" % (headings, case["expected_sections"]))
    if FORBIDDEN.search(text):
        problems.append("forbidden voice word present")
    return problems


def run_case(case, impl):
    code, text = execute(case, impl)
    if case["domain"] == "code":
        problems = check_code(case, code, text)
    else:
        problems = check_doc(case, code, text)
    return {
        "id": case["id"],
        "domain": case["domain"],
        "pass": not problems,
        "detail": "; ".join(problems) or "ok",
    }


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: run.py IMPL\n")
        return 2
    root = package_root(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "manifest.json"), "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    case_set = load_component(root, manifest, "runnable_cases")
    scoring = load_component(root, manifest, "scoring")
    impl = resolve_impl(sys.argv[1], case_set["tool"])
    results = [run_case(case, impl) for case in case_set["cases"]]
    required = set(scoring["required_case_ids"])
    overall = all(r["pass"] for r in results if r["id"] in required)
    report = {"impl": impl, "cases": results, "pass": overall}
    sys.stdout.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
