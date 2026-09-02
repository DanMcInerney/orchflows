"""A stamped sheet and an applied skill are pinned, and the pin is verified.

The pack's hazard, on two more kinds: a ticket that carried only the *name*
of a sheet or of an applied skill would resolve it to whatever bytes are
nearest at the moment it runs, so a ring that came to shadow it -- or an edit
under the seal -- would be a silent substitution. Every case here fires on
one half of the answer: the digest is taken at issue, and every later door
re-derives it and refuses the pair.

U0 stopped at the pin. U1 added the two doors that read a sheet's *content*:
`packs:` decides whether the stamp is lawful at all, and the launch prompt
hands the child the resolved path and the pinned digest. Both are asserted
here, beside the pins, because all three are one question -- which bytes this
ticket stamped -- asked at three doors. The applied skill's own role check
and its identity lines are U2's, and are checked in
`tests/test_ticket_applied_skill.py`.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import rings, rings_trust, state_root, tickets_admission, tickets_pins
from scripts.tickets_format import _parse_frontmatter

from tests.test_ticket_callables import CODE_PACK, CallableSinkTest

SHEET = "market-brief"
APPLIED_SKILL = "house-style"


def _sheet(root: Path, name: str, body: str, packs=(CODE_PACK,)) -> Path:
    """One sheet manifest. `packs` is the field the stamp is checked against."""

    path = root / "sheets" / name / rings.MANIFESTS["sheet"]
    path.parent.mkdir(parents=True, exist_ok=True)
    declared = ("packs: [" + ", ".join(packs) + "]\n") if packs else ""
    # Bytes, not text: a text write on Windows lands CRLF, and the digest
    # normalizes those away, so a CRLF fixture would hide a normalization
    # that stopped happening.
    path.write_bytes(
        f"---\nname: {name}\n{declared}---\n\n## Craft\n\n{body}\n".encode("utf-8")
    )
    return path


def _skill(root: Path, name: str, body: str, sublayer: str = "",
           role: str = "worker") -> Path:
    """One skill manifest. `sublayer` is the library's own extra level.

    The `role:` is declared because U2 refuses a `--skill` whose declared
    role is not the verb's, and every mint below applies this skill on a
    `do`: a role-less fixture would be refused at the flag and never reach
    the pin these cases are about.
    """

    path = root / "skills" / sublayer / name / rings.MANIFESTS["skill"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        f"---\nname: {name}\nrole: {role}\n---\n\n{body}\n".encode("utf-8")
    )
    return path


@contextlib.contextmanager
def _rings():
    """A project ring, a home ring and a library, all under one temp root."""

    with tempfile.TemporaryDirectory(prefix="orchflows-pins-") as tmp:
        root = Path(tmp).resolve()
        world = {
            "root": root, "home": root / "home",
            "project": root / "project", "lib": root / "lib",
        }
        for kind_dir in rings.RING_DIRS.values():
            (world["home"] / kind_dir).mkdir(parents=True, exist_ok=True)
            (world["project"] / ".orchflows" / kind_dir).mkdir(parents=True, exist_ok=True)
        for lib_dirs in rings.LIB_DIRS.values():
            for kind_dir in lib_dirs:
                (world["lib"] / kind_dir).mkdir(parents=True, exist_ok=True)
        with mock.patch.dict(os.environ, {state_root.ENV_VAR: str(world["home"] / "state")}):
            yield world


def _overrides(world) -> dict:
    return {"project": world["project"], "home": world["home"], "lib": world["lib"]}


class PinnedItemResolutionTest(unittest.TestCase):
    """One resolver, nearest first, for both kinds this module pins."""

    def test_a_sheet_resolves_nearest_first_across_project_home_and_lib(self):
        with _rings() as world:
            _sheet(world["lib"], SHEET, "lib")
            self.assertEqual(
                "lib", tickets_pins.resolved("sheet", SHEET, **_overrides(world))["ring"],
            )

            _sheet(world["home"], SHEET, "home")
            self.assertEqual(
                "home", tickets_pins.resolved("sheet", SHEET, **_overrides(world))["ring"],
            )

            _sheet(world["project"] / ".orchflows", SHEET, "project")
            rings_trust.grant(world["project"] / ".orchflows")
            self.assertEqual(
                "project", tickets_pins.resolved("sheet", SHEET, **_overrides(world))["ring"],
            )

    def test_an_applied_skill_resolves_nearest_first_the_same_way(self):
        with _rings() as world:
            _skill(world["lib"], APPLIED_SKILL, "lib", sublayer="kernel")
            self.assertEqual(
                "lib",
                tickets_pins.resolved("skill", APPLIED_SKILL, **_overrides(world))["ring"],
            )

            _skill(world["home"], APPLIED_SKILL, "home")
            self.assertEqual(
                "home",
                tickets_pins.resolved("skill", APPLIED_SKILL, **_overrides(world))["ring"],
            )

    def test_two_rings_holding_one_name_hash_to_two_digests(self):
        with _rings() as world:
            _sheet(world["lib"], SHEET, "lib")
            far = tickets_pins.item_digest("sheet", SHEET, **_overrides(world))
            _sheet(world["home"], SHEET, "home")

            self.assertNotEqual(
                far, tickets_pins.item_digest("sheet", SHEET, **_overrides(world)),
            )

    def test_a_sheets_digest_covers_every_file_in_its_directory(self):
        with _rings() as world:
            path = _sheet(world["lib"], SHEET, "lib")
            before = tickets_pins.item_digest("sheet", SHEET, **_overrides(world))

            (path.parent / "references.md").write_bytes(b"more\n")

            self.assertNotEqual(
                before, tickets_pins.item_digest("sheet", SHEET, **_overrides(world)),
            )

    def test_a_skills_digest_skips_its_tests_and_installed_dependencies(self):
        with _rings() as world:
            path = _skill(world["lib"], APPLIED_SKILL, "lib", sublayer="kernel")
            before = tickets_pins.item_digest("skill", APPLIED_SKILL, **_overrides(world))
            for directory in tickets_pins.SKIPPED_DIRS["skill"]:
                noise = path.parent / directory / "noise.py"
                noise.parent.mkdir(parents=True, exist_ok=True)
                noise.write_bytes(b"print(1)\n")

            self.assertEqual(
                before, tickets_pins.item_digest("skill", APPLIED_SKILL, **_overrides(world)),
            )

    def test_a_digest_ignores_the_checkouts_line_endings(self):
        with _rings() as world:
            path = _sheet(world["lib"], SHEET, "lib")
            lf = tickets_pins.item_digest("sheet", SHEET, **_overrides(world))
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

            self.assertEqual(
                lf, tickets_pins.item_digest("sheet", SHEET, **_overrides(world)),
            )

    def test_the_drift_refusal_names_the_item_the_ring_and_both_digests(self):
        with _rings() as world:
            _sheet(world["lib"], SHEET, "lib")
            pinned = tickets_pins.item_digest("sheet", SHEET, **_overrides(world))
            _sheet(world["home"], SHEET, "home")
            current = tickets_pins.item_digest("sheet", SHEET, **_overrides(world))

            detail = tickets_pins.drift("sheet", SHEET, pinned, **_overrides(world))

            self.assertIsNotNone(detail)
            for fragment in (f"sheet '{SHEET}'", "home ring", pinned, current):
                self.assertIn(fragment, detail)

    def test_an_unresolvable_item_is_refused_by_name_rather_than_pinned(self):
        with _rings() as world:
            detail = tickets_pins.drift("sheet", SHEET, "sha256:" + "0" * 64, **_overrides(world))

            self.assertIn("cannot be pinned", str(detail))
            with self.assertRaises(tickets_pins.PinError) as raised:
                tickets_pins.item_digest("sheet", SHEET, **_overrides(world))
            self.assertEqual("unresolved", raised.exception.code)


class PinnedItemFieldTest(unittest.TestCase):
    """What `pin_fields` writes, and what it refuses to write."""

    def test_a_ticket_stamping_nothing_gets_four_absent_fields(self):
        self.assertEqual(
            {"sheets": None, "sheet_digests": None, "skill": None, "skill_digest": None},
            tickets_pins.pin_fields((), None)[0],
        )

    def test_stamped_names_and_digests_are_written_as_one_sorted_pair(self):
        with _rings() as world:
            _sheet(world["lib"], SHEET, "lib")
            _sheet(world["lib"], "html-dossier", "lib")

            fields, refusal = tickets_pins.pin_fields(
                ["html-dossier", SHEET], None, **_overrides(world),
            )

            self.assertIsNone(refusal)
            self.assertEqual(["html-dossier", SHEET], fields["sheets"])
            self.assertEqual(
                {"html-dossier", SHEET}, set(tickets_pins.digests_of(fields["sheet_digests"])),
            )

    def test_one_sheet_stamped_twice_is_refused(self):
        with _rings() as world:
            _sheet(world["lib"], SHEET, "lib")

            fields, refusal = tickets_pins.pin_fields(
                [SHEET, SHEET], None, **_overrides(world),
            )

            self.assertIsNone(fields)
            self.assertIn(SHEET, refusal["error"])


class PinnedItemDoorTest(unittest.TestCase):
    """Every later door re-derives the pin: the grading seam they share."""

    def _findings(self, data: dict) -> list:
        return tickets_pins.pinned_findings(data, tickets_admission.finding, **self.overrides)

    def _codes(self, data: dict) -> set:
        return {item["code"] for item in self._findings(data)}

    @contextlib.contextmanager
    def _world(self):
        with _rings() as world:
            self.overrides = _overrides(world)
            yield world

    def test_an_unchanged_sheet_and_skill_pass_the_door(self):
        with self._world() as world:
            _sheet(world["lib"], SHEET, "lib")
            _skill(world["lib"], APPLIED_SKILL, "lib", sublayer="kernel")
            fields, _ = tickets_pins.pin_fields([SHEET], APPLIED_SKILL, **self.overrides)

            self.assertEqual(set(), self._codes(fields))

    def test_a_sheet_edited_under_the_seal_is_refused_at_the_door(self):
        with self._world() as world:
            path = _sheet(world["lib"], SHEET, "lib")
            fields, _ = tickets_pins.pin_fields([SHEET], None, **self.overrides)

            path.write_bytes(path.read_bytes() + b"one more clause\n")

            self.assertEqual({"sheet-digest-mismatch"}, self._codes(fields))

    def test_a_nearer_ring_shadowing_the_stamped_sheet_is_refused(self):
        with self._world() as world:
            _sheet(world["lib"], SHEET, "lib")
            fields, _ = tickets_pins.pin_fields([SHEET], None, **self.overrides)

            _sheet(world["home"], SHEET, "home")

            self.assertEqual({"sheet-digest-mismatch"}, self._codes(fields))

    def test_an_applied_skill_edited_under_the_seal_is_refused(self):
        with self._world() as world:
            path = _skill(world["lib"], APPLIED_SKILL, "lib", sublayer="kernel")
            fields, _ = tickets_pins.pin_fields((), APPLIED_SKILL, **self.overrides)

            path.write_bytes(path.read_bytes() + b"a second method\n")

            self.assertEqual({"skill-digest-mismatch"}, self._codes(fields))

    def test_half_a_pin_names_nothing_and_says_so(self):
        with self._world():
            self.assertEqual(
                {"sheet-digest-unbound"}, self._codes({"sheets": [SHEET]}),
            )
            self.assertEqual(
                {"sheet-digests-invalid"},
                self._codes({"sheet_digests": "not json"}),
            )
            self.assertEqual(
                {"skill-digest-unbound"}, self._codes({"skill": APPLIED_SKILL}),
            )
            self.assertEqual(
                {"skill-digest-unbound"},
                self._codes({"skill_digest": "sha256:" + "0" * 64}),
            )


class StampedCallableTest(CallableSinkTest):
    """`do` and `judge` take the flags, pin them, and admit through them."""

    def setUp(self):
        super().setUp()
        self.ring = Path(self.temporary.name) / "ring"
        _sheet(self.ring, SHEET, "House brief shape.")
        _skill(self.ring, APPLIED_SKILL, "The method.")
        self.home = mock.patch.object(rings, "home_ring", return_value=self.ring)
        self.home.start()
        self.addCleanup(self.home.stop)

    def _codes(self, ticket_id: str) -> set:
        from scripts.tickets_context import graded_admission, run_snapshot

        snapshot, _ = run_snapshot(self.run_dir())
        return {
            item["code"]
            for item in graded_admission(
                ticket_id, snapshot[ticket_id], snapshot, self.RUN,
            )["findings"]
        }

    def test_a_stamped_do_pins_both_kinds_and_admits(self):
        self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            "--sheet", SHEET, "--skill", APPLIED_SKILL,
        )

        data = _parse_frontmatter(self.ticket_text("B1"))
        self.assertEqual([SHEET], data["sheets"])
        self.assertEqual(APPLIED_SKILL, data["skill"])
        self.assertEqual(
            {SHEET: tickets_pins.item_digest("sheet", SHEET)},
            tickets_pins.digests_of(data["sheet_digests"]),
        )
        self.assertEqual(
            tickets_pins.item_digest("skill", APPLIED_SKILL), data["skill_digest"],
        )
        self.assertEqual(set(), self._codes("B1"))

    def test_a_stamped_judge_pins_the_same_way(self):
        self.callable(
            "judge", "--pack", CODE_PACK, "--isolation", "none",
            "--artifacts", "git:" + "a" * 40, "--sheet", SHEET,
        )

        data = _parse_frontmatter(self.ticket_text("B1"))
        self.assertEqual([SHEET], data["sheets"])
        self.assertNotIn("skill", data)
        self.assertEqual(set(), self._codes("B1"))

    def test_a_sheet_that_moves_after_the_mint_refuses_at_admission(self):
        self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required", "--sheet", SHEET,
        )

        manifest = self.ring / "sheets" / SHEET / rings.MANIFESTS["sheet"]
        manifest.write_bytes(manifest.read_bytes() + b"a clause nobody sealed\n")

        self.assertIn("sheet-digest-mismatch", self._codes("B1"))

    def test_the_stamped_pins_are_sealed_with_the_rest_of_the_assignment(self):
        self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required", "--sheet", SHEET,
        )
        plain = self.callable("do", "--pack", CODE_PACK, "--isolation", "required")

        self.assertNotEqual(
            _parse_frontmatter(self.ticket_text("B1"))["assignment_seal"],
            _parse_frontmatter(self.ticket_text(plain["do"]["id"]))["assignment_seal"],
        )

    def test_an_unresolvable_sheet_is_refused_before_the_run_exists(self):
        answer = self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            "--sheet", "no-such-sheet", expect_error=True,
        )

        self.assertIn("no-such-sheet", answer["error"])
        self.assertFalse(self.run_dir().exists())

    def test_a_do_without_the_flags_carries_no_new_frontmatter_field(self):
        """U0's own boundary: a ticket that stamps nothing gains nothing.

        The frontmatter keys are pinned as a sequence, so a field appearing
        on a ticket that stamped nothing fails here rather than at whatever
        reads the ticket next.

        U0 also compared the two prompts, on the ground that it added no
        prompt line. U2 adds two for an applied skill, so that comparison
        now lives in `tests/test_ticket_applied_skill.py`, which asserts
        the stronger thing: exactly which lines the stamp may move.
        """

        plain = self.callable("do", "--pack", CODE_PACK, "--isolation", "required")

        self.assertEqual(
            [
                "id", "run", "status", "admission", "executor", "pack",
                "pack_digest", "independence", "isolation", "bound",
                "root_generation", "cut_generation", "assignment_seal",
                "dispatch_v1", "workspace_branch", "workspace_baseline",
            ],
            list(_parse_frontmatter(self.ticket_text(plain["do"]["id"]))),
        )

    def test_an_unstamped_do_prompt_names_no_sheet(self):
        """U1's half of the same boundary, on the prompt rather than the
        frontmatter: a sheet line that leaked onto a ticket which stamped
        none would be craft the child was never assigned."""

        plain = self.callable("do", "--pack", CODE_PACK, "--isolation", "required")

        self.assertEqual(
            [], [line for line in self.prompt(plain).splitlines() if "sheet" in line],
        )

    def _sheet_line(self, answer: dict) -> str:
        """The one sheet line this launch prompt carries."""

        lines = [
            line for line in self.prompt(answer).splitlines()
            if line.startswith("Read the sheet ")
        ]
        self.assertEqual(1, len(lines), self.prompt(answer))
        return lines[0]

    def _resolved(self, name: str):
        record = tickets_pins.resolved("sheet", name)
        return record["path"], str(record["digest"]).split(":", 1)[-1]

    def test_a_stamped_do_prompt_carries_the_sheet_line_verbatim(self):
        """The maker's wording: path, pinned digest, and both halves of the
        tighten-only rule pointed at the `## Lens` entry its kind resolved."""

        answer = self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required", "--sheet", SHEET,
        )
        path, digest = self._resolved(SHEET)

        self.assertEqual(
            f"Read the sheet `{SHEET}` at {path} whole (sha256 {digest}). Its "
            "`## Craft` binds your making; its `## Lens` `### git` entry adds "
            "to the craft's `### git` and never loosens it.",
            self._sheet_line(answer),
        )

    def test_a_stamped_judge_prompt_carries_the_judges_sheet_line_verbatim(self):
        """The same three facts, turned toward the reader who reports the
        conflict rather than the one who would have to build to it."""

        answer = self.callable(
            "judge", "--pack", CODE_PACK, "--isolation", "none",
            "--artifacts", "git:" + "a" * 40, "--sheet", SHEET,
        )
        path, digest = self._resolved(SHEET)

        self.assertEqual(
            f"Read the sheet `{SHEET}` at {path} whole (sha256 {digest}). Its "
            "`## Lens` `### git` entry adds criteria you check beside the "
            "craft's; where it loosens the craft's, the craft wins and you "
            "report the conflict as a `sheet-defect` finding.",
            self._sheet_line(answer),
        )

    def test_every_stamped_sheet_gets_its_own_line(self):
        """Two stamps, two lines: one sheet's line naming another's digest
        would be the substitution the pin exists to prevent."""

        second = "house-brief"
        _sheet(self.ring, second, "The second narrowing.")
        answer = self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            "--sheet", SHEET, "--sheet", second,
        )

        lines = [
            line for line in self.prompt(answer).splitlines()
            if line.startswith("Read the sheet ")
        ]
        self.assertEqual(2, len(lines))
        for name in (SHEET, second):
            path, digest = self._resolved(name)
            self.assertTrue(
                any(f"`{name}` at {path} whole (sha256 {digest})" in line for line in lines),
                lines,
            )

    def test_a_sheet_that_does_not_name_the_stamped_pack_refuses(self):
        """The `packs:` door. A sheet tightens the craft it was written
        against; stamped beside another pack it is criteria for a domain it
        never read, so the callable never opens."""

        _sheet(self.ring, "doc-only", "Prose shape.", packs=("orch-content-pack",))

        answer = self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            "--sheet", "doc-only", expect_error=True,
        )

        self.assertIn("orch-content-pack", answer["error"])
        self.assertIn(CODE_PACK, answer["error"])
        self.assertFalse(self.run_dir().exists())

    def test_a_sheet_declaring_no_packs_is_refused_rather_than_stamped_anywhere(self):
        """The field is required (`contracts/sheet.md`), so its absence is a
        refusal with its own sentence -- not a sheet that fits every pack."""

        _sheet(self.ring, "unbound", "No packs named.", packs=())

        answer = self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            "--sheet", "unbound", expect_error=True,
        )

        self.assertIn("declares no `packs:`", answer["error"])
        self.assertFalse(self.run_dir().exists())


if __name__ == "__main__":  # pragma: no cover - direct invocation
    unittest.main()
