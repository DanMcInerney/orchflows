"""Relevance: an auditable match, pinned to the four false positives the bakeoff reproduced.

The 2026-08-17 bakeoff reproduced, on real records, what a hand-written
alternation does: `valuation` matched inside `e-valuation`, `shares?` matched
the verb `share` in a LoRa thread, bare term lists matched "Just wanted to
share my DD on this" and "Analyst calls the top", and a ticker query matched
the *authors* `SPCECDET` and `spixy`. Every one of those is a case below, and
every one is answered by a match that names its terms and its field.
"""

from __future__ import annotations

import unittest

from super_research import relevance, schema


def record(record_id, title="", body="", author="", community=""):
    return schema.AcquisitionRecord(
        record_id=record_id,
        artifact_id="artifact:r",
        manifest_id="r",
        step_id="s",
        adapter_id="fake",
        adapter_version="1",
        route_id="fake_offline",
        access_class="offline",
        operator_identity="",
        platform="fixture",
        native_identity_namespace="fixture",
        group_scope="",
        representation_kind="native",
        canonical_content_kind="post",
        native_item_id=record_id,
        native_parent_id="",
        canonical_locator="https://example.net/" + record_id,
        normalized_locator="https://example.net/" + record_id,
        exact_content_hash="",
        title=title,
        body=body,
        author=author,
        community=community,
        published_at="",
        observed_at="",
        time_confidence="unknown",
        usable_basis_time="",
        engagement=(),
        page_index=0,
        list_index=0,
        native_position=0,
        discovery_locator="",
        outcome="ok",
        loss=(),
    )


class TokenizerAndStemmerTest(unittest.TestCase):
    def test_tokens_are_whole_words_split_at_every_non_alphanumeric(self):
        self.assertEqual(
            relevance.tokenize("SpaceX ($SPCX) is FALLING — post-IPO, 2Q'26!"),
            ("spacex", "spcx", "is", "falling", "post", "ipo", "2q", "26"),
        )

    def test_the_stemmer_meets_plurals_and_inflections_and_nothing_else(self):
        self.assertEqual(relevance.stem("shares"), "share")
        self.assertEqual(relevance.stem("share"), "share")
        self.assertEqual(relevance.stem("falling"), "fall")
        self.assertEqual(relevance.stem("earnings"), "earn")
        self.assertEqual(relevance.stem("earning"), "earn")
        self.assertEqual(relevance.stem("companies"), "company")
        self.assertEqual(relevance.stem("class"), "class")
        # The pair the bakeoff's alternation could not keep apart.
        self.assertNotEqual(relevance.stem("valuation"), relevance.stem("evaluation"))
        self.assertEqual(relevance.stem("valuation"), "valuation")

    def test_a_query_compiles_to_terms_and_quoted_phrases(self):
        query = relevance.compile_query('SPCX "short squeeze" the lockup shares')

        self.assertEqual(query.terms, ("spcx", "short", "squeeze", "lockup", "share"))
        self.assertEqual(query.phrases, (("short", "squeeze"),))

    def test_a_query_of_stopwords_is_refused(self):
        with self.assertRaises(relevance.RelevanceError):
            relevance.compile_query("the of and")


class BakeoffFalsePositivesTest(unittest.TestCase):
    """The four reproduced false positives, each now a non-match or a named match."""

    def test_valuation_does_not_match_inside_e_valuation(self):
        query = relevance.compile_query("valuation")
        cable = record("cable", title="Re-evaluation of the thermal model for USB-C impedance")

        found = relevance.match(cable, query)

        self.assertEqual(found.score, 0.0)
        self.assertEqual(found.matched_terms, ())

    def test_shares_matches_the_verb_share_and_says_so_by_name(self):
        # Lexically the two are one stem, and no lexical rule can tell a
        # shared post from a share of stock. What the module owes the caller
        # is the name of the term that matched, so a reader can see it.
        query = relevance.compile_query("SPCX shares")
        lora = record("lora", body="Just wanted to share my LoRa mesh setup")

        found = relevance.match(lora, query)

        self.assertEqual(found.matched_terms, ("share",))
        self.assertEqual(found.fields, (("share", "body"),))
        # Half the terms, so half the score — and the ticker is the half that
        # did not match, which the audit says in so many words.
        self.assertEqual(found.score, 0.5)
        self.assertNotIn("spcx", found.matched_terms)

    def test_a_bare_term_list_no_longer_matches_unbounded(self):
        query = relevance.compile_query('"SpaceX stock" lockup squeeze')
        for text in ("Just wanted to share my DD on this", "Analyst calls the top",
                     "Musk puts pressure on suppliers"):
            with self.subTest(text=text):
                self.assertEqual(relevance.match(record("x", body=text), query).score, 0.0)

    def test_a_ticker_matching_an_author_is_a_field_the_audit_names(self):
        query = relevance.compile_query("SPCX")
        by_author = record("a", body="Nothing about the topic here", author="SPCECDET")
        by_body = record("b", body="Bought more $SPCX today", author="spixy")

        self.assertEqual(relevance.match(by_author, query).score, 0.0)
        with_author = relevance.match(by_author, query, fields=("title", "body", "author"))
        self.assertEqual(with_author.matched_terms, ())
        self.assertEqual(relevance.match(by_body, query).fields, (("spcx", "body"),))
        self.assertEqual(
            relevance.matched_field_counts([relevance.match(by_body, query)]), {"body": 1}
        )


