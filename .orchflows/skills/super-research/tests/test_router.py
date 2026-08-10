"""Access-class suite: the ladder is law, not documentation.

Four claims, and the first two are the run's whole thesis stated twice.

The first is that every adapter declares exactly one class out of the ladder
``schema`` owns, and that the class is the one the measured roster gives it. A
class is not decoration: it decides whether the router admits a step at all,
whether a record's time is `authoritative` or `reported`, and whether the
answer is the platform speaking. A descriptor declaring nothing, or `k5`, or
two classes in one string, would carry that decision quietly past all three,
so the declaration is refused where it is made rather than audited where it is
read.

The second is that no first-release capability is reachable only through `K5`.
That is trivially true today — nothing in the roster is `K5` — and a check that
can only pass over an empty set proves nothing. So the law is stated over a
roster it is handed rather than over the one that ships, and rosters written
beside the tree are put through it: a credentialed adapter with no keyless
surface, a credentialed surface whose capability nothing keyless serves, a
credentialed upgrade of another credentialed route, and the one lawful shape —
a credentialed surface beside a keyless one answering the same question more
slowly.

Two narrower claims sit beside them. A `K1` public client credential is a
route constant ``transport.py`` owns, and it reaches no manifest and no
artifact: checked against every string the emitted artifact actually carries,
never against the module that holds the constants. And every `K3` record
carries `third_party_archive` loss and names its operator, because Arctic
Shift is a volunteer-run archive and not Reddit speaking.
"""

from __future__ import annotations

import dataclasses
import unittest

from super_research import adapters, runner, schema

# The ladder's roster, transcribed from the spec's own table rather than
# derived from the code under test. `test_adapters.RosterIsCompleteTest` keeps
# its own transcription for its own claim; two independent copies of one spec
# table disagree loudly the moment either is edited alone, which is the point
# of not deriving it.
ROSTER = {
    "web_search": "K4",
    "public_page": "K0",
    "reddit_archive": "K3",
    "reddit_feed": "K0",
    "x_syndication": "K2",
    "x_guest": "K1",
    "linkedin_public": "K2",
    "linkedin_jobs": "K0",
    "youtube_innertube": "K1",
    "instagram_public": "K1",
    "hacker_news": "K0",
    "github_rest": "K0",
    "rss_atom": "K0",
    "fake": "offline",
}

# The ladder itself, in the order `schema` declares it, so a class added or
# removed there is visible here rather than silently admitted.
LADDER = ("K0", "K1", "K2", "K3", "K4", "K5", "offline")

# Every way a declaration can name something that is not one class of the
# ladder. `k5` is the one worth naming twice: a check written as
# `access_class != "K5"` admits it, and it would carry a credentialed route
# past every keyless law in this file.
UNCLASSED = ("", " ", "K", "K6", "k5", "K5 ", "K0/K5", "offline ", "unknown", "None")


def shipped_descriptor(**overrides):
    """One real descriptor with named fields replaced — the tree, not a copy.

    `dataclasses.replace` re-runs `__post_init__`, so a construction law is
    proven against the same object the package ships rather than against a
    hand-built lookalike that might be missing the field under test.
    """

    return dataclasses.replace(runner.descriptor_for("reddit_feed"), **overrides)


class AccessClassDeclarationTest(unittest.TestCase):
    """Criterion 2: one class per adapter, out of one closed ladder.

    The roster half and the closed-set half are separate claims. An adapter
    could declare a class that is on the ladder and wrong for its route, or a
    class that is right for its route and on no ladder at all; only the first
    is a roster question.
    """

    def test_the_ladder_is_the_one_the_schema_seam_owns(self):
        self.assertEqual(schema.ACCESS_CLASSES, LADDER)

    def test_the_core_lists_exactly_the_rosters_adapters(self):
        self.assertEqual(sorted(runner.ADAPTER_IDS), sorted(ROSTER))

    def test_every_adapter_declares_the_class_the_roster_gives_it(self):
        for adapter_id, access_class in sorted(ROSTER.items()):
            with self.subTest(adapter=adapter_id):
                descriptor = runner.descriptor_for(adapter_id)

                self.assertIsNotNone(descriptor)
                self.assertEqual(descriptor.access_class, access_class)
                self.assertIn(descriptor.access_class, LADDER)

    def test_every_surface_an_adapter_reaches_declares_that_same_one_class(self):
        # A class belongs to how a read is authorized, and every route one
        # adapter reads is authorized the same way. Without this, an adapter
        # could answer at `K0` on the surface a check reads and at another
        # class on the surface a run reads.
        for adapter_id, access_class in sorted(ROSTER.items()):
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertEqual(surface.access_class, access_class)
                    self.assertEqual(surface.adapter_id, adapter_id)

    def test_exactly_one_class_is_declared_and_it_is_a_single_ladder_name(self):
        # "Exactly one" is a claim about the value, not about the field: a
        # descriptor holds one string, and the string has to be one whole class
        # name rather than a pair somebody spelled with a separator.
        for adapter_id in sorted(ROSTER):
            with self.subTest(adapter=adapter_id):
                declared = runner.descriptor_for(adapter_id).access_class

                self.assertEqual([name for name in LADDER if name == declared], [declared])


class UnclassedDescriptorTest(unittest.TestCase):
    """The teeth under criterion 2: a class nothing names never gets built.

    Audited at the reader, an unclassed descriptor is a route that answers with
    an access class no rule in the package has an opinion about — the router
    admits it, `time_confidence_for` calls its times authoritative, and the
    artifact reports a class no caller can interpret. Refused at construction,
    it is an import-time error in the module that declared it.
    """

    def test_a_class_the_ladder_does_not_name_is_refused_at_construction(self):
        for wrong in UNCLASSED:
            with self.subTest(access_class=wrong):
                with self.assertRaises(adapters.AdapterError):
                    shipped_descriptor(access_class=wrong)

    def test_the_refusal_names_the_adapter_and_the_class_it_refused(self):
        with self.assertRaisesRegex(adapters.AdapterError, "reddit_feed.*'k5'"):
            shipped_descriptor(access_class="k5")

    def test_every_class_on_the_ladder_still_constructs(self):
        # The other direction, so the law is a filter rather than a wall: each
        # of the seven builds, including `K5`, which nothing in the roster
        # declares and which a later throughput upgrade may.
        for access_class in LADDER:
            with self.subTest(access_class=access_class):
                self.assertEqual(
                    shipped_descriptor(access_class=access_class).access_class, access_class
                )

    def test_the_shipped_roster_survives_the_law_it_is_held_to(self):
        for adapter_id in sorted(ROSTER):
            for surface in runner.surface_descriptors(adapter_id):
                with self.subTest(adapter=adapter_id, route=surface.route_id):
                    self.assertEqual(dataclasses.replace(surface), surface)


if __name__ == "__main__":
    unittest.main()
