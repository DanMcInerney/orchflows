"""Each prompt line group, checked at the line it composes.

The composer's cases split where the composer did: the order
`launch_prompt` renders its groups in, and the host binding it is resolved
from, stay with `test_dispatch_launch.py`; what any one group puts on the
line -- the commit clause's two conditions, the first line's entry
mechanism, the `## Lens` entry the resolved kind picks -- is checked here.
Every case still fires through `launch_prompt`, because a group's line is
only worth its budget as the child reads it.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tests._candidate_checkout import (
    git_checkout, record_established_workspace,
)
from scripts import state_root
from scripts import tickets
from scripts import tickets_dispatch_launch as launch

from tests._repo_root import ROOT


class ReturnLineConditionalTest(unittest.TestCase):
    """U2a: the commit clause answers two questions, not one (finding F4).

    `commits_in_place` decides whether the clause renders at all -- true for
    every adapter whose identity is a commit or a document revision one
    records (git, document-tree), false only for
    evidence-store, which alone gets its own standard's `## Workspace` sentence
    instead. `git_candidate` decides whether the clause's branch-merge
    sentence renders -- true only where the adapter establishes isolation
    over git; a document-tree child commits, onto
    the coordinator's own branch, so it keeps the clause without that
    sentence. Never both facts contradicted, never the clause and the
    workspace line together.
    """

    def assignment(
        self, *, standard: str, artifact_kind, commits_in_place: bool,
        git_candidate: bool, workspace_line,
    ):
        return {
            "assigned_name": "child-1", "assignment_seal": "sha256:seal",
            "artifact_kind": artifact_kind, "commits_in_place": commits_in_place,
            "manifest": None,
            "dependencies": [], "dispatch_id": "D1", "executor": "orch-do",
            "executor_script": None, "git_candidate": git_candidate, "id": "T",
            "lease_expires_at": "2099-01-01T00:00:00Z", "standard": standard,
            "role": "worker", "run": "run", "ticket_path": "/sink/run/T.md",
            "workspace": "/tree", "workspace_line": workspace_line,
        }

    def test_a_research_standard_do_launch_carries_no_commit_clause(self):
        from scripts.tickets_assignment import _workspace_line, commits_in_place

        standard = ROOT / "standards" / "orch-research" / "STANDARD.md"
        research_line = _workspace_line(standard)
        self.assertIsNotNone(research_line)
        self.assertFalse(commits_in_place("orch-research"))

        prompt = launch.launch_prompt(self.assignment(
            standard="orch-research", artifact_kind="evidence",
            commits_in_place=False, git_candidate=False, workspace_line=research_line,
        ))

        self.assertNotIn("Commit your work inside this candidate", prompt)
        self.assertIn(research_line, prompt)

    def test_a_code_standard_do_launch_still_commits(self):
        from scripts.tickets_assignment import commits_in_place, git_candidate

        self.assertTrue(commits_in_place("orch-code"))
        self.assertTrue(git_candidate("orch-code"))

        prompt = launch.launch_prompt(self.assignment(
            standard="orch-code", artifact_kind="git",
            commits_in_place=True, git_candidate=True, workspace_line=None,
        ))

        self.assertIn(
            "Commit your work inside this candidate before you close", prompt,
        )
        self.assertIn(
            "the landing merges the candidate, not your working tree.", prompt,
        )
        self.assertIn("artifact: git:<full-commit-id>", prompt)

    def test_a_content_standard_do_launch_commits_without_a_merge_sentence(self):
        """The document-tree adapter commits in place but establishes no git
        candidate to merge: the launch keeps the commit clause and drops the
        sentence that would claim a candidate branch nothing isolated
        (finding F4 -- U2's original condition told this child its standard
        commits nothing, which is false: run 20260901T181410Z's B1.1
        committed 89b23e3d in exactly this shape under the old prompt)."""

        from scripts.tickets_assignment import commits_in_place, git_candidate

        self.assertTrue(commits_in_place("orch-content"))
        self.assertFalse(git_candidate("orch-content"))

        prompt = launch.launch_prompt(self.assignment(
            standard="orch-content", artifact_kind="doc",
            commits_in_place=True, git_candidate=False, workspace_line=None,
        ))

        self.assertIn(
            "Commit your work in the tree you are standing in before you close",
            prompt,
        )
        # the two sentences that would name a candidate nothing isolated;
        # never the whole prompt, whose script paths carry the checkout's
        # own directory name (a worktree called *-candidate-* made the
        # broad form red with the clause itself correct)
        self.assertNotIn("inside this candidate", prompt)
        self.assertNotIn("the landing merges the candidate", prompt)
        self.assertNotIn("Your stamped standard commits nothing", prompt)
        self.assertIn(
            "artifact: doc:<path>@sha256:<digest-of-the-document-bytes>", prompt,
        )


class IdentityLineTest(unittest.TestCase):
    """The first line names the entry mechanism, its argument, and the guard.

    "Apply skill X" named no mechanism; the 2026-09-01 census of 56 live
    dispatches found 33 children guessing the Skill tool, whose fork
    arrived with nothing and refused before a re-call with hand-typed
    arguments (6 of 24 paraphrased). The line now says which tool, that
    the argument is this whole prompt verbatim, and what a fork already
    running as the skill does with the same sentence.
    """

    def prompt(self, **overrides) -> str:
        facts = dict(ReturnLineConditionalTest().assignment(
            standard="orch-code", artifact_kind="git", commits_in_place=True,
            git_candidate=True, workspace_line=None,
        ))
        facts.update(overrides)
        return launch.launch_prompt(facts)

    def test_the_first_line_names_the_skill_tool_and_the_verbatim_argument(self):
        first = self.prompt(skill_path="/lib/orch-do/SKILL.md").split("\n")[0]
        self.assertIn("Call the Skill tool with skill `orch-do`", first)
        self.assertIn("this entire prompt, verbatim, as its arguments", first)
        self.assertIn("/lib/orch-do/SKILL.md", first)
        self.assertIn("/sink/run/T.md", first)
        self.assertIn("Read that ticket whole", first)

    def test_the_first_line_tells_a_fork_already_inside_to_work_in_place(self):
        """The fork reads this same prompt as its arguments; without the
        guard it would call the tool again and recurse."""

        first = self.prompt().split("\n")[0]
        self.assertIn("Already running as that skill, do the work here", first)
        self.assertIn("never invoke it again", first)

    def test_no_skill_path_drops_only_the_file_clause(self):
        first = self.prompt().split("\n")[0]
        self.assertNotIn("skill's file", first)
        self.assertIn("Your ticket is /sink/run/T.md", first)

    def test_the_old_apply_wording_is_gone(self):
        self.assertNotIn("Apply skill", self.prompt(skill_path="/x/SKILL.md"))


class LensKeyPromptTest(unittest.TestCase):
    """U5: the prompt names the artifact kind and the `## Lens` entry it picks.

    A standard's `## Lens` carries one entry per artifact kind its domain
    produces, so the path alone left the child to choose which entry was its
    own. Each case fires through the mint that resolves the kind -- the
    adapter's for a making `do`, `--makes` for a planning one, the typed
    Context identity for a judge -- because the sentence is only worth its
    line if the resolution behind it is right.
    """

    RUN = "lensrun"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(
            os.environ,
            {
                state_root.ENV_VAR: self.temporary.name,
                "ORCHFLOWS_WORKTREES_HOME": str(
                    Path(self.temporary.name) / "worktrees"
                ),
                launch.HOST_ENV_VAR: "",
            },
        )
        self.environment.start()
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate")
        self.goal_file = Path(self.temporary.name) / "goal.md"
        self.goal_file.write_text("Deliver the behavior.\n", encoding="utf-8")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def _establish(self, run, ticket_id, _workspace):
        """`workspace.py establish` for a Git candidate: the recorded tree
        plus the branch and baseline a launch refuses to proceed without."""

        path = Path(self.temporary.name) / "tickets" / run / f"{ticket_id}.md"
        record_established_workspace(path, self.candidate, strict=False)
        text = path.read_text(encoding="utf-8")
        for field, value in (
            ("workspace_branch", f"candidate/{ticket_id}"),
            ("workspace_baseline", "0" * 40),
        ):
            text = tickets._set_frontmatter_field(text, field, value)
        path.write_text(text, encoding="utf-8")
        return {"establish": {"workspace_path": str(self.candidate)}}

    def minted(self, verb, *extra):
        facade = tickets._tickets_dispatch_facade_module
        with mock.patch.object(
            facade, "_workspace_establish", side_effect=self._establish,
        ), mock.patch.object(
            facade, "_workspace_prepare", return_value={"outcome": "skipped"},
        ):
            return tickets._dispatch([
                verb, self.RUN, "--standard", "orch-code",
                "--goal-file", str(self.goal_file), "--isolation", "required",
                "--workspace", str(self.candidate), *extra,
            ])

    def prompt(self, answer: dict) -> str:
        self.assertNotIn("error", answer, answer)
        return answer[next(iter(answer))]["launch"]["prompt"]

    def test_a_making_do_is_sent_to_its_adapters_own_kind(self):
        prompt = self.prompt(self.minted("do"))

        self.assertIn("You make a `git`:", prompt)
        self.assertIn("`## Lens` entry `### git`", prompt)
        self.assertIn("is what your artifact must satisfy.", prompt)

    def test_a_planning_do_is_sent_to_the_kind_it_was_minted_to_make(self):
        """`--makes` is the one product no adapter names: the code standard's
        adapter would have answered `git` for this same ticket."""

        answer = self.minted("do", "--makes", "root")
        prompt = self.prompt(answer)

        data = tickets._parse_frontmatter(
            (Path(self.temporary.name) / "tickets" / self.RUN
             / f"{answer['do']['id']}.md").read_text(encoding="utf-8")
        )
        self.assertEqual("root", data["makes"])
        self.assertIn("You make a `root`:", prompt)
        self.assertIn("`## Lens` entry `### root`", prompt)
        self.assertNotIn("### git", prompt)

    def test_a_judge_is_sent_to_the_kind_on_its_artifact_line(self):
        """The judge's kind is the artifact's, never the stamped standard's: this
        one is stamped for code and handed an evidence identity."""

        prompt = self.prompt(self.minted(
            "judge", "--artifacts", "evidence:store-1",
        ))

        self.assertIn("You judge `evidence` artifacts:", prompt)
        self.assertIn("`## Lens` entry `### evidence`", prompt)
        self.assertIn("is your criteria.", prompt)
        self.assertNotIn("### git", prompt)

    def test_a_judge_over_two_kinds_is_refused_at_the_mint(self):
        """No one entry is its criteria, so there is no launch to compose."""

        refusal = self.minted(
            "judge", "--artifacts", "git:0123456789abcdef",
            "--artifacts", "evidence:store-1",
        )

        self.assertIn("error", refusal)
        for kind in ("'evidence'", "'git'"):
            self.assertIn(kind, refusal["error"])
        self.assertEqual(
            [], list((Path(self.temporary.name) / "tickets").glob("*/*.md")),
        )

    def test_no_manifest_carries_no_lens_sentence(self):
        """The sentence answers to the standard it points into: an assignment
        that resolved no standard file has no entry to send anyone to."""

        facts = dict(ReturnLineConditionalTest().assignment(
            standard="orch-code", artifact_kind="git", commits_in_place=True,
            git_candidate=True, workspace_line=None,
        ))
        facts["lens_key"] = "git"

        self.assertIsNone(facts["manifest"])
        self.assertNotIn("## Lens", launch.launch_prompt(facts))


if __name__ == "__main__":
    unittest.main()
