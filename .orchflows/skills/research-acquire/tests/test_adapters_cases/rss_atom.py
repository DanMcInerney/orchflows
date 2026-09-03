from tests.test_adapters_cases.reddit_feed import *  # noqa: F401,F403

RSS_ATOM_FIXTURE_DIR = TEST_DIR / "fixtures" / "rss_atom"
FEED_VIDEO_ID = "yt:video:dQw4w9WgXcQ"
FEED_VIDEO_LOCATOR = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
PODCAST_GUID = "harbourlight-tape-014"


def read_rss_atom(name):
    return RSS_ATOM_FIXTURE_DIR.joinpath(name).read_text(encoding="utf-8")


def rss_atom_cases():
    return tuple(json.loads(read_rss_atom("feed_cases.json"))["cases"])


def syndication_request(channel_id=FEED_CHANNEL_ID):
    return adapters.AdapterRequest(step_id="s1-rss", target_ids=(channel_id,))


def rss_atom_page(fixture, status=200, channel_id=FEED_CHANNEL_ID, module=None):
    reader = rss_atom if module is None else module
    clock = helpers.FakeClock()
    carrier, opener = helpers.offline_transport(
        clock,
        {
            transport.YOUTUBE_CHANNEL_FEED_ROUTE: (
                status,
                read_rss_atom(fixture),
                "application/atom+xml",
            )
        },
    )
    return (reader.fetch_native_page(carrier, syndication_request(channel_id)), opener)


