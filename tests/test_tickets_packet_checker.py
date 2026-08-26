"""`packet --executor orch-critique` refuses where verification §10 exempts.

An all-pre-existing completion test is itself one of that section's ordinary
independence paths, and exactly one path enters an item — so the checker
packet on such a ticket is a child dispatched against an exemption the cut
already took. orch-frontier has said so in prose since its first version
("For gate-deferred, already checked, or pre-existing-only tickets, never
emit it"); only the first two clauses had a refusal behind them.

Self-contained by write scope: the shared case chain under
`tests/test_tickets_cases/` is another item's to edit in this run, so the
ticket bodies and the sink fixture here are built from `common`'s primitives
alone rather than by extending that chain's fixtures.
"""

import tempfile
import unittest
from pathlib import Path

from scripts import tickets_packet, tickets_store
from tests.test_tickets_cases.common import run_cmd, run_full, use_sink

REFUSAL = "checker not required: every criterion carries provenance: pre-existing"

PRE_EXISTING_TICKET = """---
id: T1
run: testrun
status: claimed
executor: orch-tdd
pack: orch-code-pack
depends_on: []
isolation: required
write_scope: scratch/t1.txt
bound: 30m
claimed_by: agent-a
claimed_at: 2099-01-01T00:00:00Z
---

## Objective

Add `double(n)`.

## Fixed inputs

None.

## Completion test

- the existing suite stays green | oracle: `python -m unittest` | oracle_class: deterministic | provenance: pre-existing
- the change introduces no whitespace defect | oracle: `git diff --check` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status, changed_artifacts, verification.
"""

AUTHORED_HERE_TICKET = PRE_EXISTING_TICKET.replace(
    "`git diff --check` | oracle_class: deterministic | provenance: pre-existing",
    "`git diff --check` | oracle_class: deterministic | provenance: authored-here",
)
UNDECLARED_TICKET = PRE_EXISTING_TICKET.replace(" | provenance: pre-existing", "")
CHECKER_TICKET = PRE_EXISTING_TICKET.replace(
    "executor: orch-tdd", "executor: orch-tdd\nindependence: checker"
)
GATE_TICKET = PRE_EXISTING_TICKET.replace(
    "executor: orch-tdd", "executor: orch-tdd\nindependence: gate"
)
GATE_ROOT_TICKET = PRE_EXISTING_TICKET.replace(
    "executor: orch-tdd", "executor: orch-decompose\nindependence: gate"
)


def make_repo(tmp: Path, body: str) -> Path:
    """A checkout at ``tmp`` and one claimed ticket in this test's own sink."""

    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    path = run_dir / "T1.md"
    path.write_text(body, encoding="utf-8")
    return path


SUBTREE_TICKET = """---
id: T1.01
run: testrun
status: pending
executor: orch-tdd
pack: orch-code-pack
depends_on: []
isolation: required
write_scope: scratch/t101.txt
bound: 30m
---

## Objective

One unit of the cut, so a root's cut reader has an issued set to read.
"""

SCRIPT_TICKET = PRE_EXISTING_TICKET.replace(
    "executor: orch-tdd", "executor: script:tools/measure.py"
)

#: Every shape `packet` emits, as (label, ticket body, extra argv). A part
#: this ticket adds "to every packet" is worth exactly the shapes it
#: actually reaches, so the shapes are enumerated once and every case below
#: walks all of them rather than sampling the one it was written for.
PACKET_SHAPES = (
    ("primary skill executor", PRE_EXISTING_TICKET, ()),
    ("primary script executor", SCRIPT_TICKET, ()),
    ("checker", AUTHORED_HERE_TICKET, ("--executor", "orch-critique")),
    ("re-verifier", PRE_EXISTING_TICKET, ("--executor", "orch-verify")),
    ("root cut reader", GATE_ROOT_TICKET, ("--executor", "orch-critique")),
    ("root re-verifier", GATE_ROOT_TICKET, ("--executor", "orch-verify")),
)


def make_shape_repo(tmp: Path, body: str) -> Path:
    """``make_repo`` plus one pending subtree item.

    A root's cut reader is refused a packet until the run holds a `T1.`
    item, so the subtree ticket is written for every shape rather than for
    the two that need it: the fixtures here carry no admission receipt, so
    the sibling snapshot is never graded, and `_cut_subtree` is the only
    other reader of the run directory.
    """

    path = make_repo(tmp, body)
    (path.parent / "T1.01.md").write_text(SUBTREE_TICKET, encoding="utf-8")
    return path


