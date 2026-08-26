"""Errand's closed derived-artifact registry expands invalidations."""

import unittest
from unittest import mock

from scripts import tickets_errand


class ErrandDerivedClosureTest(unittest.TestCase):
    def test_a_new_test_closes_over_the_serial_compat_manifest_and_step(self):
        closure = tickets_errand.derived_closure(
            ["create:tests/test_new_behavior.py"]
        )
        self.assertEqual(
            [
                "tests/test_new_behavior.py",
                "tests/serial_compat_manifest.json",
            ],
            closure["write_scope"],
        )
        self.assertEqual(
            [
                "create:tests/test_new_behavior.py",
                "change:tests/serial_compat_manifest.json",
            ],
            closure["mutations"],
        )
        self.assertEqual(
            [
                {
                    "name": "serial-compat-regeneration",
                    "command": "uv run --no-project python tools/run_serial_compat.py --write-manifest",
                    "oracle": "uv run --no-project python tools/run_serial_compat.py",
                }
            ],
            closure["regeneration_steps"],
        )

    def test_an_ordinary_test_edit_does_not_change_membership(self):
        closure = tickets_errand.derived_closure(
            ["change:tests/test_existing_behavior.py"]
        )
        self.assertEqual(["tests/test_existing_behavior.py"], closure["write_scope"])
        self.assertEqual([], closure["regeneration_steps"])

    def test_an_incomplete_registry_entry_is_refused_before_expansion(self):
        with mock.patch.object(
            tickets_errand,
            "DERIVED_ARTIFACT_REGISTRY",
            ({"artifact": "generated.json"},),
        ):
            with self.assertRaisesRegex(ValueError, "incomplete derived-artifact registry entry"):
                tickets_errand.derived_closure(["create:tests/test_new.py"])


if __name__ == "__main__":
    unittest.main()
