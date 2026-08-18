"""Runner-dispatch boundary checks."""

import unittest

from super_research import runner

from .support import PACKAGE_DIR, adapter_modules_imported, branch_targets

class RunnerDispatchTest(unittest.TestCase):
    """Criterion 2, dispatch half: twenty literal branches and no other way in."""

    def test_the_core_imports_fake_and_exactly_the_live_modules(self):
        imported = adapter_modules_imported(PACKAGE_DIR / "runner.py")

        self.assertEqual(sorted(imported), sorted(runner.ADAPTER_IDS))
        self.assertIn("fake", imported)
        self.assertEqual(len(imported - {"fake"}), 19)

    def test_no_other_core_module_imports_an_adapter_module_at_all(self):
        # One module can call an adapter, so there is one module to read to
        # learn what this core can reach.
        reaching = sorted(
            path.name
            for path in PACKAGE_DIR.glob("*.py")
            if path.name != "runner.py" and adapter_modules_imported(path)
        )

        self.assertEqual(reaching, [])

    def test_both_branch_chains_cover_the_declared_roster_in_its_own_order(self):
        for function_name in ("descriptor_for", "call_adapter"):
            with self.subTest(function=function_name):
                reached = branch_targets(PACKAGE_DIR / "runner.py", function_name)

                self.assertEqual(
                    tuple(adapter_id for adapter_id, _, _ in reached), runner.ADAPTER_IDS
                )

    def test_every_branch_reaches_the_module_its_own_id_names(self):
        # The failure a count cannot see: every branch the roster declares, one
        # of them returning another adapter's descriptor.
        for function_name, member in (
            ("descriptor_for", "DESCRIPTOR"),
            ("call_adapter", "fetch_native_page"),
        ):
            for adapter_id, module, reached in branch_targets(
                PACKAGE_DIR / "runner.py", function_name
            ):
                with self.subTest(function=function_name, adapter=adapter_id):
                    self.assertEqual(module, adapter_id)
                    self.assertEqual(reached, member)

    def test_every_declared_id_answers_and_an_undeclared_one_is_refused(self):
        for adapter_id in runner.ADAPTER_IDS:
            with self.subTest(adapter=adapter_id):
                self.assertEqual(runner.descriptor_for(adapter_id).adapter_id, adapter_id)

        self.assertIsNone(runner.descriptor_for("no_such_adapter"))
        with self.assertRaises(runner.RunnerError):
            runner.call_adapter("no_such_adapter", None, None)
