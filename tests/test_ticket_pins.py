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

from scripts import (
    packs_support, rings, rings_trust, state_root, tickets_admission, tickets_pins,
)
from scripts.tickets_format import _parse_frontmatter

from tests.test_ticket_callables import CODE_PACK, DOC_PACK, CallableSinkTest

SHEET = "market-brief"
APPLIED_SKILL = "house-style"


def _sheet(root: Path, name: str, body: str, narrows=None, packs=()) -> Path:
    """One narrowing manifest.

    `narrows` names the parent the chain walks to. `packs` is the field
    `narrows:` replaces, written only by the cases about the domain door
    that still reads it while an item can carry one.
    """

    path = root / "sheets" / name / rings.MANIFESTS["sheet"]
    path.parent.mkdir(parents=True, exist_ok=True)
    declared = f"narrows: {narrows}\n" if narrows else ""
    declared += ("packs: [" + ", ".join(packs) + "]\n") if packs else ""
    # Bytes, not text: a text write on Windows lands CRLF, and the digest
    # normalizes those away, so a CRLF fixture would hide a normalization
    # that stopped happening.
    path.write_bytes(
        f"---\nname: {name}\n{declared}---\n\n## Craft\n\n{body}\n".encode("utf-8")
    )
    return path


def _pack(root: Path, name: str, adapter: str = "git") -> Path:
    """One root standard, in the directory a root still lives in.

    Collapsed shape: one manifest, `adapter` in frontmatter, no cells table
    and no second file. The resolver refuses a manifest still carrying a
    `| Cell | Binding |` table, so a fixture that wrote one would exercise
    that refusal rather than the pin these cases are about.
    """

    path = root / "packs" / name / rings.MANIFESTS["pack"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (
            f"---\nname: {name}\nadapter: {adapter}\n---\n\n"
            f"# {name}\n\n## Making\n\nProse.\n"
        ).encode("utf-8")
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

    def test_a_ticket_stamping_nothing_gets_three_absent_fields(self):
        self.assertEqual(
            {"standards": None, "skill": None, "skill_digest": None},
            tickets_pins.pin_fields((), None)[0],
        )

    def test_every_resolved_level_is_written_as_one_name_and_digest(self):
        with _rings() as world:
            _pack(world["lib"], CODE_PACK)
            _sheet(world["lib"], SHEET, "lib", narrows=CODE_PACK)
            _sheet(world["lib"], "html-dossier", "lib", narrows=CODE_PACK)

            fields, refusal = tickets_pins.pin_fields(
                ["html-dossier", SHEET], None, **_overrides(world),
            )

            self.assertIsNone(refusal)
            self.assertEqual(
                [
                    (CODE_PACK, tickets_pins.item_digest(
                        "pack", CODE_PACK, **_overrides(world))),
                    ("html-dossier", tickets_pins.item_digest(
                        "sheet", "html-dossier", **_overrides(world))),
                    (SHEET, tickets_pins.item_digest(
                        "sheet", SHEET, **_overrides(world))),
                ],
                tickets_pins.standards_of(fields["standards"]),
            )

    def test_one_standard_stamped_twice_is_read_once_rather_than_refused(self):
        """The rule the duplicate refusal became: a name given twice is one
        level, at its first position, because a shared ancestor reached down
        two chains has to resolve without the caller pruning it first."""

        with _rings() as world:
            _pack(world["lib"], CODE_PACK)
            _sheet(world["lib"], SHEET, "lib", narrows=CODE_PACK)

            fields, refusal = tickets_pins.pin_fields(
                [SHEET, SHEET], None, **_overrides(world),
            )

            self.assertIsNone(refusal)
            self.assertEqual(
                [CODE_PACK, SHEET],
                [name for name, _digest in tickets_pins.standards_of(fields["standards"])],
            )


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

    def test_an_unchanged_chain_and_skill_pass_the_door(self):
        with self._world() as world:
            _pack(world["lib"], CODE_PACK)
            _sheet(world["lib"], SHEET, "lib", narrows=CODE_PACK)
            _skill(world["lib"], APPLIED_SKILL, "lib", sublayer="kernel")
            fields, _ = tickets_pins.pin_fields([SHEET], APPLIED_SKILL, **self.overrides)

            self.assertEqual(set(), self._codes(fields))

    def test_a_narrowing_edited_under_the_seal_is_refused_at_the_door(self):
        with self._world() as world:
            _pack(world["lib"], CODE_PACK)
            path = _sheet(world["lib"], SHEET, "lib", narrows=CODE_PACK)
            fields, _ = tickets_pins.pin_fields([SHEET], None, **self.overrides)

            path.write_bytes(path.read_bytes() + b"one more clause\n")

            self.assertEqual({"standard-digest-mismatch"}, self._codes(fields))

    def test_a_root_edited_under_the_seal_is_refused_at_the_door(self):
        """The level the caller never named. A chain pins every level, so an
        edit to the root a narrowing reached is a refusal too -- otherwise
        the ancestry a child reads would be unsealed above its first hop."""

        with self._world() as world:
            path = _pack(world["lib"], CODE_PACK)
            _sheet(world["lib"], SHEET, "lib", narrows=CODE_PACK)
            fields, _ = tickets_pins.pin_fields([SHEET], None, **self.overrides)

            path.write_bytes(path.read_bytes() + b"\n<!-- a clause nobody sealed -->\n")

            self.assertEqual({"standard-digest-mismatch"}, self._codes(fields))

    def test_a_nearer_ring_shadowing_a_stamped_level_is_refused(self):
        with self._world() as world:
            _pack(world["lib"], CODE_PACK)
            _sheet(world["lib"], SHEET, "lib", narrows=CODE_PACK)
            fields, _ = tickets_pins.pin_fields([SHEET], None, **self.overrides)

            _sheet(world["home"], SHEET, "home", narrows=CODE_PACK)

            self.assertEqual({"standard-digest-mismatch"}, self._codes(fields))

    def test_an_applied_skill_edited_under_the_seal_is_refused(self):
        with self._world() as world:
            path = _skill(world["lib"], APPLIED_SKILL, "lib", sublayer="kernel")
            fields, _ = tickets_pins.pin_fields((), APPLIED_SKILL, **self.overrides)

            path.write_bytes(path.read_bytes() + b"a second method\n")

            self.assertEqual({"skill-digest-mismatch"}, self._codes(fields))

    def test_half_a_pin_names_nothing_and_says_so(self):
        with self._world():
            self.assertEqual(
                {"standard-pin-invalid"}, self._codes({"standards": [SHEET]}),
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

    def _chain(self, *names) -> list:
        return [
            (name, tickets_pins.item_digest(
                "pack" if name == CODE_PACK else "sheet", name,
            ))
            for name in names
        ]

    def test_a_stamped_do_pins_the_whole_chain_and_admits(self):
        self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            "--sheet", SHEET, "--skill", APPLIED_SKILL,
        )

        data = _parse_frontmatter(self.ticket_text("B1"))
        self.assertEqual(
            self._chain(CODE_PACK, SHEET), tickets_pins.standards_of(data["standards"]),
        )
        self.assertEqual(APPLIED_SKILL, data["skill"])
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
        self.assertEqual(
            self._chain(CODE_PACK, SHEET), tickets_pins.standards_of(data["standards"]),
        )
        self.assertNotIn("skill", data)
        self.assertEqual(set(), self._codes("B1"))

    def test_a_narrowing_that_moves_after_the_mint_refuses_at_admission(self):
        self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required", "--sheet", SHEET,
        )

        manifest = self.ring / "sheets" / SHEET / rings.MANIFESTS["sheet"]
        manifest.write_bytes(manifest.read_bytes() + b"a clause nobody sealed\n")

        self.assertIn("standard-digest-mismatch", self._codes("B1"))

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
                "id", "run", "status", "admission", "executor", "standards",
                "isolation", "bound",
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

    def test_a_narrowing_off_its_declared_domain_refuses(self):
        """The domain door, under the spelling an item can still carry. A
        narrowing tightens the craft it was written against; stamped beside
        another domain it is criteria for one it never read, so the callable
        never opens."""

        _sheet(self.ring, "doc-only", "Prose shape.", packs=("orch-content-pack",))

        answer = self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            "--sheet", "doc-only", expect_error=True,
        )

        self.assertIn("orch-content-pack", answer["error"])
        self.assertIn(CODE_PACK, answer["error"])
        self.assertFalse(self.run_dir().exists())

    def test_a_narrowing_off_its_domain_refuses_through_narrows_too(self):
        """The same door under the spelling that replaces it: naming a
        parent in another domain puts two adapters in one resolved set,
        which is the contradiction rather than a preference."""

        _sheet(self.ring, "doc-narrowing", "Prose shape.", narrows="orch-content-pack")

        answer = self.callable(
            "do", "--pack", CODE_PACK, "--isolation", "required",
            "--sheet", "doc-narrowing", expect_error=True,
        )

        self.assertIn("orch-content-pack", answer["error"])
        self.assertIn(CODE_PACK, answer["error"])
        self.assertFalse(self.run_dir().exists())


