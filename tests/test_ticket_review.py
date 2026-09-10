"""Direct judging and repair remain usable without a default review policy."""
from __future__ import annotations

import json
import sys
from unittest import mock

from scripts import tickets_done, tickets_mint
from scripts.tickets_format import _parse_frontmatter, _set_frontmatter_field
from tests import test_ticket_callables as callables
from tests.test_ticket_callables import CallableSinkTest, CODE_STANDARD


class DirectReviewTest(CallableSinkTest):
    def owner(self, *args):
        return self.callable("frame-open", "--shape", "do > judge", *args)["frame_open"]["id"]

    def judge(self, parent=None, *args):
        return self.callable("judge", "--standard", CODE_STANDARD,
                             "--artifacts", "git:" + "a" * 40,
                             *(("--parent", parent) if parent else ()), *args)

    def finish_fixture(self, ticket_id):
        # These cases exercise admission; lifecycle writes preserve sealed fields.
        path = self.run_dir() / (ticket_id + ".md")
        path.write_text(_set_frontmatter_field(self.ticket_text(ticket_id),
                                              "status", "complete"), encoding="utf-8")

    def test_repeated_direct_judges_keep_pins_without_policy_fields(self):
        owner = self.owner()
        rows = []
        for _ in range(3):
            judge = self.judge(owner)["judge"]["id"]
            rows.append(_parse_frontmatter(self.ticket_text(judge)))
            self.finish_fixture(judge)
        self.assertEqual(1, len({str(row["standards"]) for row in rows}))
        self.assertFalse(any(key.startswith("review_") for row in rows for key in row))
        self.assertFalse(any(key.startswith("review_")
                             for key in _parse_frontmatter(self.ticket_text(owner))))

    def test_known_blocker_can_be_repaired_after_verification(self):
        owner = self.owner()
        first = self.judge(owner)["judge"]["id"]
        self.finish_fixture(first)
        for _ in range(2):
            repair = self.callable("do", "--parent", owner,
                                   "--standard", CODE_STANDARD)["do"]["id"]
            self.finish_fixture(repair)
            verification = self.judge(owner)["judge"]["id"]
            self.finish_fixture(verification)
        nested = self.owner("--parent", repair)
        self.assertIn("judge", self.judge(nested))

    def test_historical_review_phase_does_not_force_failed_done_closed(self):
        owner = self.owner()
        predicate = json.dumps({"form": "command", "value":
                                f'"{sys.executable}" -c "raise SystemExit(7)"'})
        mint = tickets_mint._mint
        def historical(run, run_dir, parent, fields, sections):
            # Reproduce the carried fields of an old ticket before it is sealed.
            fields = dict(fields, review_phase="repair", review_of="historical-critique",
                          review_owner=owner, review_rounds="1")
            return mint(run, run_dir, parent, fields, sections)
        with mock.patch.object(tickets_mint, "_mint", side_effect=historical):
            repair = self.callable("do", "--parent", owner, "--standard", CODE_STANDARD,
                                   "--done", predicate)["do"]["id"]
        self.assertEqual(set(), callables.CallableAdmissionTest._codes(self, repair))
        data = _parse_frontmatter(self.ticket_text(repair))
        # An old sealed review phase is provenance, not a surviving loop manager.
        decision, failure = tickets_done.resolve(
            self.RUN, repair, self.run_dir(), self.run_dir() / (repair + ".md"),
            data, self.candidate, None, repair)
        self.assertIsNone(failure)
        self.assertEqual(("arm", 7), (decision["action"], decision["reading"]["exit"]))
        self.assertTrue((self.run_dir() / (decision["repair"] + ".md")).is_file())
        path = self.run_dir() / (repair + ".md")
        path.write_text(_set_frontmatter_field(self.ticket_text(repair),
                                              "review_rounds", "2"), encoding="utf-8")
        self.assertIn("sealed-assignment-mismatch", callables.CallableAdmissionTest._codes(self, repair))

    def test_retired_review_flags_refuse_without_issuing_work(self):
        failure = self.callable("frame-open", "--shape", "do > judge",
                                "--review-rounds", "1", expect_error=True)
        self.assertIn("does not accept --review-rounds", failure["error"])
        self.assertEqual([], list(self.run_dir().glob("*.md")))
