"""One owner per enum, predicate, and idiom in `scripts/`.

The duplicated-facts class: a fact spelled in N places agrees with itself
until one copy moves, and the copy that did not move is the one some caller
was reading. Each case here fires on the mechanism -- the second spelling --
rather than on the behavior the two spellings currently share, because while
they share it no behavioral test can tell them apart.
"""

from __future__ import annotations

import ast
import inspect
import re
import tempfile
import unittest
from pathlib import Path

from tests._repo_root import ROOT
SCRIPTS = ROOT / "scripts"

from scripts import tickets_bound  # noqa: F401
from scripts import tickets_dispatch_identity, tickets_format  # noqa: E402
from scripts import tickets_assignment, tickets_markdown  # noqa: E402
from scripts import tickets_transitions  # noqa: E402
from tools.validate_support import duplication, packages  # noqa: E402


def scripts_sources():
    """Every shipped script, by path and text."""

    return [
        (path, path.read_text(encoding="utf-8"))
        for path in sorted(SCRIPTS.glob("*.py"))
    ]


class TestOneDequotingPrimitive(unittest.TestCase):
    """Backticks come off frontmatter values in exactly one place.

    Twenty-one sites spelled the removal inline and ten of them stopped a
    step early, so a padded value graded as a different value from its bare
    twin. `dequote` is the whole idiom; a site that spells it again is the
    defect, whatever it currently computes.
    """

    # The idiom itself, so a rewrite that keeps the behavior still fails.
    INLINE = re.compile(r"\.strip\(\)\.strip\((['\"])`\1\)")

    def test_no_script_spells_the_idiom_beside_its_owner(self):
        offenders = [
            f"{path.name}:{number}"
            for path, text in scripts_sources()
            if path.name != "tickets_markdown.py"
            for number, line in enumerate(text.splitlines(), 1)
            if self.INLINE.search(line)
        ]
        self.assertEqual([], offenders, "; ".join(offenders))

    def test_the_owner_is_reached_by_its_public_name(self):
        self.assertIs(tickets_format.dequote, tickets_markdown.dequote)

    def test_the_primitive_removes_padding_inside_the_backticks_too(self):
        for raw, expected in (
            ("`required`", "required"),
            (" `` required `` ", "required"),
            ("  none  ", "none"),
            (None, ""),
            ("", ""),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(expected, tickets_markdown.dequote(raw))


class TestOneOwnerPerEnumAndMapping(unittest.TestCase):
    """The enums and mappings this pass consolidated have one definition."""

    def test_checkable_statuses_is_defined_once_and_imported(self):
        self.assertIs(
            tickets_assignment.CHECKABLE_STATUSES,
            tickets_transitions.CHECKABLE_STATUSES,
        )
        # A facade re-export binds the owner's object; a second literal is
        # what a second owner looks like, so only those are counted.
        defining = [
            path.name for path, text in scripts_sources()
            if re.search(r"^CHECKABLE_STATUSES\s*=\s*(?:frozenset|set|\{|\()",
                         text, re.MULTILINE)
        ]
        self.assertEqual(["tickets_transitions.py"], defining)

    def test_the_record_id_namespace_mapping_has_one_owner(self):
        from scripts import tickets_attempts, tickets_dispatch_validate

        owner = tickets_dispatch_identity.record_id_namespace_ok
        self.assertIs(owner, tickets_attempts._namespace_ok)
        self.assertIs(owner, tickets_dispatch_validate.record_id_namespace_ok)
        for kind, record_id, expected in (
            ("launch", tickets_dispatch_identity.LAUNCH_RECORD_ID, True),
            ("launch", "anything-else", False),
            ("join", "join:1", True),
            ("generic", tickets_dispatch_identity.OUTCOME_RECORD_ID, False),
            ("generic", "r-1", True),
            ("nonsense", "r-1", None),
        ):
            with self.subTest(kind=kind, record_id=record_id):
                self.assertIs(expected, owner(kind, record_id))


class TestTheGeneratedEnumRatchet(unittest.TestCase):
    """The check that keeps the next copy from being written.

    A consolidation that leaves no mechanism behind is undone by the next
    author who needs the same members, so the ratchet is what makes this
    pass durable -- and a ratchet is only worth its ability to fail.
    """

    def _errors(self, root: Path) -> list:
        diag = packages.Diagnostics()
        duplication.validate_generated_enum_copies(diag, root=root)
        return [line for line in diag.lines() if line.startswith("ERROR")]

    def test_the_real_tree_carries_no_restatement(self):
        found = self._errors(ROOT)
        self.assertEqual([], found, found)

    def test_a_planted_restatement_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "contracts").mkdir()
            (root / "contracts" / "shapes.json").write_bytes(
                (ROOT / "contracts" / "shapes.json").read_bytes()
            )
            (root / "scripts").mkdir()
            (root / "scripts" / "tickets_planted.py").write_text(
                'FORMS = ("command", "check")\n', encoding="utf-8"
            )
            messages = self._errors(root)
        self.assertEqual(1, len(messages), messages)
        self.assertIn("FORMS", messages[0])
        self.assertIn("done_binding.form", messages[0])

    def test_a_collection_built_from_names_is_not_a_restatement(self):
        """The point is the second spelling of the members, not a second
        binding of them: a set built out of imported names is already
        reading its values from their owner."""

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "contracts").mkdir()
            (root / "contracts" / "shapes.json").write_bytes(
                (ROOT / "contracts" / "shapes.json").read_bytes()
            )
            (root / "scripts").mkdir()
            (root / "scripts" / "tickets_planted.py").write_text(
                "MODES = frozenset(EXECUTOR_RESULT_VALUES['mode'])\n", encoding="utf-8"
            )
            found = self._errors(root)
        self.assertEqual([], found)

    def test_the_declared_owners_are_the_two_modules_that_may_spell_it(self):
        self.assertEqual(
            ("tickets_shapes.py", "tickets_dispatch_identity.py"),
            duplication.ENUM_OWNER_MODULES,
        )
        for name in duplication.ENUM_OWNER_MODULES:
            self.assertTrue((SCRIPTS / name).is_file(), name)


