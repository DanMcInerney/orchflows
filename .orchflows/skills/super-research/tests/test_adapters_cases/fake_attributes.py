from tests.test_adapters_cases.unrecognized_and_roster import *  # noqa: F401,F403

def fake_page(records, **declaration):
    """Run the offline adapter over one fixture payload written here."""

    payload = dict(declaration)
    payload["records"] = list(records)
    return adapter_page(fake, 200, json.dumps(payload), "application/json")[0]


class FakeReplaysNamedAttributesTest(unittest.TestCase):
    """The offline member replays a route's own vocabulary, or stands in for less.

    `attributes` is a family of `(name, value)` pairs — the shape `engagement`
    has, not the shape a flat field has — so the fixture adapter replays it the
    way it replays `engagement`. A name repeats when the payload repeated it
    and the order is the payload's, because repetition and order are exactly
    what two of the roster's rows carry and what a set or a mapping would eat.
    """

    def test_every_pair_a_payload_states_reaches_the_record_in_its_own_order(self):
        page = fake_page([
            {
                "canonical_content_kind": "profile",
                "canonical_locator": "https://example.test/in/avery",
                "attributes": [
                    ["jobTitle", "Principal Reliability Engineer"],
                    ["worksFor", "Northwind Analytics"],
                    ["jobTitle", "Board Advisor"],
                    ["addressLocality", "Gothenburg, Vastra Gotaland County, Sweden"],
                ],
            }
        ])

        # One tuple equality against the payload's own order is the whole
        # check: a dropped pair, an invented one, a reordering, a collapsed
        # repeat, and a list of lists left unconverted each fail it.
        self.assertEqual(
            page.records[0].attributes,
            (
                ("jobTitle", "Principal Reliability Engineer"),
                ("worksFor", "Northwind Analytics"),
                ("jobTitle", "Board Advisor"),
                ("addressLocality", "Gothenburg, Vastra Gotaland County, Sweden"),
            ),
        )

    def test_a_payload_stating_no_attribute_carries_an_empty_family(self):
        # Both spellings of nothing. Neither becomes a `None` every caller
        # would have to test for, and neither becomes a pair this adapter made.
        page = fake_page([
            {
                "canonical_content_kind": "post",
                "canonical_locator": "https://example.test/1",
            },
            {
                "canonical_content_kind": "post",
                "canonical_locator": "https://example.test/2",
                "attributes": [],
            },
        ])

        self.assertEqual([record.attributes for record in page.records], [(), ()])


def fixture_row_of(record):
    """One live record written back out as the fixture row that would replay it.

    Every field the fixture adapter reads, taken off a record a live adapter
    built from its own measured page. Nothing is composed here, so a replay
    that loses something shows up as a difference from the record the payload
    was written from rather than as a difference from a second transcription.
    """

    row = {name: getattr(record, name) for name in fake.RECORD_FIELDS}
    row["engagement"] = [[name, value] for name, value in record.engagement]
    row["attributes"] = [[name, value] for name, value in record.attributes]
    row["loss"] = list(record.loss)
    return row


def stand_in_for(page):
    """Replay one live adapter's whole page through the fixture adapter.

    The declaration is taken off the page being stood in for, because that is
    the one thing this adapter reads from its payload instead of from its own
    descriptor.
    """

    return fake_page(
        [fixture_row_of(record) for record in page.records],
        platform=page.platform,
        native_identity_namespace=page.native_identity_namespace,
        representation_kind=page.representation_kind,
    )


def probe_for(adapter_id):
    """The one smoke probe declared for this adapter."""

    return next(probe for probe in probes.SMOKE_PROBES if probe.adapter_id == adapter_id)


def declared_attribute_names(probe):
    """The names this roster row asks for under `attributes`, in the row's order."""

    return tuple(
        name[len(probes.ATTRIBUTE_PREFIX):]
        for _, names in probe.field_sets
        for name in names
        if name.startswith(probes.ATTRIBUTE_PREFIX)
    )


def roster_row_shortfall(page, probe):
    """What this probe's own roster row would find absent on this page's records."""

    step = schema.AcquisitionStep(step_id="s-stand-in", kind="hydration", adapter_id="fake")
    records = normalize.normalize_page(page, step, "artifact:stand-in", "m-stand-in")
    return smoke.field_set_report(records, probe.field_sets)[0]


class FakeStandsInForTheAttributedRoutesTest(unittest.TestCase):
    """The two roster rows that are named attributes almost entirely, replayed.

    `linkedin_public` and `public_page` each carry four of what their smoke
    asserts under `attributes` and nowhere else, so a stand-in that dropped the
    family would answer for those two rows with the row's own subject missing —
    and answer confidently, since every other field survived.

    Each row here replays a live adapter's own page and then asks the roster
    row itself, read off `probes.SMOKE_PROBES` rather than transcribed into the
    assertion, whether anything went missing. Two live records equal to two
    empty families would satisfy the equality alone; the shortfall is what
    forbids that, because an absent attribute is a shortfall.
    """

    def test_the_fixture_adapter_stands_in_for_linkedin_public(self):
        probe = probe_for("linkedin_public")
        lived, _ = profile_page("profile_person.html")

        replayed = stand_in_for(lived)

        self.assertEqual(
            declared_attribute_names(probe),
            ("jobTitle", "addressLocality", "worksFor", "alumniOf"),
        )
        self.assertEqual(replayed.platform, lived.platform)
        self.assertEqual(
            [record.attributes for record in replayed.records],
            [record.attributes for record in lived.records],
        )
        self.assertEqual(roster_row_shortfall(replayed, probe), ())

    def test_the_fixture_adapter_stands_in_for_public_page(self):
        probe = probe_for("public_page")
        lived, _ = selected_page("article.html")

        replayed = stand_in_for(lived)

        self.assertEqual(
            declared_attribute_names(probe),
            ("content_type", "link", "requested_url", "final_url"),
        )
        # This route states no platform on purpose, and an unstated one is what
        # the fixture adapter reads its own descriptor for, so the declaration
        # is not part of what is replayed here. The roster row is.
        self.assertEqual(
            [record.attributes for record in replayed.records],
            [record.attributes for record in lived.records],
        )
        self.assertEqual(roster_row_shortfall(replayed, probe), ())


if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