class RssAtomReaderTest(unittest.TestCase):
    """One parser over both syndication vocabularies, on one selected route.

    The roster row's "generic" is the parser and not the route. The 2026-08-10 probes
    measured one RSS/Atom document — `feeds/videos.xml?channel_id=`, 200, 39 KB,
    0.35 s — and that is the one route this adapter declares. The RSS 2.0 half
    of the row, enclosures and transcript links, is proven against a document of
    that shape rather than against a route known to send one, which is a real
    limit and is stated in `## Risks` rather than papered over.

    The claim this half defends is that a generic reader stays generic. The
    measured feed carries `media:statistics views=` in a vendor namespace, and
    reading it would make this adapter quietly YouTube-aware — a second opinion
    about a count `youtube_innertube` already reports, under a name this row
    does not name. It is left where it is, and that is checked.
    """

    def test_an_atom_feed_yields_the_entries_it_listed(self):
        page, opener = rss_atom_page("youtube_channel_feed.xml")

        self.assertEqual(len(page.records), 2)
        self.assertEqual(page.outcome, "ok")
        self.assertEqual(len(opener.opened), 1)
        self.assertEqual(
            opener.opened[0].url,
            "https://www.youtube.com/feeds/videos.xml?channel_id=" + FEED_CHANNEL_ID,
        )

    def test_an_atom_entry_carries_its_identity_its_date_and_its_address(self):
        page, _ = rss_atom_page("youtube_channel_feed.xml")
        first = page.records[0]

        self.assertEqual(first.native_item_id, FEED_VIDEO_ID)
        self.assertEqual(first.title, "70B on two 3090s: the numbers")
        self.assertEqual(first.canonical_locator, FEED_VIDEO_LOCATOR)
        self.assertEqual(first.author, "Harbourlight Benchmarks")
        # `published` is when the entry appeared; `updated` is when it last
        # changed. A feed that states both states a publication time, and that
        # is the one a caller ordering by recency means.
        self.assertEqual(first.published_at, "2026-08-09T15:30:12Z")

    def test_an_rss_two_item_carries_the_same_row_out_of_a_different_vocabulary(self):
        page, _ = rss_atom_page("podcast_rss.xml")
        first = page.records[0]

        self.assertEqual(len(page.records), 3)
        self.assertEqual(first.native_item_id, PODCAST_GUID)
        self.assertEqual(first.title, "Measuring what a rate limit actually is")
        self.assertEqual(first.canonical_locator, "https://harbourlight.example/podcast/014")
        # RFC 822, which is what RSS 2.0 dates are, parsed rather than pattern
        # matched: `pubDate` is a different grammar from Atom's RFC 3339 and
        # reading one as the other would drop every RSS date in existence.
        self.assertEqual(first.published_at, "2026-08-10T08:41:03Z")

    def test_an_enclosure_travels_with_the_media_type_the_feed_declared(self):
        page, _ = rss_atom_page("podcast_rss.xml")
        first = page.records[0]

        self.assertEqual(
            attribute_pairs(first, rss_atom.ENCLOSURE_ATTRIBUTE),
            ("https://cdn.harbourlight.example/tape/014.mp3",),
        )
        self.assertEqual(
            attribute_pairs(first, rss_atom.ENCLOSURE_TYPE_ATTRIBUTE), ("audio/mpeg",)
        )

    def test_a_transcript_link_is_carried_for_every_one_the_feed_published(self):
        page, _ = rss_atom_page("podcast_rss.xml")
        first, second, _ = page.records

        # Two transcripts on one episode, in the feed's own order, each with
        # the type it was declared under. This is the half of the roster row no
        # route in this package is known to send, and it is why the parser is
        # generic rather than shaped to one document.
        self.assertEqual(
            attribute_pairs(first, rss_atom.TRANSCRIPT_ATTRIBUTE),
            (
                "https://cdn.harbourlight.example/tape/014.vtt",
                "https://cdn.harbourlight.example/tape/014.srt",
            ),
        )
        self.assertEqual(
            attribute_pairs(first, rss_atom.TRANSCRIPT_TYPE_ATTRIBUTE),
            ("text/vtt", "application/x-subrip"),
        )
        # An episode that published none carries none, rather than an empty
        # string standing in for a transcript nobody offered.
        self.assertEqual(attribute_pairs(second, rss_atom.TRANSCRIPT_ATTRIBUTE), ())

    def test_a_media_pair_stays_paired_when_the_feed_declared_no_type(self):
        # The two names repeat in step, one pair per enclosure, so a caller can
        # read them by position. A feed that declared a url and no type still
        # contributes to both, with the type empty — an absence stated in its
        # own slot rather than a pairing that silently slips by one.
        page, _ = rss_atom_page("podcast_rss.xml")
        undated = page.records[2]

        self.assertEqual(attribute_pairs(undated, rss_atom.ENCLOSURE_ATTRIBUTE), ())
        self.assertEqual(attribute_pairs(undated, rss_atom.ENCLOSURE_TYPE_ATTRIBUTE), ())
        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                self.assertEqual(
                    len(attribute_pairs(record, rss_atom.ENCLOSURE_ATTRIBUTE)),
                    len(attribute_pairs(record, rss_atom.ENCLOSURE_TYPE_ATTRIBUTE)),
                )

    def test_an_item_the_feed_dated_in_no_grammar_at_all_carries_no_date(self):
        page, _ = rss_atom_page("podcast_rss.xml")
        undated = page.records[2]

        self.assertEqual(undated.published_at, "")
        self.assertIn("field_omitted", undated.loss)
        self.assertNotEqual(undated.published_at, page.observed_at)

    def test_a_vendor_extension_the_feed_carries_is_left_where_it_is(self):
        # `media:statistics views="128455"` is in the measured document. A
        # generic reader that mined it would be publishing a count under a name
        # this roster row does not name, about a platform it does not know it
        # is reading, beside an adapter that reports the same quantity from the
        # platform's own API.
        page, _ = rss_atom_page("youtube_channel_feed.xml")

        for record in page.records:
            with self.subTest(entry=record.native_item_id):
                self.assertEqual(record.engagement, ())
                self.assertEqual(
                    [name for name, _ in record.attributes if "statistic" in name], []
                )
                self.assertNotIn("128455", repr(record))
        self.assertEqual(rss_atom.DESCRIPTOR.comment_count_metric, "")
        self.assertEqual(rss_atom.DESCRIPTOR.reply_count_metric, "")

    def test_a_syndication_identity_is_recorded_and_never_used_to_merge(self):
        # A `guid` is unique inside its own feed and nowhere else, and this
        # adapter cannot say which identity space it belongs to. So the id is
        # carried — it is the roster row's "identity" — and the namespace is
        # left unstated, which is exactly what makes `strong_identity` decline
        # to fold two entries that happened to be named the same thing.
        page, _ = rss_atom_page("podcast_rss.xml")
        records = normalize.normalize_page(
            page,
            schema.AcquisitionStep(
                step_id="s1-rss", kind="discovery", adapter_id="rss_atom", max_items=10
            ),
            "artifact:t", "m-t",
        )

        self.assertEqual(page.native_identity_namespace, "")
        for record in records:
            with self.subTest(entry=record.native_item_id):
                self.assertNotEqual(record.native_item_id, "")
                self.assertIsNone(normalize.strong_identity(record))

    def test_a_channel_that_published_nothing_is_empty_and_not_a_feed_that_moved(self):
        page, _ = rss_atom_page("channel_with_no_entries.xml")

        self.assertEqual(page.records, ())
        self.assertEqual(page.outcome, "empty")
        self.assertEqual(page.loss, ())

    def test_a_document_that_is_not_a_feed_is_drift_and_not_a_quiet_channel(self):
        page, _ = rss_atom_page("not_a_feed.html")

        self.assertEqual(page.outcome, "failed")
        self.assertEqual(page.loss, ("schema_drift",))
        self.assertEqual(page.records, ())

    def test_the_channel_is_read_from_the_target_or_from_the_query(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.YOUTUBE_CHANNEL_FEED_ROUTE: (
                    200,
                    read_rss_atom("youtube_channel_feed.xml"),
                    "application/atom+xml",
                )
            },
        )

        rss_atom.fetch_native_page(
            carrier, adapters.AdapterRequest(step_id="s1", query=FEED_CHANNEL_ID)
        )

        self.assertIn("channel_id=" + FEED_CHANNEL_ID, opener.opened[0].url)

    def test_the_page_speaks_for_the_route_at_the_class_the_ladder_gives_it(self):
        page, _ = rss_atom_page("youtube_channel_feed.xml")

        self.assertEqual(page.adapter_id, "rss_atom")
        self.assertEqual(page.access_class, "K0")
        self.assertEqual(page.representation_kind, "feed")
        self.assertEqual(page.route_id, transport.YOUTUBE_CHANNEL_FEED_ROUTE)
        # An entry in a feed is an entry in a feed. A generic reader does not
        # know whether the thing behind it is a video, an episode or an
        # article, and naming one would be a guess this adapter cannot support.
        self.assertEqual(
            sorted({record.canonical_content_kind for record in page.records}),
            ["feed_entry"],
        )


