"""Import-edge, execution-surface, and failure-oracle checks."""

import unittest

from super_research import runner

from .support import (
    CORE_IMPORT_EDGES,
    CORE_MODULES,
    DYNAMIC_IMPORT_MODULES,
    EXECUTION_MODULES,
    EXECUTION_NAMES,
    FIXTURE_DIR,
    NETWORK_SEAM_MODULES,
    PACKAGE_DIR,
    ROUTE_OWNING_MODULES,
    SHELL_SPELLINGS,
    STANDARD_LIBRARY_IMPORTS,
    THIRD_PARTY_SURFACES,
    absolute_imports,
    attributes_ending_in,
    branch_targets,
    dynamic_dispatch_findings,
    imports_naming,
    non_read_verb_findings,
    outside_the_standard_library,
    package_sources,
    sibling_imports,
    strings_spelling,
)

class IntraPackageImportTest(unittest.TestCase):
    """Criterion 2, edge half: every import inside the package, both directions."""

    def test_every_core_module_imports_exactly_the_siblings_it_declares(self):
        for name in CORE_MODULES:
            with self.subTest(module=name):
                imported = sibling_imports(PACKAGE_DIR / (name + ".py"))

                self.assertEqual(tuple(sorted(imported)), CORE_IMPORT_EDGES[name])

    def test_the_edge_table_covers_the_core_and_nothing_else(self):
        self.assertEqual(sorted(CORE_IMPORT_EDGES), sorted(CORE_MODULES))

    def test_no_core_module_imports_a_module_this_package_does_not_have(self):
        known = set(CORE_MODULES) | {"adapters"}
        unknown = sorted(
            (path.name, target)
            for path in PACKAGE_DIR.glob("*.py")
            for target in sibling_imports(path)
            if target not in known
        )

        self.assertEqual(unknown, [])



class NoRunSomethingSurfaceTest(unittest.TestCase):
    """Criterion 2, execution half: nothing here can run something."""

    def test_no_module_imports_a_dynamic_import_surface(self):
        self.assertEqual(imports_naming(package_sources(), DYNAMIC_IMPORT_MODULES), [])

    def test_no_module_outside_the_declared_seam_imports_an_execution_surface(self):
        # The exclusion stands for the one reason it always did — the seam owns
        # the outbound read and holds `urllib.request` on everybody's behalf —
        # and is read off the seam declaration rather than a filename, so a
        # module admitted to the route table is still scanned here.
        seam = {PACKAGE_DIR / (name + ".py") for name in NETWORK_SEAM_MODULES}
        others = [path for path in package_sources() if path not in seam]

        self.assertEqual(imports_naming(others, EXECUTION_MODULES), [])

    def test_no_module_calls_a_dynamic_import_or_a_computed_attribute(self):
        self.assertEqual(dynamic_dispatch_findings(package_sources()), [])

    def test_no_module_reaches_a_process_or_a_shell_through_an_attribute(self):
        self.assertEqual(attributes_ending_in(package_sources(), EXECUTION_NAMES), [])

    def test_no_module_spells_a_command(self):
        self.assertEqual(strings_spelling(package_sources(), SHELL_SPELLINGS), [])

    def test_the_only_non_read_verb_the_package_spells_is_a_declared_post(self):
        # Both directions, and the tighter half is the second: PUT, PATCH and
        # DELETE are spelled nowhere at all, and POST nowhere but where one of
        # the two closed exceptions to reads-only lives — the seam, which
        # admits the method, and the route owners, which spell it on the two
        # rows that carry it. Derived from those two declarations, so which
        # module holds the table is something to declare and never a filename
        # this assertion has to be told about.
        spelling_post = sorted(set(ROUTE_OWNING_MODULES) | set(NETWORK_SEAM_MODULES))

        self.assertEqual(
            non_read_verb_findings(package_sources()),
            [(name + ".py", "POST") for name in spelling_post],
        )


class BoundaryOracleCanFailTest(unittest.TestCase):
    """Criterion 4: every scan above is shown to reject, and to accept.

    Both wrong modules are written beside the tree and never imported — the
    scans read them as text. Nothing in the package produces them and nothing
    under test is mutated to obtain them.
    """

    def setUp(self):
        self.registry = FIXTURE_DIR / "registry_runner.py"
        self.write_capable = FIXTURE_DIR / "write_capable_module.py"

    def test_a_core_that_imports_by_string_fails_the_dynamic_import_scan(self):
        self.assertEqual(
            imports_naming([self.registry], DYNAMIC_IMPORT_MODULES),
            [("registry_runner.py", "importlib")],
        )

    def test_a_core_that_dispatches_by_computed_attribute_fails_the_call_scan(self):
        found = dynamic_dispatch_findings([self.registry])

        self.assertEqual([(name, called) for name, called, _ in found], [
            ("registry_runner.py", "getattr")
        ])

    def test_a_registry_offers_the_branch_reader_nothing_to_read(self):
        # The shape the enumeration is against: there is no literal chain here,
        # so `call_adapter` covers no id at all and the roster check fails on
        # an empty tuple rather than on a wrong name.
        reached = branch_targets(self.registry, "call_adapter")

        self.assertEqual(reached, ())
        self.assertNotEqual(reached, runner.ADAPTER_IDS)

    def test_a_module_that_shells_out_fails_the_execution_and_command_scans(self):
        self.assertEqual(
            imports_naming([self.registry], EXECUTION_MODULES),
            [("registry_runner.py", "importlib"), ("registry_runner.py", "subprocess")],
        )
        self.assertEqual(
            strings_spelling([self.registry], SHELL_SPELLINGS),
            [("registry_runner.py", "/bin/"), ("registry_runner.py", "sh -c")],
        )

    def test_a_module_that_imports_a_downloader_fails_the_dependency_scans(self):
        self.assertEqual(
            imports_naming([self.registry], THIRD_PARTY_SURFACES),
            [("registry_runner.py", "yt_dlp")],
        )
        self.assertEqual(
            outside_the_standard_library(absolute_imports(self.registry)),
            [("yt_dlp", "no module of that name")],
        )

    def test_a_module_that_spells_write_verbs_fails_the_verb_scan(self):
        self.assertEqual(
            non_read_verb_findings([self.write_capable]),
            [
                ("write_capable_module.py", "DELETE"),
                ("write_capable_module.py", "PATCH"),
                ("write_capable_module.py", "POST"),
                ("write_capable_module.py", "PUT"),
            ],
        )

    def test_the_same_scans_accept_the_package_that_ships(self):
        sources = package_sources()

        self.assertEqual(imports_naming(sources, DYNAMIC_IMPORT_MODULES), [])
        self.assertEqual(dynamic_dispatch_findings(sources), [])
        self.assertEqual(strings_spelling(sources, SHELL_SPELLINGS), [])
        self.assertEqual(imports_naming(sources, THIRD_PARTY_SURFACES), [])
        self.assertEqual(outside_the_standard_library(STANDARD_LIBRARY_IMPORTS), [])

    def test_nothing_in_the_package_can_reach_either_wrong_module(self):
        named = sorted(
            path.name
            for path in package_sources()
            for wrong in ("registry_runner", "write_capable_module")
            if wrong in path.read_text(encoding="utf-8")
        )

        self.assertEqual(named, [])
