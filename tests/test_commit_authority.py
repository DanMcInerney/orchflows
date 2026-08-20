"""Specification 01: ticket-owned slice commits and join-owned integration."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import tickets_admission as admission  # noqa: E402
from scripts import tickets_format as ticket_format  # noqa: E402
from scripts import tickets_packet as packet  # noqa: E402
from scripts import tickets as ticket_facade  # noqa: E402,F401  binds pack registries

FIXTURE = ROOT / "tests" / "fixtures" / "final_specs" / "01" / "authorities.json"
TDD_SKILL = ROOT / "skills" / "instances" / "orch-tdd" / "SKILL.md"
FOUNDATION_BASELINE = "ee538224ded702db0ea9ca6ccf09972edca6d665"
GIT_ENV = dict(
    os.environ,
    GIT_AUTHOR_NAME="authority-fixture",
    GIT_AUTHOR_EMAIL="authority@example.invalid",
    GIT_COMMITTER_NAME="authority-fixture",
    GIT_COMMITTER_EMAIL="authority@example.invalid",
    GIT_CONFIG_NOSYSTEM="1",
)


def authority_fixtures():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def ticket_text(authority, *, ticket_id="T1", status="pending", receipt="v1:pending"):
    scope = "\n".join(f"  - {value}" for value in authority["write_scope"])
    excluded = "\n".join(f"  - {value}" for value in authority["excluded_actions"])
    mutation = f"create:{authority['write_scope'][0]}"
    return f"""---
id: {ticket_id}
run: authority-fixture
status: {status}
admission: {receipt}
cohort: v1:ticket:{ticket_id}
executor: {authority['executor']}
pack: {authority['pack']}
independence: gate
depends_on: []
write_scope:
{scope}
mutations: [{mutation}]
excluded_actions:
{excluded}
isolation: {authority['isolation']}
bound: 10m
---

## Objective

Write one green fixture slice.

## Fixed inputs

- input: {{"identity":{{"kind":"git-tree","repo":"run-project","revision":"{FOUNDATION_BASELINE}"}},"name":"baseline","type":"identity"}}
- input: {{"name":"expected","type":"literal","value":"green"}}

## Completion test

- fixture reads green | oracle: `python verify.py` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result; changed_artifacts; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


def finding_codes(text):
    return {
        item["code"]
        for item in admission.grade_admission("T1", text, {"T1": text})["findings"]
    }


def git(cwd, *args, check=True):
    completed = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", *args],
        cwd=str(cwd), env=GIT_ENV, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and completed.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {completed.stderr}")
    return completed


def python(cwd, *args):
    return subprocess.run(
        [sys.executable, *args], cwd=str(cwd), env=GIT_ENV,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def make_repo(root):
    main = root / "main"
    main.mkdir()
    git(main, "init", "--quiet")
    (main / "README.md").write_text("baseline\n", encoding="utf-8")
    (main / "verify.py").write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "target = Path(sys.argv[1])\n"
        "raise SystemExit(0 if target.is_file() and target.read_text() == 'green\\n' else 1)\n",
        encoding="utf-8",
    )
    git(main, "add", "README.md", "verify.py")
    git(main, "commit", "--quiet", "-m", "fixture baseline")
    return main


def replay_verified_slice(main, authority, ordinal):
    baseline = git(main, "rev-parse", "HEAD").stdout.strip()
    branch = f"ticket-{ordinal}"
    worktree = main.parent / branch
    git(main, "worktree", "add", "--quiet", "-b", branch, str(worktree))
    target = authority["write_scope"][0]
    red = python(worktree, "verify.py", target)
    if red.returncode == 0:
        raise AssertionError("fixture RED unexpectedly passed")
    path = worktree / target
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("green\n", encoding="utf-8")
    green = python(worktree, "verify.py", target)
    if green.returncode:
        raise AssertionError(f"fixture GREEN failed: {green.stderr}")
    git(worktree, "add", target)
    git(worktree, "commit", "--quiet", "-m", f"verified slice {ordinal}")
    tip = git(worktree, "rev-parse", "HEAD").stdout.strip()
    result = {"branch_tip": tip, "slice_commit": tip}
    if git(worktree, "status", "--porcelain").stdout:
        raise AssertionError("ticket workspace is not clean after its slice commit")
    if git(main, "rev-parse", "HEAD").stdout.strip() != baseline:
        raise AssertionError("ticket executor moved the integrating branch")
    changed = git(main, "diff", "--name-only", f"{baseline}..{tip}").stdout.splitlines()
    if changed != [target]:
        raise AssertionError(f"join saw out-of-scope baseline-to-tip paths: {changed}")
    git(main, "merge", "--quiet", "--ff-only", branch)
    if git(main, "rev-parse", "HEAD").stdout.strip() != tip:
        raise AssertionError("join did not integrate the ticket branch tip")
    return result


