"""Acquisition, pagination, and static scheduling-ownership cases."""

from tests.test_pipeline_cases.common import *
from tests.test_pipeline_cases.artifact import run_on, tracer_governor


CONCURRENCY_OWNERS = {
    "runner.py": (
        "concurrent.futures",
        "concurrent.futures.ThreadPoolExecutor",
    ),
    "pacing.py": ("threading",),
    "cache.py": ("threading",),
}


class LanesOverlapAndTheCoreOwnsPagingTest(unittest.TestCase):
    """Scheduling owns overlap while the public runner owns cursor continuation."""

    def test_only_the_declared_owners_import_a_concurrency_primitive(self):
        taken = sorted(
            (path.name, name)
            for path in package_sources()
            for name in helpers.imported_names(path)
            if name.split(".")[0] in CONCURRENCY_MODULES
        )
        self.assertEqual(
            taken,
            sorted(
                (owner, name)
                for owner, names in CONCURRENCY_OWNERS.items()
                for name in names
            ),
        )

    def test_no_call_a_manifest_authorizes_carries_a_cursor(self):
        for payload in (DISCOVERY_MANIFEST, TWO_STEP_MANIFEST, FUSED_MANIFEST):
            for step in schema.parse_manifest(payload).steps:
                with self.subTest(manifest=payload["manifest_id"], step=step.step_id):
                    planned = runner.planned_calls(step)
                    self.assertEqual(
                        [request.cursor for request, _ in planned], [""] * len(planned)
                    )
                    if step.kind == "discovery":
                        self.assertEqual(len(planned), 1)

    def test_a_cursor_enters_a_request_in_exactly_one_place(self):
        building = sorted(
            (path.name, path.read_text(encoding="utf-8").count("cursor="))
            for path in package_sources()
            if "cursor=" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(building, [("runner.py", 1)])


def fixture_page(rows, cursor_out="", first=0):
    payload = {
        "platform": "fixture",
        "cursor_out": cursor_out,
        "records": [
            {
                "canonical_content_kind": "post",
                "canonical_locator": "https://fixture.invalid/p/{0}".format(first + index),
                "native_item_id": str(first + index),
                "title": "row {0}".format(first + index),
            }
            for index in range(rows)
        ],
    }
    return (200, json.dumps(payload), "application/json")


def fixture_pages(count, rows=3, last_offers_more=False):
    return [
        fixture_page(
            rows,
            cursor_out=""
            if index == count - 1 and not last_offers_more
            else "c{0}".format(index + 1),
            first=index * rows,
        )
        for index in range(count)
    ]


def fixture_step(kind="discovery", max_items=100, hits=1):
    if kind == "discovery":
        return schema.AcquisitionStep(
            step_id="s1-fixture",
            kind="discovery",
            adapter_id="fake",
            query="local models",
            max_items=max_items,
        )
    return schema.AcquisitionStep(
        step_id="s1-fixture",
        kind="hydration",
        adapter_id="fake",
        selected_hits=tuple(
            schema.SelectedHit(
                discovery_locator="https://fixture.invalid/p/{0}".format(index),
                target_id=str(index),
            )
            for index in range(hits)
        ),
        max_items=max_items,
    )


def fixture_run(answers, step=None):
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock, {transport.FAKE_OFFLINE_ROUTE: answers}
    )
    resolved = fixture_step() if step is None else step
    result, records, operations = runner.run_step(
        resolved, carrier, "artifact:paging", "m-paging", clock=clock.monotonic
    )
    return result, records, operations, opener


