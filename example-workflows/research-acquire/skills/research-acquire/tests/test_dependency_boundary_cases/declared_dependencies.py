"""Declared-dependency boundary checks."""

import sys
import unittest

from .support import (
    STANDARD_LIBRARY_IMPORTS,
    THIRD_PARTY_SURFACES,
    absolute_imports,
    declared_import_names,
    imports_naming,
    outside_the_standard_library,
    package_sources,
)

class DeclaredDependenciesOnlyTest(unittest.TestCase):
    """Criterion 2, dependency half: nothing undeclared, on the 3.9 floor.

    The stdlib-only bar was lifted on 2026-09-02 (`docs/custom-workflow-
    authoring.md`, Dependencies): a ring item uses the libraries it needs and
    declares them in `requirements.txt` beside its manifest. What survives is
    the enumeration -- every module the package takes from outside itself is
    spelled out, and every one the interpreter does not answer from its own
    standard library has to be one the declaration accounts for. An import
    that is neither is a dependency nobody promised to install.
    """

    def test_the_package_takes_exactly_these_modules_from_outside_itself(self):
        taken = set()
        for path in package_sources():
            taken |= absolute_imports(path)

        self.assertEqual(tuple(sorted(taken)), STANDARD_LIBRARY_IMPORTS)

    def test_every_one_outside_the_stdlib_is_declared_beside_the_manifest(self):
        undeclared = [
            (name, origin)
            for name, origin in outside_the_standard_library(STANDARD_LIBRARY_IMPORTS)
            if name not in declared_import_names()
        ]

        self.assertEqual(undeclared, [])

    def test_the_floor_this_was_resolved_against_is_the_declared_one(self):
        # The resolution above is a fact about the interpreter that ran it, so
        # the interpreter is asserted rather than assumed.
        self.assertEqual(sys.version_info[:2], (3, 9))

    def test_no_module_names_an_sdk_a_driver_or_a_downloader(self):
        self.assertEqual(imports_naming(package_sources(), THIRD_PARTY_SURFACES), [])
