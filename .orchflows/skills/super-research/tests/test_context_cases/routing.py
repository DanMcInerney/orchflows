"""Route ownership, admission, and outcome-reduction cases."""

from .support import *  # noqa: F403

class RouteConstantOwnershipTest(unittest.TestCase):
    """Route constants live in transport.py; callers see booleans, not hosts."""

    def test_every_declared_route_carries_its_origin_and_access_class(self):
        route = transport.ROUTE_CONSTANTS["ddg_html"]

        self.assertEqual(route.access_class, "K4")
        self.assertEqual(route.origin, "https://html.duckduckgo.com")

        built = transport.build_transport_request("ddg_html", {"q": "best local model"})
        self.assertTrue(built.url.startswith("https://html.duckduckgo.com/html/?"))
        self.assertIn("q=best+local+model", built.url)

    def test_route_admissions_are_booleans_only(self):
        admissions = transport.route_admissions()

        self.assertIn("ddg_html", admissions)
        self.assertTrue(all(value is True or value is False for value in admissions.values()))
        self.assertTrue(admissions["ddg_html"])

    def test_default_opener_refuses_a_non_https_url_without_touching_a_socket(self):
        offline = transport.TransportRequest(
            route_id="ddg_html", method="GET", url="http://html.duckduckgo.com/html/"
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError):
                transport.urlopen_response(offline)


class RouterTest(unittest.TestCase):
    """The router decides from per-route booleans and nothing else."""

    def setUp(self):
        self.step = schema.parse_manifest(TRACER_MANIFEST).steps[0]

    def test_an_admitted_route_is_selected(self):
        decision = router.select_route(self.step, web_search.DESCRIPTOR, {"ddg_html": True})

        self.assertTrue(decision.admitted)
        self.assertEqual(decision.route_id, "ddg_html")
        self.assertEqual(decision.access_class, "K4")
        self.assertEqual(decision.refusal_reason, "")

    def test_the_same_route_turned_off_is_refused_as_auth_required(self):
        decision = router.select_route(self.step, web_search.DESCRIPTOR, {"ddg_html": False})

        self.assertFalse(decision.admitted)
        self.assertEqual(decision.refusal_reason, "auth_required")

    def test_a_route_absent_from_the_admissions_map_is_refused_as_no_route(self):
        decision = router.select_route(self.step, web_search.DESCRIPTOR, {})

        self.assertFalse(decision.admitted)
        self.assertEqual(decision.refusal_reason, "no_route")

    def test_a_descriptor_for_another_adapter_is_refused_as_no_route(self):
        decision = router.select_route(
            self.step, reddit_archive.DESCRIPTOR, {"arctic_shift_posts_ids": True}
        )

        self.assertFalse(decision.admitted)
        self.assertEqual(decision.refusal_reason, "no_route")


class OutcomeReductionTest(unittest.TestCase):
    """Batch reduction is exact; a usable record never hides a failure."""

    def test_every_reduction_branch(self):
        self.assertEqual(schema.reduce_outcomes(("empty", "empty")), "empty")
        self.assertEqual(schema.reduce_outcomes(("ok", "empty")), "ok")
        self.assertEqual(schema.reduce_outcomes(("ok", "partial")), "partial")
        self.assertEqual(schema.reduce_outcomes(("ok", "failed")), "partial")
        self.assertEqual(schema.reduce_outcomes(("failed", "refused")), "failed")
        self.assertEqual(schema.reduce_outcomes(("refused", "refused")), "refused")
        self.assertEqual(schema.reduce_outcomes(()), "empty")


