from tests.test_adapters_cases.rss_atom import *  # noqa: F401,F403

PUBLIC_PAGE_FIXTURE_DIR = TEST_DIR / "fixtures" / "public_page"
ARTICLE_TARGET = "article:" + ARTICLE_TITLE
ARTICLE_LOCATOR = "https://en.wikipedia.org/wiki/" + ARTICLE_TITLE
CONTROL_LOCATOR = "https://example.com/"
# The roster row's capability, as the spec's own table names it. The oracle
# refuses an adapter that reaches none of it, because an adapter that can do
# nothing satisfies "reaches no host a caller chose" perfectly.
PAGE_ROSTER_SELECTIONS = ("article", "control")
WRONG_PAGE_ADAPTERS = ("any_url_adapter", "no_selection_adapter")

# Every shape a caller could use to try to name an address instead of a
# document, plus the same shapes behind a valid selection prefix. None of them
# reaches the network.
UNSELECTABLE_TARGETS = ADDRESS_SHAPED_VALUES + tuple(
    "article:" + value for value in ADDRESS_SHAPED_VALUES
) + (
    "",
    "article",
    "control:something",
    "shell:rm -rf /",
    "not_a_selection:x",
)


def read_public_page(name):
    return PUBLIC_PAGE_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def page_cases():
    return tuple(json.loads(read_public_page("page_cases.json"))["cases"])


def page_request(target):
    return adapters.AdapterRequest(step_id="s1-page", target_ids=(target,))


def selected_page(fixture, status=200, target=ARTICLE_TARGET, module=None, final_url=None):
    """Run the page adapter over one canned answer; return its page and the opener.

    A four-part answer is how an offline read reports that the origin answered
    from an address other than the one asked for. The carrier treats a
    three-part answer as a read that was not redirected, so every existing
    seeding in this suite keeps meaning what it meant.
    """

    reader = public_page if module is None else module
    body = read_public_page(fixture)
    answer = (status, body, "text/html")
    if final_url is not None:
        answer = answer + (final_url,)
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {route_id: answer for route_id in transport.ROUTE_CONSTANTS}
    )
    return (reader.fetch_native_page(carrier, page_request(target)), opener)


