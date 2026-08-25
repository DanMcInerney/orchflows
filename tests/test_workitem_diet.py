"""The work-item contract's diet: pure shape, one owner per passage.

contracts/work-item.md states the ticket's shape. Every passage that
states a *procedure* over that shape belongs to the owner that runs the
procedure — the claim grader, the scheduler, the verification law, the
spec workflow. This module pins the ceiling that keeps the contract
shape-only, and pins each relocated passage to exactly one owner.

The table is complete. Half of it landed with the item that authored
this module; the other half — the staleness timer, the cut-reader
staffing rule, the successors prose, and the line ceiling itself —
landed with 00-root.11, which also amended the assertions in
tests/test_contracts_cases/work_item.py,
tests/test_contracts_cases/rules.py, and
tests/test_carriage_cases/verification_flow.py that pinned those
passages where they were. No check here is ``expectedFailure``: every
one of them fails if the contract takes a relocated passage back.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WORK_ITEM = ROOT / "contracts" / "work-item.md"
PACK_SIGNATURE = ROOT / "contracts" / "pack-signature.md"
VERIFICATION = ROOT / "rules" / "verification.md"
FRONTIER = ROOT / "skills" / "engines" / "orch-frontier" / "SKILL.md"
SPEC = ROOT / "skills" / "workflows" / "orch-spec" / "SKILL.md"
PROJECT = ROOT / "scripts" / "tickets_project.py"
BOUND = ROOT / "scripts" / "tickets_bound.py"

#: contracts/work-item.md is shape, not procedure; the ceiling is what
#: makes a procedural passage cost something to leave here.
LINE_CEILING = 180

#: Each relocated passage: the markers that must have left the contract,
#: the owner that must carry them, and the markers proving it does.
RELOCATIONS = {
    # The claim-admission seam left tickets_lifecycle.py for tickets_project.py,
    # where the project binding it now grades also lives. The owner moves with
    # the passage: `_admit_ready_cas` still compare-and-swaps in the lifecycle
    # module, but it swaps into `ready` and not into a live claim, so naming it
    # here would keep the row green off a phrase that no longer describes it.
    "claim compare-and-swap": {
        "gone_from_contract": ("compare-and-swap", "portable grader"),
        "owner": PROJECT,
        "owner_carries": ("compare-and-swap", "live claim"),
    },
    "successors ownership": {
        "gone_from_contract": ("`successors.md`", "sole writer"),
        "owner": SPEC,
        "owner_carries": ("`successors.md`", "sole writer"),
    },
    # The cut named skills/engines/orch-frontier as this passage's owner;
    # orch-frontier states no default and no artifact-motion rule, and sits
    # at its word budget. `scripts/tickets_bound.py` is where the 60-minute
    # substitution and the motion measurement are implemented, so it is the
    # owner that can carry the sentence truthfully.
    "staleness timer": {
        "gone_from_contract": ("staleness", "wall clock", "60 minutes"),
        "owner": BOUND,
        "owner_carries": ("wall clock", "60 minutes", "`## Result`"),
    },
    # The contract keeps a pointer at rules/verification.md §10, which owns
    # the root cut reader as §10's distinct exception; the threshold that
    # staffs one is orch-frontier's and stays there.
    "cut-reader staffing": {
        "gone_from_contract": ("three or more", "cut checker", "advisory"),
        "owner": FRONTIER,
        "owner_carries": ("three or more", "cut reader", "advisory"),
    },
}

#: Every passage's contract-side deletion has landed.
ABSENT_FROM_CONTRACT = tuple(RELOCATIONS)

#: Every passage's owner carries it.
OWNED_ELSEWHERE = tuple(RELOCATIONS)

#: Markers no second prose surface may carry once the passage has moved.
#: The staleness timer's owner is a script, so its sole-owner check is the
#: one below rather than a row here: `prose_surfaces()` reads markdown.
SOLE_PROSE_OWNER = {
    "after a cutcheck advisory": FRONTIER,
    "three or more": FRONTIER,
    "is that artifact's sole writer": SPEC,
}

#: The timer's markers, which no prose surface may carry at all now that
#: `scripts/tickets_bound.py` states them.
CODE_OWNED_MARKERS = {
    "staleness": BOUND,
    "wall clock": BOUND,
    "60 minutes": BOUND,
}

#: The sentence the signature used to copy; the contract alone states it.
SHARED_T0_SENTENCE = "updates its focused contract checks and re-pins the"


def non_empty(text):
    """The contract's own budget unit: lines carrying content."""
    return [line for line in text.splitlines() if line.strip()]


