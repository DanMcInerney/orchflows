"""Transport route-ownership cases."""

from .common import *

def package_sources_but(declared):
    """Every package module a declaration does not name.

    The declaration names core modules by stem, so it excludes the one file the
    package root holds under that name and never an adapter that happens to
    share it.
    """

    excluded = {PACKAGE_DIR / (name + ".py") for name in declared}
    return sorted(path for path in PACKAGE_DIR.rglob("*.py") if path not in excluded)


def package_sources():
    """Every package module but the ones declared to own a route."""

    return package_sources_but(ROUTE_OWNING_MODULES)


def adapter_sources():
    """Every adapter module the package ships, the shared protocol excluded."""

    return sorted(path for path in ADAPTER_DIR.rglob("*.py") if path.name != "__init__.py")


def owned_route_literals():
    """Every string only a declared route owner may name: a host, an endpoint, a credential."""

    literals = set()
    for route in transport.ROUTE_CONSTANTS.values():
        # An open route declares no origin, and an empty literal names nothing.
        if not route.origin:
            continue
        literals.add(route.origin)
        literals.add(route.origin + route.path)
    return sorted(literals)


def sources_naming(literals, paths):
    """Every (file name, literal) pair where a source names something it must not."""

    found = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for literal in literals:
            if literal in source:
                found.append((path.name, literal))
    return sorted(found)


def imported_names(path):
    """Every module and imported symbol path one source file names in an import."""

    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module:
                names.add(module)
            for alias in node.names:
                names.add(module + "." + alias.name if module else alias.name)
    return names


class RouteOwnershipScanTest(unittest.TestCase):
    """Criterion 3: one owner for the route table, booleans for the router.

    The scan covers the package's own modules. Tests are excluded on purpose:
    naming a route constant to assert it is exactly what a test is for.
    """

    def test_no_module_outside_the_declared_owners_names_a_route_host_or_a_credential(self):
        self.assertEqual(sources_naming(owned_route_literals(), package_sources()), [])

    def test_the_ownership_scan_can_fail(self):
        # A module that names a route origin and a credential, written beside
        # the tree so the scan is shown to discriminate rather than to match
        # nothing at all.
        rogue = FIXTURE_DIR / "rogue_module_source.txt"

        found = sources_naming(owned_route_literals(), [rogue])

        self.assertEqual(
            [literal for _, literal in found],
            [
                transport.ROUTE_CONSTANTS[transport.HN_ALGOLIA_SEARCH_ROUTE].origin,
                transport.ROUTE_CONSTANTS[transport.HN_ALGOLIA_SEARCH_ROUTE].origin
                + transport.ROUTE_CONSTANTS[transport.HN_ALGOLIA_SEARCH_ROUTE].path,
            ],
        )

    def test_no_module_outside_the_declared_seam_reaches_the_network(self):
        # Quantified over the seam declaration and not the route one, because
        # the two answer different questions: a module admitted to the route
        # table is admitted to spell an address, never to open a socket.
        for path in package_sources_but(NETWORK_SEAM_MODULES):
            with self.subTest(module=path.name):
                named = imported_names(path)

                for module in NETWORK_MODULES:
                    self.assertNotIn(module, named)
