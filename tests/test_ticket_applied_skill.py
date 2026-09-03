"""An applied skill is a method; the kernel verb stays the contract.

U2. `--skill` hands a child somebody else's skill to work *through*, which
raises two questions U0's pin does not answer. Which skill may be applied --
never a kernel verb, and never one declaring the other role, because the
launch binding (agent, model, effort) is chosen off the verb's role and a
planner-role method entered by a worker agent is a child running a prompt
written for someone else. And what the child is still bound by once its
first line names a skill that is not `orch-do`: the verb's Require, Never
and Return, which the prompt now names at the flat `by-name/` path every
host resolves, plus the private interpreter that skill's own scripts run
through when it declares one.

Every prompt case fires through the mint, because the fact under test is
one the assignment reading resolves and the composer only renders.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest import mock

from scripts import rings, tickets_assignment

from tests.test_ticket_callables import CODE_PACK, CallableSinkTest
from tests.test_ticket_pins import _skill

WORKER_SKILL = "house-style"
PLANNER_SKILL = "house-review"
ROLELESS_SKILL = "house-notes"
# The one thing two prompts minted seconds apart differ by on their own: the
# absolute lease. Normalized away rather than tolerated as a diff, so the
# comparison below still fails on any other difference.
STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def library_workflow() -> str:
    """One shipped reusable workflow's name, read from the home the
    resolver owns rather than spelled here: the case is about the kind,
    not about which workflow happens to ship today."""

    home = rings.lib_root() / "skills" / "workflows"
    for path in sorted(home.iterdir()):
        if (path / rings.MANIFESTS["workflow"]).is_file():
            return path.name
    raise AssertionError(f"{home} ships no reusable workflow to apply")


class AppliedSkillTest(CallableSinkTest):
    """A home ring holding one skill per role, and one declaring none."""

    def setUp(self):
        super().setUp()
        self.ring = Path(self.temporary.name) / "ring"
        _skill(self.ring, WORKER_SKILL, "The method.")
        _skill(self.ring, PLANNER_SKILL, "The reading.", role="planner")
        path = self.ring / "skills" / ROLELESS_SKILL / rings.MANIFESTS["skill"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            f"---\nname: {ROLELESS_SKILL}\n---\n\nNotes.\n".encode("utf-8")
        )
        self.home = mock.patch.object(rings, "home_ring", return_value=self.ring)
        self.home.start()
        self.addCleanup(self.home.stop)

    def do(self, *arguments, **keywords):
        return self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            *arguments, **keywords,
        )

    def judge(self, *arguments, **keywords):
        return self.callable(
            "judge", "--pack", CODE_PACK, "--isolation", "none",
            "--artifacts", "git:" + "a" * 40, *arguments, **keywords,
        )

    def requirements(self, name: str) -> Path:
        path = self.ring / "skills" / name / "requirements.txt"
        path.write_text("httpx==0.27.0\n", encoding="utf-8")
        return path


class AppliedSkillRefusalTest(AppliedSkillTest):
    """Which skills may be applied, refused at the flag before anything mints."""

    def test_a_kernel_verb_is_refused_as_an_applied_skill(self):
        """The ring floor does not reach a library name, so this door does.

        `orch-do` resolves from the lib ring, where the reserved prefix is
        lawful, so a mint that only asked the resolver would have accepted
        the verb as its own method.
        """

        answer = self.do("--skill", "orch-do", expect_error=True)

        self.assertIn("orch-do", answer["error"])
        self.assertIn("reserved", answer["error"])
        self.assertFalse(self.run_dir().exists())

    def test_a_planner_skill_is_refused_on_do(self):
        answer = self.do("--skill", PLANNER_SKILL, expect_error=True)

        self.assertIn(PLANNER_SKILL, answer["error"])
        self.assertIn("planner", answer["error"])
        self.assertIn("worker", answer["error"])
        self.assertFalse(self.run_dir().exists())

    def test_a_worker_skill_is_refused_on_judge(self):
        answer = self.judge("--skill", WORKER_SKILL, expect_error=True)

        self.assertIn(WORKER_SKILL, answer["error"])
        self.assertIn("planner", answer["error"])

    def test_a_skill_declaring_no_role_is_refused_rather_than_assumed(self):
        """Silence is not a claim to be either role, and a wrong guess here
        launches the child under the other role's agent and model."""

        answer = self.do("--skill", ROLELESS_SKILL, expect_error=True)

        self.assertIn(ROLELESS_SKILL, answer["error"])
        self.assertIn("none", answer["error"])

    def test_a_matching_role_mints_on_each_verb(self):
        self.assertNotIn("error", self.do("--skill", WORKER_SKILL))
        self.assertNotIn("error", self.judge("--skill", PLANNER_SKILL))

    def test_a_library_workflow_is_refused_as_the_workflow_it_is(self):
        """`skills/workflows` sits inside the skills tier, so a body there
        used to answer to kind `skill` too and arrive at the role door --
        which reads a workflow's deliberate silence as a missing field.
        The kind is the refusal: a workflow is prose the driver runs in its
        own context, never a method a child is handed."""

        name = library_workflow()

        answer = self.do("--skill", name, expect_error=True)

        self.assertIn(name, answer["error"])
        self.assertIn("workflow", answer["error"])
        self.assertNotIn("declares role", answer["error"])
        self.assertFalse(self.run_dir().exists())

    def test_an_unresolvable_skill_is_refused_by_name(self):
        answer = self.do("--skill", "no-such-skill", expect_error=True)

        self.assertIn("no-such-skill", answer["error"])
        self.assertFalse(self.run_dir().exists())


