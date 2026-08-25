"""Family 3's one law, asked of both of its hosts by name.

The agreement pin in ``tests.test_tickets_lint`` asks whether the two readers
say the same thing. That question alone cannot see a defect they share -- it
was green for a year while `./scratch/T1.txt` escaped both of them, because
escaping both is agreement. So every case here states the set it expects and
asserts it against each reader separately; agreement is then a consequence
worth checking rather than the whole of the evidence.

The architecture map forbids this family importing cutcheck, so the reading is
written twice. Two readers, one law: a case that greens one and reds the other
is the drift these cases exist to catch.
"""

from scripts import cutcheck_scope, tickets_lint

import unittest


def _readings(scope, excluded):
    """What each reader reports as a scope contradiction, as two sets."""
    data = {"write_scope": list(scope), "excluded_actions": list(excluded)}
    theirs = {
        detail
        for code, detail in cutcheck_scope._scope_closure(data, "")
        if code == cutcheck_scope.SCOPE_CONTRADICTION
    }
    mine = {
        finding["message"].split(": ", 1)[1]
        for finding in tickets_lint._contradiction_findings(data)
        if finding["code"] == "scope-contradiction"
    }
    return theirs, mine


PROVISO = "Editing a proposal file in the sink with tests/pins.json re-pinned"
OWNED = "The manifest is the join's act once tests/pins.json is re-pinned"
BOTH_WAYS = "never write scratch/T1.txt, even with scratch/T1.txt re-pinned"
# The two corrections have to compose. The token reader hands `_prohibits` the
# *plain* spelling while the action keeps its own, so a proviso written `./x`
# is looked up at an index past the `./` and the clause in front of it reads
# `with ./` -- no marker, and the false positive this unit removed comes back
# for exactly the paths the other half of the unit taught it to fold.
DOT_PROVISO = "Editing a proposal file in the sink with ./tests/pins.json re-pinned"
# Permitted first and forbidden second: the ordering that makes the scan walk
# past an occurrence rather than answer on it. `BOTH_WAYS` forbids first and so
# answers on the first occurrence, leaving the walk itself unasked-for.
PERMIT_FIRST = "with scratch/T1.txt re-pinned, never write scratch/T1.txt"
# (write_scope, excluded_actions, the contradictions this pair states)
FAMILY_3_CASES = (
    # A proviso names a path the item *may* write in order to act. Read as a
    # prohibition it contradicts the grant the ticket never contradicted --
    # the live false positive, at exit 1 by design and with no fix flag.
    (["scripts/a.py", "tests/pins.json"], [PROVISO], set()),
    (["tests/pins.json"], [OWNED], set()),
    # The path in front of the proviso is still the prohibited one.
    (["scratch/T1.txt"], ["never write scratch/T1.txt with approval recorded"],
     {"never write scratch/T1.txt with approval recorded | scratch/T1.txt"}),
    # Forbidden in one clause and permitted in another is still forbidden --
    # in either order. Forbidden-second is the one that has to walk.
    (["scratch/T1.txt"], [BOTH_WAYS], {BOTH_WAYS + " | scratch/T1.txt"}),
    (["scratch/T1.txt"], [PERMIT_FIRST], {PERMIT_FIRST + " | scratch/T1.txt"}),
    # A proviso is a proviso in either spelling of its path.
    (["tests/pins.json"], [DOT_PROVISO], set()),
    # `./x` and `x` are one path, from either side of the comparison. Both of
    # these were silently clean: a real contradiction neither reader could see.
    (["scratch/T1.txt"], ["never write ./scratch/T1.txt"],
     {"never write ./scratch/T1.txt | scratch/T1.txt"}),
    (["./scratch/T1.txt"], ["never write scratch/T1.txt"],
     {"never write scratch/T1.txt | ./scratch/T1.txt"}),
    (["scratch/"], ["never write ./scratch/T1.txt"],
     {"never write ./scratch/T1.txt | scratch/"}),
    # Unchanged by either correction: the plain contradiction, and a grant the
    # exclusion never reaches.
    (["scratch/T1.txt"], ["never write scratch/T1.txt"],
     {"never write scratch/T1.txt | scratch/T1.txt"}),
    (["scratch/T1.txt"], ["never write docs/other.md"], set()),
    (["scratch/T1.txt"], ["vcs.push", "vcs.integrate"], set()),
)


