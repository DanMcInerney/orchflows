"""Compatibility seam for the partitioned benchmaker regression tests.

It also owns the one case that must not live beside the scan it exercises:
`tests/test_benchmaker_cases/retirement.py` is at the source-size ceiling.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.test_benchmaker_cases import retirement
from tests.test_benchmaker_cases.fixture import TestBenchmarkFixture
from tests.test_benchmaker_cases.protocol import TestCanonicalBenchmaker
from tests.test_benchmaker_cases.retirement import TestCanonicalSurface

__all__ = (
    "TestBenchmarkFixture",
    "TestCanonicalBenchmaker",
    "TestCanonicalSurface",
    "TestVendoredTreesAreNotSurfaces",
)

# Bytes no UTF-8 decoder accepts, so a file holding them is red rather than
# accidentally readable: 0xFF and 0xFE are legal in no position at all.
UNDECODABLE = b"\xff\xfe" + os.urandom(4094)
FIXTURE_DIR = "orchflows-scan-fixture"


class TestVendoredTreesAreNotSurfaces(unittest.TestCase):
    """A vendored tree and a font file are not live surfaces.

    `node_modules` and `.venv` are gitignored working trees no law or live
    surface ever reached, and a font is bytes the scan cannot decode. Both
    are proved against the real walk: `live_files` is memoized, so a cache
    filled before the fixture existed would answer without ever seeing it.
    """

    def test_a_font_suffix_is_declared_binary_rather_than_unreadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            for suffix in (".ttf", ".woff", ".woff2"):
                path = Path(tmp, "vendor" + suffix)
                path.write_bytes(UNDECODABLE)
                self.assertIsNone(retirement.read_surface(path, path.name))

    def test_the_live_scan_prunes_a_vendored_tree_holding_binaries(self):
        root = retirement.ROOT
        planted = []
        for tree in ("node_modules", ".venv"):
            base = root / tree
            planted.append(base if not base.exists() else base / FIXTURE_DIR)
            fixture = base / FIXTURE_DIR
            fixture.mkdir(parents=True, exist_ok=True)
            for name in ("x.ttf", "notes.dat"):
                fixture.joinpath(name).write_bytes(UNDECODABLE)
        try:
            names = [name for name, _ in retirement._live_scan(root)]
        finally:
            for path in planted:
                shutil.rmtree(path, ignore_errors=True)
        self.assertTrue(names)
        self.assertEqual([name for name in names if FIXTURE_DIR in name], [])


if __name__ == "__main__":
    unittest.main()
