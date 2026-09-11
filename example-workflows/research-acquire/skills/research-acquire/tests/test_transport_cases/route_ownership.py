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
    for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values():
        literals.add(credential.value)
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


# The nouns that make a sentence a claim about route data, and how wide a
# claim reaches around the module it names.
ROUTE_DATA_NOUNS = ("route", "host", "endpoint", "credential", "address")
CLAIM_WINDOW = 80


def prose_blocks(path):
    """Everything one tracked file says in prose, each block flowed to one line.

    A markdown file is prose throughout. A python file is prose in its comment
    runs and its docstrings, and consecutive comment lines are one run: a claim
    wraps across lines, so a scan reading each line alone would miss every claim
    long enough to be worth making.
    """

    if path.suffix == ".md":
        return [" ".join(path.read_text(encoding="utf-8").split())]

    source = path.read_text(encoding="utf-8")
    blocks = []
    run = []
    previous = None
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        if previous is not None and token.start[0] != previous + 1:
            blocks.append(" ".join(run))
            run = []
        run.append(token.string.lstrip("#").strip())
        previous = token.start[0]
    if run:
        blocks.append(" ".join(run))

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            text = ast.get_docstring(node)
            if text:
                blocks.append(" ".join(text.split()))
    return blocks


def module_spellings():
    """Every way this item's prose names one of the package's core modules.

    Core modules by stem, the same unit the declarations above are written in:
    the route table is a core module and a claim about where it lives names one.
    Adapters are out on purpose — an adapter's name is possessive all over the
    roster, and none of those sentences is about a route's address.
    """

    spellings = {}
    for path in sorted(PACKAGE_DIR.glob("*.py")):
        if path.stem == "__init__":
            continue
        for form in (
            "``super_research." + path.stem + "``",
            "`super_research." + path.stem + "`",
            "``" + path.stem + ".py``",
            "`" + path.stem + ".py`",
            ":mod:`." + path.stem + "`",
            "``" + path.stem + "``",
            "`" + path.stem + "`",
        ):
            spellings[form] = path.stem
    return spellings


def route_ownership_claims(paths):
    """Every (file, module) where prose gives route data to a named module.

    A claim is recognised by shape and never by a remembered sentence: the
    module's name carries a possessive, or is owning something, or is what
    something belongs to — with a route, a host, an endpoint, a credential or an
    address inside the same window. The alternative, a list of the exact
    sentences that were wrong once, would pass the next one written.
    """

    found = []
    spellings = module_spellings()
    for path in paths:
        for block in prose_blocks(path):
            for form, stem in spellings.items():
                start = block.find(form)
                while start != -1:
                    end = start + len(form)
                    before, after = block[:start], block[end:]
                    claiming = (
                        after.startswith("'s")
                        or after.lstrip().split(" ")[0].strip(".,;:") in ("owns", "own", "owned")
                        or "owner of" in after[:40]
                        or before.rstrip().endswith(("belongs to", "belong to"))
                    )
                    window = block[max(0, start - CLAIM_WINDOW): end + CLAIM_WINDOW]
                    if claiming and any(noun in window for noun in ROUTE_DATA_NOUNS):
                        found.append((path.name, stem))
                    start = block.find(form, end)
    return sorted(set(found))


def prose_bearing_files():
    """Every tracked file in this item that makes a claim in prose."""

    return (
        sorted(PACKAGE_DIR.rglob("*.py"))
        + sorted((ITEM_DIR / "references").glob("*.md"))
        + [ITEM_DIR / "SKILL.md"]
    )


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
                transport.PUBLIC_CLIENT_CREDENTIALS[transport.INSTAGRAM_WEB_APP_ID].value,
                transport.ROUTE_CONSTANTS[transport.DDG_HTML_ROUTE].origin,
                transport.ROUTE_CONSTANTS[transport.DDG_HTML_ROUTE].origin
                + transport.ROUTE_CONSTANTS[transport.DDG_HTML_ROUTE].path,
            ],
        )

    def test_no_credential_value_reaches_the_tracked_evidence_document(self):
        # `references/evidence.md` distils records of live reads, and a
        # transcript is exactly where a credential value would be copied from.
        # The scan above, the same literals, one surface that is prose.
        credentials = sorted(
            credential.value for credential in transport.PUBLIC_CLIENT_CREDENTIALS.values()
        )

        self.assertEqual(sources_naming(credentials, [EVIDENCE_DOC]), [])

    def test_no_module_outside_the_declared_seam_reaches_the_network(self):
        # Quantified over the seam declaration and not the route one, because
        # the two answer different questions: a module admitted to the route
        # table is admitted to spell an address, never to open a socket.
        for path in package_sources_but(NETWORK_SEAM_MODULES):
            with self.subTest(module=path.name):
                named = imported_names(path)

                for module in NETWORK_MODULES:
                    self.assertNotIn(module, named)

    def test_the_router_never_sees_a_module_that_holds_an_address(self):
        # `router.py`'s own docstring states the law: it never sees a host, a
        # path, or a credential. While one module held every address, naming
        # that module here was the whole law. Now that the addresses are
        # declared, this reads the declaration — because `from . import routes`
        # would hand the router every origin in the allowlist without spelling
        # one literal for the scan above to catch.
        holding = sorted(
            {Path(name).name for name in ROUTE_OWNING_MODULES}
            | set(NETWORK_SEAM_MODULES)
        )
        named = imported_names(PACKAGE_DIR / "router.py")

        self.assertEqual(
            [name for name in sorted(named) if any(held in name for held in holding)], []
        )


class RouteOwnershipIsStatedTrulyTest(unittest.TestCase):
    """Criterion 12: what the item says about who owns route data is true.

    The scan above reads literals; this one reads sentences, and the two answer
    different questions. Splitting the table left `transport` the seam and made
    every comment calling it the owner of a host false — a source can pass every
    literal scan in this file while telling the next maintainer to put the next
    host in the wrong module. Quantified over the same declaration the literal
    scan uses, so moving the table again moves both. Tests are excluded for the
    reason they are above: describing a wrong arrangement is what one is for.
    """

    def test_no_prose_in_the_item_gives_route_data_to_a_module_that_does_not_declare_it(self):
        claims = route_ownership_claims(prose_bearing_files())

        # Non-empty first. A file set that went empty, or a reader that stopped
        # recognising a claim, is how this assertion would go on passing while
        # deciding nothing — and the item does say who owns the table.
        self.assertNotEqual(claims, [], "the scan found no ownership claim anywhere")
        owner_stems = {Path(name).name for name in ROUTE_OWNING_MODULES}
        self.assertEqual([claim for claim in claims if claim[1] not in owner_stems], [])

    def test_the_prose_scan_can_fail(self):
        # One source with the misattribution put back, written beside the tree
        # with a .txt suffix so it can never be imported, so the scan is shown
        # to discriminate rather than to match nothing at all.
        misattributing = FIXTURE_DIR / "misattributed_ownership_source.txt"

        self.assertEqual(
            route_ownership_claims([misattributing]),
            [(misattributing.name, "transport")],
        )