def flat(text):
    """Whitespace collapsed, so a wrapped clause still matches."""
    return re.sub(r"\s+", " ", text)


def missing_markers(text, markers):
    """Markers the text does not carry, in the order given."""
    haystack = flat(text)
    return [marker for marker in markers if marker not in haystack]


def present_markers(text, markers):
    """Markers the text still carries, in the order given."""
    haystack = flat(text)
    return [marker for marker in markers if marker in haystack]


def prose_surfaces():
    """Every library prose file a passage could be duplicated into."""
    paths = []
    for relative in ("contracts", "rules", "docs"):
        paths.extend(sorted((ROOT / relative).glob("*.md")))
    paths.extend(sorted((ROOT / "skills").rglob("*.md")))
    return paths


def contract_line_count():
    return len(non_empty(WORK_ITEM.read_text(encoding="utf-8")))


def passages_left_in_contract(names):
    """The markers each named passage still states inside the contract."""
    text = WORK_ITEM.read_text(encoding="utf-8")
    return {
        name: present_markers(text, RELOCATIONS[name]["gone_from_contract"])
        for name in names
        if present_markers(text, RELOCATIONS[name]["gone_from_contract"])
    }


def owners_missing_passage(names):
    """The markers each named owner does not yet carry."""
    gaps = {}
    for name in names:
        spec = RELOCATIONS[name]
        absent = missing_markers(
            spec["owner"].read_text(encoding="utf-8"), spec["owner_carries"]
        )
        if absent:
            gaps[name] = absent
    return gaps


def surfaces_carrying(marker):
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in prose_surfaces()
        if marker in flat(path.read_text(encoding="utf-8"))
    )


class DietReaderTest(unittest.TestCase):
    """The can-fail direction: each reader reacts to the thing it reads."""

    def test_the_line_counter_separates_over_from_under(self):
        over = "\n".join(f"line {n}" for n in range(LINE_CEILING + 1))
        under = "\n\n".join(f"line {n}" for n in range(LINE_CEILING))
        self.assertGreater(len(non_empty(over)), LINE_CEILING)
        self.assertLessEqual(len(non_empty(under)), LINE_CEILING)

    def test_the_marker_readers_separate_a_stated_passage_from_a_moved_one(self):
        for name, spec in RELOCATIONS.items():
            with self.subTest(passage=name):
                stated = " ".join(spec["gone_from_contract"])
                self.assertEqual(
                    list(spec["gone_from_contract"]),
                    present_markers(stated, spec["gone_from_contract"]),
                )
                self.assertEqual([], present_markers("", spec["gone_from_contract"]))
                self.assertEqual(
                    list(spec["owner_carries"]),
                    missing_markers("", spec["owner_carries"]),
                )


class LandedRelocationTest(unittest.TestCase):
    """The passages whose move is complete keep exactly one owner."""

    def test_the_contract_no_longer_states_them(self):
        left = passages_left_in_contract(ABSENT_FROM_CONTRACT)
        self.assertEqual(
            {},
            left,
            f"contracts/work-item.md still states: {left}",
        )

    def test_their_named_owners_carry_them(self):
        gaps = owners_missing_passage(OWNED_ELSEWHERE)
        self.assertEqual(
            {},
            gaps,
            f"a relocated passage never reached its owner: {gaps}",
        )


class SharedT0NoteTest(unittest.TestCase):
    """One T0-supersession note, cited by the signature, never copied."""

    def signature_note(self):
        text = PACK_SIGNATURE.read_text(encoding="utf-8")
        self.assertIn("## T0 supersession", text)
        return flat(text.split("## T0 supersession", 1)[1])

    def test_the_signature_cites_the_contract_note_instead_of_copying_it(self):
        note = self.signature_note()
        self.assertIn(
            "[work-item.md](work-item.md)",
            note,
            "pack-signature.md's T0 note does not cite the contract that "
            "owns the note",
        )
        self.assertNotIn(
            SHARED_T0_SENTENCE,
            note,
            "pack-signature.md still copies work-item.md's T0 sentence "
            "instead of sharing the one note",
        )

    def test_the_contract_still_owns_the_shared_note(self):
        raw = WORK_ITEM.read_text(encoding="utf-8")
        self.assertIn("## T0 supersession", raw)
        for token in (SHARED_T0_SENTENCE, "tests/pins.json"):
            with self.subTest(token=token):
                self.assertIn(token, flat(raw))


