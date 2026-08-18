"""Two social adapters, offline: Bluesky's AppView and X through FxTwitter.

Both read a public JSON surface and both have a way of failing that looks
exactly like having nothing to say, so most of this suite exists to keep those
apart.

The claim the Bluesky half defends is that a refusal about *who is asking* is
never an empty search. On this host, on 2026-08-17, ``searchPosts`` answered
403 with an HTML page from the CDN in front of the AppView while
``getAuthorFeed`` answered 200 on the same origin in the same minute. An
adapter that read that 403 as "no posts matched" would report a live platform
as silent, on a method that is documented keyless; one that read the *body*
rather than the status line would type an ordinary 400 the same way, because
both bodies say something about not being served. So the status line decides
and the body only speaks: the same bytes at 403 and at 400 are two different
answers, and that pair is asserted directly.

The claim the FxTwitter half defends is that a record which travelled through
an independent operator says so *on the record*. `third_party_archive` is the
descriptor's standing loss and it is asserted on every record of every page
this suite produces, not on the page — a caller holding one row cannot
correlate it back to a page to learn where it came from. Beside it sits this
origin's own oddity: it states a ``code`` inside a body it has already
answered 200 to, and a 404 there is an absence while anything else there is
the status the read got, one layer in. Neither is `schema_drift`, because the
envelope is exactly the shape this module declares and is being read
correctly.

Three smaller claims hold both halves up. Counts are the origin's own exact
integers under the origin's own names, so a ``null`` view count is absent
rather than zero and a ``bookmarkCount`` the module does not declare is
carried nowhere. A caller's window reaches Bluesky's search in that method's
own terms — ``since`` and ``until`` on the built address — and reaches the
author feed not at all, because that method takes no bound on time. And a
conversation's root is read once: the payload puts the root at the head of
its own ``thread`` as well as under ``status``, and an adapter reading both
would emit one status twice under one id.

Every test here runs offline against fixtures under ``fixtures/bluesky/`` and
``fixtures/x_fxtwitter/``, captured live from both origins on 2026-08-17.
"""

from __future__ import annotations

import unittest

from super_research.adapters._support import bluesky_extract, x_fxtwitter_records
from tests.test_social_adapters_cases.bluesky import *  # noqa: F401,F403
from tests.test_social_adapters_cases.x_fxtwitter import *  # noqa: F401,F403


class BothAdaptersRefuseToInventNumbersTest(unittest.TestCase):
    """Engagement admits only what the origin published as an exact integer."""

    def test_neither_module_reads_a_float_a_bool_or_a_formatted_string_as_a_count(self):
        for module in (bluesky_extract, x_fxtwitter_records):
            for value in (1.5, True, False, "21,068", "1.2K", None, [], {}):
                with self.subTest(module=module.__name__, value=value):
                    self.assertIsNone(module.exact_count(value))

    def test_a_json_integer_is_a_count_and_zero_is_one_too(self):
        for module in (bluesky_extract, x_fxtwitter_records):
            with self.subTest(module=module.__name__):
                self.assertEqual(module.exact_count(0), 0)
                self.assertEqual(module.exact_count(9487), 9487)


if __name__ == "__main__":
    unittest.main()
