"""The installed ticket family is discovered by install.py's own rule."""

from .common import *  # noqa: F401,F403

import unittest

from .common import TICKETS_MODULES, TICKETS_PY, TICKETS_SUPPORT_NAMES, support_names


class TestTheTicketFamilyIsDiscoveredNotListed(unittest.TestCase):
    """`install.py:discover_script_names` copies every `scripts/tickets_*.py`
    beside the installed facade. A fixture that restates that set by hand
    goes stale the moment a module is added: the installed-copy cases then
    fail on an `ImportError` for a module that exists in the checkout, which
    grades the fixture's age rather than the behavior under test.
    """

    def test_the_support_names_are_the_sorted_siblings_of_the_facade(self):
        expected = tuple(
            sorted(path.name for path in TICKETS_PY.parent.glob("tickets_*.py"))
        )
        self.assertEqual(expected, TICKETS_SUPPORT_NAMES)
        self.assertEqual(expected, support_names())

    def test_the_facade_is_not_one_of_its_own_support_modules(self):
        """`tickets.py` is an entrypoint, not support: install.py copies it
        under `SCRIPT_NAMES` and excludes it from the discovered set."""

        self.assertNotIn(TICKETS_PY.name, TICKETS_SUPPORT_NAMES)
        self.assertEqual(TICKETS_PY, TICKETS_MODULES[0])
        self.assertEqual(len(TICKETS_SUPPORT_NAMES) + 1, len(TICKETS_MODULES))
        for path in TICKETS_MODULES:
            self.assertTrue(path.is_file(), path)

    def test_a_module_added_beside_the_facade_joins_the_family(self):
        """Graded against the real `scripts/` directory, because a helper
        that returned a frozen list would answer the same before and after.
        The probe is removed on the way out whatever the read does."""

        probe = TICKETS_PY.with_name("tickets_zz_probe.py")
        self.assertFalse(probe.exists(), "the probe name is already taken")
        probe.write_text("VALUE = 1\n", encoding="utf-8")
        try:
            names = support_names()
        finally:
            probe.unlink()
        self.assertIn("tickets_zz_probe.py", names)
        self.assertEqual(tuple(sorted(names)), names)
        self.assertNotIn("tickets_zz_probe.py", support_names())