class RssAtomDescriptorTest(unittest.TestCase):
    """One route, its measured cost, and the seam a second feed would use."""

    def test_the_route_is_paced_by_the_interval_the_evidence_measured(self):
        budget = runner.route_budgets()[transport.YOUTUBE_CHANNEL_FEED_ROUTE]

        # The 2026-08-10 probes: 0.35 s per request, the cheapest read in the roster.
        # Nothing on this route was measured refusing, so `burst` and
        # `cooldown_ms` keep the protocol's conservative defaults rather than a
        # ceiling nobody observed.
        self.assertEqual(budget.min_interval_ms, 350)
        self.assertEqual(budget.burst, adapters.DEFAULT_BURST)
        self.assertEqual(budget.cooldown_ms, adapters.DEFAULT_COOLDOWN_MS)

    def test_it_is_the_cheapest_read_the_roster_declares(self):
        budgets = runner.route_budgets()
        cheapest = min(budgets, key=lambda route_id: budgets[route_id].min_interval_ms)

        self.assertEqual(cheapest, transport.YOUTUBE_CHANNEL_FEED_ROUTE)

    def test_it_declares_no_rotating_identifier_because_it_depends_on_none(self):
        self.assertEqual(rss_atom.DESCRIPTOR.volatile_identifiers, ())

    def test_the_core_can_reach_it_by_both_of_its_literal_branches(self):
        clock = helpers.FakeClock()
        carrier, opener = helpers.offline_transport(
            clock,
            {
                transport.YOUTUBE_CHANNEL_FEED_ROUTE: (
                    200,
                    read_rss_atom("youtube_channel_feed.xml"),
                    "application/atom+xml",
                )
            },
        )

        self.assertIn("rss_atom", runner.ADAPTER_IDS)
        self.assertIs(runner.descriptor_for("rss_atom"), rss_atom.DESCRIPTOR)
        page = runner.call_adapter("rss_atom", carrier, syndication_request())

        self.assertEqual(len(page.records), 2)
        self.assertEqual(len(opener.opened), 1)

    def test_one_route_today_and_the_seam_a_second_feed_would_arrive_through(self):
        # A second measured feed is a second route constant and a second
        # descriptor under this same id, reachable through `surface_descriptors`
        # — not a second adapter and not a caller-supplied address.
        self.assertEqual(
            [descriptor.route_id for descriptor in runner.surface_descriptors("rss_atom")],
            [transport.YOUTUBE_CHANNEL_FEED_ROUTE],
        )

    def test_the_code_for_a_missing_credential_is_declared_and_never_produced(self):
        self.assertEqual(rss_atom.AUTH_REQUIRED, "auth_required")
        self.assertEqual(names_read(ADAPTER_DIR / "rss_atom.py", "AUTH_REQUIRED"), 0)


class RssAtomCaseTableTest(unittest.TestCase):
    """Every answer this route can give, typed as its own evidence names it."""

    def test_every_case_is_typed_as_its_evidence_says(self):
        for row in rss_atom_cases():
            with self.subTest(case=row["case_name"]):
                page, _ = rss_atom_page(row["body_fixture"], status=row["status"])

                self.assertEqual(page.outcome, row["expected_outcome"])
                self.assertEqual(
                    tuple(page.loss),
                    (row["expected_loss"],) if row["expected_loss"] else (),
                )
                self.assertNotIn(rss_atom.AUTH_REQUIRED, page.loss)

    def test_the_one_row_the_evidence_measured_is_marked_as_measured(self):
        measured = sorted(row["case_name"] for row in rss_atom_cases() if row["measured"])

        self.assertEqual(measured, ["an_atom_channel_feed"])
