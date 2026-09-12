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


def attribute_names_of(page):
    """Every attribute name this page's records carry, first-seen order."""

    names = []
    for record in page.records:
        for name, _ in record.attributes:
            if name not in names:
                names.append(name)
    return tuple(names)




if __name__ == "__main__":  # pragma: no cover - convenience runner
    unittest.main()
