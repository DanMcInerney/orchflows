"""Shared transport policy fixtures and helpers."""

from .common import *

THREAT_FIXTURE_DIR = TEST_DIR / "fixtures" / "threats"

# The ladder the retained threat oracles are remapped onto. `offline` is the
# fixture adapter's class and is not on it: nothing about `fake` is a claim
# about a route.
KEYLESS_CLASSES = ("K0", "K1", "K2", "K3", "K4")
CREDENTIALED_CLASS = "K5"
EVERY_CLASS = KEYLESS_CLASSES + (CREDENTIALED_CLASS,)
# The two classes where a credential exists at all. `K1`'s is vendor-published
# and names no user; `K5`'s is the user's own and no first-release capability
# may depend on it. Every credential-handling threat is quantified over both.
CREDENTIAL_CLASSES = ("K1", CREDENTIALED_CLASS)
NO_CLASS = ()

# T01-T16, retained by reference from the superseded spec and remapped from
# `A0`-`A5` to `K0`-`K5`. The remap is of *applicability* — which classes a
# threat is about — and the rule is the one the old mapping used: a threat
# applies to a class when that class has the machinery the threat is about.
#
# Three threats apply to no class, and that is the finding rather than a gap.
# `A2` was a CLI with an ambient identity and `A3` was an exported browser
# session; the new ladder has neither, so T05, T06's argv half, T07 and T08
# are about machinery this package does not contain. They are answered by its
# absence, which `test_dependency_boundary` proves and which the row below
# restates at this seam.
#
# One clause is dropped on purpose. The superseded T09 also demanded a
# `hostile_instruction_present` code. The frozen spec's criterion 11 states
# the remapped T09 without it — "acquired text is `untrusted_content` and
# cannot alter plan, grants, or write set" — and the criterion is the runnable
# authority here. Emitting a code would mean this package judging which text
# is hostile, which is the calling lane's job and is the one thing an
# acquisition core must not start doing.
THREAT_REMAP = {
    "T01": (CREDENTIAL_CLASSES, "no credential id or value reaches a request, a response, a call log, or an artifact"),
    "T02": (CREDENTIAL_CLASSES, "an echoed credential — the address a query-placed key was appended to — comes back stripped"),
    "T03": (CREDENTIAL_CLASSES, "a credential is attached at send time from the route's own constant, so it reaches that origin and no other"),
    "T04": (EVERY_CLASS, "no route admits a state-changing verb: PUT, PATCH and DELETE nowhere, POST only for two named reads"),
    "T05": (NO_CLASS, "no process is launched, because none can be: nothing here imports one or spells a command"),
    "T06": (EVERY_CLASS, "a caller cannot escape a route's admitted method set, and a body is the route's shape with the caller's values"),
    "T07": (NO_CLASS, "there is no session state to export: the one token a run mints lives in memory and nowhere else"),
    "T08": (NO_CLASS, "nothing navigates, clicks or submits: the only outbound operation is one bounded read"),
    "T09": (EVERY_CLASS, "acquired text is untrusted_content: it changes no plan, no grant, and no write set"),
    "T10": (CREDENTIAL_CLASSES, "a K1 credential names no user, so there is no principal to mismatch; the operator that answered is declared"),
    "T11": (EVERY_CLASS, "a refusal is typed rate_limited on one call, and no identity changes because of it"),
    "T12": (EVERY_CLASS, "a route the run cannot reach is refused with a typed reason and never probed"),
    "T13": (("K4",), "an index surface declares itself an index, and it is the only surface in the roster that does"),
    "T14": (EVERY_CLASS, "the package has no delete primitive: its only stores are in memory and clearing one is all there is"),
    "T15": (EVERY_CLASS, "a refusal costs the origin nothing: it is decided before any call is made"),
    "T16": (EVERY_CLASS, "no fallback: a failed read is a typed failure, never a second read somewhere else"),
}


