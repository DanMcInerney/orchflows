"""A second `--pin` inside one change grades against the committed pin.

`--pin` rewrites `tests/pins.json` in the working tree. The supersession
check reads that file back, so after one mid-change `--pin` the digest it
compares against is an intermediate no commit carries: there is no
`before` text to diff the T0 shape against, and the record it then demands
would cite a digest no reader can ever look up. The fallback is the digest
`git show HEAD:tests/pins.json` carries -- the last `before` a reader
shares with the author.

The fixture is a real repository because that is the seam: the check's
answer is a function of what HEAD carries, not of what the process
remembers writing.
"""

import json
import subprocess
import sys
import unittest

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_validator_cases.support import _IsolatedTree  # noqa: E402

CONTRACT = "work-item.md"
T0_FIELD = "\n- `mutant_field` — an unsuperseded T0 field.\n"
SECOND_T0_FIELD = "\n- `second_field` — a second unsuperseded T0 field.\n"
PROSE = "\nA prose clause that moves the digest and no named field.\n"


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _commit(root, *paths):
    """A fixture repository whose HEAD carries ``paths`` and nothing else.

    Auto-gc detaches and keeps writing .git/objects after the commit
    returns; the tempdir teardown then races it to ENOTEMPTY.
    """

    _git(root, "init")
    for key, value in (
        ("gc.auto", "0"),
        ("gc.autoDetach", "false"),
        ("user.email", "validator@example.invalid"),
        ("user.name", "Validator Test"),
    ):
        _git(root, "config", key, value)
    _git(root, "add", *paths)
    _git(root, "commit", "-m", "baseline")


class _RepinFixture(_IsolatedTree):
    def _append(self, text):
        with (self.tmp_path / "contracts" / CONTRACT).open("a", encoding="utf-8") as stream:
            stream.write(text)

    def _pinned(self):
        pins = (self.tmp_path / "tests" / "pins.json").read_text(encoding="utf-8")
        return json.loads(pins)[CONTRACT]


class RepinAgainstTheCommittedPinTest(_RepinFixture):
    """HEAD carries the pins file, so the committed digest is the `before`."""

    def setUp(self):
        super().setUp()
        _commit(self.tmp_path, ".")
        self.committed = self._pinned()

    def test_one_record_citing_the_committed_pin_covers_both_pins(self):
        self._append(T0_FIELD + f"\nT0 supersession record: sha256:{self.committed}.\n")
        first = self._run("--pin")
        self.assertEqual(0, first.returncode, first.stdout)
        self.assertNotEqual(self.committed, self._pinned())

        self._append(SECOND_T0_FIELD)
        second = self._run("--pin")

        self.assertEqual(0, second.returncode, second.stdout)

    def test_the_requirement_still_bites_and_names_the_committed_digest(self):
        """Can-fail for the case above: the fallback relaxes which digest
        the record must cite, never whether one is required."""

        self._append(PROSE)
        self.assertEqual(0, self._run("--pin").returncode)
        intermediate = self._pinned()

        self._append(T0_FIELD)
        result = self._run("--pin")

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(f"sha256:{self.committed}", result.stdout)
        self.assertNotIn(intermediate, result.stdout)

    def test_a_prose_only_change_needs_no_record_after_a_first_pin(self):
        self._append(PROSE)
        self.assertEqual(0, self._run("--pin").returncode)

        self._append("\nA second prose clause, still naming no field.\n")
        result = self._run("--pin")

        self.assertEqual(0, result.returncode, result.stdout)


class RepinWithoutACommittedPinsFileTest(_RepinFixture):
    """HEAD carries the contracts and no pins file: nothing to fall back to,
    so the recorded digest stays the one the record must cite."""

    def setUp(self):
        super().setUp()
        _commit(self.tmp_path, "contracts", "tools", "scripts")

    def test_the_recorded_digest_stays_the_cited_one(self):
        self._append(PROSE)
        self.assertEqual(0, self._run("--pin").returncode)
        intermediate = self._pinned()

        self._append(T0_FIELD)
        result = self._run("--pin")

        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn(f"sha256:{intermediate}", result.stdout)


if __name__ == "__main__":
    unittest.main()
