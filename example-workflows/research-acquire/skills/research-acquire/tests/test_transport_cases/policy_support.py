"""Shared transport policy fixtures and helpers."""

from .common import *

THREAT_FIXTURE_DIR = TEST_DIR / "fixtures" / "threats"

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






def route_grants():
    """Every grant this package holds, as one comparable value.

    Two halves, because a widening could arrive as either: which routes are
    reachable at all, and what each one is allowed to do.
    """

    return (
        tuple(
            (route_id, transport.READ_METHODS)
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
        if call.method not in transport.READ_METHODS:
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
    """One discovery step over a publisher feed, answered with an injected page."""

    return schema.AcquisitionManifest(
        manifest_id="m-injected",
        as_of=FROZEN_OBSERVED_AT,
        steps=(
            schema.AcquisitionStep(
                step_id="s1-discover",
                kind="discovery",
                adapter_id="rss_atom",
                query="https://8.8.8.8/feed.xml",
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
