"""Route ownership and outcome-reduction cases."""

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

    def test_default_opener_refuses_a_non_https_url_without_touching_a_socket(self):
        offline = transport.TransportRequest(
            route_id="ddg_html", method="GET", url="http://html.duckduckgo.com/html/"
        )

        with forbid_io():
            with self.assertRaises(transport.TransportError):
                transport.urlopen_read(offline)


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
