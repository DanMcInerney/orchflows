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
    # Forbidden in one clause and permitted in another is still forbidden.
    (["scratch/T1.txt"], [BOTH_WAYS], {BOTH_WAYS + " | scratch/T1.txt"}),
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