class PublicPageReadTest(unittest.TestCase):
    """One selected document, read as a document.

    The roster row is body, hash, links, media type, redirects and observed
    time — everything a caller needs to say "this is the document I read, here
    is its fingerprint, and here is where it actually came from". The body is
    the bytes the origin served rather than text extracted from them, because
    the hash has to be of something exact and an extraction is this package's
    reading rather than the origin's document.
    """

    def test_one_page_carries_the_one_document_it_selected(self):
        page, opener = selected_page("article.html")

        self.assertEqual(len(page.records), 1)
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(opener.opened[0].url, ARTICLE_LOCATOR)

    def test_the_record_carries_every_field_its_roster_row_names(self):
        page, _ = selected_page("article.html")
        record = page.records[0]
        named = dict(record.attributes)

        # body, as served
        self.assertEqual(record.body, read_public_page("article.html"))
        # media type
        self.assertEqual(named[public_page.CONTENT_TYPE_ATTRIBUTE], "text/html")
        # links
        self.assertGreater(len(attribute_pairs(record, public_page.LINK_ATTRIBUTE)), 1)
        # redirects: what was asked, and what answered
        self.assertEqual(named[public_page.REQUESTED_URL_ATTRIBUTE], ARTICLE_LOCATOR)
        self.assertEqual(named[public_page.FINAL_URL_ATTRIBUTE], ARTICLE_LOCATOR)
        # observed time, which a page states and every record built from it
        # inherits: the moment the origin was read, not the moment it was
        # normalized.
        self.assertEqual(page.observed_at, helpers.FROZEN_START)

    def test_the_hash_is_of_the_document_that_was_read(self):
        # The hash is derived by the one module that owns hashing rather than
        # computed a second time here, which is why the body is the bytes the
        # origin served: an extraction would fingerprint this package's reading
        # of a document instead of the document.
        page, _ = selected_page("article.html")
        records = normalize.normalize_page(
            page,
            schema.AcquisitionStep(
                step_id="s1-page", kind="discovery", adapter_id="public_page", max_items=5
            ),
            "artifact:t", "m-t",
        )

        self.assertEqual(
            records[0].exact_content_hash,
            normalize.content_hash(read_public_page("article.html")),
        )
        self.assertEqual(len(records[0].exact_content_hash), 64)

    def test_the_links_are_the_ones_the_document_published_exactly_as_published(self):
        page, _ = selected_page("article.html")
        links = attribute_pairs(page.records[0], public_page.LINK_ATTRIBUTE)

        # In the document's own order, and relative where the document was
        # relative: resolving one here would mean guessing the base a page
        # states elsewhere, and the record already carries the address the
        # origin answered from for a caller that wants to resolve them.
        self.assertEqual(
            links,
            (
                "/wiki/Denial-of-service_attack",
                "/wiki/Bandwidth_throttling",
                "/wiki/Token_bucket",
                "/wiki/Project_Shield",
                "https://www.rfc-editor.org/rfc/rfc6585",
                "https://foundation.wikimedia.org/wiki/Policy:Privacy_policy",
            ),
        )

    def test_a_read_that_was_redirected_says_what_it_asked_and_what_answered(self):
        answered_from = "https://en.wikipedia.org/wiki/Rate_limiting_(computing)"
        page, _ = selected_page("article.html", final_url=answered_from)
        record = page.records[0]
        named = dict(record.attributes)

        # One hop's worth of truth: "I asked X and read the document at Y".
        self.assertEqual(named[public_page.REQUESTED_URL_ATTRIBUTE], ARTICLE_LOCATOR)
        self.assertEqual(named[public_page.FINAL_URL_ATTRIBUTE], answered_from)
        # And the locator is where the document actually came from, so two
        # requests that land on one document name one thing.
        self.assertEqual(record.canonical_locator, answered_from)

    def test_a_read_that_was_not_redirected_names_one_address_twice(self):
        page, _ = selected_page("control.html", target="control")
        record = page.records[0]
        named = dict(record.attributes)

        self.assertEqual(named[public_page.REQUESTED_URL_ATTRIBUTE], CONTROL_LOCATOR)
        self.assertEqual(named[public_page.FINAL_URL_ATTRIBUTE], CONTROL_LOCATOR)
        self.assertEqual(record.canonical_locator, CONTROL_LOCATOR)

    def test_the_control_selection_takes_no_argument_and_reads_one_document(self):
        page, opener = selected_page("control.html", target="control")

        self.assertEqual(len(page.records), 1)
        self.assertEqual(opener.opened[0].url, CONTROL_LOCATOR)
        self.assertEqual(
            attribute_pairs(page.records[0], public_page.LINK_ATTRIBUTE),
            ("https://www.iana.org/domains/example",),
        )

    def test_a_page_the_origin_does_not_have_is_the_status_it_is(self):
        page, _ = selected_page("article_absent.html", status=404)

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("http_status",))
        self.assertEqual(page.records, ())
        self.assertNotIn(public_page.AUTH_REQUIRED, page.loss)

    def test_the_page_speaks_for_the_document_at_the_class_the_ladder_gives_it(self):
        page, _ = selected_page("article.html")

        self.assertEqual(page.adapter_id, "public_page")
        self.assertEqual(page.access_class, "K0")
        self.assertEqual(page.representation_kind, "page")
        self.assertEqual(page.route_id, transport.PUBLIC_PAGE_ARTICLE_ROUTE)
        self.assertEqual(page.operator_identity, "wikimedia")
        self.assertEqual(page.records[0].canonical_content_kind, "web_page")
        # A document has no platform identity to be qualified against, so
        # nothing here can be folded with anything by strong identity.
        self.assertEqual(page.native_identity_namespace, "")

    def test_every_case_is_typed_as_its_evidence_says(self):
        for row in page_cases():
            with self.subTest(case=row["case_name"]):
                page, _ = selected_page(
                    row["body_fixture"], status=row["status"], target=row["target"]
                )

                self.assertEqual(page.outcome, row["expected_outcome"])
                self.assertEqual(
                    tuple(page.loss),
                    (row["expected_loss"],) if row["expected_loss"] else (),
                )