#: The shapes whose packet grants the ticket's own write scope, and so the
#: ones a ceiling measurement is about. The re-verifiers are granted no
#: write at all, and a root's cut reader is granted `amend`/`new` over the
#: subtree rather than the root's workspace -- measuring a scope the child
#: may not touch would be a line it can only ignore.
SCOPE_BEARING_SHAPES = frozenset(
    {"primary skill executor", "primary script executor", "checker"}
)

CEILING_TOOL = "check_source_sizes.py"


def filing_lines(prompt: str) -> list:
    """Every emitted `result --section` line, found by its own tokens.

    By the tokens rather than by position: the same reading a child does,
    and the one `tests/test_tickets_cases/cli_help.py` does for the single
    shape it covers. Here it walks all six.
    """

    found = []
    for line in prompt.splitlines():
        tokens = line.split()
        if len(tokens) > 2 and Path(tokens[1]).name == "tickets.py" and tokens[2] == "result":
            found.append(line)
    return found


def measurement_lines(prompt: str) -> list:
    """Every emitted source-ceiling measurement line."""

    found = []
    for line in prompt.splitlines():
        tokens = line.split()
        if len(tokens) > 1 and Path(tokens[1]).name == CEILING_TOOL:
            found.append(line)
    return found


class TestEveryEmittedPacketFilesAndMeasuresByRunnableCommand(unittest.TestCase):
    """Proposal `2026-08-25-packets-carry-runnable-commands-not-command-prose`.

    The largest cluster in the harvest, ~25 entries: hand-composed commands
    losing a fight with this host's shell. Two faces survive the
    perfect-model test and are this class's subject.

    First, the filing line the packet already emits omitted `--append`,
    while the prose beside it said to add one -- so every write after a
    section's first was refused, and the refusal arrived a round trip later
    (T10:41:03Z, T19:09:33Z). `--append` is lawful on an empty section
    (`tickets_result` refuses only a *non*-append write onto content that is
    already there), so the flag is correct on the first write too and the
    template can simply carry it. The `--text` form keeps none: it is the
    one-line form, and a section's opening line is where it belongs.

    Second, a measurement relayed into a packet is a measurement that goes
    stale between the cut and the tip the child works at -- one coordinator
    relayed a line count as fact (T09:42:11Z) and this run's own cut relayed
    "398 of 510, headroom 112". The generator already parses the scope, so
    it emits the command that measures it instead, to be run at the child's
    own tip.
    """

    def emitted(self, tmp: Path, body: str, extra, *name):
        make_shape_repo(tmp, body)
        argv = ["packet", "testrun", "T1", "--reply-to", "main"]
        if name:
            argv += ["--by", name[0]]
        payload = run_cmd(tmp, *argv, *extra)
        self.assertNotIn("error", payload, payload)
        return payload["packet"]

    def test_the_file_filing_form_carries_append_on_every_shape(self):
        """The flag whose absence cost a round trip per section, on all six.

        Still exactly two filing forms: this adds a flag to one of them
        rather than a third line, so a reader still has one file form and
        one one-line form to choose between.
        """
        for label, body, extra in PACKET_SHAPES:
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmp:
                packet = self.emitted(Path(tmp), body, extra)
                lines = filing_lines(packet["prompt"])
                self.assertEqual(2, len(lines), packet["prompt"])
                file_line, text_line = lines
                self.assertEqual(
                    ["--section", "SECTION", "--file", "PATH", "--append"],
                    file_line.split()[5:],
                    file_line,
                )
                self.assertEqual(
                    ["--section", "SECTION", "--text", "TEXT"],
                    text_line.split()[5:],
                    text_line,
                )

    def test_the_file_form_is_named_the_primary_channel_and_multiline_is_refused(self):
        """The prose the child reads before choosing a form.

        The executor that lost five consecutive attempts did not know a
        file form existed until it found `--help`; naming it primary is
        what the proposal asks the CLI and the packet to agree on.
        """
        for label, body, extra in PACKET_SHAPES:
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmp:
                prompt = self.emitted(Path(tmp), body, extra)["prompt"]
                self.assertIn("--append", prompt)
                self.assertIn("primary", prompt)
                self.assertIn("multiline", prompt)

    def test_a_scope_bearing_shape_carries_the_ceiling_measurement_command(self):
        """The command stands where the number would have been, and names
        the scope the ticket actually granted."""
        for label, body, extra in PACKET_SHAPES:
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmp:
                packet = self.emitted(Path(tmp), body, extra)
                lines = measurement_lines(packet["prompt"])
                if label not in SCOPE_BEARING_SHAPES:
                    self.assertEqual([], lines, packet["prompt"])
                    continue
                self.assertEqual(1, len(lines), packet["prompt"])
                self.assertEqual("scratch/t1.txt", lines[0].split()[-1], lines[0])

    def test_a_shape_with_no_write_scope_measures_nothing(self):
        """A read-only lane has no scope to price, so no line is emitted --
        an empty measurement is a line that teaches the reader to skip."""
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.emitted(
                Path(tmp),
                PRE_EXISTING_TICKET.replace(
                    "write_scope: scratch/t1.txt", "write_scope: []"
                ),
                (),
            )
            self.assertEqual([], measurement_lines(packet["prompt"]))
            # the filing channel is not scope-conditional: it still files
            self.assertEqual(2, len(filing_lines(packet["prompt"])))

    def test_every_filing_and_measurement_line_is_argv_safe_on_every_shape(self):
        """One token per argument, no shell metacharacter, both programs
        absolute: the line is pasted, never composed."""
        for label, body, extra in PACKET_SHAPES:
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmp:
                prompt = self.emitted(Path(tmp), body, extra)["prompt"]
                lines = filing_lines(prompt) + measurement_lines(prompt)
                self.assertTrue(lines, prompt)
                for line in lines:
                    for forbidden in ("|", ">", "<", "&&", "$(", '"', "'", "`"):
                        self.assertNotIn(forbidden, line, line)
                    tokens = line.split()
                    self.assertTrue(Path(tokens[0]).is_absolute(), tokens[0])
                    self.assertTrue(Path(tokens[1]).is_absolute(), tokens[1])


