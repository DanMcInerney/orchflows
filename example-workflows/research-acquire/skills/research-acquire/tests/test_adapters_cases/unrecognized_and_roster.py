from super_research import dispatch
from tests.test_adapters_cases.feed_page_artifact import *  # noqa: F401,F403


# One row per adapter that reads a container out of a 200. Each names a body
# whose container is present and holds nothing this adapter recognizes, and a
# body whose container is present and genuinely holds nothing. The pair is the
# point: an adapter that types both the same way has stopped distinguishing
# "the route changed" from "there is nothing there", and only the second is a
# statement about the platform.
UNRECOGNIZED_CONTAINER_CASES = (
{
        "adapter": "reddit_archive",
        "request": adapters.AdapterRequest(step_id="s1", target_ids=("1abc234",)),
        "content_type": "application/json",
        "unrecognized": json.dumps({"data": {"t3_1abc234": {"id": "1abc234"}}}),
        "names": "data",
        "empty": json.dumps({"data": []}),
    },
{
        "adapter": "github_rest",
        "request": adapters.AdapterRequest(step_id="s1", query="search:local models"),
        "content_type": "application/json",
        "unrecognized": json.dumps(
            {"total_count": 2, "items": [{"full_name": "a/b"}, {"full_name": "c/d"}]}
        ),
        "names": "id",
        "empty": json.dumps({"total_count": 0, "items": []}),
    },
)


class UnrecognizedContainerIsNeverAnEmptySuccessTest(unittest.TestCase):
    """Criterion 8, widened to every adapter that reads a container out of a 200.

    `hacker_news` already proves this shape as `HackerNewsAbsenceIsNotDriftTest`
    and the four adapters here did not. Each answered a present-but-unreadable
    container with `outcome='empty'` and `loss=()` — indistinguishable, at the
    artifact, from a query that matched nothing. The frozen spec says it twice:
    a stale identifier produces typed `schema_drift` or `stale_identifier` and
    never an empty success, and structured-data drift is typed rather than
    silently empty.

    The empty half of each row is what keeps the fix honest. Typing every
    unreadable answer as drift is easy; typing only the unreadable ones is the
    property, so each adapter is shown answering a real absence as `empty` in
    the same test.
    """

    def _page(self, row, body):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                descriptor.route_id: (200, body, row["content_type"])
                for descriptor in runner.surface_descriptors(row["adapter"])
            },
        )
        module = getattr(dispatch, row["adapter"])
        return module.fetch_native_page(carrier, row["request"]), opener

    def test_a_container_holding_nothing_this_adapter_reads_is_typed_drift(self):
        for row in UNRECOGNIZED_CONTAINER_CASES:
            with self.subTest(adapter=row["adapter"]):
                page, opener = self._page(row, row["unrecognized"])

                self.assertEqual(page.outcome, "failed")
                self.assertEqual(tuple(page.loss), ("schema_drift",))
                self.assertEqual(page.records, ())
                # The warning names what it looked for, so a reader knows which
                # shape to go and check rather than which platform to blame.
                self.assertIn(row["names"], " ".join(page.warnings))
                # And it cost exactly one read: drift is an answer, not a
                # reason to look somewhere else.
                self.assertEqual(len(opener.opened), 1)

    def test_a_container_that_genuinely_holds_nothing_stays_an_empty_answer(self):
        for row in UNRECOGNIZED_CONTAINER_CASES:
            with self.subTest(adapter=row["adapter"]):
                page, _ = self._page(row, row["empty"])

                self.assertEqual(page.outcome, "empty")
                self.assertEqual(page.records, ())
                self.assertNotIn("schema_drift", page.loss)
                self.assertTrue(
                    page.warnings,
                    "an empty answer was returned with nothing said about it",
                )


class RosterIsCompleteTest(unittest.TestCase):
    """The retained adapters resolve to reads, descriptors and paced surfaces.

    This is the revision the roster closes at. An adapter is only really in it
    when the core can name it, describe it, call it, see every surface it can
    reach, and pace every route that surface declares — and the four are
    separate registrations, so a later adapter that lands three of them is a
    `RunnerError` at its first paced live read rather than a red test.
    """

    def test_the_core_lists_exactly_the_roster_the_spec_names(self):
        self.assertEqual(sorted(runner.ADAPTER_IDS), sorted(ROSTER))
        self.assertEqual(len(runner.ADAPTER_IDS), 9)
        live = [
            adapter_id
            for adapter_id, access_class in ROSTER.items()
            if access_class != "offline"
        ]
        self.assertEqual(len(live), 8)

    def test_every_adapter_declares_the_class_the_measured_ladder_gives_it(self):
        for adapter_id, access_class in sorted(ROSTER.items()):
            with self.subTest(adapter=adapter_id):
                descriptor = runner.descriptor_for(adapter_id)

                self.assertIsNotNone(descriptor)
                self.assertEqual(descriptor.access_class, access_class)
                self.assertIn(access_class, schema.ACCESS_CLASSES)
                # Every surface of a multi-surface adapter speaks at the same
                # class: a class belongs to how a read is authorized, and both
                # of an adapter's routes are authorized the same way.
                for surface in runner.surface_descriptors(adapter_id):
                    self.assertEqual(surface.access_class, access_class)
                    self.assertEqual(surface.adapter_id, adapter_id)

    def test_no_capability_in_the_roster_is_reachable_only_through_a_credential(self):
        # The spec's first rule: `K5` is the one credentialed class and nothing
        # here is in it. Absence of a credential yields full capability at
        # lower throughput, never a refusal.
        self.assertEqual(
            sorted({access_class for access_class in ROSTER.values()}),
            ["K0", "K2", "K3", "offline"],
        )
        self.assertNotIn("K5", ROSTER.values())


    def test_every_listed_adapter_resolves_to_a_descriptor_and_to_a_call(self):
        # Each adapter is asked in its own grammar (`helpers.roster_request`),
        # because two of them take an address and nothing else: `open_page`
        # refuses anything that is not an https locator on an undeclared host,
        # and `reddit_shreddit` refuses a target its grammar does not name. A
        # universal nonsense string would prove those two refuse, which is not
        # what this row is about — it is about every listed adapter resolving
        # to a descriptor and spending exactly one call.
        for adapter_id in sorted(ROSTER):
            with self.subTest(adapter=adapter_id):
                descriptor = runner.descriptor_for(adapter_id)
                clock = helpers.FakeClock()
                carrier, opener = helpers.offline_transport(
                    clock,
                    {
                        surface.route_id: (200, "{}", "application/json")
                        for surface in runner.surface_descriptors(adapter_id)
                    },
                )

                page = runner.call_adapter(adapter_id, carrier, helpers.roster_request(adapter_id))

                self.assertEqual(page.adapter_id, adapter_id)
                self.assertIn(
                    page.route_id,
                    {surface.route_id for surface in runner.surface_descriptors(adapter_id)},
                )
                self.assertEqual(len(opener.opened), 1)