#: The close law's tokens, which must sit inside the bullet that owns it.
CLOSE_LAW_TOKENS = (
    "running each criterion's oracle once",
    "UNVERIFIED alone",
    "the one outside execution arrives per §10",
)


def completion_test_bullet(text):
    """The `## Completion test` bullet alone, not the whole contract.

    The close law is that bullet's. Counting its tokens file-wide would
    stay green if they migrated to any other bullet, so the guard slices
    the bullet out first and counts only inside it.
    """
    start = text.index("- `## Completion test`")
    tail = text[start + 1 :]
    end = tail.find("\n- `")
    return flat(tail if end == -1 else tail[:end])


class OneOutsideExecutionLawTest(unittest.TestCase):
    """The diet never costs the close law the contract owns."""

    def test_the_bullet_slice_stops_at_the_next_bullet(self):
        """Can-fail: the slice must exclude a token placed outside it."""
        sliced = completion_test_bullet(
            "- `## Completion test` — UNVERIFIED alone\n"
            "- `## Return fields` — UNVERIFIED alone\n"
        )
        self.assertEqual(1, sliced.count("UNVERIFIED alone"))

    def test_the_completion_test_bullet_keeps_the_one_outside_execution_law(self):
        raw = WORK_ITEM.read_text(encoding="utf-8")
        bullet = completion_test_bullet(raw)
        whole = flat(raw)
        for token in CLOSE_LAW_TOKENS:
            with self.subTest(token=token):
                self.assertEqual(
                    1,
                    bullet.count(token),
                    "contracts/work-item.md's `## Completion test` bullet must "
                    f"state the close law's {token!r} exactly once",
                )
                self.assertEqual(
                    1,
                    whole.count(token),
                    f"the close law's {token!r} is stated outside its bullet "
                    "as well; the bullet is its one owner",
                )


class CompletedDietTest(unittest.TestCase):
    """The whole table, live: the ceiling and one owner per passage."""

    def test_the_contract_holds_at_most_the_ceiling_in_non_empty_lines(self):
        count = contract_line_count()
        self.assertLessEqual(
            count,
            LINE_CEILING,
            f"contracts/work-item.md holds {count} non-empty lines, over the "
            f"{LINE_CEILING}-line ceiling that keeps it pure shape",
        )

    def test_the_contract_states_none_of_the_relocated_passages(self):
        left = passages_left_in_contract(RELOCATIONS)
        self.assertEqual({}, left, f"still stated in the contract: {left}")

    def test_every_passage_reaches_its_named_owner(self):
        gaps = owners_missing_passage(RELOCATIONS)
        self.assertEqual({}, gaps, f"owner does not carry the passage: {gaps}")

    def test_no_second_prose_surface_carries_a_relocated_marker(self):
        drift = {
            marker: surfaces_carrying(marker)
            for marker, owner in SOLE_PROSE_OWNER.items()
            if surfaces_carrying(marker) != [owner.relative_to(ROOT).as_posix()]
        }
        self.assertEqual({}, drift, f"more than one prose owner: {drift}")

    def test_no_prose_surface_carries_a_marker_a_script_now_owns(self):
        """The lease timer left the library's prose entirely."""
        drift = {
            marker: surfaces_carrying(marker)
            for marker in CODE_OWNED_MARKERS
            if surfaces_carrying(marker)
        }
        self.assertEqual({}, drift, f"prose still states the timer: {drift}")
        for marker, owner in CODE_OWNED_MARKERS.items():
            with self.subTest(marker=marker):
                self.assertIn(
                    marker,
                    flat(owner.read_text(encoding="utf-8")),
                    f"{owner.name} does not state {marker!r}",
                )


if __name__ == "__main__":
    unittest.main()
