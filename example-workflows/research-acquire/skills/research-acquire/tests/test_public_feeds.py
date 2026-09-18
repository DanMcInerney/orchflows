"""Caller-visible feed acquisition, date provenance and shared URL failures."""
import io
from email.message import Message
import socket
import unittest
from unittest import mock
import urllib.request
import urllib.response

from super_research import runner, schema, transport
from super_research.adapters import AdapterRequest, open_page, rss_atom
from tests.helpers import FakeClock


FEED_URL = "https://publisher.example/feeds/research.xml"
ATOM = '''<a:feed xmlns:a="http://www.w3.org/2005/Atom" xml:base="../articles/">
  <a:title>Research feed</a:title><a:updated>2026-09-12T12:00:00Z</a:updated>
  <a:entry xml:base="quantum/">
    <a:id>old</a:id><a:title>An old result</a:title><a:link href="old"/>
    <a:published>2025-09-01T12:00:00Z</a:published><a:updated>2026-09-12T10:00:00Z</a:updated>
  </a:entry>
  <a:entry xml:base="quantum/">
    <a:id>new</a:id><a:title>A new result</a:title><a:link href="new"/>
    <a:published>2026-09-11T09:30:00.125-04:00</a:published>
    <a:summary type="html">&lt;p&gt;An experiment &lt;b&gt;measured&lt;/b&gt; this.&lt;/p&gt;</a:summary>
    <a:link rel="enclosure" href="audio.mp3" type="audio/mpeg"/>
  </a:entry>
  <a:entry><a:id>undated</a:id><a:title>Date unknown</a:title><a:link href="unknown"/>
    <a:updated>2026-09-12T10:00:00Z</a:updated>
  </a:entry>
</a:feed>'''


def carrier_for(body, status=200, final_url=None):
    return transport.Transport(
        opener=lambda request: (status, body, "application/atom+xml", final_url or request.url, ()),
        now=lambda: "2026-09-12T12:00:00Z")