class TestEveryEmittedPacketCarriesTheThreeDispatchParts(unittest.TestCase):
    """A fork holding a skill contract and nothing else has three questions.

    Five entries in one session, from the proposal this class delivers
    (`2026-08-24-skill-forks-arrive-without-packet-or-name`): three skill
    forks arrived with contract text and no packet, one checker fork
    recorded `check --by` under a name nobody dispatched
    (`checker-fable-01` against the dispatched `checker-opus-01`), which
    `checked_by`'s immutability then made uncorrectable, and one join
    re-armed a fork from notification memory. The packet is the one
    surface all three cross, so it answers all three questions on every
    shape it emits: what am I called, where does the ticket store live,
    and what do I do when I arrive holding none of this.
    """

    def emitted(self, tmp: Path, body: str, extra, *name):
        make_shape_repo(tmp, body)
        argv = ["packet", "testrun", "T1", "--reply-to", "main"]
        if name:
            argv += ["--by", name[0]]
        payload = run_cmd(tmp, *argv, *extra)
        self.assertNotIn("error", payload, payload)
        return payload["packet"]

    def test_every_shape_states_the_name_the_dispatch_assigned_the_child(self):
        """The `checker-fable-01` incident, at its one correctable point.

        `assigned_name` reached dispatching executors only, so the two §10
        children -- the ones that run `check --by` at all -- were handed
        the literal `NAME` and invented a filling for it.
        """
        for label, body, extra in PACKET_SHAPES:
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmp:
                packet = self.emitted(
                    Path(tmp), body, extra, "checker-opus-01",
                )
                self.assertEqual("checker-opus-01", packet["assigned_name"])
                # backticked: the fixture paths carry names as substrings
                self.assertIn("assigned name is `checker-opus-01`", packet["prompt"])

    def test_a_checker_is_told_to_record_under_that_name_not_under_NAME(self):
        """The assigned name reaches the invocation that spends it."""
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.emitted(
                Path(tmp), AUTHORED_HERE_TICKET,
                ("--executor", "orch-critique"), "checker-opus-01",
            )
            check = [
                line for line in packet["prompt"].splitlines()
                if " check " in line and "--by" in line
            ]
            self.assertEqual(1, len(check), packet["prompt"])
            self.assertTrue(check[0].endswith("--by checker-opus-01"), check[0])

    def test_every_shape_resolves_the_ticket_store_to_the_sink(self):
        """The 01:08:09Z fork searched a checkout's `.orch/` and found
        nothing; the sink it should have read is a resolved absolute path,
        so the packet prints that path rather than the rule alone."""
        for label, body, extra in PACKET_SHAPES:
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                make_shape_repo(tmp, body)
                argv = ["packet", "testrun", "T1", "--reply-to", "main"]
                packet = run_cmd(tmp, *argv, *extra)["packet"]
                prompt = packet["prompt"]
                self.assertIn("state_root.py", prompt)
                self.assertIn(".orch/", prompt)
                self.assertIn(str((tmp / "state-sink").resolve() / "tickets"), prompt)

    def test_every_shape_carries_the_refusal_channel_sentence(self):
        """A fork that arrives without the packet has one lawful move, and
        the packet it did not get is where the move is written -- so the
        sentence is what a *re-armed* fork reads before it acts."""
        for label, body, extra in PACKET_SHAPES:
            with self.subTest(shape=label), tempfile.TemporaryDirectory() as tmp:
                packet = self.emitted(Path(tmp), body, extra)
                for token in (
                    "without this packet",
                    "never to the coordinator",
                    "self-invented name",
                ):
                    self.assertIn(token, packet["prompt"], label)

    def test_a_primary_packet_with_no_name_falls_back_to_the_claim(self):
        """A claim is taken under a name, so an executor's is on the ticket."""
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.emitted(Path(tmp), PRE_EXISTING_TICKET, ())
            self.assertEqual("agent-a", packet["assigned_name"])
            self.assertIn("assigned name is `agent-a`", packet["prompt"])

    def test_a_further_child_with_no_name_is_forbidden_to_invent_one(self):
        """A checker's name is the dispatcher's, never the ticket's: the
        ticket's `claimed_by` is the *executor* whose result is under
        review. With no `--by` there is no name to state, and the one
        thing the packet must still rule out is the filling-in that
        produced `checker-fable-01`."""
        for executor in ("orch-critique", "orch-verify"):
            with self.subTest(executor=executor), tempfile.TemporaryDirectory() as tmp:
                packet = self.emitted(
                    Path(tmp), AUTHORED_HERE_TICKET, ("--executor", executor),
                )
                self.assertIsNone(packet["assigned_name"])
                self.assertNotIn("agent-a`", packet["prompt"])
                self.assertIn("assigned name", packet["prompt"])
                self.assertIn("under no name you invent", packet["prompt"])

    def test_the_usage_line_names_the_flag_that_supplies_the_name(self):
        """A channel a dispatcher cannot find is a channel nobody uses.

        `--by` rather than a new spelling: it is the flag `claim` and
        `check` already take for *the name an agent acts under*, it is
        already in `tickets_commands.VALUE_FLAGS`, and the name this
        supplies is the one the child spends on `check --by`.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_shape_repo(tmp, PRE_EXISTING_TICKET)
            payload = run_cmd(tmp, "packet", "testrun")
            self.assertIn("usage:", payload.get("error", ""), payload)
            self.assertIn("--by", payload["error"])


class TestCheckerNotDispatchedWhenSectionTenExempts(unittest.TestCase):
    """The refusal, and each direction it must not reach."""

    def packet(self, tmp: Path, *extra):
        return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main", *extra)

    def test_an_all_pre_existing_ticket_is_refused_the_checker_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = make_repo(tmp, PRE_EXISTING_TICKET)
            before = path.read_bytes()
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertIn(REFUSAL, payload.get("error", ""), payload)
            # the refusal names the rule, never only the condition
            self.assertIn("verification.md §10", payload["error"])
            self.assertNotIn("packet", payload)
            self.assertEqual(before, path.read_bytes())

    def test_the_refusal_is_a_non_zero_exit_across_the_process_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, PRE_EXISTING_TICKET)
            completed = run_full(
                tmp, "packet", "testrun", "T1", "--reply-to", "main",
                "--executor", "orch-critique",
            )
            self.assertNotEqual(0, completed.returncode, completed.stdout)
            self.assertIn(REFUSAL, completed.stdout)

    def test_an_explicit_independence_checker_is_refused_the_same_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, CHECKER_TICKET)
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertIn(REFUSAL, payload.get("error", ""), payload)

    def test_the_same_ticket_still_gets_its_own_executor_packet(self):
        """The exemption is of the further §10 child, never of the work."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, PRE_EXISTING_TICKET)
            packet = self.packet(tmp)["packet"]
            self.assertEqual("orch-tdd", packet["executor"])
            self.assertIn("Apply skill orch-tdd", packet["prompt"])

    def test_one_authored_here_criterion_still_issues_the_checker_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, AUTHORED_HERE_TICKET)
            packet = self.packet(tmp, "--executor", "orch-critique")["packet"]
            self.assertEqual("orch-critique", packet["executor"])
            self.assertIn("Apply skill orch-critique", packet["prompt"])

    def test_a_criterion_declaring_no_provenance_still_issues_it(self):
        """`provenance` is optional (contracts/work-item.md), and an absent
        one is not a claim that the oracle predates the item: the exemption
        is read off what the ticket carries, never off what it omits."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, UNDECLARED_TICKET)
            packet = self.packet(tmp, "--executor", "orch-critique")["packet"]
            self.assertEqual("orch-critique", packet["executor"])

    def test_the_re_verifier_packet_is_unchanged(self):
        """§10's other further child re-verifies a checked result; what
        exempts the checker says nothing about it."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, PRE_EXISTING_TICKET)
            packet = self.packet(tmp, "--executor", "orch-verify")["packet"]
            self.assertEqual("orch-verify", packet["executor"])

    def test_gate_deferred_behaviour_is_unchanged(self):
        """A gate-deferred ticket is refused for its own reason and with its
        own message, both further children alike."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, GATE_TICKET)
            for executor in ("orch-critique", "orch-verify"):
                with self.subTest(executor=executor):
                    payload = self.packet(tmp, "--executor", executor)
                    self.assertIn("downstream gate", payload.get("error", ""), payload)
                    self.assertNotIn(REFUSAL, payload["error"])

    def test_a_gate_root_still_reaches_its_cut_reader(self):
        """`independence` is the load-bearing half of the condition only on a
        root: `gate` is the one value that is not `checker`, and the branch
        above returns for every *non-root* ticket carrying it, so the case
        above passes whether the condition reads `independence` or not. The
        root is where it decides — contracts/work-item.md gives every root
        `independence: gate`, and the cut reader's lens is the issued subtree,
        never the root's own completion test, however that test is sourced."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, GATE_ROOT_TICKET)
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertNotIn(REFUSAL, payload.get("error", ""), payload)
            self.assertIn("subtree ticket yet", payload["error"])


