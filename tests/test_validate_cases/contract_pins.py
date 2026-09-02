"""The T0 contract pin: a digest of the contract, not of its bytes' shape.

`compute_pins` hashed raw bytes, and the tree stores LF
(`.gitattributes`), so a working copy a Windows tool rewrote as CRLF
pinned a digest that host alone could reproduce: `--pin` green where it
ran, `T0 contract changed` on every CI leg, and five test modules red
behind it. The guard whose whole job is to report a changed contract
reported one that had not changed.

Both halves are pinned here -- the endings do not move the digest, and
real content still does -- in their own module, because
`validator_ownership.py` sits four lines under the source ceiling.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from tests._repo_root import ROOT
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.validate_support.lint import compute_pins  # noqa: E402

LF = bytes((10,))
CRLF = bytes((13, 10))
CONTRACT = b"# Sample" + LF + LF + b"One clause the pin covers." + LF


class ContractPinIsNewlineInsensitiveTest(unittest.TestCase):
    def pin_of(self, tmp, text):
        """The digest `compute_pins` gives a contracts directory holding
        exactly ``text``. The directory is a parameter rather than a
        patched global: a test that mutates module state owes the serial
        manifest a restoration, and this one has nothing to restore."""

        contracts = Path(tmp) / "contracts"
        contracts.mkdir()
        (contracts / "sample.md").write_bytes(text)
        return compute_pins(contracts)["sample.md"]

    def test_crlf_and_lf_pin_the_same_contract(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            self.assertEqual(
                self.pin_of(one, CONTRACT),
                self.pin_of(two, CONTRACT.replace(LF, CRLF)),
                "the same contract pins two digests depending on the host "
                "that last wrote it, which is the shape that reddened CI",
            )

    def test_a_changed_clause_still_moves_the_pin(self):
        """Can-fail: normalizing must not flatten the check itself."""

        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            self.assertNotEqual(
                self.pin_of(one, CONTRACT),
                self.pin_of(two, CONTRACT.replace(b"One", b"Two")),
            )


if __name__ == "__main__":
    unittest.main()
