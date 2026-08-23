"""The subcommand tables live in their own module, and dispatch reads them."""

from tests.test_tickets_issue_cases.common import *  # noqa: F401,F403

from scripts import tickets_commands, tickets_dispatch


class CommandTableTest(unittest.TestCase):
    def test_tables_are_owned_by_the_commands_module(self):
        for name in ("SUBCOMMAND_USAGE", "SUBCOMMAND_SUMMARY", "VALUE_FLAGS",
                     "HELP_FLAGS", "HELP_COMMANDS", "GATE_USAGE",
                     "INSTANTIATE_USAGE"):
            self.assertIs(
                getattr(tickets_dispatch, name), getattr(tickets_commands, name),
                f"{name} is dispatch's copy rather than the table module's",
            )

    def test_every_routed_subcommand_states_a_usage_and_a_summary(self):
        for name in ("new", "amend", "recut", "instantiate", "gate", "list",
                     "ready", "claim", "grant", "check", "set-status",
                     "result-grade", "packet", "result", "worklog",
                     "run-state", "improvement", "lint"):
            self.assertIn(name, tickets_commands.SUBCOMMAND_USAGE)
            self.assertIn(name, tickets_commands.SUBCOMMAND_SUMMARY)

    def test_the_new_payload_flags_are_value_flags(self):
        self.assertIn("--record-file", tickets_commands.VALUE_FLAGS)
        self.assertIn("--file", tickets_commands.VALUE_FLAGS)