class ScoreTest(unittest.TestCase):
    def test_full_term_and_phrase_coverage_is_one(self):
        query = relevance.compile_query('SPCX "short squeeze"')
        found = relevance.match(record("x", title="SPCX short squeeze incoming?"), query)

        self.assertEqual(found.score, 1.0)
        self.assertEqual(found.matched_phrases, (("short", "squeeze"),))

    def test_words_out_of_order_earn_terms_and_not_the_phrase(self):
        query = relevance.compile_query('"short squeeze"')
        found = relevance.match(record("x", title="A squeeze on the short side"), query)

        self.assertEqual(found.matched_terms, ("short", "squeeze"))
        self.assertEqual(found.matched_phrases, ())
        self.assertEqual(found.score, relevance.TERM_WEIGHT)

    def test_a_plain_query_takes_term_coverage_for_the_whole_score(self):
        query = relevance.compile_query("spacex lockup earnings")
        found = relevance.match(record("x", body="SpaceX earnings call"), query)

        self.assertAlmostEqual(found.score, 2.0 / 3.0, places=5)

    def test_the_title_is_read_before_the_body_and_named(self):
        query = relevance.compile_query("lockup")
        found = relevance.match(record("x", title="Lockup expiry", body="the lockup"), query)

        self.assertEqual(found.fields, (("lockup", "title"),))

    def test_an_unknown_field_is_refused(self):
        with self.assertRaises(relevance.RelevanceError):
            relevance.match(record("x"), relevance.compile_query("a b"), fields=("engagement",))


class RankAndPartitionTest(unittest.TestCase):
    def setUp(self):
        self.query = relevance.compile_query("SPCX lockup")
        self.records = [
            record("both", title="SPCX lockup ends Thursday"),
            record("one", body="Thoughts on the SPCX dip"),
            record("none", body="AMD earnings beat"),
            record("also_one", body="lockup calendar for the year"),
        ]

    def test_rank_puts_the_best_first_and_breaks_ties_by_id(self):
        ranked = relevance.rank(self.records, self.query)

        self.assertEqual([found.record_id for found in ranked], ["both", "also_one", "one", "none"])

    def test_partition_lists_every_drop_with_its_evidence(self):
        kept, dropped = relevance.partition(self.records, self.query, floor=0.5)

        self.assertEqual([found.record_id for found in kept], ["both", "also_one", "one"])
        self.assertEqual([found.record_id for found in dropped], ["none"])
        self.assertEqual(relevance.audit_lines(dropped), ("none score=0.000 terms=- phrases=-",))

    def test_a_floor_outside_the_unit_interval_is_refused(self):
        with self.assertRaises(relevance.RelevanceError):
            relevance.partition(self.records, self.query, floor=1.5)

    def test_engagement_never_enters_a_score(self):
        # The same text scores the same whatever counts ride on the record;
        # weighting by engagement is the calling lane's decision, made in the
        # open, and never this module's.
        plain = record("p", title="SPCX lockup")
        counted = schema.AcquisitionRecord(
            **dict(
                plain.__dict__,
                record_id="c",
                engagement=(schema.EngagementSnapshot("score", 1265, "2026-08-17T12:00:00Z"),),
            )
        )
        self.assertEqual(
            relevance.match(plain, self.query).score, relevance.match(counted, self.query).score
        )


if __name__ == "__main__":
    unittest.main()