class TestContentAudienceCarriage(unittest.TestCase):
    """A content section or terminal edit carries the root reader exactly."""

    ROOT = """---
id: 00-root
run: content-run
status: claimed
executor: orch-decompose
pack: orch-content-pack
depends_on: []
write_scope: [Introduction]
bound: 30m
root_generation: v2:root:00-root:1:sha256:{digest}
cut_generation: v2:cut:00-root:1:sha256:{digest}
ownership_regions: []
assignment_seal: sha256:{digest}
---

## Objective

Produce one document.

## Fixed inputs

- input: {{"name":"audience","type":"literal","value":"operators"}}

## Completion test

- the document works | oracle: review | oracle_class: judged | provenance: authored-here

## Return fields

status.
""".format(digest="0" * 64)

    ITEM = ROOT.replace("id: 00-root", "id: 00-root.01").replace(
        "executor: orch-decompose", "executor: orch-draft"
    ).replace("status: claimed", "status: claimed", 1)

    def defect(self, audience_line):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            root = run / "00-root.md"
            item = run / "00-root.01.md"
            root.write_text(self.ROOT, encoding="utf-8")
            item.write_text(
                self.ITEM.replace(
                    '- input: {"name":"audience","type":"literal","value":"operators"}',
                    audience_line,
                ),
                encoding="utf-8",
            )
            loaded = {"id": "00-root.01", "executor": "orch-draft", "pack": "orch-content-pack"}
            return tickets_packet._content_audience_defect(
                item, loaded, item.read_text(encoding="utf-8")
            )

    def test_a_matching_root_audience_is_carried(self):
        self.assertIsNone(
            self.defect('- input: {"name":"audience","type":"literal","value":"operators"}')
        )

    def test_a_missing_audience_is_refused(self):
        self.assertIn("missing", self.defect("None.") or "")

    def test_an_altered_audience_is_refused(self):
        self.assertIn(
            "does not match",
            self.defect('- input: {"name":"audience","type":"literal","value":"executives"}') or "",
        )

    def test_v2_content_gets_the_script_owned_workspace_path(self):
        self.assertTrue(
            tickets_store.establishes_a_workspace("orch-content-pack", v2=True)
        )
        self.assertFalse(
            tickets_store.establishes_a_workspace("orch-content-pack", v2=False)
        )


if __name__ == "__main__":
    unittest.main()