def load_threat_fixture(name):
    """Load one module written beside the tree, by path."""

    spec = importlib.util.spec_from_file_location(
        "threat_fixture_" + name, THREAT_FIXTURE_DIR / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_threat_fixture(name):
    return THREAT_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def routes_at(classes):
    """Every declared route answering at one of these access classes."""

    return tuple(
        route_id
        for route_id, route in sorted(transport.ROUTE_CONSTANTS.items())
        if route.access_class in classes
    )


def sent_and_answered(route_id, params=None):
    """One read through the real opener, with the wire captured and no socket.

    The recorder answers from the address it was asked at, which is what
    urllib reports for a read nobody redirected. That makes the outbound blob
    and the returned address two different things: the credential belongs in
    the first and must not survive into the second.
    """

    recorder = RecordingUrlopen(200, "{}", "application/json")
    request = transport.build_transport_request(
        route_id, dict(helpers.probe_params(route_id), **(params or {}))
    )
    with mock.patch.object(urllib.request, "urlopen", recorder):
        answered = transport.urlopen_read(request)
    return answered, recorder.requests[0]


def route_grants():
    """Every grant this package holds, as one comparable value.

    Two halves, because a widening could arrive as either: which routes are
    reachable at all, and what each one is allowed to do.
    """

    return (
        tuple(sorted(transport.route_admissions().items())),
        tuple(
            (route_id, transport.admitted_methods(route_id))
            for route_id in sorted(transport.ROUTE_CONSTANTS)
        ),
    )


def authorized_routes(manifest):
    """Every route the steps of one manifest authorize a read on."""

    return {
        surface.route_id
        for step in manifest.steps
        for surface in runner.surface_descriptors(step.adapter_id)
    }


def assert_acquired_text_changed_nothing(case, manifest, artifact, calls, grants_before):
    """The T09 oracle: what was read cannot decide what happens next.

    Four clauses, and they are four separate ways for the claim to be false: a
    read that left for a route the plan never authorized, a read that left for
    an address its own route does not own, a verb on the wire the route does
    not admit, and a grant that is not the grant the run started with. The
    fifth is vacuity — an artifact holding nothing proves nothing about what
    text can do, and fails here rather than passing.
    """

    if not artifact.records:
        case.fail("no acquired text reached the artifact, so nothing about it was proven")
    if not calls:
        case.fail("no read was made, so nothing about what a read can be aimed at was proven")

    authorized = authorized_routes(manifest)
    for call in calls:
        if call.route_id not in authorized:
            case.fail(
                "acquired text reached a route the plan never authorized: " + call.route_id
            )
        if call.method not in transport.admitted_methods(call.route_id):
            case.fail(
                "acquired text put {0} on the wire, which route {1} does not admit".format(
                    call.method, call.route_id
                )
            )
        origin = transport.route_constant(call.route_id).origin
        if not call.url.startswith(origin):
            case.fail("acquired text chose the address a read went to: " + call.url)

    if route_grants() != grants_before:
        case.fail("acquired text changed the grants this package holds")
    if tuple(step.adapter_id for step in artifact.steps) != tuple(
        step.adapter_id for step in manifest.steps
    ):
        case.fail("acquired text changed the plan the caller wrote")


def assert_hostile_text_is_carried_as_content(case, artifact, markers):
    """The other half: the text is kept verbatim, and it is kept only as text.

    Refusing to record a hostile sentence would be the same mistake in the
    other direction — a caller cannot judge a source it is not shown. So each
    marker has to be somewhere in the acquired rows, and nowhere in the fields
    that decide anything.
    """

    if not markers:
        case.fail("no hostile text was looked for, so nothing about it was checked")
    for marker in markers:
        carried = [
            record
            for record in artifact.records
            if marker in record.title or marker in record.body
        ]
        if not carried:
            case.fail("marker {0!r} never reached a record: nothing hostile was carried".format(marker))
    for record in artifact.records:
        deciding = (
            record.adapter_id,
            record.route_id,
            record.access_class,
            record.representation_kind,
            record.operator_identity,
        ) + tuple(record.loss)
        for marker in markers:
            for field in deciding:
                if marker in field:
                    case.fail(
                        "hostile text reached a field that decides something: {0!r} in {1!r}".format(
                            marker, field
                        )
                    )


def injected_manifest():
    """One discovery step over the K4 surface, answered with an injected page."""

    return schema.AcquisitionManifest(
        manifest_id="m-injected",
        mode="staged",
        as_of=FROZEN_OBSERVED_AT,
        steps=(
            schema.AcquisitionStep(
                step_id="s1-discover",
                kind="discovery",
                adapter_id="web_search",
                query="local model benchmarks",
                max_items=10,
            ),
        ),
    )


def injected_run():
    """Acquire the injected page, and hand back everything a caller would hold."""

    carrier, opener = offline_transport(
        {
            route_id: (200, read_threat_fixture("injected_search_results.html"), "text/html")
            for route_id in transport.ROUTE_CONSTANTS
        }
    )
    manifest = injected_manifest()
    artifact = runner.run_acquisition(manifest, carrier)
    return manifest, artifact, carrier, opener

MINTED_GUEST_TOKEN = "a-token-this-run-minted"
ACTIVATION_ANSWER = (
    200,
    json.dumps({transport.GUEST_TOKEN_FIELD: MINTED_GUEST_TOKEN}),
    "application/json",
)
GUEST_READ_ANSWER = (200, "{}", "application/json")

# The one function that turns an activation into a token. A place that calls it
# is a place that mints, which is what the site scan below counts.
MINTER = "mint_guest_token"


def guest_read_request():
    """One read on the route that declares an activation route of its own."""

    return transport.build_transport_request(
        transport.X_GUEST_GRAPHQL_ROUTE,
        {"query_id": "abc123", "operation_name": "UserByScreenName"},
    )


def called_name(func):
    """The bare name a call node spells, whether it was reached plainly or dotted."""

    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else ""


def sites_calling(node, owners, module_name, found):
    """Collect every enclosing function in one tree that calls the minter."""

    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            sites_calling(child, owners + (child.name,), module_name, found)
            continue
        if isinstance(child, ast.Call) and called_name(child.func) == MINTER:
            found.add(module_name + ":" + ".".join(owners))
        sites_calling(child, owners, module_name, found)


def minting_sites():
    """Every place in the package that mints, as ``module:qualified name``.

    Stated as the set of sites for the reason `test_pipeline` states the set of
    modules that build a carrier as a set: naming one site would not notice a
    second one appearing beside it, and a count would not say which.
    """

    found = set()
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        sites_calling(ast.parse(path.read_text(encoding="utf-8")), (), path.name, found)
    return sorted(found)

INTERNALS_PATH = ITEM_DIR / "references" / "internals.md"

# The one table in `internals.md` that restates `THREAT_REMAP`, named by its
# header row. Only this table is read; every other table in that file belongs
# to someone else.
THREAT_TABLE_HEADER = "| threat | applies to | form here |"


def threat_table_rows():
    """`internals.md`'s threat table, as `(threat, applies, form)` cells in document order.

    Parsed rather than transcribed: the table a reader meets is the one the
    assertions run against, so a row corrected in the document and left in
    `THREAT_REMAP` — or the reverse — is a red test rather than two statements
    nobody compared.
    """

    rows = []
    inside = False
    for line in INTERNALS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == THREAT_TABLE_HEADER:
            inside = True
            continue
        if not inside:
            continue
        if not stripped.startswith("|"):
            break
        cells = tuple(cell.strip() for cell in stripped.strip("|").split("|"))
        if set(cells[0]) <= set("- "):
            continue
        rows.append(cells)
    return tuple(rows)


def documented_classes(cell):
    """The access classes one `applies to` cell names, `K0`–`K5` read as a range.

    The ladder the range is expanded over is `schema.ACCESS_CLASSES`, so the
    shorthand means whatever the package says it means and not a second list.
    """

    named = tuple(piece for index, piece in enumerate(cell.split("`")) if index % 2 and piece)
    if not named or "–" not in cell:
        return named
    ladder = list(schema.ACCESS_CLASSES)
    return tuple(ladder[ladder.index(named[0]) : ladder.index(named[-1]) + 1])


def comparable(prose):
    """One form statement with the document's typography taken off, and nothing else.

    Backticks and line breaks are how a cell is written, not what it claims.
    Every word survives, so a clause dropped on either side stays a difference.
    """

    return " ".join(prose.replace("`", "").split())
