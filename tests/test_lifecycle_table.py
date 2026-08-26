"""State/command table regressions for the sealed ticket lifecycle."""

import re
import unittest

from scripts import tickets_admission, tickets_format, tickets_transitions


BACKTICKED = re.compile(r"`([a-z][a-z-]*(?: [a-z-]+)?)`")


def commands_named(text: str) -> set:
    return {token for token in BACKTICKED.findall(text) if token in tickets_transitions.COMMANDS}


def chain_commands(status: str, command: str) -> set:
    path = tickets_transitions.remedy_path(status, command)
    if not path and not tickets_transitions.allows(status, command):
        return set()
    return commands_named(" ".join(path)) | {command}


class TransitionTableTest(unittest.TestCase):
    def test_status_and_command_vocabularies_are_closed(self):
        self.assertEqual(tuple(sorted(tickets_format.VALID_STATUSES)), tickets_transitions.STATUSES)
        for command in ("claim", "grant", "check", "recut", "set-status pending"):
            self.assertIn(command, tickets_transitions.COMMANDS)

    def test_claim_runs_only_at_the_admission_boundary(self):
        for status in tickets_transitions.STATUSES:
            self.assertEqual(status in ("pending", "ready"), tickets_transitions.allows(status, "claim"))

    def test_only_pending_releases_the_lease(self):
        self.assertEqual(tickets_transitions.LEASE_FIELDS, tickets_transitions.set_status_blanks("pending"))
        for target in ("suspended", *tickets_format.TERMINAL_STATES):
            self.assertEqual((), tickets_transitions.set_status_blanks(target))

    def test_refusals_name_only_commands_in_their_table_chain(self):
        for status in tickets_transitions.STATUSES:
            for command in tickets_transitions.COMMANDS:
                rendered = tickets_transitions.refusal("subject", command, status)
                self.assertEqual(chain_commands(status, command), commands_named(rendered), rendered)

    def test_sealed_assignments_never_offer_cut_mutation(self):
        for command in tickets_transitions.SEAL_REFUSED:
            path = " ".join(tickets_transitions.remedy_path("claimed", command, sealed=True))
            self.assertNotIn(f"`{command}`", path)
            self.assertEqual({"set-status suspended"}, commands_named(path))


class StampingTest(unittest.TestCase):
    def test_every_producer_stamps_the_one_pending_value(self):
        for name in ("stamp", "draft-validate"):
            entry = tickets_transitions.stamp(name)
            self.assertEqual(tickets_admission.ADMISSION_PENDING, entry.admission)

    def test_draft_validation_accepts_only_pre_execution_states(self):
        entry = tickets_transitions.stamp("draft-validate")
        self.assertEqual(("pending", "ready", "suspended"), entry.draft_statuses)
        self.assertNotIn(tickets_transitions.CLAIMED, entry.draft_statuses)


if __name__ == "__main__":
    unittest.main()