class StandardChainTest(unittest.TestCase):
    """The `narrows:` walk: what resolves, in what order, and what refuses.

    Every case is one clause of the cascade rule. A chain is walked from the
    stamped name to a standard carrying no `narrows:`, and the resolved set
    is checked for exactly one adapter -- zero leaves the ticket with no
    workspace mechanism, two leave it with a contradiction, and neither is
    something a later door can repair.
    """

    def _names(self, world, *stamped):
        return [
            entry["name"]
            for entry in tickets_pins.resolved_standards(stamped, **_overrides(world))
        ]

    def _refusal(self, world, *stamped):
        with self.assertRaises(packs_support.PackError) as raised:
            tickets_pins.resolved_standards(stamped, **_overrides(world))
        return raised.exception

    def test_a_chain_of_three_pins_three_digests_broad_to_narrow(self):
        with _rings() as world:
            _pack(world["lib"], CODE_PACK)
            _sheet(world["lib"], "javascript", "JS.", narrows=CODE_PACK)
            _sheet(world["lib"], "three-js", "3D.", narrows="javascript")

            entries = tickets_pins.resolved_standards(
                ["three-js"], **_overrides(world),
            )

            self.assertEqual(
                [CODE_PACK, "javascript", "three-js"],
                [entry["name"] for entry in entries],
            )
            self.assertEqual(
                [
                    tickets_pins.item_digest("pack", CODE_PACK, **_overrides(world)),
                    tickets_pins.item_digest("sheet", "javascript", **_overrides(world)),
                    tickets_pins.item_digest("sheet", "three-js", **_overrides(world)),
                ],
                [entry["digest"] for entry in entries],
            )

    def test_a_standard_named_twice_is_read_once_at_its_first_position(self):
        with _rings() as world:
            _pack(world["lib"], CODE_PACK)
            _sheet(world["lib"], "house", "House.", narrows=CODE_PACK)
            _sheet(world["lib"], "brief", "Brief.", narrows=CODE_PACK)

            self.assertEqual(
                [CODE_PACK, "house", "brief"], self._names(world, "house", "brief"),
            )
            self.assertEqual(
                [CODE_PACK, "house", "brief"],
                self._names(world, CODE_PACK, "house", CODE_PACK, "brief"),
            )

    def test_a_cycle_refuses_by_name(self):
        with _rings() as world:
            _sheet(world["lib"], "a", "A.", narrows="b")
            _sheet(world["lib"], "b", "B.", narrows="a")

            error = self._refusal(world, "a")

            self.assertEqual("standard-cycle", error.code)
            self.assertIn("a", error.detail)
            self.assertIn("b", error.detail)

    def test_a_ninth_hop_refuses_and_an_eighth_resolves(self):
        with _rings() as world:
            _pack(world["lib"], CODE_PACK)
            previous = CODE_PACK
            for level in range(1, 9):
                _sheet(world["lib"], f"n{level}", "level", narrows=previous)
                previous = f"n{level}"

            self.assertEqual(9, len(self._names(world, "n8")))

            _sheet(world["lib"], "n9", "one hop too far", narrows="n8")
            error = self._refusal(world, "n9")

            self.assertEqual("standard-depth", error.code)
            self.assertIn("8", error.detail)

    def test_a_parent_that_resolves_in_no_ring_refuses(self):
        with _rings() as world:
            _sheet(world["lib"], "orphan", "No parent.", narrows="nowhere")

            error = self._refusal(world, "orphan")

            self.assertEqual("standard-parent-unresolved", error.code)
            self.assertIn("nowhere", error.detail)
            self.assertIn("orphan", error.detail)

    def test_a_resolved_set_carrying_two_adapters_refuses(self):
        with _rings() as world:
            _pack(world["lib"], CODE_PACK)
            _pack(world["lib"], DOC_PACK, adapter="document-tree")

            error = self._refusal(world, CODE_PACK, DOC_PACK)

            self.assertEqual("standard-adapter-conflict", error.code)
            for fragment in (CODE_PACK, DOC_PACK, "git", "document-tree"):
                self.assertIn(fragment, error.detail)

    def test_a_resolved_set_carrying_no_adapter_refuses(self):
        with _rings() as world:
            _sheet(world["lib"], "bare", "No domain.", narrows=None)

            error = self._refusal(world, "bare")

            self.assertEqual("standard-adapter-missing", error.code)
            self.assertIn("bare", error.detail)


if __name__ == "__main__":  # pragma: no cover - direct invocation
    unittest.main()
