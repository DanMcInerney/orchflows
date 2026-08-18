"""Source-roster documentation and descriptor checks."""

import unittest

from super_research import runner
from super_research.adapters import youtube_innertube
from tests import test_keyless

from .source_roster_support import (
    CAPTION_WORDS,
    KEYLESS_NAMING_ANCHOR,
    KEYLESS_SAYING_ANCHOR,
    OPERATING_PATH,
    PROTOCOL_PATH,
    READ_SURFACE_ANCHOR,
    RESOLVER_COUNT_ANCHOR,
    ROSTER_SIZE_ANCHOR,
    SURFACE_TOTAL_ANCHOR,
    YOUTUBE,
    adapters_naming_the_refusal,
    backticked,
    counted_as,
    denied_in,
    live_adapters,
    multi_surface_adapters,
    multi_surface_counts_in,
    read_surface_total,
    resolver_chain_ids,
    roster_manifest,
    roster_table_rows,
    surface_total,
)

class RosterIsReadOffTheSourceTest(unittest.TestCase):
    """The roster's counted and enumerated claims, against `runner`'s own answer.

    `protocol.md` and `operating.md` both count the adapters reaching more
    than one route surface, and both said seven while the source said ten:
    `bluesky`, `x_guest` and `youtube_innertube` joined the roster with a
    second surface each and no one re-counted. This is the same lesson
    `LossVocabularyIsReadOffTheSourceTest` records one class up, so it gets
    the same treatment — the number stays in the prose, where a reader meets
    it, and the assertion runs against the prose.

    Two docstrings stated it too, and they were the last two: `roster_manifest`
    also said seven, and `surface_descriptors` counted four exceptions directly
    above the chain that answers for ten.

    Every one of them is anchored on the phrase its count cannot leave rather
    than on its sentence — the three that share a phrase on that phrase, the
    resolver on its own — because the four paragraphs are written in different
    voices and are meant to stay that way, and a sentence match would pin the
    voice along with the number.
    """

    def setUp(self):
        self.multi = multi_surface_adapters()
        self.rows = roster_table_rows()

    def youtube_row(self, column):
        # If the parse silently found nothing, a cell assertion would pass
        # against no table at all.
        self.assertEqual(set(self.rows), set(runner.ADAPTER_IDS))
        return self.rows[YOUTUBE][column]

    def passages_counting_the_multi_surface_adapters(self):
        """Every passage that counts them in the one phrase they share.

        Two reference documents and one docstring. `roster_manifest` says why
        its dispatch has more steps than the roster has adapters, and the
        number in that sentence is the same fact `protocol.md` states about the
        roster — kept beside the manifest, where its reader meets it, and
        reached here by importing the function rather than by reading the file
        it happens to sit in.
        """

        return (
            (PROTOCOL_PATH.name, PROTOCOL_PATH.read_text(encoding="utf-8")),
            (OPERATING_PATH.name, OPERATING_PATH.read_text(encoding="utf-8")),
            ("test_keyless.roster_manifest", roster_manifest.__doc__),
        )

    def test_every_document_and_docstring_states_one_count(self):
        # If the source ever gave every adapter one surface the claim would be
        # vacuous rather than wrong, so the reading is shown to be a reading.
        self.assertGreater(len(self.multi), 1)

        for name, text in self.passages_counting_the_multi_surface_adapters():
            with self.subTest(passage=name):
                stated = multi_surface_counts_in(text)
                self.assertEqual(
                    len(stated),
                    1,
                    "{0} states the multi-surface count {1} times".format(
                        name, len(stated)
                    ),
                )
                self.assertEqual(
                    stated[0],
                    len(self.multi),
                    "{0} says {1}; the descriptors say {2}: {3}".format(
                        name, stated[0], len(self.multi), sorted(self.multi)
                    ),
                )

    def test_the_resolver_docstring_counts_its_own_chain(self):
        """The exceptions `surface_descriptors` counts, against the branches beneath it.

        The one place this count is stated in the file it is about, and it was
        the furthest wrong: the docstring named four adapters and the chain
        immediately under it answered for ten. A count in prose beside a list
        is the cheapest thing in a repository to leave behind, and this one was
        beside the list it counts.
        """

        answered = resolver_chain_ids()

        # The chain is the subject, so it is shown to be the same set the
        # descriptors call multi-surface: a branch whose module declared one
        # surface would make the docstring's count true of nothing.
        self.assertEqual(sorted(answered), sorted(self.multi))

        stated = RESOLVER_COUNT_ANCHOR.findall(runner.surface_descriptors.__doc__)

        self.assertEqual(
            len(stated),
            1,
            "surface_descriptors states its exception count {0} times".format(len(stated)),
        )
        self.assertEqual(
            counted_as(stated[0]),
            len(answered),
            "surface_descriptors says {0}; its own chain answers for {1}: {2}".format(
                stated[0], len(answered), sorted(answered)
            ),
        )

    def test_the_roster_size_it_states_is_the_declared_ids_own(self):
        """Both halves of "Twenty adapters, nineteen live plus `fake`", off the source.

        The same sentence that said seven says these, and they were the two
        counts in it still resting on a reader.
        """

        stated = ROSTER_SIZE_ANCHOR.findall(PROTOCOL_PATH.read_text(encoding="utf-8"))

        self.assertEqual(len(stated), 1, "protocol.md states the roster size {0} times".format(len(stated)))
        counted, live = stated[0]
        self.assertEqual(
            counted_as(counted),
            len(runner.ADAPTER_IDS),
            "protocol.md says {0} adapters; the core declares {1}".format(
                counted, len(runner.ADAPTER_IDS)
            ),
        )
        self.assertEqual(
            counted_as(live),
            len(live_adapters()),
            "protocol.md says {0} live; the descriptors say {1}".format(
                live, sorted(live_adapters())
            ),
        )

    def test_every_statement_of_the_surface_total_is_checked(self):
        """Both statements of "thirty-six", and the count the second derives from it.

        The pin that landed here read the first and stopped: it holds on the
        words `route surfaces`, which the sentence two lines down does not
        spell, so the roster paragraph stated the total twice, derived a third
        count from it, and one of the three was checked. Add a read surface and
        the unchecked pair goes wrong with nothing failing — which is how
        "seven" survived three new adapters, surviving here inside the very
        paragraph the pin was raised to hold.

        Two anchors rather than one rewritten sentence, because the two
        sentences are written in different voices and pinning either to the
        other's phrasing would forbid the rewrite an anchor pin exists to
        permit.
        """

        text = PROTOCOL_PATH.read_text(encoding="utf-8")
        stated = SURFACE_TOTAL_ANCHOR.findall(text)
        read_stated = READ_SURFACE_ANCHOR.findall(text)

        # Distinct from the adapter count above and from the multi-surface count
        # below it — a surface total that merely equalled the roster size would
        # be a count of adapters wearing another name.
        self.assertGreater(surface_total(), len(runner.ADAPTER_IDS))
        self.assertEqual(len(stated), 1, "protocol.md states the surface total {0} times".format(len(stated)))
        self.assertEqual(
            counted_as(stated[0]),
            surface_total(),
            "protocol.md says {0} route surfaces; the descriptors say {1}".format(
                stated[0], surface_total()
            ),
        )

        self.assertEqual(
            len(read_stated),
            1,
            "protocol.md states the read-surface split {0} times".format(len(read_stated)),
        )
        read, total = read_stated[0]
        self.assertEqual(
            counted_as(total),
            surface_total(),
            "protocol.md's second statement says {0}; the descriptors say {1}".format(
                total, surface_total()
            ),
        )
        # The derived count is a count of something else, so a sentence that had
        # quietly restated the total under its name would fail rather than pass.
        self.assertLess(read_surface_total(), surface_total())
        self.assertEqual(
            counted_as(read),
            read_surface_total(),
            "protocol.md says {0} of them are read; the descriptors say {1}".format(
                read, read_surface_total()
            ),
        )

        # Both readers can fail, and the second on exactly the shape this test
        # was raised for: a paragraph whose second statement of the total no
        # longer spells the phrase. The first reader is blind to the move —
        # it still finds its one match and still agrees — which is the finding.
        moved = (
            "thirty-six route surfaces, because ten adapters reach more than"
            " one. Thirty-five of the thirty-six carry records"
        )
        self.assertEqual(len(SURFACE_TOTAL_ANCHOR.findall(moved)), 1)
        self.assertEqual(READ_SURFACE_ANCHOR.findall(moved), [])
        # The compound reader can fail rather than shrug: a name it cannot spell
        # answers None, which no count equals, so an unreadable number is a
        # failure here and never a pass.
        self.assertIsNone(counted_as("thirty-eleven"))

    def test_the_keyless_docstring_counts_the_modules_that_name_it(self):
        """`test_keyless`' counts of `auth_required`, off the scan the tables use.

        It said the string was one "which seven adapters and the router all
        know how to say". Five adapters can say it and nine name it, so the one
        number was wrong in both directions at once — and it went wrong the way
        the roster's "seven" did, with an adapter joining, a constant being
        declared, and the sentence beside them the only thing counting.

        Two counts because the sentence's subject needs both: a module that
        binds the name and loads it nowhere cannot say the word, and four of
        them are in the roster deliberately.
        """

        naming, saying, modules_saying = adapters_naming_the_refusal()

        # The two counts are counts of different things, and the scan is shown
        # to draw the line it claims to: a scan that read a declaration as an
        # emission would collapse them into one number and pass both anchors.
        self.assertLess(len(saying), len(naming))
        # The other half of the sentence, enumerated rather than counted,
        # because there is one of it.
        self.assertIn("router", modules_saying)

        for anchor, counted, subject in (
            (KEYLESS_NAMING_ANCHOR, naming, "name it"),
            (KEYLESS_SAYING_ANCHOR, saying, "can say it"),
        ):
            with self.subTest(subject=subject):
                stated = anchor.findall(test_keyless.__doc__)

                self.assertEqual(
                    len(stated),
                    1,
                    "the keyless docstring states the {0} count {1} times".format(
                        subject, len(stated)
                    ),
                )
                self.assertEqual(
                    counted_as(stated[0]),
                    len(counted),
                    "the keyless docstring says {0} {1}; the source says {2}: {3}".format(
                        stated[0], subject, len(counted), sorted(counted)
                    ),
                )

        # Both readers can fail on a count that stayed and a phrase that moved,
        # which is the one thing an anchor pin trades for the rewrite it permits.
        self.assertEqual(KEYLESS_NAMING_ANCHOR.findall("nine adapters name the code"), [])
        self.assertEqual(KEYLESS_SAYING_ANCHOR.findall("five of them say it"), [])

    def test_the_youtube_row_names_every_surface_it_reads(self):
        # The row said one surface while the adapter reads two, which is how a
        # transcript operation came to be described by a row that denied it.
        self.assertIn(YOUTUBE, self.multi)

        self.assertEqual(
            set(backticked(self.youtube_row("route surfaces"))),
            {
                descriptor.route_id
                for descriptor in runner.surface_descriptors(YOUTUBE)
            },
        )

    def test_the_youtube_row_names_every_operation(self):
        cell = self.youtube_row("what ships")
        named = set(backticked(cell))

        for operation in youtube_innertube.INNERTUBE_OPERATIONS:
            with self.subTest(operation=operation):
                self.assertIn(
                    operation,
                    named,
                    "the youtube row ships {0} and names {1}".format(
                        operation, sorted(named)
                    ),
                )

        # The scan can fail, and on the clause this row actually carried: the
        # operation was shipping while the cell beside it said otherwise.
        self.assertEqual(
            denied_in("`player` metadata. No captions", CAPTION_WORDS),
            ["No captions"],
        )
        self.assertEqual(denied_in(cell, CAPTION_WORDS), [])
