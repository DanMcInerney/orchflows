"""The work-item contract's diet: pure shape, one owner per passage.

contracts/work-item.md states the ticket's shape. Every passage that
states a *procedure* over that shape belongs to the owner that runs the
procedure — the claim grader, the scheduler, the verification law, the
spec workflow. This module pins the ceiling that keeps the contract
shape-only, and pins each relocated passage to exactly one owner.

Half the table is still pending. Deleting the staleness timer, the
cut-reader staffing rule, or the successors prose from the contract
breaks assertions that live in tests/test_contracts_cases/work_item.py,
tests/test_contracts_cases/rules.py, and
tests/test_carriage_cases/verification_flow.py — files outside the write
scope of the item that authored this module. Those checks carry
``expectedFailure`` and name the successor that owns them, so the day the
successor lands the deletions they turn into unexpected successes and
this module fails until the markers come off.
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
LIFECYCLE = ROOT / "scripts" / "tickets_lifecycle.py"

#: The successor item that owns the still-pending half of the diet.
SUCCESSOR = "00-root.11"

#: contracts/work-item.md is shape, not procedure; the ceiling is what
#: makes a procedural passage cost something to leave here.
LINE_CEILING = 180

#: Each relocated passage: the markers that must have left the contract,
#: the owner that must carry them, and the markers proving it does.
RELOCATIONS = {
    "claim compare-and-swap": {
        "gone_from_contract": ("compare-and-swap", "portable grader"),
        "owner": LIFECYCLE,
        "owner_carries": ("compare-and-swap", "live claim"),
    },
    "successors ownership": {
        "gone_from_contract": ("`successors.md`", "sole writer"),
        "owner": SPEC,
        "owner_carries": ("`successors.md`", "sole writer"),
    },
    "staleness timer": {
        "gone_from_contract": ("staleness", "wall clock", "60 minutes"),
        "owner": FRONTIER,
        "owner_carries": ("wall clock", "60 minutes", "`## Result`"),
    },
    "cut-reader staffing": {
        "gone_from_contract": ("three or more", "cut checker", "advisory"),
        "owner": VERIFICATION,
        "owner_carries": ("three or more", "cut checker", "advisory"),
    },
}

#: The passages whose contract-side deletion has landed.
ABSENT_FROM_CONTRACT = ("claim compare-and-swap",)

#: The passages whose owner already carries them.
OWNED_ELSEWHERE = ("claim compare-and-swap", "successors ownership")

#: Markers no second prose surface may carry once the passage has moved.
SOLE_PROSE_OWNER = {
    "staleness": FRONTIER,
    "wall clock alone": FRONTIER,
    "cut checker": VERIFICATION,
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


class PendingDietTest(unittest.TestCase):
    """The half the successor owns; each check flips when it lands."""

    @unittest.expectedFailure
    def test_the_contract_holds_at_most_the_ceiling_in_non_empty_lines(self):
        """Pending 00-root.11: the ceiling needs the blocked deletions."""
        count = contract_line_count()
        self.assertLessEqual(
            count,
            LINE_CEILING,
            f"contracts/work-item.md holds {count} non-empty lines, over the "
            f"{LINE_CEILING}-line ceiling that keeps it pure shape",
        )

    @unittest.expectedFailure
    def test_the_contract_no_longer_states_the_blocked_passages(self):
        """Pending 00-root.11: deleting these breaks pins it also owns."""
        pending = [
            name for name in RELOCATIONS if name not in ABSENT_FROM_CONTRACT
        ]
        left = passages_left_in_contract(pending)
        self.assertEqual({}, left, f"still stated in the contract: {left}")

    @unittest.expectedFailure
    def test_the_blocked_passages_reach_their_named_owners(self):
        """Pending 00-root.11: orch-frontier and §10 must gain the text."""
        pending = [name for name in RELOCATIONS if name not in OWNED_ELSEWHERE]
        gaps = owners_missing_passage(pending)
        self.assertEqual({}, gaps, f"owner does not carry the passage: {gaps}")

    @unittest.expectedFailure
    def test_no_second_prose_surface_carries_a_relocated_marker(self):
        """Pending 00-root.11: the contract is still the second carrier."""
        drift = {
            marker: surfaces_carrying(marker)
            for marker, owner in SOLE_PROSE_OWNER.items()
            if surfaces_carrying(marker) != [owner.relative_to(ROOT).as_posix()]
        }
        self.assertEqual({}, drift, f"more than one prose owner: {drift}")


if __name__ == "__main__":
    unittest.main()