class AppliedSkillPromptTest(AppliedSkillTest):
    """What the child reads: the method on line one, the contract under it."""

    def test_the_identity_line_enters_the_applied_skill_and_its_file(self):
        first = self.prompt(self.do("--skill", WORKER_SKILL)).split("\n")[0]

        self.assertIn(f"Call the Skill tool with skill `{WORKER_SKILL}`", first)
        self.assertIn("this entire prompt, verbatim, as its arguments", first)
        self.assertIn(
            str(self.ring / "skills" / WORKER_SKILL / rings.MANIFESTS["skill"]),
            first,
        )
        self.assertNotIn("orch-do", first)

    def test_the_second_line_binds_the_ticket_to_the_kernel_contract(self):
        second = self.prompt(self.do("--skill", WORKER_SKILL)).split("\n")[1]

        self.assertEqual(
            "Your kernel contract is `orch-do` at "
            f"{tickets_assignment._kernel_contract('orch-do')}: read it; its "
            "Require, Never and Return bind this ticket; the applied skill "
            "is the method.",
            second,
        )

    def test_the_judge_verb_names_its_own_contract(self):
        second = self.prompt(self.judge("--skill", PLANNER_SKILL)).split("\n")[1]

        self.assertIn("Your kernel contract is `orch-judge` at", second)

    def test_the_contract_path_is_the_installers_flat_by_name_file(self):
        """The one spelling of a canonical name that holds on every host.

        The checkout has no `by-name/` -- the installer mints it -- so the
        preference is proved against a library root that does.
        """

        minted = Path(self.temporary.name) / "lib"
        contract = minted / "by-name" / "orch-do" / rings.MANIFESTS["skill"]
        contract.parent.mkdir(parents=True, exist_ok=True)
        contract.write_text("Read the kernel verb.\n", encoding="utf-8")

        with mock.patch.object(rings, "lib_root", return_value=minted):
            self.assertEqual(
                str(contract), tickets_assignment._kernel_contract("orch-do"),
            )

    def test_a_checkout_without_by_name_falls_back_to_the_resolved_skill(self):
        resolved = tickets_assignment._kernel_contract("orch-do")

        self.assertTrue(Path(resolved).is_file(), resolved)
        self.assertNotIn("by-name", resolved)

    def test_a_declared_environment_adds_the_interpreter_line(self):
        self.requirements(WORKER_SKILL)

        third = self.prompt(self.do("--skill", WORKER_SKILL)).split("\n")[2]

        self.assertEqual(
            "Its scripts run through the interpreter `orchflows env skill "
            f"{WORKER_SKILL}` prints.",
            third,
        )

    def test_no_declared_environment_leaves_the_interpreter_line_off(self):
        """The line would otherwise send the child to `orchflows env` for an
        item that has none, and be answered with this process's own."""

        self.assertNotIn(
            "orchflows env skill", self.prompt(self.do("--skill", WORKER_SKILL)),
        )

    def test_the_stamp_moves_the_first_line_and_adds_exactly_one(self):
        """The whole surface, held: a stamped `do` differs from a plain one
        by its own identity, the entered skill, and the contract line."""

        plain = self.do()
        stamped = self.do("--skill", WORKER_SKILL)

        left = self.prompt(plain).splitlines()
        right = self.prompt(stamped).splitlines()
        self.assertEqual(len(left) + 1, len(right))
        self.assertNotEqual(left[0], right[0])
        for plain_line, stamped_line in zip(left[1:], right[2:]):
            if STAMP.sub("<lease>", plain_line) == STAMP.sub("<lease>", stamped_line):
                continue
            self.assertIn(plain["do"]["id"], plain_line)
            self.assertIn(stamped["do"]["id"], stamped_line)

    def test_a_do_stamping_no_skill_enters_the_kernel_verb_as_before(self):
        prompt = self.prompt(self.do())

        self.assertIn("Call the Skill tool with skill `orch-do`", prompt)
        self.assertNotIn("Your kernel contract is", prompt)


if __name__ == "__main__":  # pragma: no cover - direct invocation
    unittest.main()