def assert_the_target_set_is_selected_and_enumerable(case, adapter_id, module):
    """Row 2's oracle: what this adapter can read is a list, and it is closed.

    Not "no test pointed it somewhere else". Every other adapter in this roster
    is pinned to a vendor's endpoint shape and could not be pointed anywhere if
    it tried; this one takes an argument, and an argument is one bad branch away
    from being an address. So the claim is made by enumerating what the adapter
    can reach and then trying to escape it.

    Four clauses. The selection set covers the roster's capability and is
    therefore not empty — without which an adapter that reads nothing at all
    passes perfectly. Every selection resolves to a route this module declares,
    which `transport.py` owns, which declares a read and admits nothing else.
    Every selection actually run leaves exactly one call, on that route, at that
    origin. And every caller string shaped like an address reaches the network
    zero times.
    """

    selections = dict(module.PAGE_SELECTIONS)
    surfaces = tuple(descriptor.route_id for descriptor in module.SURFACE_DESCRIPTORS)
    uncovered = [name for name in PAGE_ROSTER_SELECTIONS if name not in selections]
    if uncovered:
        case.fail(
            "{0} enumerates a selection set that reaches none of the roster's"
            " capability {1}: nothing was proven closed by proving nothing is"
            " reachable".format(adapter_id, uncovered)
        )

    origins = set()
    for name in sorted(selections):
        descriptor, _ = selections[name]
        route_id = descriptor.route_id
        detail = " {0} selection {1} on route {2}".format(adapter_id, name, route_id)
        if route_id not in surfaces:
            case.fail("a selection reaches a route this adapter never declared:" + detail)
        route = transport.route_constant(route_id)
        origins.add(urllib.parse.urlsplit(route.origin).netloc)
        if route.method not in transport.READ_METHODS:
            case.fail(
                "a write-capable verb {0} is declared by the route behind:{1}".format(
                    route.method, detail
                )
            )
        if transport.admitted_methods(route_id) != transport.READ_METHODS:
            case.fail("a route this adapter reads admits a verb that is not a read:" + detail)
        if route.body_params:
            case.fail("a route this adapter reads carries a request body:" + detail)

    for row in page_cases():
        if row["status"] != 200:
            continue
        name = row["case_name"]
        _, opener = selected_page(row["body_fixture"], target=row["target"], module=module)
        detail = " {0} case {1}".format(adapter_id, name)
        if len(opener.opened) != 1:
            case.fail(
                "one selected read cost {0} calls rather than one:{1}".format(
                    len(opener.opened), detail
                )
            )
        sent = opener.opened[0]
        if sent.method not in transport.READ_METHODS:
            case.fail(
                "a write-capable verb {0} is reachable through:{1}".format(sent.method, detail)
            )
        if sent.body:
            case.fail("a request this adapter sent carried a body:" + detail)
        if urllib.parse.urlsplit(sent.url).netloc not in origins:
            case.fail(
                "a read left for a host outside the selection set: {0}{1}".format(
                    sent.url, detail
                )
            )

    for target in UNSELECTABLE_TARGETS:
        page, opener = selected_page("article.html", target=target, module=module)
        detail = " {0} target {1!r}".format(adapter_id, target)
        if opener.opened:
            reached = urllib.parse.urlsplit(opener.opened[0].url).netloc
            if reached not in origins:
                case.fail(
                    "a caller chose the host a read went to: {0} reached {1}{2}".format(
                        target, opener.opened[0].url, detail
                    )
                )
            case.fail(
                "an arbitrary caller-supplied target reached the network:" + detail
            )
        if page.outcome != "refused":
            case.fail(
                "a target naming no selection was answered rather than refused:"
                " outcome {0}{1}".format(page.outcome, detail)
            )
        if page.records:
            case.fail("a refused target still produced records:" + detail)


# Everything a module would have to reach to run something rather than read
# something. None of it is imported here, named here, or read here.
EXECUTION_MODULES = (
    "subprocess",
    "os",
    "sys",
    "shlex",
    "shutil",
    "pty",
    "socket",
    "urllib.request",
    "http.client",
    "ssl",
    "importlib",
    "ctypes",
)
EXECUTION_NAMES = (
    "eval",
    "exec",
    "compile",
    "__import__",
    "getattr",
    "setattr",
    "system",
    "popen",
    "spawn",
    "fork",
    "execv",
    "run",
    "call",
    "check_output",
)
