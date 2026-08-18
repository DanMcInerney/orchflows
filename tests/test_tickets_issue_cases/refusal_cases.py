"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class RefusalTextTest(unittest.TestCase):
    """A refusal is read where it is printed. Windows consoles decode this
    script's stdout as cp1252, so a non-ASCII character in a refusal reaches
    its reader as mojibake in the one message that has to be understood."""

    def refusals(self) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(
                sink, "testrun", "P1",
                GOOD_TICKET.replace("id: T1", "id: P1").replace(
                    f"- {GOOD_CRITERION}", f"- {GOOD_CRITERION}\n- second | oracle: b"
                ),
            )
            directory = make_template(tmp, three_stubs())
            fat = tmp / "F1.md"
            fat.write_text(
                ceiling_ticket(tickets_mod.INSTRUCTION_BUDGET + 1, ticket_id="F1"),
                encoding="utf-8",
            )
            return [
                run_cmd("new", "testrun", "--file", str(fat)),
                run_cmd("new", "testrun", "T1", "--executor", "orch-verify",
                        "--objective", "o", "--criterion", "x"),
                run_cmd("new", "testrun", "T1", "--executor", "orch-verify",
                        "--objective", "o", "--criterion",
                        "x | oracle: y | oracle_class: mechanical"),
                run_cmd("new", "testrun", "T1", "--objective", "o"),
                run_cmd("new", "testrun", "T1", "--executor", "orch-verify",
                        "--objective", "o", "--criterion", GOOD_CRITERION,
                        "--isolation", "maybe"),
                run_cmd("instantiate", str(directory), "--run", "testrun"),
                run_cmd("instantiate", str(directory), "--run", "testrun",
                        "--set", "target"),
                run_cmd("packet", "testrun", "P1", "--reply-to", "main"),
            ]

    def test_every_refusal_this_path_emits_is_ascii(self):
        for payload in self.refusals():
            message = payload.get("error", "")
            with self.subTest(message[:48]):
                self.assertTrue(message, payload)
                message.encode("ascii")  # raises, and names the character