class PagingIsTheCoresTest(unittest.TestCase):
    def test_a_page_that_offers_a_cursor_is_read_and_so_is_the_one_it_offers(self):
        result, records, _, opener = fixture_run(fixture_pages(2))
        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(result.pages, 2)
        self.assertEqual(
            [record.native_item_id for record in records],
            ["0", "1", "2", "3", "4", "5"],
        )
        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.loss, ())

    def test_records_from_every_page_reach_the_artifact_in_the_order_read(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, {transport.FAKE_OFFLINE_ROUTE: fixture_pages(3)}
        )
        artifact = runner.run_acquisition(
            schema.AcquisitionManifest(
                manifest_id="m-paging",
                as_of="2026-08-10T09:30:00Z",
                steps=(fixture_step(),),
            ),
            carrier,
            clock=clock.monotonic,
        )
        self.assertEqual(len(opener.opened), 3)
        self.assertEqual(len(artifact.records), 9)
        self.assertEqual(
            [(record.page_index, record.list_index) for record in artifact.records],
            [(0, 0), (0, 1), (0, 2), (1, 3), (1, 4), (1, 5), (2, 6), (2, 7), (2, 8)],
        )
        self.assertEqual(artifact.steps[0].records_received, 9)

    def test_a_page_that_offers_no_cursor_is_the_only_call_the_step_makes(self):
        result, records, _, opener = fixture_run(fixture_pages(1))
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(result.pages, 1)
        self.assertEqual(len(records), 3)
        self.assertEqual(result.outcome, "ok")

    def test_the_cap_bounds_the_whole_step_and_never_one_page_of_it(self):
        result, records, _, opener = fixture_run(
            fixture_pages(4), step=fixture_step(max_items=4)
        )
        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(len(records), 4)
        self.assertEqual(result.records_received, 6)
        self.assertEqual(result.outcome, "partial")
        self.assertIn("recall_window_partial", result.loss)

    def test_a_step_that_meets_its_cap_exactly_asks_for_no_further_page(self):
        result, records, _, opener = fixture_run(
            fixture_pages(3), step=fixture_step(max_items=6)
        )
        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(len(records), 6)
        self.assertEqual(result.outcome, "ok")
        self.assertEqual(result.loss, ())

    def test_a_declared_page_cap_stops_an_origin_that_keeps_offering(self):
        result, _, _, opener = fixture_run(fixture_pages(12, last_offers_more=True))
        self.assertGreater(runner.MAX_PAGES_PER_STEP, 1)
        self.assertEqual(len(opener.opened), runner.MAX_PAGES_PER_STEP)
        self.assertEqual(result.pages, runner.MAX_PAGES_PER_STEP)
        self.assertEqual(result.outcome, "partial")
        self.assertIn("recall_window_partial", result.loss)

    def test_a_cursor_that_repeats_ends_the_step_rather_than_spinning(self):
        result, records, _, opener = fixture_run([fixture_page(3, cursor_out="c1")])
        self.assertEqual(len(opener.opened), 2)
        self.assertLess(result.pages, runner.MAX_PAGES_PER_STEP)
        self.assertEqual(len(records), 6)
        self.assertEqual(result.outcome, "partial")
        self.assertIn("recall_window_partial", result.loss)

    def test_a_hydration_step_still_spends_one_call_per_frozen_hit(self):
        step = fixture_step(kind="hydration", hits=2)
        result, records, _, opener = fixture_run(
            [fixture_page(1, cursor_out="c1"), fixture_page(1, cursor_out="c2", first=1)],
            step=step,
        )
        self.assertEqual(
            [request.cursor for request, _ in runner.planned_calls(step)], ["", ""]
        )
        self.assertEqual(len(opener.opened), 2)
        self.assertEqual(result.pages, 2)
        self.assertEqual(len(records), 2)

    def test_each_page_is_billed_as_its_own_planned_operation(self):
        result, _, operations, opener = fixture_run(fixture_pages(3))
        self.assertEqual(len(operations), len(opener.opened))
        self.assertEqual([operation.page_index for operation in operations], [0, 1, 2])
        self.assertEqual(
            [operation.records_received for operation in operations], [3, 3, 3]
        )
        self.assertEqual(
            [operation.reached_origin for operation in operations], [True] * 3
        )
        self.assertEqual(
            sum(operation.records_received for operation in operations),
            result.records_received,
        )

    def test_the_ledger_charges_one_native_page_per_call_across_the_pages(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock, {transport.FAKE_OFFLINE_ROUTE: fixture_pages(3)}
        )
        run = runner.run_scheduled(
            schema.AcquisitionManifest(
                manifest_id="m-paging",
                as_of="2026-08-10T09:30:00Z",
                steps=(fixture_step(),),
            ),
            carrier,
            clock=clock.monotonic,
        )
        sums = runner.ledger_sums(run.ledger)
        self.assertEqual(sums["pages"], len(opener.opened))
        self.assertEqual(sums["calls"], len(opener.opened))
        self.assertEqual(sums["items"], 9)

    def test_the_cursor_a_page_offered_is_the_cursor_the_next_call_goes_out_with(self):
        from super_research.adapters import hacker_news
        body = {"hits": [{"objectID": "1", "title": "first", "_tags": ["story"]}], "page": 0, "nbPages": 2}
        second = {"hits": [{"objectID": "2", "title": "second", "_tags": ["story"]}], "page": 1, "nbPages": 2}
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(clock, {
            transport.HN_ALGOLIA_SEARCH_ROUTE: [(200, json.dumps(body), "application/json"), (200, json.dumps(second), "application/json")]
        })
        step = schema.AcquisitionStep(step_id="hn", kind="discovery", adapter_id="hacker_news", query="python", max_items=10)
        result, records, _ = runner.run_step(step, carrier, "a", "m", clock=clock.monotonic)
        self.assertEqual(len(opener.opened), 2)
        self.assertEqual([row.native_item_id for row in records], ["1", "2"])
        self.assertIn("page=1", opener.opened[1].url)
