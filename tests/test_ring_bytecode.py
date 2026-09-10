"""Generated caches cannot revoke source trust or conceal changed executable code."""

from pathlib import Path
import py_compile
import sys
import unittest

from scripts import rings_trust, tickets_pins
from tests.test_rings import _item, _world


class RingBytecodeTests(unittest.TestCase):
    def test_only_bytecode_derived_from_unchanged_source_preserves_trust(self):
        with _world() as world:
            bundle = world["project"] / ".orchflows"
            package = _item(bundle / "workflows", "workflow", "cached").parent
            source = package / "tool.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            rings_trust.grant(bundle)
            pinned = tickets_pins.tree_digest("workflow", package)
            cache = package / "__pycache__" / f"tool.{sys.implementation.cache_tag}.pyc"
            py_compile.compile(str(source), cfile=str(cache), doraise=True)
            self.assertEqual(pinned, tickets_pins.tree_digest("workflow", package))
            self.assertTrue(rings_trust.state(bundle)["trusted"])

            # A forged cache with the original source's filename and a valid
            # header is still executable input; it must not disappear from trust.
            altered = package / "altered.py"
            altered.write_text("VALUE = 2\n", encoding="utf-8")
            py_compile.compile(str(altered), cfile=str(cache), dfile=str(source), doraise=True)
            altered.unlink()
            self.assertFalse(rings_trust.state(bundle)["trusted"])
            py_compile.compile(str(source), cfile=str(cache), doraise=True)
            self.assertTrue(rings_trust.state(bundle)["trusted"])
            source.write_text("VALUE = 2\n", encoding="utf-8")
            self.assertFalse(rings_trust.state(bundle)["trusted"])

    def test_cache_directory_source_and_sourceless_bytecode_remain_trust_inputs(self):
        with _world() as world:
            bundle = world["project"] / ".orchflows"
            package = _item(bundle / "workflows", "workflow", "cached").parent
            cache_dir = package / "__pycache__"
            cache_dir.mkdir()
            for path in (cache_dir / "hidden.py", package / "tool.pyc"):
                with self.subTest(path=path.name):
                    rings_trust.grant(bundle)
                    path.write_bytes(b"changed executable input")
                    self.assertFalse(rings_trust.state(bundle)["trusted"])
                    path.unlink()
