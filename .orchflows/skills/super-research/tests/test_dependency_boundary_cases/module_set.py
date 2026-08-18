"""Public module-set and private-support ownership checks."""

import unittest

from super_research import runner

from .source_roster_support import NUMBER_WORDS
from .support import (
    ADAPTER_DIR,
    CORE_MODULES,
    PACKAGE_DIR,
    PRIVATE_SUPPORT_OWNERS,
    private_support_importers,
    private_support_modules_on_disk,
)

class ModuleSetTest(unittest.TestCase):
    """The set of modules the rest of this file quantifies over."""

    def test_the_core_is_exactly_the_modules_this_file_names(self):
        on_disk = tuple(sorted(path.stem for path in PACKAGE_DIR.glob("*.py")))

        self.assertEqual(on_disk, tuple(sorted(CORE_MODULES)))

    def test_the_adapter_modules_on_disk_are_exactly_the_declared_roster(self):
        # Derived from the roster the core declares, not transcribed: an
        # adapter file with no id, and an id with no file, are the same defect
        # read from two ends.
        on_disk = {path.stem for path in ADAPTER_DIR.glob("*.py")} - {"__init__"}

        self.assertEqual(sorted(on_disk), sorted(runner.ADAPTER_IDS))
        self.assertEqual(len(runner.ADAPTER_IDS), 20)


class PrivateSupportOwnershipTest(unittest.TestCase):
    """Every extracted private module belongs to exactly one public facade."""

    def test_the_private_support_set_is_exactly_the_declared_owner_map(self):
        self.assertEqual(
            private_support_modules_on_disk(),
            tuple(sorted(PRIVATE_SUPPORT_OWNERS)),
        )

    def test_every_private_support_module_is_imported_by_its_one_owner(self):
        importers = private_support_importers()

        self.assertEqual(set(importers), set(PRIVATE_SUPPORT_OWNERS))
        for key, owner in sorted(PRIVATE_SUPPORT_OWNERS.items()):
            with self.subTest(module=key):
                self.assertEqual(importers[key], (owner,))

    def test_every_owner_is_a_public_core_or_adapter_facade(self):
        for (namespace, _), owner in sorted(PRIVATE_SUPPORT_OWNERS.items()):
            with self.subTest(namespace=namespace, owner=owner):
                public = CORE_MODULES if namespace == "core" else runner.ADAPTER_IDS
                self.assertIn(owner, public)


class ThisSuiteCountsItsOwnModuleSetTest(unittest.TestCase):
    """The module count in this file's docstring, against the tuple it describes.

    It said eleven over fourteen entries: `ledger`, `ordering` and `pacing`
    joined the core and the sentence above them did not. A count in prose beside
    a list is the cheapest thing in a repository to leave behind, and this file
    exists to enumerate — so its own enumeration is counted too.
    """

    def test_the_docstring_names_the_number_of_core_modules_there_are(self):
        from tests import test_dependency_boundary

        counted = NUMBER_WORDS[len(CORE_MODULES) - 1].lower()

        self.assertIn("core's " + counted + " modules", test_dependency_boundary.__doc__)