class PublicFeedTests(unittest.TestCase):
    def test_bad_entry_link_is_a_record_gap_and_bad_xml_base_is_only_a_feed_gap(self):
        good = ATOM
        invalid_link = ATOM.replace('href="new"', 'href="https://[broken"')
        invalid_base = ATOM.replace('xml:base="../articles/"', 'xml:base="https://[broken"')
        payloads = {FEED_URL + "?good": good, FEED_URL + "?link": invalid_link,
                    FEED_URL + "?base": invalid_base}
        carrier = transport.Transport(opener=lambda request: (
            200, payloads[request.url], "application/atom+xml", request.url, ()),
            now=lambda: "2026-09-12T12:00:00Z")
        manifest = schema.AcquisitionManifest(manifest_id="malformed-locators", as_of="2026-09-12T13:00:00Z",
            steps=tuple(schema.AcquisitionStep(step_id=kind, kind="discovery", adapter_id="rss_atom",
                                               query=FEED_URL + "?" + kind, max_items=10)
                        for kind in ("base", "link", "good")))
        artifact = runner.run_acquisition(manifest, carrier)
        self.assertEqual(artifact.steps[0].outcome, "failed")
        self.assertIn("schema_drift", artifact.steps[0].loss)
        good_records = [record for record in artifact.records if record.step_id == "good"]
        self.assertEqual(len(good_records), 3)
        bad_link = next(record for record in artifact.records if record.step_id == "link" and record.native_item_id == "new")
        self.assertEqual(bad_link.canonical_locator, "")
        self.assertIn("field_omitted", bad_link.loss)

    def test_transport_failure_keeps_the_selected_feed_route_and_origin_accounting(self):
        for reached in (False, True):
            with self.subTest(reached=reached):
                def failed(request):
                    raise transport.TransportError("DNS failure for publisher.example", reached=reached)
                carrier = transport.Transport(opener=failed)
                manifest = schema.AcquisitionManifest(manifest_id="feed-failed", as_of="2026-09-12T13:00:00Z",
                    steps=(schema.AcquisitionStep(step_id="feed", kind="discovery", adapter_id="rss_atom",
                                                  query=FEED_URL, max_items=10),))
                result = runner.run_step(manifest.steps[0], carrier, "artifact:feed-failed", "feed-failed")
                step, records, operations = result
                self.assertEqual(step.route_id, transport.WEB_PAGE_OPEN_ROUTE)
                self.assertEqual(step.query, FEED_URL)
                self.assertEqual(step.outcome, "failed")
                self.assertEqual(step.loss, ("unreachable",))
                self.assertIn("publisher.example", " ".join(step.warnings))
                self.assertFalse(records)
                self.assertEqual(operations[0].route_id, transport.WEB_PAGE_OPEN_ROUTE)
                self.assertEqual(operations[0].reached_origin, reached)

    def test_supplied_feed_is_acquired_with_original_source_and_resolved_links(self):
        final_url = "https://cdn.publisher.example/news/feed.xml"
        carrier = carrier_for(ATOM, final_url=final_url)
        page = rss_atom.fetch_native_page(carrier, AdapterRequest(step_id="feed", query=FEED_URL))
        self.assertEqual([call.url for call in carrier.calls], [FEED_URL])
        self.assertEqual(page.platform, "web")
        self.assertEqual(page.representation_kind, "feed")
        record = page.records[1]
        self.assertEqual(record.canonical_locator, "https://cdn.publisher.example/articles/quantum/new")
        self.assertEqual(record.body, "An experiment measured this.")
        self.assertEqual(dict(record.attributes)["feed_text_kind"], "summary")
        self.assertEqual(record.published_at, "2026-09-11T13:30:00Z")
        self.assertEqual(dict(record.attributes)["feed_url"], FEED_URL)
        self.assertEqual(dict(record.attributes)["final_feed_url"], final_url)
        self.assertEqual(dict(record.attributes)["enclosure"], "https://cdn.publisher.example/articles/quantum/audio.mp3")

    def test_window_filters_publication_and_keeps_unknown_dates_explicit(self):
        manifest = schema.AcquisitionManifest(
            manifest_id="feed-window", as_of="2026-09-12T13:00:00Z",
            steps=(schema.AcquisitionStep(step_id="feed", kind="discovery", adapter_id="rss_atom",
                                          query=FEED_URL, max_items=10,
                                          window_start="2026-08-13T00:00:00Z", window_end="2026-09-12T12:00:00Z"),))
        artifact = runner.run_acquisition(manifest, carrier=carrier_for(ATOM))
        self.assertEqual({record.native_item_id for record in artifact.records}, {"new", "undated"})
        unknown = next(record for record in artifact.records if record.native_item_id == "undated")
        self.assertEqual(unknown.published_at, "")
        self.assertEqual(dict(unknown.attributes)["modified_at"], "2026-09-12T10:00:00Z")
        self.assertIn("field_omitted", unknown.loss)
        self.assertIn("window_not_honored", artifact.steps[0].loss)
        self.assertTrue(any("publisher-selected slice" in warning for warning in artifact.steps[0].warnings))

    def test_feed_and_page_reads_share_one_host_budget(self):
        clock = FakeClock()
        reads = []
        carrier = transport.Transport(opener=lambda request: (
            reads.append(clock.seconds) or 200, ATOM, "application/atom+xml", request.url, ()), now=clock.stamp)
        governor = runner.RateGovernor(carrier, clock=clock.monotonic, sleep=clock.sleep)
        rss_atom.fetch_native_page(governor, AdapterRequest(step_id="feed", query=FEED_URL))
        open_page.fetch_native_page(governor, AdapterRequest(step_id="page", query="https://publisher.example/article"))
        self.assertEqual(reads, [0, 2])

    def test_rss_cdata_and_guid_permalink_are_usable(self):
        body = '''<rss version="2.0"><channel><item><title>Research</title>
        <guid>https://publisher.example/research</guid>
        <pubDate>Fri, 11 Sep 2026 12:00:00 GMT</pubDate>
        <description><![CDATA[<p>A result.</p><script>ignore()</script>]]></description>
        </item></channel></rss>'''
        page = rss_atom.fetch_native_page(carrier_for(body), AdapterRequest(step_id="feed", query=FEED_URL))
        self.assertEqual(page.records[0].canonical_locator, "https://publisher.example/research")
        self.assertEqual(page.records[0].body, "A result.")
        self.assertEqual(page.records[0].published_at, "2026-09-11T12:00:00Z")

    def test_youtube_feed_url_uses_its_existing_budget_and_attribution(self):
        url = "https://www.youtube.com/feeds/videos.xml?channel_id=UC_example"
        carrier = carrier_for(ATOM)
        page = rss_atom.fetch_native_page(carrier, AdapterRequest(step_id="feed", query=url))
        self.assertEqual(carrier.calls[0].route_id, transport.YOUTUBE_CHANNEL_FEED_ROUTE)
        self.assertEqual(page.platform, "youtube")
        self.assertEqual(dict(page.records[0].attributes)["feed_url"], url)

    def test_malformed_nonfeed_and_entity_payloads_are_gaps(self):
        for body in ("<feed><entry>", "<html><feed/></html>", "<rss/>",
                     '<!DOCTYPE feed [<!ENTITY bomb "expanded">]><feed><title>&bomb;</title></feed>'):
            with self.subTest(body=body):
                page = rss_atom.fetch_native_page(carrier_for(body), AdapterRequest(step_id="feed", query=FEED_URL))
                self.assertEqual(page.outcome, "failed")
                self.assertEqual(page.loss, ("schema_drift",))
                self.assertFalse(page.records)
                self.assertTrue(page.warnings)

    def test_empty_feed_is_empty_with_coverage_gap_and_no_inherited_date(self):
        body = "<rss><channel><title>Quiet</title><pubDate>Sat, 12 Sep 2026 04:00:00 GMT</pubDate></channel></rss>"
        page = rss_atom.fetch_native_page(carrier_for(body), AdapterRequest(step_id="feed", query=FEED_URL))
        self.assertEqual(page.outcome, "empty")
        self.assertFalse(page.records)
        self.assertTrue(page.warnings)

    def test_unsafe_input_is_refused_before_transport(self):
        for url in ("UC_example", "publisher", "", "http://publisher.example/feed", "file:///tmp/feed", "https://127.0.0.1/feed",
                    "https://10.0.0.1/feed", "https://[::1]/feed", "https://localhost/feed",
                    "https://user:secret@publisher.example/feed", "https://publisher.example:444/feed",
                    "https://publisher.example/\nfeed", "https://[bad/feed"):
            with self.subTest(url=url):
                carrier = carrier_for(ATOM)
                page = rss_atom.fetch_native_page(carrier, AdapterRequest(step_id="feed", query=url))
                self.assertEqual(page.outcome, "refused")
                self.assertFalse(carrier.calls)


