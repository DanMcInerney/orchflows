"""A stamped standard and an applied skill are pinned, and the pin is verified.

The standard's hazard, on two more kinds: a ticket that carried only the *name*
of a standard or of an applied skill would resolve it to whatever bytes are
nearest at the moment it runs, so a ring that came to shadow it -- or an edit
under the seal -- would be a silent substitution. Every case here fires on
one half of the answer: the digest is taken at issue, and every later door
re-derives it and refuses the pair.

U0 stopped at the pin. U1 added the two doors that read a standard's *content*:
`standards:` decides whether the stamp is lawful at all, and the launch prompt
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
    standards_support, rings, rings_trust, state_root, tickets_admission, tickets_pins,
)
from scripts.tickets_format import _parse_frontmatter

from tests.test_ticket_callables import CODE_STANDARD, DOC_STANDARD, CallableSinkTest

STANDARD = "market-brief"
APPLIED_SKILL = "house-style"


def _narrowing(root: Path, name: str, body: str, narrows=None, standards=()) -> Path:
    """One narrowing manifest.

    `narrows` names the parent the chain walks to. `standards` is the field
    `narrows:` replaces, written only by the cases about the domain door
    that still reads it while an item can carry one.
    """

    path = root / "standards" / name / rings.MANIFESTS["standard"]
    path.parent.mkdir(parents=True, exist_ok=True)
    declared = f"narrows: {narrows}\n" if narrows else ""
    declared += ("standards: [" + ", ".join(standards) + "]\n") if standards else ""
    # Bytes, not text: a text write on Windows lands CRLF, and the digest
    # normalizes those away, so a CRLF fixture would hide a normalization
    # that stopped happening.
    path.write_bytes(
        f"---\nname: {name}\n{declared}---\n\n## Standard\n\n{body}\n".encode("utf-8")
    )
    return path


def _root(root: Path, name: str, adapter: str = "git") -> Path:
    """One root standard.

    Collapsed shape: one manifest, `adapter` in frontmatter, no cells table
    and no second file. The resolver refuses a manifest still carrying a
    `| Cell | Binding |` table, so a fixture that wrote one would exercise
    that refusal rather than the pin these cases are about.
    """

    path = root / "standards" / name / rings.MANIFESTS["standard"]
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

    def test_a_standard_resolves_nearest_first_across_project_home_and_lib(self):
        with _rings() as world:
            _narrowing(world["lib"], STANDARD, "lib")
            self.assertEqual(
                "lib", tickets_pins.resolved("standard", STANDARD, **_overrides(world))["ring"],
            )

            _narrowing(world["home"], STANDARD, "home")
            self.assertEqual(
                "home", tickets_pins.resolved("standard", STANDARD, **_overrides(world))["ring"],
            )

            _narrowing(world["project"] / ".orchflows", STANDARD, "project")
            rings_trust.grant(world["project"] / ".orchflows")
            self.assertEqual(
                "project", tickets_pins.resolved("standard", STANDARD, **_overrides(world))["ring"],
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
            _narrowing(world["lib"], STANDARD, "lib")
            far = tickets_pins.item_digest("standard", STANDARD, **_overrides(world))
            _narrowing(world["home"], STANDARD, "home")

            self.assertNotEqual(
                far, tickets_pins.item_digest("standard", STANDARD, **_overrides(world)),
            )

    def test_a_standards_digest_covers_every_file_in_its_directory(self):
        with _rings() as world:
            path = _narrowing(world["lib"], STANDARD, "lib")
            before = tickets_pins.item_digest("standard", STANDARD, **_overrides(world))

            (path.parent / "references.md").write_bytes(b"more\n")

            self.assertNotEqual(
                before, tickets_pins.item_digest("standard", STANDARD, **_overrides(world)),
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
            path = _narrowing(world["lib"], STANDARD, "lib")
            lf = tickets_pins.item_digest("standard", STANDARD, **_overrides(world))
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

            self.assertEqual(
                lf, tickets_pins.item_digest("standard", STANDARD, **_overrides(world)),
            )

    def test_the_drift_refusal_names_the_item_the_ring_and_both_digests(self):
        with _rings() as world:
            _narrowing(world["lib"], STANDARD, "lib")
            pinned = tickets_pins.item_digest("standard", STANDARD, **_overrides(world))
            _narrowing(world["home"], STANDARD, "home")
            current = tickets_pins.item_digest("standard", STANDARD, **_overrides(world))

            detail = tickets_pins.drift("standard", STANDARD, pinned, **_overrides(world))

            self.assertIsNotNone(detail)
            for fragment in (f"standard '{STANDARD}'", "home ring", pinned, current):
                self.assertIn(fragment, detail)

    def test_an_unresolvable_item_is_refused_by_name_rather_than_pinned(self):
        with _rings() as world:
            detail = tickets_pins.drift("standard", STANDARD, "sha256:" + "0" * 64, **_overrides(world))

            self.assertIn("cannot be pinned", str(detail))
            with self.assertRaises(tickets_pins.PinError) as raised:
                tickets_pins.item_digest("standard", STANDARD, **_overrides(world))
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
            _root(world["lib"], CODE_STANDARD)
            _narrowing(world["lib"], STANDARD, "lib", narrows=CODE_STANDARD)
            _narrowing(world["lib"], "html-dossier", "lib", narrows=CODE_STANDARD)

            fields, refusal = tickets_pins.pin_fields(
                ["html-dossier", STANDARD], None, **_overrides(world),
            )

            self.assertIsNone(refusal)
            self.assertEqual(
                [
                    (CODE_STANDARD, tickets_pins.item_digest(
                        "standard", CODE_STANDARD, **_overrides(world))),
                    ("html-dossier", tickets_pins.item_digest(
                        "standard", "html-dossier", **_overrides(world))),
                    (STANDARD, tickets_pins.item_digest(
                        "standard", STANDARD, **_overrides(world))),
                ],
                tickets_pins.standards_of(fields["standards"]),
            )

    def test_one_standard_stamped_twice_is_read_once_rather_than_refused(self):
        """The rule the duplicate refusal became: a name given twice is one
        level, at its first position, because a shared ancestor reached down
        two chains has to resolve without the caller pruning it first."""

        with _rings() as world:
            _root(world["lib"], CODE_STANDARD)
            _narrowing(world["lib"], STANDARD, "lib", narrows=CODE_STANDARD)

            fields, refusal = tickets_pins.pin_fields(
                [STANDARD, STANDARD], None, **_overrides(world),
            )

            self.assertIsNone(refusal)
            self.assertEqual(
                [CODE_STANDARD, STANDARD],
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
            _root(world["lib"], CODE_STANDARD)
            _narrowing(world["lib"], STANDARD, "lib", narrows=CODE_STANDARD)
            _skill(world["lib"], APPLIED_SKILL, "lib", sublayer="kernel")
            fields, _ = tickets_pins.pin_fields([STANDARD], APPLIED_SKILL, **self.overrides)

            self.assertEqual(set(), self._codes(fields))

    def test_a_narrowing_edited_under_the_seal_is_refused_at_the_door(self):
        with self._world() as world:
            _root(world["lib"], CODE_STANDARD)
            path = _narrowing(world["lib"], STANDARD, "lib", narrows=CODE_STANDARD)
            fields, _ = tickets_pins.pin_fields([STANDARD], None, **self.overrides)

            path.write_bytes(path.read_bytes() + b"one more clause\n")

            self.assertEqual({"standard-digest-mismatch"}, self._codes(fields))

    def test_a_root_edited_under_the_seal_is_refused_at_the_door(self):
        """The level the caller never named. A chain pins every level, so an
        edit to the root a narrowing reached is a refusal too -- otherwise
        the ancestry a child reads would be unsealed above its first hop."""

        with self._world() as world:
            path = _root(world["lib"], CODE_STANDARD)
            _narrowing(world["lib"], STANDARD, "lib", narrows=CODE_STANDARD)
            fields, _ = tickets_pins.pin_fields([STANDARD], None, **self.overrides)

            path.write_bytes(path.read_bytes() + b"\n<!-- a clause nobody sealed -->\n")

            self.assertEqual({"standard-digest-mismatch"}, self._codes(fields))

    def test_a_nearer_ring_shadowing_a_stamped_level_is_refused(self):
        with self._world() as world:
            _root(world["lib"], CODE_STANDARD)
            _narrowing(world["lib"], STANDARD, "lib", narrows=CODE_STANDARD)
            fields, _ = tickets_pins.pin_fields([STANDARD], None, **self.overrides)

            _narrowing(world["home"], STANDARD, "home", narrows=CODE_STANDARD)

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
                {"standard-pin-invalid"}, self._codes({"standards": [STANDARD]}),
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
        _narrowing(self.ring, STANDARD, "House brief shape.")
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
                "standard" if name == CODE_STANDARD else "standard", name,
            ))
            for name in names
        ]

    def test_a_stamped_do_pins_the_whole_chain_and_admits(self):
        self.callable(
            "do", "--standard", CODE_STANDARD, "--isolation", "required",
            "--standard", STANDARD, "--skill", APPLIED_SKILL,
        )

        data = _parse_frontmatter(self.ticket_text("B1"))
        self.assertEqual(
            self._chain(CODE_STANDARD, STANDARD), tickets_pins.standards_of(data["standards"]),
        )
        self.assertEqual(APPLIED_SKILL, data["skill"])
        self.assertEqual(
            tickets_pins.item_digest("skill", APPLIED_SKILL), data["skill_digest"],
        )
        self.assertEqual(set(), self._codes("B1"))

    def test_a_stamped_judge_pins_the_same_way(self):
        self.callable(
            "judge", "--standard", CODE_STANDARD, "--isolation", "none",
            "--artifacts", "git:" + "a" * 40, "--standard", STANDARD,
        )

        data = _parse_frontmatter(self.ticket_text("B1"))
        self.assertEqual(
            self._chain(CODE_STANDARD, STANDARD), tickets_pins.standards_of(data["standards"]),
        )
        self.assertNotIn("skill", data)
        self.assertEqual(set(), self._codes("B1"))

    def test_a_narrowing_that_moves_after_the_mint_refuses_at_admission(self):
        self.callable(
            "do", "--standard", CODE_STANDARD, "--isolation", "required", "--standard", STANDARD,
        )

        manifest = self.ring / "standards" / STANDARD / rings.MANIFESTS["standard"]
        manifest.write_bytes(manifest.read_bytes() + b"a clause nobody sealed\n")

        self.assertIn("standard-digest-mismatch", self._codes("B1"))

    def test_the_stamped_pins_are_sealed_with_the_rest_of_the_assignment(self):
        self.callable(
            "do", "--standard", CODE_STANDARD, "--isolation", "required", "--standard", STANDARD,
        )
        plain = self.callable("do", "--standard", CODE_STANDARD, "--isolation", "required")

        self.assertNotEqual(
            _parse_frontmatter(self.ticket_text("B1"))["assignment_seal"],
            _parse_frontmatter(self.ticket_text(plain["do"]["id"]))["assignment_seal"],
        )

    def test_an_unresolvable_standard_is_refused_before_the_run_exists(self):
        answer = self.callable(
            "do", "--standard", CODE_STANDARD, "--isolation", "required",
            "--standard", "no-such-standard", expect_error=True,
        )

        self.assertIn("no-such-standard", answer["error"])
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

        plain = self.callable("do", "--standard", CODE_STANDARD, "--isolation", "required")

        self.assertEqual(
            [
                "id", "run", "status", "admission", "executor", "standards",
                "isolation", "bound",
                "root_generation", "cut_generation", "assignment_seal",
                "dispatch_v1", "workspace_branch", "workspace_baseline",
            ],
            list(_parse_frontmatter(self.ticket_text(plain["do"]["id"]))),
        )

    def test_a_root_only_do_prompt_names_no_further_standard(self):
        """U1's half of the same boundary, on the prompt rather than the
        frontmatter: a second standard's line leaking onto a ticket that
        stamped one would be a standard the child was never assigned. The
        anchor is `Read the standard `, the opener of the per-standard line,
        because the word alone now appears in ordinary prompt prose."""

        plain = self.callable("do", "--standard", CODE_STANDARD, "--isolation", "required")

        self.assertEqual(
            [],
            [
                line for line in self.prompt(plain).splitlines()
                if line.startswith("Read the standard ")
            ],
        )

    def _standard_line(self, answer: dict) -> str:
        """The one standard line this launch prompt carries."""

        lines = [
            line for line in self.prompt(answer).splitlines()
            if line.startswith("Read the standard ")
        ]
        self.assertEqual(1, len(lines), self.prompt(answer))
        return lines[0]

    def _resolved(self, name: str):
        record = tickets_pins.resolved("standard", name)
        return record["path"], str(record["digest"]).split(":", 1)[-1]

    def test_a_stamped_do_prompt_carries_the_standard_line_verbatim(self):
        """The maker's wording: path, pinned digest, and both halves of the
        tighten-only rule pointed at the `## Lens` entry its kind resolved."""

        answer = self.callable(
            "do", "--standard", CODE_STANDARD, "--isolation", "required", "--standard", STANDARD,
        )
        path, digest = self._resolved(STANDARD)

        self.assertEqual(
            f"Read the standard `{STANDARD}` at {path} whole (sha256 {digest}). Its "
            "`## Making` binds your making; its `## Lens` `### git` entry adds "
            "to the standard's `### git` and never loosens it.",
            self._standard_line(answer),
        )

    def test_a_stamped_judge_prompt_carries_the_judges_standard_line_verbatim(self):
        """The same three facts, turned toward the reader who reports the
        conflict rather than the one who would have to build to it."""

        answer = self.callable(
            "judge", "--standard", CODE_STANDARD, "--isolation", "none",
            "--artifacts", "git:" + "a" * 40, "--standard", STANDARD,
        )
        path, digest = self._resolved(STANDARD)

        self.assertEqual(
            f"Read the standard `{STANDARD}` at {path} whole (sha256 {digest}). Its "
            "`## Lens` `### git` entry adds criteria you check beside the "
            "standard's; where it loosens the standard's, the standard wins and you "
            "report the conflict as a `standard-defect` finding.",
            self._standard_line(answer),
        )

    def test_every_stamped_standard_gets_its_own_line(self):
        """Two stamps, two lines: one standard's line naming another's digest
        would be the substitution the pin exists to prevent."""

        second = "house-brief"
        _narrowing(self.ring, second, "The second narrowing.")
        answer = self.callable(
            "do", "--standard", CODE_STANDARD, "--isolation", "required",
            "--standard", STANDARD, "--standard", second,
        )

        lines = [
            line for line in self.prompt(answer).splitlines()
            if line.startswith("Read the standard ")
        ]
        self.assertEqual(2, len(lines))
        for name in (STANDARD, second):
            path, digest = self._resolved(name)
            self.assertTrue(
                any(f"`{name}` at {path} whole (sha256 {digest})" in line for line in lines),
                lines,
            )

    def test_a_narrowing_off_its_declared_domain_refuses(self):
        """The domain door, under the spelling an item can still carry. A
        narrowing tightens the standard it was written against; stamped beside
        another domain it is criteria for one it never read, so the callable
        never opens."""

        _narrowing(self.ring, "doc-only", "Prose shape.", standards=("orch-content",))

        answer = self.callable(
            "do", "--standard", CODE_STANDARD, "--isolation", "required",
            "--standard", "doc-only", expect_error=True,
        )

        self.assertIn("orch-content", answer["error"])
        self.assertIn(CODE_STANDARD, answer["error"])
        self.assertFalse(self.run_dir().exists())

    def test_a_narrowing_off_its_domain_refuses_through_narrows_too(self):
        """The same door under the spelling that replaces it: naming a
        parent in another domain puts two adapters in one resolved set,
        which is the contradiction rather than a preference."""

        _narrowing(self.ring, "doc-narrowing", "Prose shape.", narrows="orch-content")

        answer = self.callable(
            "do", "--standard", CODE_STANDARD, "--isolation", "required",
            "--standard", "doc-narrowing", expect_error=True,
        )

        self.assertIn("orch-content", answer["error"])
        self.assertIn(CODE_STANDARD, answer["error"])
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
        with self.assertRaises(standards_support.StandardError) as raised:
            tickets_pins.resolved_standards(stamped, **_overrides(world))
        return raised.exception

    def test_a_chain_of_three_pins_three_digests_broad_to_narrow(self):
        with _rings() as world:
            _root(world["lib"], CODE_STANDARD)
            _narrowing(world["lib"], "javascript", "JS.", narrows=CODE_STANDARD)
            _narrowing(world["lib"], "three-js", "3D.", narrows="javascript")

            entries = tickets_pins.resolved_standards(
                ["three-js"], **_overrides(world),
            )

            self.assertEqual(
                [CODE_STANDARD, "javascript", "three-js"],
                [entry["name"] for entry in entries],
            )
            self.assertEqual(
                [
                    tickets_pins.item_digest("standard", CODE_STANDARD, **_overrides(world)),
                    tickets_pins.item_digest("standard", "javascript", **_overrides(world)),
                    tickets_pins.item_digest("standard", "three-js", **_overrides(world)),
                ],
                [entry["digest"] for entry in entries],
            )

    def test_a_standard_named_twice_is_read_once_at_its_first_position(self):
        with _rings() as world:
            _root(world["lib"], CODE_STANDARD)
            _narrowing(world["lib"], "house", "House.", narrows=CODE_STANDARD)
            _narrowing(world["lib"], "brief", "Brief.", narrows=CODE_STANDARD)

            self.assertEqual(
                [CODE_STANDARD, "house", "brief"], self._names(world, "house", "brief"),
            )
            self.assertEqual(
                [CODE_STANDARD, "house", "brief"],
                self._names(world, CODE_STANDARD, "house", CODE_STANDARD, "brief"),
            )

    def test_a_cycle_refuses_by_name(self):
        with _rings() as world:
            _narrowing(world["lib"], "a", "A.", narrows="b")
            _narrowing(world["lib"], "b", "B.", narrows="a")

            error = self._refusal(world, "a")

            self.assertEqual("standard-cycle", error.code)
            self.assertIn("a", error.detail)
            self.assertIn("b", error.detail)

    def test_a_ninth_hop_refuses_and_an_eighth_resolves(self):
        with _rings() as world:
            _root(world["lib"], CODE_STANDARD)
            previous = CODE_STANDARD
            for level in range(1, 9):
                _narrowing(world["lib"], f"n{level}", "level", narrows=previous)
                previous = f"n{level}"

            self.assertEqual(9, len(self._names(world, "n8")))

            _narrowing(world["lib"], "n9", "one hop too far", narrows="n8")
            error = self._refusal(world, "n9")

            self.assertEqual("standard-depth", error.code)
            self.assertIn("8", error.detail)

    def test_a_parent_that_resolves_in_no_ring_refuses(self):
        with _rings() as world:
            _narrowing(world["lib"], "orphan", "No parent.", narrows="nowhere")

            error = self._refusal(world, "orphan")

            self.assertEqual("standard-parent-unresolved", error.code)
            self.assertIn("nowhere", error.detail)
            self.assertIn("orphan", error.detail)

    def test_a_resolved_set_carrying_two_adapters_refuses(self):
        with _rings() as world:
            _root(world["lib"], CODE_STANDARD)
            _root(world["lib"], DOC_STANDARD, adapter="document-tree")

            error = self._refusal(world, CODE_STANDARD, DOC_STANDARD)

            self.assertEqual("standard-adapter-conflict", error.code)
            for fragment in (CODE_STANDARD, DOC_STANDARD, "git", "document-tree"):
                self.assertIn(fragment, error.detail)

    def test_a_resolved_set_carrying_no_adapter_refuses(self):
        with _rings() as world:
            _narrowing(world["lib"], "bare", "No domain.", narrows=None)

            error = self._refusal(world, "bare")

            self.assertEqual("standard-adapter-missing", error.code)
            self.assertIn("bare", error.detail)


if __name__ == "__main__":  # pragma: no cover - direct invocation
    unittest.main()