class TestTheUnreachableIsGone(unittest.TestCase):
    """What no command reaches is deleted, not left reachable as an import."""

    GONE = {
        "tickets_project.py": ("_cmd_claim", "_do_claim", "_claim_under_run_lock",
                               "CLAIM_USAGE", "_project_at", "_root_ticket_text"),
        # `_cmd_packet` joined them: `packet` stopped being routed at the
        # dispatch-v1 cutover and the handler stayed reachable as an
        # import, which is the same shape the claim path had. The wire it
        # built went next, and `_packet_under_run_lock` with it.
        "tickets_assignment.py": ("_cut_lens_path", "_cut_subtree",
                                  "CUT_LENS_PARTS", "_cmd_packet",
                                  "_packet_under_run_lock"),
        "workspace_git.py": ("_checkouts",),
        # The checker-stage apparatus that survived the `review_kind`
        # deletion: no live command ever minted a `.check` ticket or built the
        # `review_v1` chain `tickets.py check` required, so its one input
        # was always hand-edited state -- test-only reachability, not
        # liveness. `tickets_review.py` and `tickets_review_schema.py`
        # (the ledger's own construction and schema) are deleted whole.
        "tickets_format.py": ("GATE_ID_MARKER", "CHECKER_STAGE_SUFFIX",
                              "CHECKED_BY_KEY", "is_review_stage_id"),
        "tickets_lifecycle.py": ("_cmd_check", "_check_under_run_lock",
                                 "CHECK_USAGE"),
        "tickets_admission.py": ("_checker_stage_target",),
    }

    def test_no_module_still_defines_the_deleted_names(self):
        for name, gone in self.GONE.items():
            tree = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))
            defined = set()
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    defined.add(node.name)
                elif isinstance(node, ast.Assign):
                    defined.update(
                        target.id for target in node.targets
                        if isinstance(target, ast.Name)
                    )
            with self.subTest(module=name):
                self.assertEqual(set(), defined & set(gone))

    def test_the_motion_reader_takes_only_the_path_it_reads(self):
        """`_last_motion` reads the ticket file's mtime; the result body it
        was handed and the tuple after it had been unread since that became
        the record, and the caller was extracting the body to pass it."""

        signature = inspect.signature(tickets_bound._last_motion)
        self.assertEqual(["ticket_path"], list(signature.parameters))


if __name__ == "__main__":
    unittest.main()