class PublicDestinationTests(unittest.TestCase):
    def test_custom_opener_adds_only_the_redirect_guard_without_auth_or_cookies(self):
        request = transport.build_transport_request(transport.WEB_PAGE_OPEN_ROUTE, {"url": FEED_URL})
        prepared = urllib.request.build_opener(transport._PublicReadRedirect())
        headers = Message()
        headers["Content-Type"] = "application/atom+xml"
        response = urllib.response.addinfourl(io.BytesIO(ATOM.encode()), headers, FEED_URL, 200)
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with mock.patch.object(socket, "getaddrinfo", return_value=public), \
                mock.patch.object(urllib.request, "build_opener", return_value=prepared) as build, \
                mock.patch.object(prepared, "open", return_value=response):
            transport.urlopen_read(request)
        handlers, options = build.call_args
        self.assertEqual(options, {})
        self.assertEqual(len(handlers), 1)
        self.assertIs(type(handlers[0]), transport._PublicReadRedirect)
        self.assertFalse({type(handler).__name__ for handler in prepared.handlers} & {
            "HTTPCookieProcessor", "HTTPBasicAuthHandler", "HTTPDigestAuthHandler",
            "ProxyBasicAuthHandler", "ProxyDigestAuthHandler"})

    def test_private_dns_destination_is_refused_before_open(self):
        request = transport.build_transport_request(transport.WEB_PAGE_OPEN_ROUTE, {"url": FEED_URL})
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]
        with mock.patch.object(socket, "getaddrinfo", return_value=private), \
                mock.patch.object(urllib.request, "build_opener") as opened:
            with self.assertRaisesRegex(transport.TransportError, "non-public"):
                transport.urlopen_read(request)
        opened.assert_not_called()

    def test_redirects_obey_the_same_public_destination_policy(self):
        for destination, succeeds in (("https://cdn.publisher.example/feed", True),
                                      ("https://127.0.0.1/feed", False),
                                      ("http://publisher.example/feed", False),
                                      ("https://www.reddit.com/feed", False)):
            with self.subTest(destination=destination):
                calls = []
                class ScriptedHTTPS(urllib.request.HTTPSHandler):
                    def https_open(self, request):
                        calls.append(request.full_url)
                        headers = Message()
                        headers["Content-Type"] = "application/atom+xml"
                        if len(calls) == 1:
                            headers["Location"] = destination
                        response = urllib.response.addinfourl(io.BytesIO(ATOM.encode()), headers,
                                                             request.full_url, 302 if len(calls) == 1 else 200)
                        response.msg = "fixture"
                        return response
                opener = urllib.request.build_opener(transport._PublicReadRedirect(), ScriptedHTTPS())
                public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
                request = transport.build_transport_request(transport.WEB_PAGE_OPEN_ROUTE, {"url": FEED_URL})
                with mock.patch.object(socket, "getaddrinfo", return_value=public), \
                        mock.patch.object(urllib.request, "build_opener", return_value=opener):
                    if succeeds:
                        result = transport.urlopen_read(request)
                        self.assertEqual(result[3], destination)
                        self.assertEqual(calls, [FEED_URL, destination])
                    else:
                        with self.assertRaises(transport.TransportError):
                            transport.urlopen_read(request)
                        self.assertEqual(calls, [FEED_URL])


if __name__ == "__main__":
    unittest.main()