class Family3OneLawTest(unittest.TestCase):
    """Both hosts of family 3's reading, each asked for its own answer."""

    def test_each_reader_reports_exactly_the_stated_contradictions(self):
        for scope, excluded, expected in FAMILY_3_CASES:
            theirs, mine = _readings(scope, excluded)
            self.assertEqual(expected, theirs, f"cutcheck: {excluded} vs {scope}")
            self.assertEqual(expected, mine, f"lint: {excluded} vs {scope}")

    def test_the_two_readers_agree_case_by_case(self):
        """A consequence of the above, and the drift alarm if one is edited alone."""
        for scope, excluded, _ in FAMILY_3_CASES:
            theirs, mine = _readings(scope, excluded)
            self.assertEqual(theirs, mine, f"{excluded} vs {scope}")

    def test_a_proviso_is_read_by_the_clause_and_not_by_the_sentence(self):
        """Adjacency, not presence: the marker has to stand in front of the path."""
        self.assertFalse(cutcheck_scope._prohibits(PROVISO, "tests/pins.json"))
        self.assertFalse(tickets_lint._prohibits(PROVISO, "tests/pins.json"))
        far = "with the join's ruling recorded, never write tests/pins.json"
        self.assertTrue(cutcheck_scope._prohibits(far, "tests/pins.json"))
        self.assertTrue(tickets_lint._prohibits(far, "tests/pins.json"))

    def test_a_dot_slash_write_is_covered_by_the_grant_it_names(self):
        """The write half of the same escape: cutcheck's prose reader.

        `lint` has no prose write reader, so this half has one host and the
        agreement pin has nothing to say about it.
        """
        data = {"write_scope": ["scratch/T1.txt"], "excluded_actions": []}
        self.assertEqual(
            [], cutcheck_scope._scope_closure(data, "The item writes ./scratch/T1.txt."),
        )
        self.assertEqual(
            [(cutcheck_scope.UNSCOPED_WRITE, "docs/other.md")],
            cutcheck_scope._scope_closure(data, "The item writes ./docs/other.md."),
        )

    def test_the_plain_spelling_drops_only_a_leading_dot_slash(self):
        for reader in (cutcheck_scope, tickets_lint):
            self.assertEqual("scratch/T1.txt", reader._plain("./scratch/T1.txt"))
            self.assertEqual("scratch/T1.txt", reader._plain("././scratch/T1.txt"))
            self.assertEqual("scratch/T1.txt", reader._plain("scratch/T1.txt"))
            self.assertEqual("a/./b.txt", reader._plain("a/./b.txt"))
            self.assertEqual("../outside.txt", reader._plain("../outside.txt"))

    def test_every_permitting_marker_is_read_by_both_readers(self):
        """The vocabulary case by case, not just the two the cases happen to use.

        Cut to `with|once` in both readers, every other case here stays green:
        four of the six words were carried by no oracle at all.
        """
        for word in ("with", "once", "after", "provided", "unless", "except"):
            action = "The join acts %s tests/pins.json is re-pinned" % word
            for reader in (cutcheck_scope, tickets_lint):
                self.assertFalse(reader._prohibits(action, "tests/pins.json"),
                                 f"{reader.__name__}: {word!r} is a proviso marker")
        plain = "The join acts before tests/pins.json is re-pinned"
        for reader in (cutcheck_scope, tickets_lint):
            self.assertTrue(reader._prohibits(plain, "tests/pins.json"),
                            f"{reader.__name__}: a non-marker permits nothing")

    def test_a_marker_inside_a_longer_word_is_not_a_marker(self):
        """`\\b` and the window at once: the window may not slice a word open.

        `herewith` carries `with` and permits nothing. Read through a window
        too short to reach the `here`, it becomes one -- which is the only
        direction in which `PERMISSION_WINDOW`'s value is load-bearing, the
        pattern being anchored to the path's own edge.
        """
        action = "The join acts herewith tests/pins.json unresolved"
        for reader in (cutcheck_scope, tickets_lint):
            self.assertTrue(reader._prohibits(action, "tests/pins.json"),
                            f"{reader.__name__}: 'herewith' is not 'with'")

    def test_the_two_readers_state_one_vocabulary_and_one_window(self):
        """The law is written twice, so its two spellings are pinned equal.

        The agreement cases compare what the readers *say*; they cannot see a
        word one reader knows and the other does not, because no case names
        it. Divergence here is the drift the whole family is against, and
        cutcheck spells the window as an alias of a constant this file does
        not own while lint spells it as a literal -- so the two can part
        without either being edited.
        """
        self.assertEqual(cutcheck_scope.PERMISSION_RE.pattern,
                         tickets_lint.PERMISSION_RE.pattern)
        self.assertEqual(cutcheck_scope.PERMISSION_RE.flags,
                         tickets_lint.PERMISSION_RE.flags)
        self.assertEqual(cutcheck_scope.PERMISSION_WINDOW,
                         tickets_lint.PERMISSION_WINDOW)
