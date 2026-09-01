"""One door opens a brick, and the door is what seals it.

Every case fires on a step a caller used to run by hand between `new` and
`dispatch`. The id is minted under the run lock rather than authored; a
child's seal comes through its parent rather than through a cut that closed
before it existed; and the launch carries the three lines a parent needs to
relay a child's answer without paraphrasing it -- the commit instruction two
of four workers skipped on 2026-08-31, the typed artifact line, and the
judge's findings line.

This module's `do`/`judge` cases assert against `orch-do`/`orch-judge`,
the registry names W2b (verbs-rename) minted from `orch-execute` and
`orch-check`. They stay red on the `lego-W2b` branch alone: brick's own
`DO_EXECUTOR`/`JUDGE_EXECUTOR` in `scripts/tickets_brick.py` (W2a's file,
fenced from this ticket) still name the pre-rename verbs, so every mint
here is refused as `executor-unregistered` until the two branches merge
and that one-site constant flip lands with them.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tests._candidate_checkout import git_checkout, record_established_workspace
from scripts import tickets
from scripts import tickets_brick
from scripts.tickets_format import _parse_frontmatter, _sections, parse_canonical_json

CODE_PACK = "orch-code-pack"
DOC_PACK = "orch-content-pack"
GOAL = "Deliver the widget and prove it runs.\n"
DETAILS = "Read the craft first; report every exit code.\n"


class BrickSinkTest(unittest.TestCase):
    """A temp sink, a real candidate checkout, and a stubbed establishment."""

    RUN = "brickrun"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(
            os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name}
        )
        self.environment.start()
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate")
        self.goal_file = Path(self.temporary.name) / "goal.md"
        self.goal_file.write_text(GOAL, encoding="utf-8")
        self.details_file = Path(self.temporary.name) / "details.md"
        self.details_file.write_text(DETAILS, encoding="utf-8")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def run_dir(self) -> Path:
        return Path(self.temporary.name) / "tickets" / self.RUN

    def ticket_text(self, ticket_id: str) -> str:
        return (self.run_dir() / f"{ticket_id}.md").read_text(encoding="utf-8")

    def _establish(self, run, ticket_id, _workspace):
        """What `workspace.py establish` writes, for a Git candidate.

        The two Git-only observations go on with the path: an isolated Git
        item whose branch and baseline are absent is refused at the launch,
        and a stub that recorded only the path would be testing the stub.
        """

        path = self.run_dir() / f"{ticket_id}.md"
        record_established_workspace(path, self.candidate, strict=False)
        text = path.read_text(encoding="utf-8")
        for field, value in (
            ("workspace_branch", f"candidate/{ticket_id}"),
            ("workspace_baseline", "0" * 40),
        ):
            text = tickets._set_frontmatter_field(text, field, value)
        path.write_text(text, encoding="utf-8")
        return {"establish": {"workspace_path": str(self.candidate)}}

    def brick(self, verb, *arguments, expect_error=False):
        facade = tickets._tickets_dispatch_facade_module
        with mock.patch.object(
            facade, "_workspace_establish", side_effect=self._establish,
        ), mock.patch.object(
            facade, "_workspace_prepare", return_value={"outcome": "skipped"},
        ):
            answer = tickets._dispatch([
                verb, self.RUN, "--goal-file", str(self.goal_file), *arguments,
            ])
        if expect_error:
            self.assertIn("error", answer, answer)
        else:
            self.assertNotIn("error", answer, answer)
        return answer

    def prompt(self, answer: dict) -> str:
        return answer[next(iter(answer))]["launch"]["prompt"]


class BrickIdGrammarTest(BrickSinkTest):
    """Ids are minted, and the mint is what the run lock arbitrates."""

    def test_a_parentless_brick_roots_its_own_tree_and_seals_itself(self):
        answer = self.brick("do", "--pack", CODE_PACK, "--isolation", "required")

        self.assertEqual("B1", answer["do"]["id"])
        self.assertIsNone(answer["do"]["parent"])
        data = _parse_frontmatter(self.ticket_text("B1"))
        self.assertTrue(data["root_generation"].startswith("root:B1:1:sha256:"))
        self.assertTrue(data["cut_generation"].startswith("cut:B1:1:sha256:"))
        self.assertTrue(data["assignment_seal"].startswith("sha256:"))
        self.assertEqual("orch-do", data["executor"])
        self.assertNotIn("parent", data)
        # prose order replaces edges: a brick declares no dependencies at all
        self.assertNotIn("depends_on", data)
        self.assertEqual(GOAL.strip(), _sections(self.ticket_text("B1"))["Goal"].strip())

    def test_a_child_is_minted_under_its_parent_and_sealed_through_it(self):
        self.brick("do", "--pack", CODE_PACK, "--isolation", "required")

        answer = self.brick(
            "do", "--pack", CODE_PACK, "--parent", "B1", "--isolation", "required",
            "--details-file", str(self.details_file),
        )

        self.assertEqual("B1.1", answer["do"]["id"])
        parent = _parse_frontmatter(self.ticket_text("B1"))
        child = _parse_frontmatter(self.ticket_text("B1.1"))
        self.assertEqual("B1", child["parent"])
        for field in ("root_generation", "cut_generation"):
            self.assertEqual(parent[field], child[field])
        self.assertNotEqual(parent["assignment_seal"], child["assignment_seal"])
        self.assertEqual(
            DETAILS.strip(), _sections(self.ticket_text("B1.1"))["Details"].strip(),
        )
        self.assertIn("- parent: B1", _sections(self.ticket_text("B1.1"))["Context"])
        # the second child takes the next ordinal under the same parent
        second = self.brick(
            "do", "--pack", CODE_PACK, "--parent", "B1", "--isolation", "required",
        )
        self.assertEqual("B1.2", second["do"]["id"])
        # and the next parentless brick roots a second tree
        self.assertEqual(
            "B2", self.brick(
                "do", "--pack", CODE_PACK, "--isolation", "required",
            )["do"]["id"],
        )

    def test_two_concurrent_calls_under_one_parent_mint_distinct_ids(self):
        """The run lock the door holds at the mint is the whole arbiter."""

        self.brick("do", "--pack", CODE_PACK, "--isolation", "required")
        answers, start = [], threading.Barrier(2)

        def call():
            start.wait()
            answers.append(self.brick(
                "do", "--pack", CODE_PACK, "--parent", "B1",
                "--isolation", "required",
            ))

        threads = [threading.Thread(target=call) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        minted = sorted(answer["do"]["id"] for answer in answers)
        self.assertEqual(["B1.1", "B1.2"], minted)

    def test_a_child_of_an_unsealed_parent_is_refused_with_its_remedy(self):
        self.brick("do", "--pack", CODE_PACK, "--isolation", "required")
        tickets._dispatch([
            "new", self.RUN, "L", "--executor", "orch-do",
            "--goal", "Unsealed.", "--context", "[]", "--pack", CODE_PACK,
        ])

        refused = self.brick(
            "do", "--pack", CODE_PACK, "--parent", "L", expect_error=True,
        )

        self.assertIn("is not sealed", refused["error"])
        self.assertIn("seal the parent first", refused["error"])
        self.assertFalse((self.run_dir() / "L.1.md").exists())


class BrickAdmissionTest(BrickSinkTest):
    """A runtime child crosses admission through its parent, not the cut."""

    def _codes(self, ticket_id: str) -> set:
        from scripts.tickets_context import graded_admission, run_snapshot

        snapshot, _ = run_snapshot(self.run_dir())
        grade = graded_admission(
            ticket_id, snapshot[ticket_id], snapshot, self.RUN,
        )
        return {item["code"] for item in grade["findings"]}

    def test_parent_and_child_both_admit_and_the_parent_owns_no_members(self):
        self.brick("do", "--pack", CODE_PACK, "--isolation", "required")
        self.brick(
            "do", "--pack", CODE_PACK, "--parent", "B1", "--isolation", "required",
        )
        self.brick(
            "judge", "--pack", CODE_PACK, "--parent", "B1",
            "--artifacts", "git:" + "a" * 40, "--isolation", "none",
        )

        for ticket_id in ("B1", "B1.1", "B1.2"):
            self.assertEqual(set(), self._codes(ticket_id), ticket_id)

    def test_a_child_edited_after_it_was_minted_is_bound_by_nothing(self):
        self.brick("do", "--pack", CODE_PACK, "--isolation", "required")
        self.brick(
            "do", "--pack", CODE_PACK, "--parent", "B1", "--isolation", "required",
        )
        path = self.run_dir() / "B1.1.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace("widget", "widgets", 1),
            encoding="utf-8",
        )

        self.assertIn("sealed-assignment-mismatch", self._codes("B1.1"))

    def test_a_child_whose_parent_the_seal_does_not_name_is_refused(self):
        self.brick("do", "--pack", CODE_PACK, "--isolation", "required")
        self.brick(
            "do", "--pack", CODE_PACK, "--parent", "B1", "--isolation", "required",
        )
        parent = self.run_dir() / "B1.md"
        parent.write_text(tickets._set_frontmatter_field(
            parent.read_text(encoding="utf-8"), "assignment_seal",
            "sha256:" + "0" * 64,
        ), encoding="utf-8")

        self.assertIn("sealed-parent-mismatch", self._codes("B1.1"))


class BrickPromptTest(BrickSinkTest):
    """The three lines the launch gained, and the adapter that types them."""

    def test_a_git_brick_is_told_to_commit_and_to_print_a_git_line(self):
        answer = self.brick("do", "--pack", CODE_PACK, "--isolation", "required")

        prompt = self.prompt(answer)
        self.assertIn("Commit your work inside this candidate before you close", prompt)
        self.assertIn("artifact: git:<full-commit-id>", prompt)
        self.assertNotIn("findings: <path>", prompt)

    def test_a_document_brick_is_told_to_print_a_doc_line(self):
        answer = self.brick("do", "--pack", DOC_PACK)

        prompt = self.prompt(answer)
        self.assertIn(
            "artifact: doc:<path>@sha256:<digest-of-the-document-bytes>", prompt,
        )
        self.assertNotIn("artifact: git:", prompt)

    def test_a_judge_prints_the_findings_line_beside_its_artifact_line(self):
        self.brick("do", "--pack", CODE_PACK, "--isolation", "required")

        answer = self.brick(
            "judge", "--pack", CODE_PACK, "--parent", "B1",
            "--artifacts", "git:" + "b" * 40, "--isolation", "none",
        )

        self.assertEqual("orch-judge", _parse_frontmatter(
            self.ticket_text("B1.1")
        )["executor"])
        prompt = self.prompt(answer)
        self.assertIn("findings: <path>", prompt)
        self.assertIn("artifact: git:<full-commit-id>", prompt)
        self.assertIn(
            "- artifact: git:" + "b" * 40,
            _sections(self.ticket_text("B1.1"))["Context"],
        )

    def test_an_untyped_artifact_is_refused_before_anything_is_written(self):
        self.brick("do", "--pack", CODE_PACK, "--isolation", "required")

        refused = self.brick(
            "judge", "--pack", CODE_PACK, "--parent", "B1",
            "--artifacts", "the draft I made earlier", expect_error=True,
        )

        self.assertIn("is not one typed identity", refused["error"])
        self.assertFalse((self.run_dir() / "B1.1.md").exists())


class RepairRoundAdmissionTest(BrickSinkTest):
    """A `do` brick's repair round binds through the brick, not the frame.

    The wedge run 20260901T021739Z hit: the sealed record for a frame-rooted
    run names only the frame in `assignment_seals`, but a repair round's
    grammar-derived parent (`landing_round_parent`) is the brick it repairs,
    which is itself a runtime-minted child the cut never named. Grading the
    round's admission through one hop found a parent absent from the sealed
    set and refused `sealed-parent-mismatch` -- every repair round of every
    `do`/`judge` brick, unconditionally.
    """

    def _issue(self, verb, *arguments) -> dict:
        """One non-brick door, under the same establishment stub `brick` uses."""

        facade = tickets._tickets_dispatch_facade_module
        with mock.patch.object(
            facade, "_workspace_establish", side_effect=self._establish,
        ), mock.patch.object(
            facade, "_workspace_prepare", return_value={"outcome": "skipped"},
        ):
            return tickets._dispatch([verb, self.RUN, *arguments])

    def _lease(self) -> str:
        return (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

    def test_a_runtime_bricks_repair_round_admits_and_dispatches(self):
        frame_id = self.brick("frame-open")["frame_open"]["id"]
        command = f'"{sys.executable}" -c "raise SystemExit(3)"'
        done = json.dumps({"form": "command", "value": command}, sort_keys=True)

        brick_id = self.brick(
            "do", "--pack", CODE_PACK, "--parent", frame_id,
            "--isolation", "none", "--done", done,
        )["do"]["id"]
        seal = parse_canonical_json(
            _parse_frontmatter(self.ticket_text(brick_id))["dispatch_v1"]
        )["attempts"][0]["assignment_seal"]

        self._issue(
            "dispatch-outcome", brick_id, "--note", "delivered and verified",
        )
        landed = self._issue(
            "land", brick_id, "--assignment-seal", seal,
            "--dispatch-id", f"{brick_id}:d1", "--outcome-record-id", "outcome",
            "--by", "root-join",
        )
        self.assertNotIn("error", landed, landed)
        self.assertIsNone(landed["land"]["status"])
        repair_id = landed["land"]["steps"][-1]["repair"]
        self.assertEqual(f"{brick_id}.repair.1", repair_id)

        dispatched = self._issue(
            "dispatch", repair_id, "--by", repair_id,
            "--dispatch-id", f"{repair_id}:d1",
            "--lease-expires-at", self._lease(),
            "--workspace", str(self.candidate),
        )

        self.assertNotIn("error", dispatched, dispatched)


class BrickLandingTest(BrickSinkTest):
    """`do` to `land`, once over a git pack and once over a document tree.

    The whole chain the door is meant to fold: one command mints, seals,
    establishes and emits; the child files a result and closes its reserved
    outcome; `land` evaluates, joins, and reports.
    """

    def _filed_and_closed(self, ticket_id: str, artifact: str):
        attempt = parse_canonical_json(
            _parse_frontmatter(self.ticket_text(ticket_id))["dispatch_v1"]
        )["attempts"][0]
        filed = tickets._dispatch([
            "result", self.RUN, ticket_id,
            "--assignment-seal", attempt["assignment_seal"],
            "--dispatch-id", attempt["dispatch_id"],
            "--record-id", "note-1", "--by", ticket_id,
            "--text", f"Committed in the candidate.\n\nartifact: {artifact}",
        ])
        self.assertNotIn("error", filed, filed)
        closed = tickets._dispatch([
            "dispatch-outcome", self.RUN, ticket_id,
            "--note", f"delivered; artifact: {artifact}",
        ])
        self.assertNotIn("error", closed, closed)
        return attempt

    def _land(self, ticket_id: str, attempt: dict, *extra):
        return tickets._dispatch([
            "land", self.RUN, ticket_id,
            "--assignment-seal", attempt["assignment_seal"],
            "--dispatch-id", attempt["dispatch_id"],
            "--outcome-record-id", "outcome", "--by", "driver", *extra,
        ])

    def _assert_three_lines(self, answer: dict, artifact_form: str, findings: bool):
        prompt = self.prompt(answer)
        self.assertIn("Commit your work inside this candidate before you close", prompt)
        self.assertIn(artifact_form, prompt)
        self.assertEqual(findings, "findings: <path>" in prompt)

    def test_a_git_brick_runs_its_done_predicate_at_the_landing(self):
        import sys

        done = json.dumps(
            {"form": "command", "value": f'"{sys.executable}" -c "raise SystemExit(0)"'},
            sort_keys=True,
        )
        answer = self.brick(
            "do", "--pack", CODE_PACK, "--isolation", "none", "--done", done,
        )
        self._assert_three_lines(answer, "artifact: git:<full-commit-id>", False)

        attempt = self._filed_and_closed("B1", "git:" + "d" * 40)
        landed = self._land("B1", attempt)

        self.assertNotIn("error", landed, landed)
        self.assertEqual("complete", landed["land"]["status"])
        self.assertEqual(0, landed["land"]["done"]["exit"])
        self.assertIn("Committed in the candidate.", _sections(
            self.ticket_text("B1")
        )["Report"])

    def test_a_document_brick_lands_on_the_drivers_grade(self):
        answer = self.brick("do", "--pack", DOC_PACK)
        self._assert_three_lines(
            answer, "artifact: doc:<path>@sha256:<digest-of-the-document-bytes>", False,
        )

        attempt = self._filed_and_closed("B1", "doc:notes.md@sha256:" + "e" * 64)
        landed = self._land("B1", attempt, "--status", "complete")

        self.assertNotIn("error", landed, landed)
        self.assertEqual("complete", landed["land"]["status"])

    def test_a_judge_under_a_landed_brick_carries_both_machine_lines(self):
        self.brick("do", "--pack", DOC_PACK)

        answer = self.brick(
            "judge", "--pack", DOC_PACK, "--parent", "B1",
            "--artifacts", "doc:notes.md@sha256:" + "e" * 64,
        )

        self._assert_three_lines(
            answer, "artifact: doc:<path>@sha256:<digest-of-the-document-bytes>", True,
        )
        attempt = self._filed_and_closed("B1.1", "doc:review.md@sha256:" + "f" * 64)
        landed = self._land("B1.1", attempt, "--status", "complete")
        self.assertNotIn("error", landed, landed)
        self.assertEqual("complete", landed["land"]["status"])


class TypedArtifactGrammarTest(unittest.TestCase):
    """Every adapter fixes the prefix its artifact line and its joins take."""

    def test_each_registered_adapter_names_one_line_kind(self):
        from scripts.tickets_adapters import ADAPTER_REGISTRY
        from scripts.tickets_dispatch_launch import ARTIFACT_LINE_FORMS

        for adapter in ADAPTER_REGISTRY.values():
            self.assertIn(adapter.artifact_kind, ARTIFACT_LINE_FORMS)
        self.assertEqual(
            tickets_brick.ARTIFACT_KINDS, set(ARTIFACT_LINE_FORMS),
        )


if __name__ == "__main__":
    unittest.main()