@unittest.skipUnless(git(Path.cwd(), "--version", check=False).returncode == 0, "git required")
class CommitAuthorityReplayTest(unittest.TestCase):
    def test_three_historical_integration_only_authorities_commit_and_join(self):
        fixtures = authority_fixtures()
        self.assertEqual(4, len(fixtures))
        with tempfile.TemporaryDirectory(prefix="commit-authority-") as raw:
            root = Path(raw)
            main = make_repo(root)
            try:
                for ordinal, authority in enumerate(fixtures[:3], start=1):
                    with self.subTest(source=authority["source"]):
                        self.assertIsNone(authority["source_isolation"])
                        self.assertEqual("required", authority["isolation"])
                        text = ticket_text(authority)
                        self.assertEqual(set(), finding_codes(text))
                        result = replay_verified_slice(main, authority, ordinal)
                        self.assertEqual(result["slice_commit"], result["branch_tip"])
                        self.assertRegex(result["branch_tip"], r"^[0-9a-f]{40,64}$")
            finally:
                for ordinal in range(1, 4):
                    tree = root / f"ticket-{ordinal}"
                    if tree.exists():
                        git(main, "worktree", "remove", "--force", str(tree), check=False)

    def test_failing_slice_produces_no_commit(self):
        with tempfile.TemporaryDirectory(prefix="commit-authority-red-") as raw:
            root = Path(raw)
            main = make_repo(root)
            baseline = git(main, "rev-parse", "HEAD").stdout.strip()
            tree = root / "failing-ticket"
            git(main, "worktree", "add", "--quiet", "-b", "failing-ticket", str(tree))
            try:
                target = "scratch/failing.txt"
                path = tree / target
                path.parent.mkdir(parents=True)
                path.write_text("red\n", encoding="utf-8")
                self.assertNotEqual(0, python(tree, "verify.py", target).returncode)
                self.assertEqual(baseline, git(tree, "rev-parse", "HEAD").stdout.strip())
                self.assertEqual("1", git(tree, "rev-list", "--count", "HEAD").stdout.strip())
                status = git(
                    tree, "status", "--porcelain", "--untracked-files=all",
                ).stdout
                self.assertIn("scratch/failing.txt", status)
            finally:
                git(main, "worktree", "remove", "--force", str(tree), check=False)


class AdmissionAuthorityTest(unittest.TestCase):
    def base(self):
        return dict(authority_fixtures()[0])

    def test_foundation_baseline_is_reachable_from_the_repository_head(self):
        reachable = git(
            ROOT,
            "merge-base",
            "--is-ancestor",
            FOUNDATION_BASELINE,
            "HEAD",
            check=False,
        )
        self.assertEqual(0, reachable.returncode, reachable.stderr)

    def test_closed_admission_matrix(self):
        valid = self.base()
        self.assertEqual(set(), finding_codes(ticket_text(valid)))
        cases = []
        wrong_binding = dict(valid, executor="orch-draft")
        cases.append(("executor-pack-mismatch", wrong_binding))
        wrong_adapter = dict(valid, pack="orch-content-pack")
        cases.append(("vcs-adapter-required", wrong_adapter))
        cases.append(("vcs-isolation-required", dict(valid, isolation="none")))
        for token in ("vcs.isolate", "vcs.commit"):
            cases.append(("vcs-action-excluded", dict(valid, excluded_actions=[token])))
        cases.append(("vcs-action-excluded", dict(
            valid, excluded_actions=["vcs.isolate", "vcs.commit"],
        )))
        for code, authority in cases:
            with self.subTest(code=code, authority=authority):
                self.assertIn(code, finding_codes(ticket_text(authority)))
        allowed = dict(
            valid, excluded_actions=["vcs.integrate", "vcs.push", "vcs.open-pr"],
        )
        self.assertEqual(set(), finding_codes(ticket_text(allowed)))

    def test_lexical_vcs_prose_is_refused_but_non_vcs_prose_remains_valid(self):
        valid = self.base()
        for prose in (
            "do not use Git here", "caller owns this branch", "never commit",
            "join must merge", "do not push", "no pull-request", "version-control is reserved",
        ):
            with self.subTest(prose=prose):
                authority = dict(valid, excluded_actions=[prose])
                self.assertIn("vcs-exclusion-not-tokenized", finding_codes(ticket_text(authority)))
        non_vcs = dict(valid, excluded_actions=["do not edit generated documentation"])
        self.assertEqual(set(), finding_codes(ticket_text(non_vcs)))

    def test_u1_explicit_local_vcs_exclusions_are_refused(self):
        u1 = authority_fixtures()[3]
        self.assertEqual("orchflows-ui-2026-08-10/U1", u1["source"])
        self.assertEqual(
            {"vcs.isolate", "vcs.commit", "vcs.open-pr"}, set(u1["excluded_actions"]),
        )
        self.assertIn("vcs-action-excluded", finding_codes(ticket_text(u1)))

    def test_packet_uses_stored_authority_without_synthesizing_a_mode(self):
        authority = self.base()
        pending = ticket_text(authority)
        receipt = admission.grade_admission("T1", pending, {"T1": pending})["receipt"]
        claimed = ticket_text(authority, status="claimed", receipt=receipt)
        with tempfile.TemporaryDirectory(prefix="authority-packet-") as raw:
            tickets_root = Path(raw)
            run = tickets_root / "authority-fixture"
            run.mkdir()
            path = run / "T1.md"
            path.write_text(claimed, encoding="utf-8")
            before = path.read_bytes()
            with patch.object(packet, "_tickets_root", return_value=tickets_root):
                payload = packet._packet_under_run_lock([
                    "authority-fixture", "T1", "--reply-to", "join",
                ])
            self.assertNotIn("error", payload)
            self.assertEqual(before, path.read_bytes())
            prompt = payload["packet"]["prompt"]
            self.assertNotIn("commit_authority", prompt)
            self.assertNotIn("leave an anonymous", prompt.casefold())
            stored = ticket_format._parse_frontmatter(path.read_text(encoding="utf-8"))
            self.assertEqual(authority["excluded_actions"], stored["excluded_actions"])


class SkillBoundaryTest(unittest.TestCase):
    def test_skill_names_ticket_local_commit_and_join_boundary(self):
        text = TDD_SKILL.read_text(encoding="utf-8")
        for phrase in (
            "Commit each verified slice",
            "inside the ticket workspace",
            "perform integration",
            "publish with push",
            "checked out at the run branch",
            "the join alone applies them",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("commit_authority", text)


if __name__ == "__main__":
    unittest.main()
